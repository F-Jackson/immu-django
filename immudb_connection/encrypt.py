from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization


def generate_new_keys():
    # Generate private key
    private_key = ec.generate_private_key(ec.SECP256R1())

    # Serialize private key to PEM format
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    # Save private key to file
    with open('private_signing_key.pem', 'wb') as f:
        f.write(private_key_pem)

    # Generate public key
    public_key = private_key.public_key()

    # Serialize public key to PEM format
    public_key_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    # Save public key to file
    with open('public_signing_key.pem', 'wb') as f:
        f.write(public_key_pem)
        
        
if __name__ == '__main__':
    generate_new_keys()        
        