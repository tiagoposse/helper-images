#!/usr/bin/env python3

import logging, os, re, subprocess, sys, yaml
from k8s import execute_kubectl, execute_helm
from vault import Vault
from argsparsing import ArgsParsing

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

def fill_params(arguments):
  if arguments['details'] != None:
    arguments['_base_path'] = f"{ os.path.dirname(arguments['details']) }"

    with open(arguments['details'], 'r') as f:
      arguments['details'] = yaml.safe_load(f.read())

  if arguments['vault_token'] == None:
    try:
      with open('/vault/secrets/token', 'r') as f:
        arguments['vault_token'] = yaml.safe_load(f.read())
    except:
      pass

  return arguments

def process_hook(args, hook, vault):
  if hook['operation'] in ['apply', 'remove']:
    cmd = [ hook['operation'] ]
    if hook['operation'] == 'apply':
      if not hook['resource'].startswith('http') and not hook['resource'].startswith(args['_base_path']):
        cmd += [ '-f', f"{ args['_base_path'] }/{ hook['resource'] }" ]
      else:
        cmd += [ '-f', hook['resource'] ]
    else:
      cmd.append(hook['resource'])

    execute_kubectl(cmd)

  elif hook['operation'] == 'vault':
    vault.process_deployment_vault(args['details']['vault'], args['_base_path'], args['dry_run'])

def upgrade_deployment(vault, args):
  process = {
    'pre': 'hooks' in args['details'] and 'preInstall' in args['details']['hooks'] and (not args['hooks'] or args['hooks'] in ["only", "only-pre", "pre"]),
    'post': 'hooks' in args['details'] and 'postInstall' in args['details']['hooks'] and (not args['hooks'] or args['hooks'] in ["only", "only-post", "post"]),
    'helm': 'releases' in args['details'] and (not args['hooks'] or args['hooks'].startswith("only"))
  }

  wait = args['wait'] or (args['action'] == 'upgrade' and process['post'])

  if process['pre']:
    print('Execute preInstall hooks')
    try:
      resp = execute_kubectl(f"create namespace { args['details']['namespace'] }".split(' '))
      print(resp)
    except subprocess.CalledProcessError as e:
      if e.stderr == f"Error from server (AlreadyExists): namespaces \"{ args['details']['namespace'] }\" already exists":
        pass

    for hook in args['details']['hooks']['preInstall']:
      process_hook(args, hook, vault)

  if process['helm']:
    for release in args['details']['releases']:
      execute_helm(
        args['action'],
        release['namespace'] if 'namespace' in release else args['details']['namespace'],
        release['name'],
        release['chart'],
        release['version'],
        f"{ args['_base_path'] }/{release['valuesFile'] }" if 'valuesFile' in release else '',
        release['url'] if 'url' in release else '',
        wait,
        'insecure' not in release or release['insecure']
      )

  if process['post']:
    print('Execute postInstall hooks')
    for hook in args['details']['hooks']['postInstall']:
      process_hook(args, hook, vault)


def _get_vault_client(args):
  if args['vault_address'].startswith('https'):
    scheme = 'https'
    address = re.sub('https://', '', args['vault_address'])
  else:
    scheme = 'http'
    address = re.sub('http://', '', args['vault_address'])

  return Vault(scheme, address, args['vault_token'], args['v_ca'], args['insecure_vault'])

def main():
  parser = ArgsParsing()

  args = fill_params(parser.parse())
  
  print("Action: " + args['action'])
  if args['action'] == 'vault_setup':
    if not parser.validate_args(args, ['vault_address', 'config']):
      exit(1)

    vault = _get_vault_client(args)
    vault.setup_vault(args)
  elif args['action'] == 'vault_process':
    vault = _get_vault_client(args)
    vault.process_deployment_vault(
      args['details']['vault'],
      args['_base_path'],
      args['dry_run']
    )

  elif args['action'] == 'uninstall':
    execute_helm(args)

  elif args['action'] == 'upgrade':
    vault = _get_vault_client(args)
    upgrade_deployment(vault, args)
  else:
    print("No action provided.")

if __name__ == '__main__':
  main()