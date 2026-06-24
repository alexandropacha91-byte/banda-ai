"""
BANDA AI - Export Sécurisé Modèle IA
Chiffre le modèle TFLite avec BANDA_SECURITY_SALT avant upload R2.
USAGE: BANDA_SECURITY_SALT=xxx python ml/secure_export.py
"""
import os
import json
import hashlib
import boto3
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import base64

MODEL_PATH = "ml/models/banda_v1.tflite"
R2_BUCKET = os.environ.get("R2_BUCKET_NAME", "banda-models")


def derive_key(salt: str) -> bytes:
    """Dérive la clé de chiffrement depuis le sel GitHub."""
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt.encode(), iterations=480_000)
    return base64.urlsafe_b64encode(kdf.derive(b"banda-model-v1"))


def secure_and_upload():
    salt = os.environ.get("BANDA_SECURITY_SALT")
    if not salt or salt == "CHANGE_ME_VIA_GITHUB_SECRETS":
        raise ValueError("❌ BANDA_SECURITY_SALT manquant ou invalide!")
    
    # 1. Chiffrer le modèle
    with open(MODEL_PATH, "rb") as f:
        model_data = f.read()
    
    key = derive_key(salt)
    fernet = Fernet(key)
    encrypted = fernet.encrypt(model_data)
    
    # 2. Créer payload avec hash d'intégrité
    integrity_hash = hashlib.sha256(encrypted).hexdigest()[:16]
    payload = json.dumps({"v": 2, "h": integrity_hash, "m": encrypted.decode()})
    
    # 3. Upload sur R2
    s3 = boto3.client(
        "s3",
        endpoint_url=f"https://{os.environ['R2_ACCESS_KEY']}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY"],
        aws_secret_access_key=os.environ["R2_SECRET_KEY"],
    )
    s3.put_object(Bucket=R2_BUCKET, Key="models/banda_v1.enc", Body=payload.encode())
    
    print(f"🔒 Modèle chiffré et uploadé sur R2")
    print(f"   Hash intégrité: {integrity_hash}")
    print(f"   Taille originale: {len(model_data)//1024} KB")
    print(f"   Taille chiffrée: {len(payload)//1024} KB")


if __name__ == "__main__":
    secure_and_upload()
