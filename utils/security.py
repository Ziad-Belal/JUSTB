import bcrypt

def hash_password(plain: str) -> str:
    """Hash a plain-text password. Returns a bcrypt string safe to store in JSON."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(hashed: str, plain: str) -> bool:
    """Return True if plain matches the stored bcrypt hash."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False

def is_hashed(value: str) -> bool:
    """Return True if the value looks like a bcrypt hash (starts with $2b$ or $2a$)."""
    return isinstance(value, str) and value.startswith(("$2b$", "$2a$", "$2y$"))