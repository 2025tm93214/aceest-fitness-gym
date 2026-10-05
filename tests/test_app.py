import pytest

from app import (PROGRAMS, bmi_category, calculate_bmi, calculate_calories,
                 create_app)


@pytest.fixture()
def client(tmp_path):
    app = create_app({"TESTING": True,
                      "DATABASE": str(tmp_path / "test.db")})
    return app.test_client()


def add(client, **overrides):
    payload = {"name": "Arun", "age": 28, "weight": 70, "program": "FL"}
    payload.update(overrides)
    return client.post("/clients", json=payload)


# ---------- pure logic ----------
def test_calories_fat_loss():
    assert calculate_calories(70, "FL") == 1540


def test_calories_muscle_gain():
    assert calculate_calories(80, "MG") == 2800


def test_calories_beginner_truncates_to_int():
    assert calculate_calories(65.5, "BG") == 1703


def test_bmi_value():
    assert calculate_bmi(70, 175) == 22.9


@pytest.mark.parametrize("bmi,label", [
    (17.0, "Underweight"), (22.0, "Normal"),
    (27.0, "Overweight"), (31.0, "Obese")])
def test_bmi_categories(bmi, label):
    assert bmi_category(bmi) == label


# ---------- general ----------
def test_index(client):
    res = client.get("/")
    assert res.status_code == 200
    assert res.get_json()["status"] == "ok"


def test_health(client):
    assert client.get("/health").get_json() == {"status": "healthy"}


def test_unknown_route_returns_json_404(client):
    res = client.get("/nope")
    assert res.status_code == 404
    assert "error" in res.get_json()


# ---------- programs ----------
def test_list_programs(client):
    data = client.get("/programs").get_json()
    assert set(data) == {"FL", "MG", "BG"}
    assert data["MG"]["calorie_factor"] == 35


def test_get_program_case_insensitive(client):
    res = client.get("/programs/fl")
    assert res.status_code == 200
    assert res.get_json()["name"] == PROGRAMS["FL"]["name"]


def test_get_program_not_found(client):
    assert client.get("/programs/XX").status_code == 404


# ---------- clients ----------
def test_add_client_calculates_calories(client):
    res = add(client)
    assert res.status_code == 201
    assert res.get_json()["calories"] == 1540


def test_get_client_after_add(client):
    add(client)
    res = client.get("/clients/Arun")
    assert res.status_code == 200
    assert res.get_json()["program"] == "FL"


def test_list_clients_sorted(client):
    add(client, name="Zed")
    add(client, name="Anu")
    names = [c["name"] for c in client.get("/clients").get_json()]
    assert names == ["Anu", "Zed"]


def test_add_client_missing_name(client):
    assert add(client, name="").status_code == 400


def test_add_client_invalid_program(client):
    assert add(client, program="XYZ").status_code == 400


def test_add_client_invalid_weight(client):
    assert add(client, weight=-5).status_code == 400


def test_add_client_invalid_age(client):
    assert add(client, age="abc").status_code == 400


def test_add_client_no_json_body(client):
    assert client.post("/clients").status_code == 400


def test_update_client_replaces_record(client):
    add(client)
    add(client, weight=80, program="MG")
    data = client.get("/clients/Arun").get_json()
    assert data["calories"] == 2800
    assert len(client.get("/clients").get_json()) == 1


def test_get_missing_client(client):
    assert client.get("/clients/Ghost").status_code == 404


def test_delete_client(client):
    add(client)
    assert client.delete("/clients/Arun").status_code == 200
    assert client.get("/clients/Arun").status_code == 404


def test_delete_missing_client(client):
    assert client.delete("/clients/Ghost").status_code == 404


# ---------- progress ----------
def test_progress_logging_and_average(client):
    add(client)
    client.post("/progress", json={"name": "Arun", "adherence": 80})
    client.post("/progress", json={"name": "Arun", "adherence": 60})
    data = client.get("/progress/Arun").get_json()
    assert len(data["history"]) == 2
    assert data["average_adherence"] == 70.0


def test_progress_empty_history(client):
    add(client)
    assert client.get("/progress/Arun").get_json()["average_adherence"] is None


def test_progress_rejects_out_of_range(client):
    add(client)
    res = client.post("/progress", json={"name": "Arun", "adherence": 150})
    assert res.status_code == 400


def test_progress_unknown_client(client):
    res = client.post("/progress", json={"name": "Ghost", "adherence": 50})
    assert res.status_code == 404


# ---------- workouts ----------
def test_workout_log_and_fetch(client):
    add(client)
    res = client.post("/workouts", json={
        "name": "Arun", "workout_type": "Strength",
        "duration_min": 60, "date": "2026-01-15"})
    assert res.status_code == 201
    history = client.get("/workouts/Arun").get_json()
    assert history[0]["workout_type"] == "Strength"


def test_workout_invalid_type(client):
    add(client)
    res = client.post("/workouts", json={
        "name": "Arun", "workout_type": "Yoga", "duration_min": 30})
    assert res.status_code == 400


def test_workout_invalid_date(client):
    add(client)
    res = client.post("/workouts", json={
        "name": "Arun", "workout_type": "Cardio",
        "duration_min": 30, "date": "15-01-2026"})
    assert res.status_code == 400


def test_workout_unknown_client(client):
    res = client.post("/workouts", json={
        "name": "Ghost", "workout_type": "Cardio", "duration_min": 30})
    assert res.status_code == 404


# ---------- metrics ----------
def test_metrics_returns_bmi(client):
    add(client)
    res = client.post("/metrics", json={
        "name": "Arun", "weight": 70, "height": 175})
    assert res.status_code == 201
    body = res.get_json()
    assert body["bmi"] == 22.9
    assert body["category"] == "Normal"


def test_metrics_missing_height(client):
    add(client)
    res = client.post("/metrics", json={"name": "Arun", "weight": 70})
    assert res.status_code == 400
