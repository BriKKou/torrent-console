import unittest
from unittest import mock

from errors import RemoteError
from httpclient import get_json


class GetJsonTest(unittest.TestCase):
    def test_reads_json(self):
        with mock.patch("httpclient.get", return_value=b'{"ok": true}'):
            self.assertEqual(get_json("https://site.example/api"), {"ok": True})

    def test_maintenance_page_is_a_remote_error(self):
        with mock.patch("httpclient.get", return_value=b"<html>Maintenance en cours</html>"):
            with self.assertRaisesRegex(RemoteError, "site.example : réponse illisible"):
                get_json("https://site.example/api")


if __name__ == "__main__":
    unittest.main()
