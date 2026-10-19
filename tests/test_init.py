"""Initialization must not change deployed credentials or depend on env line order."""

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


class InitTests(unittest.TestCase):
    def test_login_id_generation_is_order_independent_and_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "scripts").mkdir()
            shutil.copy2(
                Path(__file__).parents[1] / "scripts/init-env.py",
                root / "scripts/init-env.py",
            )
            (root / ".env.example").write_text(
                "MUSECAT_LOGIN_CLIENT_ID=change_me_login\nPARTNER_ID=change_me\nSESSION_SECRET=\nDATA_KEY=\nMUSECAT_CLIENT_SECRET=existing-api-secret\nMUSECAT_LOGIN_CLIENT_SECRET=existing-login-secret\n"
            )
            subprocess.run(
                [sys.executable, str(root / "scripts/init-env.py")],
                check=True,
                capture_output=True,
            )
            first = (root / ".env").read_text()
            values = dict(
                line.split("=", 1) for line in first.splitlines() if "=" in line
            )
            self.assertEqual(
                values["MUSECAT_LOGIN_CLIENT_ID"], values["PARTNER_ID"] + "_login"
            )
            self.assertEqual(
                values["MUSECAT_LOGIN_CLIENT_SECRET"], "existing-login-secret"
            )
            self.assertEqual(values["MUSECAT_CLIENT_SECRET"], "existing-api-secret")
            self.assertEqual((root / ".env").stat().st_mode & 0o777, 0o600)
            subprocess.run(
                [sys.executable, str(root / "scripts/init-env.py")],
                check=True,
                capture_output=True,
            )
            self.assertEqual((root / ".env").read_text(), first)
