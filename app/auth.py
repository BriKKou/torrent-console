"""Accès à la page protégé par mot de passe (authentification HTTP Basic)."""
import base64
import hashlib
import hmac
import secrets
import threading

ITERATIONS = 200_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), ITERATIONS).hex()
    return f"pbkdf2_sha256${ITERATIONS}${salt}${digest}"


def check_password(password: str, stored: str) -> bool:
    try:
        _, iterations, salt, digest = stored.split("$")
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iterations)).hex()
    except ValueError:
        return False
    return hmac.compare_digest(candidate, digest)


class BasicAuth:
    def __init__(self, user: str = "", password_hash: str = ""):
        self._user = user
        self._hash = password_hash
        # En-têtes déjà vérifiés : le calcul du mot de passe est volontairement lent
        self._accepted: set[str] = set()
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return bool(self._user and self._hash)

    def allows(self, header: str | None) -> bool:
        if not self.enabled:
            return True
        if not header or not header.startswith("Basic "):
            return False
        fingerprint = hashlib.sha256(header.encode()).hexdigest()
        with self._lock:
            if fingerprint in self._accepted:
                return True
        try:
            user, _, password = base64.b64decode(header[6:], validate=True).decode().partition(":")
        except (ValueError, UnicodeDecodeError):
            return False
        if not (hmac.compare_digest(user, self._user) and check_password(password, self._hash)):
            return False
        with self._lock:
            self._accepted.add(fingerprint)
        return True
