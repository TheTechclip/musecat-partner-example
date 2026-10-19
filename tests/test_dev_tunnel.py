import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "dev_tunnel", ROOT / "scripts/dev-tunnel.py"
)
tunnel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tunnel)


class DevTunnelTests(unittest.TestCase):
    def test_origin_change_preserves_secrets_and_limits_file_permissions(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text(
                "PARTNER_ORIGIN=http://localhost:8088\nMUSECAT_CLIENT_SECRET=existing\nDATA_KEY=existing-key\n"
            )
            tunnel.configure(path, "https://test-only.trycloudflare.com")
            self.assertIn("MUSECAT_CLIENT_SECRET=existing\n", path.read_text())
            self.assertIn("DATA_KEY=existing-key\n", path.read_text())
            self.assertIn(
                "PARTNER_HOST=test-only.trycloudflare.com\n", path.read_text()
            )
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
