import argparse, os, yaml
from typing import final

DEFAULT_ACTION='store'

class ArgsParsing:
  def __init__(self, args = None, path = None):
    if args:
      self.args = args
    elif path:
      self.args = self._load_app_args_file(path)
    else:
      try:
        self.args = self._load_app_args_file(f"{ os.path.dirname(__file__) }/.appargs.yml")
      except:
        print("No arguments provided")
        exit(1)

  def _load_app_args_file(self, path):
    with open(path, 'r') as f:
      return yaml.safe_load(f.read())

  def get_args(self):
    return self.args

  def _parse_cli(self):
    cli_parser = argparse.ArgumentParser()

    cli_parser.add_argument(
      '-e', '--env',
      action='store',
      dest='env',
      default=None,
      help='Path to an env file'
    )

    for a in self.args:
      if '-e' in a['calls'] or '--env' in a['calls']:
        print('-e and --env cannot overwrite the feature')
      else:
        cli_parser.add_argument(
          *a['calls'],
          action=a['action'] if 'action' in a else DEFAULT_ACTION,
          default=None,
          dest=a['dest'],
          help=a['help'] if 'help' in a else ''
        )

    cli_args = cli_parser.parse_args()
    final_args = {}
    for a in self.args:
      if getattr(cli_args, a['dest']) != None:
        final_args[a['dest']] = getattr(cli_args, a['dest'])

    return final_args
    
  
  def _parse_env(self):
    if 'env' in os.environ:
      pass

    args = {}
    for a in self.args:
      if 'env' in a and a['env'] in os.environ:
        args[a['dest']] = os.environ[a['env']]
    
    return args

  def validate_args(self, args, val_list):
    valid = True
    for a in val_list:
      if args[a] == None:
        print(f"Argument { a } is not valid.")
        valid = False
        
    return valid

  def _parse_conf(self, conf_path):
    args = {}

    with open(conf_path, 'r') as f:
      args_as_str = f.readlines()
    
    env_var_args = {}
    for line in args_as_str:
      kv = line.split('=')
      args[kv[0]] = kv[1:]
    
    for a in self.args:
      if a['env'] in env_var_args:
        args[a['dest']] = env_var_args[a['env']]
    
    return args

  def parse(self):
    env_args = self._parse_env()
    cli_args = self._parse_cli()

    if 'env' in cli_args:
      conf_args = self._parse_conf(cli_args['env'])
    elif 'env' in env_args:
      conf_args = self._parse_conf(env_args['env'])
    else:
      conf_args = {}

    args = {}
    for a in self.args:
      args[a['dest']] = None

    for k, v in conf_args.items():
      args[k] = v
    for k, v in env_args.items():
      args[k] = v
    for k, v in cli_args.items():
      args[k] = v

    return args