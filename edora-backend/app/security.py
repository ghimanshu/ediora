import hashlib
import secrets
from pwdlib import PasswordHash

password_hasher = PasswordHash.recommended()
DUMMY_HASH = password_hasher.hash("unused-timing-equalization-password")

def new_token():
    return secrets.token_urlsafe(32)

def digest(token: str):
    return hashlib.sha256(token.encode()).hexdigest()
