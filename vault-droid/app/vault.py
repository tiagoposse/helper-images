import hvac, logging, re, os, time
from utils import get_random_string

DEFAULT_TTL = 2764800

class Vault:
  def __init__(self, scheme, vault_addr, token_path = None, ca_cert_path = None):
    '''Configure the connection to a vault instance with the provided arguments'''

    self.scheme = scheme
    self.addr = vault_addr
    self.ca = ca_cert_path

    if ca_cert_path != None:
      self.client = hvac.Client(url=f"{ scheme }://{ vault_addr }", verify=ca_cert_path)
    else:
      self.client = hvac.Client(url=f"{ scheme }://{ vault_addr }", verify=False) # url=f"{ scheme }://vault-0.{ vault_addr }"

    if token_path != None:
      with open(token_path, 'r') as f:
        self.set_token(f.read().strip())


  def set_token(self, token):
    '''Set the auth token for this vault connection'''

    self.client.token = token

  def create_policy(self, name, path):
    '''Create a vault policy using a file'''

    with open(path, 'r') as f:
      policy = f.read()

    logging.debug(f"Creating policy { name }")
    self.client.sys.create_or_update_policy(name, policy)

  def create_kubernetes_role(self, name, sas, ns, policies):
    """Create a kubernetes authentication role in the vault instance"""
    
    self.client.auth.kubernetes.create_role(name, sas, ns, policies=policies)

  def create_secret_if_not_exists(self, path: str, values: dict = {}, mount_point: str = "kv", force: bool = False):
    """Check if secret does not exist in vault and creates it according to the secret definition."""

    try:
      existing = self.client.secrets.kv.v2.read_secret_version(path, mount_point=mount_point)
    except hvac.exceptions.InvalidPath:
      existing = None
    
    if existing and existing['data']['data'] != None and not force: # If the secret doesn't exist, generate the values to insert
      logging.info("Secret already exists and not forcing, doing nothing.")
    else:
      logging.info("Creating a new version of this secret.")
      if len(values.keys()) == 0: # If no value keys were provided to create, throw exception
        raise Exception("Secret does not exist and no values were given.")

      creation_values = {}
      for k, v in values.items():

        # the length of the string can be specified by adding the length value in [],
        # e.g. 'gen[64]' for a string with 64 characters
        if re.match(r"^gen\[[0-9]{1,4}\]$", v):
          length = re.search(r"\[([0-9]+)\]", v)
          creation_values[k] = get_random_string(int(length.group(1)))
        elif v == 'gen':
          creation_values[k] = get_random_string()
        elif v.startswith('env_'):
          creation_values[k] = os.environ[v[4:]]
        else:
          creation_values[k] = v
  
      self.client.secrets.kv.v2.create_or_update_secret(path, secret=creation_values, mount_point=mount_point)


  def initialize_vault(self, shares = 5, threshold = 3):
    """
      Initialize vault and return the resulting data
    
      If vault is already initialized, it does nothing.
    """

    if not self.client.sys.is_initialized():
      result = self.client.sys.initialize(shares, threshold)
      root_token = result['root_token']
      keys = result['keys']

      if not self.client.sys.is_initialized():
        logging.error("Error initializing vault")
        exit()
      else:
        logging.info("Client has been initialized.")
      
      return root_token, keys
    else:
      logging.info("Vault already initialized")
      return None, None


  def unseal(self, keys, replicas: int = 3):
    """Unseal all vault replicas"""

    logging.info(f"Unsealing replica 0")
    self.client.sys.submit_unseal_keys(keys=keys)
    while True:
      resp = self.client.sys.read_health_status(method='GET')
      if (not isinstance(resp, dict)) and resp.status_code == 429:
        logging.debug("Not ready yet, wait")
        time.sleep(1)
      else:
        time.sleep(5)
        break

    for i in range(1, replicas):

      if self.ca != None:
        aux_client = hvac.Client(url=f"{ self.scheme }://vault-{ i }.{ self.addr }", verify=self.ca)
      else:
        aux_client = hvac.Client(url=f"{ self.scheme }://vault-{ i }.{ self.addr }", verify=False)

      logging.info(f"Unsealing replica { i }")
      retry = 0
      while retry < 3:
        try:
          aux_client.sys.submit_unseal_keys(keys=keys)
          retry = 4
        except:
          retry += 1
          time.sleep(2)

      while aux_client.sys.is_sealed():
        time.sleep(2)


  def enable_secrets_engine(self, mount_point: str = 'kv', description: str = '', options: dict = {}, max_versions: int = 10):
    """
      Enable and configure a secrets engine
    """

    print(f"Enable secrets engine { mount_point }")

    self.client.sys.enable_secrets_engine(
      'kv',
      description=description,
      path=mount_point,
      config={
        'version': 2,
        'default_lease_ttl': DEFAULT_TTL,
        'max_lease_ttl': DEFAULT_TTL,
        'force_no_cache': False
      },
      options=options
    )

    self.client.secrets.kv.v2.configure(
      mount_point=mount_point,
      max_versions=max_versions
    )

  def enable_pki_engine(self, mount_point: str = 'pki', description: str = '', options: dict = {}, config: dict = {}):
    """
      Enable and configure a pki engine
    """


    print(f"Enable pki engine { mount_point }")
    self.client.sys.enable_secrets_engine(
      'pki',
      description=description,
      path=mount_point,
      config=config,
      options=options
    )

    self.client.sys.tune_mount_configuration(path=mount_point, **config)


  def enable_kubernetes_auth(self, host, token, ca, mount_point = 'kubernetes'):
    '''Enable and configure kubernetes authentication'''

    desired_state = {
      'kubernetes_host': host,
      'token_reviewer_jwt': token,
      'kubernetes_ca_cert': ca,
      'mount_point': mount_point
    }

    try:
      current_state = self.client.auth.kubernetes.read_config(mount_point=mount_point)
    except hvac.exceptions.InvalidPath:
      current_state = {}

    if current_state == {}:
      self.client.sys.enable_auth_method(
          method_type='kubernetes',
          path=mount_point,
      )

    self.client.auth.kubernetes.configure(**desired_state)


  def enable_userpass_auth(self, path = 'userpass'):
    '''Enable userpass auth method'''

    self.client.sys.enable_auth_method(
      method_type='userpass',
      path=path,
    )
