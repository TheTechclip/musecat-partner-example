import os
from pathlib import Path
import tempfile
import time
import unittest

from cryptography.fernet import Fernet

from partner.storage import Ledger


class StoragePermissionsTests(unittest.TestCase):
    def test_new_ledger_is_private_and_reopening_preserves_data(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.db"
            key = Fernet.generate_key().decode()
            previous = os.umask(0)
            try:
                ledger = Ledger(str(path), key)
            finally:
                os.umask(previous)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with ledger.transaction() as tx:
                ledger.put(tx, "fixture", "alice", {"synthetic": True}, int(time.time()) + 60)
            reopened = Ledger(str(path), key)
            with reopened.transaction() as tx:
                self.assertEqual(reopened.get(tx, "fixture", "alice"), {"synthetic": True})
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
