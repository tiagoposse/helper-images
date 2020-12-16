# vault-droid

Four actions:
- unseal
- setup
- certificate
- process

Variables:
- kubernetes_ca: path for the ca file
- vault_address:
- vault_token_path: path to the file containing a vault authentication token
- action: see above
- secret: name of the secret where vault root key and unseal keys will be writen to, defaults to `vault`, or where the tls certificate will be writen to, defaults to `vault-tls`
- config_path: required for setup and certificate, contains the configurations used to tune vault
- details_file: path to the file where the secrets, roles and policies are defined
- ca_cert: <used for certificate>, path to the ca that signs this certificate
- ca_key: <used for certificate>, path to the key of the ca that signs this certificate