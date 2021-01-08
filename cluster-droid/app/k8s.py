import requests, subprocess, yaml

def execute_kubectl(command: list, ignore = False, dry_run = False):
  cmd = ['kubectl'] + command
  if dry_run:
    print(f"{ ' '.join(cmd) }")
  else:
    try:
      return subprocess.check_output(cmd)
    except subprocess.CalledProcessError as e:
      if ignore:
        return e
      else:
        raise e

def execute_helm(args):
  cmd = [
    'helm',
    args['action']
  ]

  if args['action'] == 'upgrade':
    cmd.append('-i')

  if 'valuesFile' in args['details']:
    cmd += ["-f", f"{ args['_base_path'] }/{ args['details']['valuesFile'] }" ]

  if 'namespace' in args['details']:
    cmd += [ '-n', args['details']['namespace'] ]

  if args['wait']:
    cmd.append('--wait')

  cmd.append(args['details']['release'])

  if '/' not in args['details']['chart']:
    if 'url' not in args['details']:
      print("You must either specify the url of the repository or provide a chart like <repo/release>")
      exit(1)
    else:
      resp = requests.get(f"{ args['details']['url'] }/index.yaml")
      charts = yaml.safe_load(resp.content)

      chart_url = None
      for e in charts['entries'][args['details']['chart']]:
        if e['version'] == args['details']['version']:
          chart_url = e['urls'][0]

      if chart_url == None:
        print("No chart of that version could be found.")
        exit(1)
      else:
        curl_cmd = ['curl']

        if 'insecure' in args['details']:
          curl_cmd.append('-k')

        curl_cmd += [ chart_url, "-Lo", f"/tmp/{ args['details']['chart'] }.tgz" ]

      print(curl_cmd)
      subprocess.check_output(curl_cmd)

      cmd.append(f"/tmp/{ args['details']['chart'] }.tgz")
  else:
    cmd.append(args['details']['chart'])

  print(cmd)
  subprocess.check_output(cmd)
  print("Success")
  pass