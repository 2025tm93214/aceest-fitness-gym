import pytest

from app import DEFAULT_VERSION, create_app


@pytest.fixture()
def client(tmp_path):
    app = create_app({"TESTING": True,
                      "DATABASE": str(tmp_path / "test.db")})
    return app.test_client()


def test_version_endpoint_default(client):
    body = client.get("/version").get_json()
    assert body["version"] == DEFAULT_VERSION
    assert body["service"] == "ACEest Fitness & Gym"
    assert body["host"]


def test_version_can_be_overridden(tmp_path):
    app = create_app({"TESTING": True, "APP_VERSION": "9.9.9",
                      "DATABASE": str(tmp_path / "v.db")})
    assert app.test_client().get("/version").get_json()["version"] == "9.9.9"


def test_index_reports_version(client):
    assert client.get("/").get_json()["version"] == DEFAULT_VERSION


def test_calories_estimate(client):
    res = client.get("/calories?program=fl&weight=70")
    assert res.status_code == 200
    assert res.get_json()["calories"] == 1540


def test_calories_invalid_program(client):
    assert client.get("/calories?program=XX&weight=70").status_code == 400


def test_calories_missing_weight(client):
    assert client.get("/calories?program=FL").status_code == 400


def test_calories_negative_weight(client):
    assert client.get("/calories?program=FL&weight=-5").status_code == 400
