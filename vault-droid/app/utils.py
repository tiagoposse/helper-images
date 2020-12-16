
import ipaddress, random, string
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from datetime import datetime, timedelta

def create_vault_cert(common_name, namespace, ca_path, ca_key_path, replicas = 3, type = 'server'):
  key = rsa.generate_private_key(
      public_exponent=65537,
      key_size=2048,
      backend=default_backend(),
  )

  name = x509.Name([
    x509.NameAttribute(NameOID.COMMON_NAME, common_name)
  ])

  alt_names = [
    x509.DNSName('localhost'),
    x509.DNSName(f"vault"),
    x509.DNSName(f"vault.{ namespace }.svc"),
    x509.DNSName(f"vault-internal"),
    x509.DNSName(f"vault-internal.{ namespace }"),
    x509.DNSName(f"vault-internal.{ namespace }.svc"),
    x509.DNSName(f"vault-internal.{ namespace }.svc.cluster.local"),
    x509.IPAddress(ipaddress.ip_address("127.0.0.1"))
  ]

  for i in range(0, replicas):
    alt_names += [
      x509.DNSName(f"vault-{ i }"),
      x509.DNSName(f"vault-{ i }.vault-internal"),
      x509.DNSName(f"vault-{ i }.vault-internal.{ namespace }.svc"),
      x509.DNSName(f"vault-{ i }.vault-internal.{ namespace }.svc.cluster.local")
    ]

  basic_contraints = x509.BasicConstraints(ca=False, path_length=None)
  keyUsage = x509.KeyUsage(
      digital_signature=True,
      key_encipherment=True,
      data_encipherment=False,
      key_agreement=True,
      content_commitment=False,
      key_cert_sign=False,
      crl_sign=False,
      encipher_only=False,
      decipher_only=False
  )

  if type == 'server':
    extKeyUsage = x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH])
  else:
    extKeyUsage = x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH])

  # Load CA Private key
  with open(ca_key_path, 'r') as f:
    ca_key = f.read()

  with open(ca_path, 'r') as f:
    ca = f.read()

  ca = x509.load_pem_x509_certificate(
    ca.encode("ascii"), default_backend()
  )

  ca_key = serialization.load_pem_private_key(
    ca_key.encode("ascii"), password=None, backend=default_backend()
  )

  cert = (
    x509.CertificateBuilder()
    .subject_name(name)
    .issuer_name(ca.issuer)
    .public_key(key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(datetime.utcnow())
    .not_valid_after(datetime.utcnow() + timedelta(days=365))
    .add_extension(basic_contraints, False)
    .add_extension(extKeyUsage, critical=True)
    .add_extension(keyUsage, critical=True)
    .add_extension(x509.SubjectAlternativeName(alt_names), False)
    .sign(ca_key, hashes.SHA256(), default_backend())
  )

  return key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.TraditionalOpenSSL,
    encryption_algorithm=serialization.NoEncryption()
  ).decode("utf-8"), cert.public_bytes(serialization.Encoding.PEM).decode("utf-8"), ca.public_bytes(serialization.Encoding.PEM).decode("utf-8")

def get_random_string(length = 32):
    chars = string.ascii_letters + string.digits
    result_str = ''.join(random.choice(chars) for i in range(length))

    return result_str