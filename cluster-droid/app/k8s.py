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

def execute_helm(action, namespace, release, chart, version, values_file = "", url = "", wait = False, insecure = False):
  cmd = [
    'helm',
    action,
    '-n',
    namespace,
    release
  ]

  if action == 'upgrade':
    cmd += [ '-i', '--create-namespace' ]

    if 'valuesFile' != "":
      cmd += ["-f", f"{ values_file }" ]

    if wait:
      cmd.append('--wait')

    if '/' not in chart:
      if 'url' == "":
        print("You must either specify the url of the repository or provide a chart like <repo/release>")
        exit(1)
      else:
        resp = requests.get(f"{ url }/index.yaml")
        charts = yaml.safe_load(resp.content)

        chart_url = None
        for e in charts['entries'][chart]:
          if e['version'] == version:
            chart_url = e['urls'][0]

        if chart_url == None:
          print("No chart of that version could be found.")
          exit(1)
        else:
          curl_cmd = ['curl']

          if insecure:
            curl_cmd.append('-k')

          curl_cmd += [ chart_url, "-Lo", f"/tmp/{ chart }.tgz" ]

        print(curl_cmd)
        subprocess.check_output(curl_cmd)

        cmd.append(f"/tmp/{ chart }.tgz")
    else:
      cmd.append(chart)

  print(cmd)
  subprocess.check_output(cmd)
  print("Success")
  pass