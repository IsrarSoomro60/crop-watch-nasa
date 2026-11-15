from fastapi.testclient import TestClient

from app.main import app
from app.repositories.farms import SqliteFarmRepository
from app.schemas.farm import FarmCreate, FarmResources, Location


def _farm(name: str) -> FarmCreate:
    return FarmCreate(name=name, location=Location(latitude=30.2, longitude=71.47),
                      resources=FarmResources(area_hectares=2.0))


def test_sqlite_farms_survive_a_restart(tmp_path):
    db = tmp_path / "farms.db"
    created = SqliteFarmRepository(db).create(_farm("Field A"))

    reopened = SqliteFarmRepository(db)  # new instance = app restart
    assert reopened.get(created.id) == created
    assert [f.name for f in reopened.list()] == ["Field A"]
    assert reopened.get("missing") is None


def test_unhandled_errors_return_json_without_internals():
    @app.get("/boom-test")
    def boom():
        raise RuntimeError("secret internal detail")

    resp = TestClient(app, raise_server_exceptions=False).get("/boom-test")
    assert resp.status_code == 500
    assert resp.json() == {"detail": "Internal error; the server log has details."}
    assert "secret" not in resp.text
