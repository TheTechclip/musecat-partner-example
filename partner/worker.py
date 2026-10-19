"""Durable bilateral revocation delivery; run as one separate Compose service."""

import time

from . import create_app
from .common import ProtocolError, ledger, now, remote


def deliver(app):
    with app.app_context():
        with ledger().transaction() as tx:
            jobs = ledger().items(tx, "outbox")
        delivered = 0
        for jid, job in jobs:
            if job["next"] > now():
                continue
            try:
                if job["kind"] == "joint":
                    result = remote(
                        "POST",
                        "/partner/v1/revocations",
                        {**job["body"], "_request_id": jid},
                        joint=True,
                    )
                    if result.get("status") not in [
                        "revoked",
                        "already_revoked",
                        "unknown_generation",
                    ]:
                        raise ProtocolError("invalid_revocation_response", 502)
                elif job["kind"] == "oidc":
                    cid = app.config.get("MUSECAT_LOGIN_CLIENT_ID")
                    secret = app.config.get("MUSECAT_LOGIN_CLIENT_SECRET")
                    if not secret or cid != job["client_id"]:
                        raise ProtocolError("oidc_configuration_required", 503)
                    remote(
                        "POST",
                        "/oauth/revoke",
                        {"token": job["token"]},
                        form=True,
                        client_auth=(cid, secret),
                    )
                else:
                    remote("POST", "/oauth/revoke", {"token": job["token"]}, form=True)
                with ledger().transaction() as tx:
                    ledger().delete(tx, "outbox", jid)
                delivered += 1
            except ProtocolError:
                job["attempts"] += 1
                job["next"] = now() + min(300, 5 * 2 ** min(job["attempts"], 6))
                with ledger().transaction() as tx:
                    ledger().put(tx, "outbox", jid, job, now() + 365 * 86400)
        with ledger().transaction() as tx:
            ledger().prune(tx)
        return delivered


if __name__ == "__main__":
    application = create_app()
    while True:
        deliver(application)
        time.sleep(5)
