"""Tamper-evident log: each batch of measurements is hashed together with the previous batch's hash."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Sequence
from datetime import UTC, datetime

from argus.domain import Measurement
from argus.storage.db import Database

GENESIS = "0" * 64


def batch_hash(previous: str, rows: Sequence[Measurement]) -> str:
    payload = json.dumps([row.model_dump(mode="json") for row in rows], sort_keys=True, separators=(",", ":"))
    return hashlib.sha256((previous + payload).encode("utf-8")).hexdigest()


def append_batch(conn: sqlite3.Connection, run_id: str, rows: Sequence[Measurement]) -> str:
    """Add one link to the run's chain; call inside the transaction that stores the rows."""
    last = conn.execute(
        "SELECT batch_index, sha256 FROM audit_chain WHERE run_id=? ORDER BY batch_index DESC LIMIT 1", (run_id,)
    ).fetchone()
    index, previous = (0, GENESIS) if last is None else (last[0] + 1, last[1])
    digest = batch_hash(previous, rows)
    conn.execute(
        "INSERT INTO audit_chain(run_id, batch_index, sha256, measurement_ids, created_at) VALUES (?,?,?,?,?)",
        (run_id, index, digest, json.dumps([r.id for r in rows]), datetime.now(UTC).isoformat()),
    )
    return digest


def verify_chain(db: Database, run_id: str) -> bool:
    """Recompute every link from the stored measurements; False if any hash or row differs."""
    columns = "id, vessel_id, frame_id, t, metric, value, uncertainty, unit, method_version"
    with db.read() as c:
        links = c.execute(
            "SELECT sha256, measurement_ids FROM audit_chain WHERE run_id=? ORDER BY batch_index", (run_id,)
        ).fetchall()
        stored = {
            r["id"]: Measurement(**dict(r))
            for r in c.execute(f"SELECT {columns} FROM measurements WHERE run_id=?", (run_id,))
        }
    previous, covered = GENESIS, set()
    for link in links:
        ids = json.loads(link["measurement_ids"])
        if any(i not in stored for i in ids) or batch_hash(previous, [stored[i] for i in ids]) != link["sha256"]:
            return False
        previous = link["sha256"]
        covered.update(ids)
    return covered == set(stored)
