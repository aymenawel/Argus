from argus.storage.audit import verify_chain
from argus.storage.repos import add_measurements
from tests.records import draft


def test_chain_links_batches_and_verifies(db, run, vessel):
    add_measurements(db, run.id, [draft(vessel.id, t=0.0)])
    add_measurements(db, run.id, [draft(vessel.id, t=300.0), draft(vessel.id, t=600.0)])
    with db.read() as c:
        hashes = [
            r[0] for r in c.execute("SELECT sha256 FROM audit_chain WHERE run_id=? ORDER BY batch_index", (run.id,))
        ]
    assert len(hashes) == 2 and hashes[0] != hashes[1] and verify_chain(db, run.id)


def test_a_changed_hash_breaks_verification(db, run, vessel):
    add_measurements(db, run.id, [draft(vessel.id, t=0.0)])
    with db.write() as c:
        c.execute("UPDATE audit_chain SET sha256=? WHERE run_id=?", ("f" * 64, run.id))
    assert not verify_chain(db, run.id)
