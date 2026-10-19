#!/usr/bin/env python3
"""Start automatic HTTPS for a local sample, preserving existing credentials."""

import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
URL = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com\b")


def configure(path, origin):
    lines = path.read_text().splitlines()
    values = {"PARTNER_ORIGIN": origin, "PARTNER_HOST": origin.removeprefix("https://")}
    seen = set()
    result = []
    for line in lines:
        key = line.split("=", 1)[0]
        if key in values:
            line = key + "=" + values[key]
            seen.add(key)
        result.append(line)
    result.extend(key + "=" + value for key, value in values.items() if key not in seen)
    path.write_text("\n".join(result) + "\n")
    path.chmod(0o600)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8088)
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument(
        "--no-compose",
        action="store_true",
        help="Only configure the origin; caller starts its own isolated container",
    )
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    if not args.env_file.is_file():
        parser.error("Run python scripts/init-env.py first")
    binary = shutil.which("cloudflared")
    if not binary:
        parser.error(
            "Install cloudflared first: https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/downloads/"
        )
    if not args.no_compose and args.env_file.resolve() != (ROOT / ".env").resolve():
        parser.error(
            "Compose uses the project's .env; custom env-file requires --no-compose"
        )
    os.umask(0o077)
    process = subprocess.Popen(
        [
            binary,
            "tunnel",
            "--url",
            "http://127.0.0.1:" + str(args.port),
            "--no-autoupdate",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    ready = False
    try:
        for line in process.stdout:
            found = URL.search(line)
            if not found or ready:
                continue
            origin = found.group()
            configure(args.env_file, origin)
            if not args.no_compose:
                subprocess.run(
                    [
                        "docker",
                        "compose",
                        "up",
                        "-d",
                        "--build",
                        "--force-recreate",
                        "app",
                        "worker",
                    ],
                    cwd=ROOT,
                    check=True,
                )
            ready = True
            print("Sample URL: " + origin, flush=True)
            print(
                "Registration JSON: " + origin + "/onboarding.json?flow=b", flush=True
            )
            print(
                "Register this development app in Musecat Developer Center; owner/testers can connect immediately. Keep this process running. A changed URL requires updated registration and new consent.",
                flush=True,
            )
        if not ready:
            raise SystemExit(
                "Tunnel did not become ready. Check cloudflared and network access."
            )
        raise SystemExit(process.wait())
    except KeyboardInterrupt:
        pass
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


if __name__ == "__main__":
    main()
