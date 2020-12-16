#!/usr/bin/env python3

import logging, re, os, yaml
from k8s import K8s
from vault import Vault
from utils import create_vault_cert
from argsparsing import ArgsParsing

def fill_params(arguments):
  if arguments['details'] != '':
    if arguments['base_path'] == None:
      arguments['base_path'] = f"{ os.path.dirname(arguments['details']) }/vault"

    with open(arguments['details'], 'r') as f:
      arguments['details'] = yaml.safe_load(f.read())

  if arguments['vault_token'] == None:
    try:
      with open('/vault/secrets/token', 'r') as f:
        arguments['vault_token'] = yaml.safe_load(f.read())
    except:
      print("No vault token loaded!")

  if arguments['k_ca'] == None:
    arguments['k_ca'] = '/var/run/secrets/kubernetes.io/serviceaccount/ca.crt'

  if arguments['k_token'] == None:
    arguments['k_token'] = '/var/run/secrets/kubernetes.io/serviceaccount/token'

  if arguments['k_address'] == None:
    arguments['k_address'] = f"https://{ os.environ['KUBERNETES_PORT_443_TCP_ADDR'] }"

  return arguments

def _action_setup(vault, k8s, args):
  logging.info("Creating clients...")

  with open(args['config'], 'r') as f:
    init_conf = yaml.safe_load(f.read())

  token, keys = vault.initialize_vault(init_conf['init']['shares'], init_conf['init']['threshold'])

  if token != None:
    logging.info("INIT RESULT:")
    logging.info(token)
    for k in keys:
      logging.info(k)

    logging.info("Creating secret with keys...")
    k8s.create_secret(
      'vault',
      args['details']['namespace'],
      {
        'root_key': token,
        'keys': ','.join(keys)
      }
    )

    vault.set_token(token)
    with open('/tmp/token', 'w') as f:
      f.write(token)

    logging.info("Unsealing...")
    vault.unseal(keys[0:int(len(keys)/2+1)])
    logging.info("Enable k8s auth...")

    def_engine = { 'description': '', 'options': {}, 'config': {}, 'max_versions': 10 }
    for engine in init_conf['engines']:
      tmp = def_engine.copy()
      tmp.update(engine)
      engine = tmp

      if engine['type'] == 'kubernetes':
        with open(args['k_ca'], 'r') as f:
          args['k_ca'] = f.read()

        with open(args['k_token'], 'r') as f:
          args['k_token'] = f.read()
      
        vault.enable_kubernetes_auth(args['k_address'], args['k_token'], args['k_ca'])
      elif engine['type'] == 'userpass':
        vault.enable_userpass_auth(engine['mount_path'])
      elif engine['type'] == 'pki':
        vault.enable_pki_engine(engine['mount_path'], engine['description'], engine['options'], engine['config'])
      elif engine['type'] == 'kv':
        vault.enable_secrets_engine(engine['mount_path'], engine['description'], engine['options'], engine['max_versions'])
  else:
    with open(os.environ['VAULT_TOKEN']) as f:
      token = f.read()

    vault.set_token(token)


# def _action_unseal_vault(vault, args):
#   conf = load_config()

#   keys = os.environ['VAULT_KEYS'].split(',')
#   vault.unseal(keys[0:int(len(keys)/2+1)])


def _action_create_vault_cert(k8s, args):
  target = args['secret'] if args['secret'] else 'vault-tls'

  # Try to determine replicas
  if 'valuesFile' in args['details']:
    try:
      with open(args['details']['valuesFile'], 'r') as f: # open values file for vault
        replicas = int(yaml.safe_load(f.read())['server']['ha']['replicas'])
    except Exception:
      replicas = 1
  else:
    replicas = 1

  logging.info("Create csr key and spec...")
  key, cert, ca = create_vault_cert(
    args['common_name'],
    args['details']['namespace'],
    args['sign_ca'],
    args['sign_ca_key'],
    replicas,
    'server'
  )

  k8s.create_secret(
    target,
    args['details']['namespace'],
    {
      'vault.crt': cert,
      'vault.key': key,
      'vault.ca': ca
    }
  )
  logging.info("Finished.")

def _get_vault_client(args):
  if args['vault_address'].startswith('https'):
    scheme = 'https'
    address = re.sub('https://', '', args['vault_address'])
  else:
    scheme = 'http'
    address = re.sub('http://', '', args['vault_address'])

  return Vault(scheme, address, args['vault_token'], args['v_ca'])

def main():
  parser = ArgsParsing()

  args = fill_params(parser.parse())

  if args['action'] == 'certificate':
    k8s = K8s(args['k_address'], args['k_token'], args['k_ca'])
    _action_create_vault_cert(k8s, args)
  elif args['action'] == 'setup':
    k8s = K8s(args['k_address'], args['k_token'], args['k_ca'])
    vault = _get_vault_client(args)
    _action_setup(vault, k8s, args)
  # elif args['action'] == 'unseal':
  #   _action_unseal_vault(vault, args)
  elif args['action'] == 'process':
    vault = _get_vault_client(args)
    _action_process_build(
      vault,
      args['base_path'],
      args['details']['vault']['policies'],
      args['details']['vault']['roles'],
      args['details']['vault']['secrets']
    )

def _action_process_build(vault, base_path: str, policies = [], roles = [], secrets = []):
  for pol in policies:
    vault.create_policy(pol, f"{ base_path }/{ pol }.hcl")
  
  for role in roles:
    vault.create_kubernetes_role(role['name'], role['sa'], role['namespaces'], role['policies'])

  for secret in secrets:
    spl_path = secret['path'].split('/')
    vault.create_secret_if_not_exists(
      '/'.join(spl_path[1:]),
      mount_point=spl_path[0],
      values=secret['values'],
      force=secret['force'] if 'force' in secret else False
    )

if __name__ == "__main__":
  main()