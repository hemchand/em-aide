import hashlib

def sha256_short(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def sha256_64(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
