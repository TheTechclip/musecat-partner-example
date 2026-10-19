"""Small encrypted SQLite ledger. Atomic writes serialize code/intent consumption."""

import hashlib
import json
import sqlite3
import time
from contextlib import contextmanager

from cryptography.fernet import Fernet


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


class Ledger:
    def __init__(self, path, key):
        self.path, self.cipher = path, Fernet(key.encode())
        with self.transaction() as tx:
            tx.execute(
                "CREATE TABLE IF NOT EXISTS ledger (kind TEXT, id TEXT, value BLOB, expires INTEGER, PRIMARY KEY(kind,id))"
            )

    @contextmanager
    def transaction(self):
        db = sqlite3.connect(self.path, timeout=15)
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def get(self, tx, kind, key):
        row = tx.execute(
            "SELECT value FROM ledger WHERE kind=? AND id=? AND expires>?",
            (kind, key, int(time.time())),
        ).fetchone()
        return json.loads(self.cipher.decrypt(row[0])) if row else None

    def put(self, tx, kind, key, value, expires):
        tx.execute(
            "INSERT OR REPLACE INTO ledger VALUES(?,?,?,?)",
            (kind, key, self.cipher.encrypt(json.dumps(value).encode()), expires),
        )

    def delete(self, tx, kind, key):
        tx.execute("DELETE FROM ledger WHERE kind=? AND id=?", (kind, key))

    def items(self, tx, kind):
        rows = tx.execute(
            "SELECT id,value FROM ledger WHERE kind=? AND expires>?",
            (kind, int(time.time())),
        ).fetchall()
        return [(key, json.loads(self.cipher.decrypt(value))) for key, value in rows]

    def prune(self, tx):
        tx.execute("DELETE FROM ledger WHERE expires<=?", (int(time.time()),))
