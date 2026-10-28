import pytest

from argus.domain import Role, RunMode, VesselDraft
from argus.storage.db import Database
from argus.storage.repos import add_vessels, create_experiment, create_run


@pytest.fixture
def db(tmp_path):
    database = Database(tmp_path / "data dir é" / "argus.sqlite")
    yield database
    database.close()


@pytest.fixture
def exp(db):
    return create_experiment(db, "Salt-stress germination", "seed-germination", 1)


@pytest.fixture
def run(db, exp):
    return create_run(db, exp.id, RunMode.IMPORTED, time_scale=600.0)


@pytest.fixture
def vessel(db, run):
    return add_vessels(db, run.id, [VesselDraft(label="A", role=Role.TREATMENT, roi=[(0, 0), (10, 0), (10, 30)])])[0]
