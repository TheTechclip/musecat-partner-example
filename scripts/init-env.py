#!/usr/bin/env python3
"""Generate local-only sample credentials. Existing values are preserved."""

import base64
import os
from pathlib import Path
import secrets

root = Path(__file__).resolve().parent.parent
path = root / ".env"
lines = (path if path.exists() else root / ".env.example").read_text().splitlines()
generated = []
for line in lines:
    if "=" in line and not line.startswith("#"):
        key, value = line.split("=", 1)
        if key == "PARTNER_ID" and value in ("", "change_me"):
            value = "example_" + secrets.token_hex(4)
        elif not value and key in [
            "PARTNER_OAUTH_CLIENT_SECRET",
            "MUSECAT_TO_PARTNER_KEY",
            "DEMO_PASSWORD",
            "SESSION_SECRET",
        ]:
            value = secrets.token_urlsafe(32)
        elif key == "DATA_KEY" and not value:
            value = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
        line = key + "=" + value
    generated.append(line)
os.umask(0o077)
path.write_text("\n".join(generated) + "\n")
path.chmod(0o600)
print(
    "Prepared .env (existing keys preserved). Set PARTNER_ORIGIN, then register /onboarding.json in Musecat."
)
