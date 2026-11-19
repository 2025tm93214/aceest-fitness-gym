import pytest

from app import create_app


@pytest.fixture()
def client(tmp_path):
    app = create_app({"TESTING": True,
                      "DATABASE": str(tmp_path / "test.db")})
    return app.test_client()


def add_client(c, name="Arun"):
    return c.post("/clients", json={"name": name, "age": 28,
                                    "weight": 70, "program": "FL"})


def test_version_is_2_0_0(client):
    assert client.get("/version").get_json()["version"] == "2.0.0"


def test_summary_empty_client(client):
    add_client(client)
    body = client.get("/clients/Arun/summary").get_json()
    assert body["client"]["calories"] == 1540
    assert body["program_name"] == "Fat Loss"
    assert body["adherence"] == {"weeks_logged": 0, "average": None}
    assert body["workouts"] == {"count": 0, "total_minutes": 0}
    assert body["bmi"] is None


def test_summary_with_data(client):
    add_client(client)
    client.post("/progress", json={"name": "Arun", "adherence": 80})
    client.post("/progress", json={"name": "Arun", "adherence": 60})
    client.post("/workouts", json={"name": "Arun", "workout_type": "Cardio",
                                   "duration_min": 30})
    client.post("/workouts", json={"name": "Arun", "workout_type": "Strength",
                                   "duration_min": 45})
    client.post("/metrics", json={"name": "Arun", "weight": 70, "height": 175})
    body = client.get("/clients/Arun/summary").get_json()
    assert body["adherence"]["average"] == 70.0
    assert body["adherence"]["weeks_logged"] == 2
    assert body["workouts"] == {"count": 2, "total_minutes": 75}
    assert body["bmi"] == 22.9
    assert body["bmi_category"] == "Normal"


def test_summary_unknown_client(client):
    assert client.get("/clients/Ghost/summary").status_code == 404
