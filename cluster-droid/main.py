#!/usr/bin/env python3

import base64, os, subprocess, yaml

def generate_kube_config(details):
  if 'ca_path' not in details and 'PLUGIN_DEFAULT_CA_PATH' in os.environ:
    details['ca_path'] = os.environ['PLUGIN_DEFAULT_CA_PATH']

  if 'token_path' not in details and 'PLUGIN_DEFAULT_TOKEN_PATH' in os.environ:
    details['token_path'] = os.environ['PLUGIN_DEFAULT_TOKEN_PATH']

  with open(details['ca_path'], 'r') as f:
    encoded_ca = base64.b64encode(f.read().rstrip().encode('utf-8')).decode()

  with open(details['token_path'], 'r') as f:
    token = f.read().rstrip()

  kubeconfig = {
    'apiVersion': 'v1',
    'clusters': [{
      'cluster': {
        'certificate-authority-data': encoded_ca,
        'server': f"https://{ os.environ['PLUGIN_SERVER'] }:{ os.environ['PLUGIN_SERVER_PORT'] }",
      },
      'name': 'default'
    }],
    'contexts': [{
      'context': {
        'cluster': 'default',
        'user': 'default'
      },
      'name': 'default'
    }],
    'kind': 'Config',
    'users': [{
      'name': 'default',
      'user': {
        'token': token
      }
    }],
    'current-context': 'default'
  }

  os.makedirs(f"{ os.environ['HOME'] }/.kube", exist_ok=True)

  with open(f"{ os.environ['HOME'] }/.kube/config", 'w+') as f:
    f.write(yaml.dump(kubeconfig))


def execute_helm(details, wait):
  cmd = [
    'helm',
    details['operation']
  ]

  if details['operation'] == 'upgrade':
    cmd.append('-i')

  if 'valuesFile' in details:
    cmd += ["-f", details['valuesFile'] ]


  if 'namespace' in details:
    cmd += [ '-n', details['namespace'] ]

  if wait:
    cmd.append('--wait')

  cmd.append(details['release'])
  if '/' not in details['chart']:
    if 'url' not in details:
      print("You must either specify the url of the repository or provide a chart like <repo/release>")
      exit(1)
    else:
      details['chart'] = f"{ details['chart'] }-{ details['version'] }.tgz"
      # print(f"Execute { ' '.join(cmd) }")

      curl_cmd = ['curl']
      if 'insecure' in details:
        curl_cmd.append('-k')
      curl_cmd += [f"{ details['url'] }/{ details['chart'] }", "-o", f"/tmp/{ details['chart'] }"]
      
      print(curl_cmd)
      subprocess.check_output(curl_cmd)

      cmd.append(f"/tmp/{ details['chart'] }")
  else:
    cmd.append(details['chart'])

  subprocess.check_output(cmd)
  pass

def _raw_kubectl(command):
  cmd = ['kubectl'] + command.split(' ')
  print(f"Execute { ' '.join(cmd) }")
  subprocess.check_output(cmd)

def execute_kubectl(details, hook):
  cmd = [ 'kubectl', hook['operation'] ]

  if hook['operation'] == 'apply':
    if not hook['resource'].startswith('http') and not hook['resource'].startswith(details['base_path']):
      hook['resource'] = f"{ details['base_path'] }/{ hook['resource'] }"
    cmd += ['-f', hook['resource']]
  else:
    cmd += [ hook['resource'] ]

  print(f"Execute { ' '.join(cmd) }")
  subprocess.check_output(cmd)

def load_details():
  with open(os.environ['PLUGIN_DETAILS_FILE'], 'r') as f:
    details = yaml.safe_load(f.read())
    details['base_path'] = '/'.join(os.environ['PLUGIN_DETAILS_FILE'].split('/')[:-1])

  if "PLUGIN_STATE" not in os.environ:
    print("please specify a plugin state (upgrade / uninstall)")
    exit(1)
  else:
    details['operation'] = os.environ['PLUGIN_STATE']

  print("Details to process:")
  print(details)
  return details

def process_hook(details, hook):
  if hook['operation'] in ['apply', 'remove']:
    execute_kubectl(details, hook)

def main():
  if os.environ['PLUGIN_STATE'] in [ 'upgrade', 'uninstall' ]:
    details = load_details()
    generate_kube_config(details)

    wait = ((os.environ['PLUGIN_WAIT'] == 'true' if 'PLUGIN_WAIT' in os.environ else False) or
      (details['operation'] == 'upgrade' and  'hooks' in details and 'postInstall' in details['hooks']))

    if (details['operation'] == 'upgrade' and 
        'hooks' in details and
        'preInstall' in details['hooks']):

      print('Execute preInstall hooks')
      for hook in details['hooks']['preInstall']:
        process_hook(details, hook)

    execute_helm(details, wait)

    if (details['operation'] == 'upgrade' and 
        'hooks' in details and
        'postInstall' in details['hooks']):

      print('Execute postInstall hooks')
      for hook in details['hooks']['postInstall']:
        process_hook(details, hook)

  elif os.environ['PLUGIN_STATE'] in [ 'rm', 'apply' ]:
    generate_kube_config({})
    execute_kubectl({}, { 'operation': os.environ['PLUGIN_STATE'], 'resource': os.environ['PLUGIN_RESOURCE'] })

  elif os.environ['PLUGIN_STATE'] in [ 'secret' ]:
    generate_kube_config({})

    _base_cmd = f"create secret { os.environ['PLUGIN_TYPE'] } -n { os.environ['PLUGIN_NAMESPACE'] } { os.environ['PLUGIN_NAME'] } { os.environ['PLUGIN_ARGS'] }"
    _raw_kubectl(_base_cmd)

if __name__ == '__main__':
  main()