import base64
import unittest

from auth import BasicAuth, check_password, hash_password


def basic(user: str, password: str) -> str:
    return "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()


class AuthTest(unittest.TestCase):
    def test_password_hash_round_trip(self):
        stored = hash_password("secret")
        self.assertTrue(check_password("secret", stored))
        self.assertFalse(check_password("Secret", stored))
        self.assertFalse(check_password("secret", "pas-un-hash"))

    def test_disabled_without_password(self):
        self.assertTrue(BasicAuth().allows(None))

    def test_basic_header(self):
        auth = BasicAuth("alice", hash_password("secret"))
        self.assertTrue(auth.allows(basic("alice", "secret")))
        self.assertTrue(auth.allows(basic("alice", "secret")))  # 2e fois : depuis le cache
        self.assertFalse(auth.allows(basic("alice", "faux")))
        self.assertFalse(auth.allows(basic("autre", "secret")))
        self.assertFalse(auth.allows(None))
        self.assertFalse(auth.allows("Basic !!!"))


if __name__ == "__main__":
    unittest.main()
