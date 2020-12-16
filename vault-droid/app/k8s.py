from kubernetes import client as kc
import base64
from datetime import datetime, timezone

class K8s:
  def __init__(self, host, tokenPath, caPath):
    '''Login to kubernetes via SA token'''
    with open(tokenPath, 'r') as f:
      token = f.read().strip()

    configuration = kc.Configuration()
    configuration.api_key["authorization"] = token
    configuration.api_key_prefix['authorization'] = 'Bearer'
    configuration.host = host
    configuration.ssl_ca_cert = caPath

    self.client = kc.ApiClient(configuration)

  def get_service_account_token_and_ca(self, sa: str) -> str:
    '''Get the token and ca values of a service account'''

    spl = sa.split('/')
    resp = kc.CoreV1Api(self.client).read_namespaced_service_account(spl[1], spl[0])
    secret_name = resp.secrets[0].name

    resp = kc.CoreV1Api(self.client).read_namespaced_secret(secret_name, spl[0])
    return base64.b64decode(resp.data.get('token')).decode("utf-8"), base64.b64decode(resp.data.get('ca.crt')).decode("utf-8")

  def create_secret(self, name: str, namespace: str, data: str, type: str = 'Opaque'):
    '''Create a secret in kubernetes using the info provided'''
    metadata = kc.V1ObjectMeta(
      name=name,
      namespace=namespace
    )
  
    enc_data = {}
    for k,v in data.items():
      enc_data[k] = base64.b64encode(v.encode('utf-8')).decode('utf-8')

    print(enc_data)
    body = kc.V1Secret( # compile the body to send to the k8s api
      metadata=metadata,
      type=type,
      data=enc_data
    )
  
    # try:
    #   print("HERE")
    ret = kc.CoreV1Api(self.client).create_namespaced_secret(namespace, body)
    #   print(ret)
    # except kc.rest.ApiException as e: # Secret does not exist
    #   if e.status == 409:
    #     print(f"Secret { namespace }:{ name } already exists, skipping.")