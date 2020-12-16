#!/usr/bin/env python3
from argsparsing import ArgsParsing

args = {
  'PLUGIN_ACTION': 'process',
  'PLUGIN_DETAILS_FILE': 'details.yml',
  'PLUGIN_VAULT_TOKEN': '/Users/tposse/.vault-token',
  'PLUGIN_VAULT_CA': './tmp/v_ca.crt',
  'PLUGIN_SIGN_CA': './tmp/ca.crt',
  'PLUGIN_SIGN_CA_KEY': './tmp/ca.key',
  'PLUGIN_SECRET': 'vault',
  'PLUGIN_CONFIG_PATH': 'vault/config.yml',
  'PLUGIN_VAULT_ADDRESS': 'https://vault.tiagoposse.com',
  'PLUGIN_DETAILS_FILE': 'vault/details.yml',
  'PLUGIN_KUBERNETES_ADDRESS': 'https://192.168.178.48:6443',
  'PLUGIN_KUBERNETES_CA': './tmp/k_ca.crt',
  'PLUGIN_KUBERNETES_TOKEN_PATH': './tmp/k_token'
}

def load_as_cli():
  app_args = ArgsParsing()
  



def print_as_env():
  for a, v in args.items():
    print(f"export { a }='{ v }'")

def print_as_cli():
  app_args = ArgsParsing()

  for arg in app_args.get_args():
    print(f"{ arg['calls'][0] }=\"{ args[arg['env']] }\" \\")

print_as_env()