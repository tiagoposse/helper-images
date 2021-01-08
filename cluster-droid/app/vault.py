import base64, hvac, logging, os, random, re, string, time, yaml
from k8s import execute_kubectl

DEFAULT_TTL = 2764800

def get_random_string(length = 32):
    chars = string.ascii_letters + string.digits
    result_str = ''.join(random.choice(chars) for i in range(length))

    return result_str

class Vault:
  def __init__(self, scheme, vault_addr, token_path = None, ca_cert_path = None, insecure = False):
    '''Configure the connection to a vault instance with the provided arguments'''

    self.scheme = scheme
    self.addr = vault_addr
    self.ca = ca_cert_path
    self.insecure = insecure

    self._get_prefixed_client()

    if token_path != None:
      with open(token_path, 'r') as f:
        self.set_token(f.read().strip())

  def _get_prefixed_client(self, prefix = ""):
    if self.ca != None:
      self.client = hvac.Client(url=f"{ self.scheme }://{ prefix }{ self.addr }", verify=self.ca)
    elif self.insecure:
      self.client = hvac.Client(url=f"{ self.scheme }://{ prefix }{ self.addr }", verify=False)
    else:
      self.client = hvac.Client(url=f"{ self.scheme }://{ prefix }{ self.addr }")


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

    for i in range(0, replicas):
      self._get_prefixed_client(f"vault-{ i }.")

      logging.info(f"Unsealing replica { i }")
      retry = 0
      while retry < 5:
        try:
          self.client.sys.submit_unseal_keys(keys=keys)
          break
        except:
          retry += 1
          time.sleep(3)

      retry = 0
      while retry < 10:
        if self.client.sys.is_sealed():
          retry += 1
          time.sleep(3)
        else:
          break

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

  def setup_vault(self, args):
    logging.info("Creating clients...")

    with open(args['config'], 'r') as f:
      init_conf = yaml.safe_load(f.read())

    self._get_prefixed_client('vault-0.')

    print("In setup.")
    token, keys = self.initialize_vault(init_conf['init']['shares'], init_conf['init']['threshold'])
    print("After: " + token)
    logging.info("Initialized.")

    if token != None:
      for k in keys:
        logging.info(k)

      logging.info("Creating secret with keys...")
      execute_kubectl([
        'create',
        'secret',
        'generic',
        '-n',
        args['details']['namespace'],
        'vault',
        f"--from-literal=root_key={ token }",
        f"--from-literal=keys={ ','.join(keys) }"
      ])

      self.set_token(token)
      with open('/tmp/token', 'w') as f:
        f.write(token)

      logging.info("Unsealing...")
      self.unseal(keys[0:int(len(keys)/2+1)])
      logging.info("Enable k8s auth...")

      def_engine = { 'description': '', 'options': {}, 'config': {}, 'max_versions': 10 }
      for engine in init_conf['engines']:
        tmp = def_engine.copy()
        tmp.update(engine)
        engine = tmp

        if engine['type'] == 'kubernetes':
          with open(engine['ca'], 'r') as f:
            ca = f.read()

          vault_sa_secret = execute_kubectl(f"get sa -n { args['details']['namespace'] } -ojsonpath='{{.secrets[0].name}}' vault".split(" ")).decode()[1:-1]

          vault_sa_token = base64.b64decode(execute_kubectl(f"get secret -n { args['details']['namespace'] } { vault_sa_secret } -ojsonpath='{{.data.token}}'".split(' '))).decode()

          self.enable_kubernetes_auth(engine['address'], vault_sa_token, ca)
        elif engine['type'] == 'userpass':
          self.enable_userpass_auth(engine['mount_path'])
        elif engine['type'] == 'pki':
          self.enable_pki_engine(engine['mount_path'], engine['description'], engine['options'], engine['config'])
        elif engine['type'] == 'kv':
          self.enable_secrets_engine(engine['mount_path'], engine['description'], engine['options'], engine['max_versions'])


  def process_deployment_vault(self, details: dict, base_path: str = ".", dry_run = False):
    for pol in details['policies']:
      if dry_run:
        print(f"vault policy write { base_path }/vault/{ pol }.hcl")
      else:
        self.create_policy(pol, f"{ base_path }/vault/{ pol }.hcl")
    
    for role in details['roles']:
      if dry_run:
        print(f"vault write auth/kubernetes/role/{ role['name'] } bound_service_account_names={ role['sa'] } bound_service_account_namespaces={ role['namespaces'] } policies={ role['policies'] }")
      else:
        self.create_kubernetes_role(role['name'], role['sa'], role['namespaces'], role['policies'])

    for secret in details['secrets']:
      spl_path = secret['path'].split('/')

      if dry_run:
        val_string = ""
        for k, v in secret['values'].items:
          val_string += f"{ k }={ v } "

        print(f"vault write { spl_path[0] }/{ '/'.join(spl_path[1:]) } { val_string }")
      else:
        self.create_secret_if_not_exists(
          '/'.join(spl_path[1:]),
          mount_point=spl_path[0],
          values=secret['values'],
          force=secret['force'] if 'force' in secret else False
        )
