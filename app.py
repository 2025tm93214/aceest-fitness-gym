"""ACEest Fitness & Gym - Flask service.

Web port of the legacy Tkinter desktop versions (see ``legacy/``).
Provides program catalogue, client management, weekly adherence
tracking, workout logging and body-metric (BMI) endpoints.
"""
import os
import sqlite3
from datetime import date, datetime

from flask import Flask, g, jsonify, request

# Calorie factor (kcal per kg body weight) - carried over from legacy v1.1+
PROGRAMS = {
    "FL": {
        "name": "Fat Loss",
        "workout": "Mon: Back Squat 5x5 | Tue: EMOM 20min Assault Bike | "
                   "Wed: Bench Press + 21-15-9 | Thu: Deadlift + Box Jumps | "
                   "Fri: Zone 2 Cardio 30min",
        "diet": "Egg Whites + Oats | Grilled Chicken + Brown Rice | "
                "Fish Curry + Millet Roti (~2000 kcal)",
        "calorie_factor": 22,
    },
    "MG": {
        "name": "Muscle Gain",
        "workout": "Mon: Squat 5x5 | Tue: Bench 5x5 | Wed: Deadlift 4x6 | "
                   "Thu: Front Squat 4x8 | Fri: Incline Press 4x10 | "
                   "Sat: Barbell Rows 4x10",
        "diet": "Eggs + Peanut Butter Oats | Chicken Biryani | "
                "Mutton Curry + Rice (~3200 kcal)",
        "calorie_factor": 35,
    },
    "BG": {
        "name": "Beginner",
        "workout": "Full Body Circuit: Air Squats, Ring Rows, Push-ups. "
                   "Focus: Technique & Consistency",
        "diet": "Balanced Tamil Meals: Idli/Dosa/Rice + Dal. "
                "Protein target 120g/day",
        "calorie_factor": 26,
    },
}

WORKOUT_TYPES = {"Strength", "Hypertrophy", "Cardio", "Mobility"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    age INTEGER,
    weight REAL,
    program TEXT,
    calories INTEGER
);
CREATE TABLE IF NOT EXISTS progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name TEXT NOT NULL,
    week TEXT NOT NULL,
    adherence INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS workouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name TEXT NOT NULL,
    date TEXT NOT NULL,
    workout_type TEXT NOT NULL,
    duration_min INTEGER NOT NULL,
    notes TEXT
);
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name TEXT NOT NULL,
    date TEXT NOT NULL,
    weight REAL NOT NULL,
    height REAL,
    waist REAL,
    bodyfat REAL
);
"""


# ---------- pure business logic (easy to unit test) ----------
def calculate_calories(weight_kg, program_code):
    """Estimated daily calories = weight x program calorie factor."""
    return int(weight_kg * PROGRAMS[program_code]["calorie_factor"])


def calculate_bmi(weight_kg, height_cm):
    """BMI rounded to 1 decimal place."""
    height_m = height_cm / 100
    return round(weight_kg / (height_m ** 2), 1)


def bmi_category(bmi):
    if bmi < 18.5:
        return "Underweight"
    if bmi < 25:
        return "Normal"
    if bmi < 30:
        return "Overweight"
    return "Obese"


def _error(message, status=400):
    return jsonify({"error": message}), status


def _number(value, minimum=None, maximum=None):
    """Return value as float if numeric and in range, else None."""
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if minimum is not None and number < minimum:
        return None
    if maximum is not None and number > maximum:
        return None
    return number


# ---------- application factory ----------
def create_app(test_config=None):
    app = Flask(__name__)
    app.config["DATABASE"] = os.environ.get("ACEEST_DB", "aceest_fitness.db")
    if test_config:
        app.config.update(test_config)

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(_exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    with app.app_context():
        get_db().executescript(SCHEMA)

    def client_exists(name):
        row = get_db().execute(
            "SELECT 1 FROM clients WHERE name=?", (name,)).fetchone()
        return row is not None

    # ----- general -----
    @app.get("/")
    def index():
        return jsonify({"service": "ACEest Fitness & Gym", "status": "ok"})

    @app.get("/health")
    def health():
        return jsonify({"status": "healthy"})

    # ----- programs -----
    @app.get("/programs")
    def list_programs():
        return jsonify(PROGRAMS)

    @app.get("/programs/<code>")
    def get_program(code):
        program = PROGRAMS.get(code.upper())
        if not program:
            return _error("Program not found", 404)
        return jsonify(program)

    # ----- clients -----
    @app.post("/clients")
    def add_client():
        data = request.get_json(silent=True) or {}
        name = str(data.get("name", "")).strip()
        program = str(data.get("program", "")).upper()
        age = _number(data.get("age"), 1, 120)
        weight = _number(data.get("weight"), 1, 500)
        if not name:
            return _error("name is required")
        if program not in PROGRAMS:
            return _error("program must be one of: FL, MG, BG")
        if age is None:
            return _error("age must be a number between 1 and 120")
        if weight is None:
            return _error("weight must be a positive number (kg)")
        calories = calculate_calories(weight, program)
        db = get_db()
        db.execute(
            "INSERT OR REPLACE INTO clients "
            "(name, age, weight, program, calories) VALUES (?,?,?,?,?)",
            (name, int(age), weight, program, calories))
        db.commit()
        return jsonify({"name": name, "age": int(age), "weight": weight,
                        "program": program, "calories": calories}), 201

    @app.get("/clients")
    def list_clients():
        rows = get_db().execute(
            "SELECT name, age, weight, program, calories "
            "FROM clients ORDER BY name").fetchall()
        return jsonify([dict(r) for r in rows])

    @app.get("/clients/<name>")
    def get_client(name):
        row = get_db().execute(
            "SELECT name, age, weight, program, calories "
            "FROM clients WHERE name=?", (name,)).fetchone()
        if not row:
            return _error("Client not found", 404)
        return jsonify(dict(row))

    @app.delete("/clients/<name>")
    def delete_client(name):
        db = get_db()
        cur = db.execute("DELETE FROM clients WHERE name=?", (name,))
        db.commit()
        if cur.rowcount == 0:
            return _error("Client not found", 404)
        return jsonify({"deleted": name})

    # ----- weekly progress -----
    @app.post("/progress")
    def add_progress():
        data = request.get_json(silent=True) or {}
        name = str(data.get("name", "")).strip()
        adherence = _number(data.get("adherence"), 0, 100)
        if not name or adherence is None:
            return _error("name and adherence (0-100) are required")
        if not client_exists(name):
            return _error("Client not found", 404)
        week = datetime.now().strftime("Week %U - %Y")
        db = get_db()
        db.execute(
            "INSERT INTO progress (client_name, week, adherence) "
            "VALUES (?,?,?)", (name, week, int(adherence)))
        db.commit()
        return jsonify({"name": name, "week": week,
                        "adherence": int(adherence)}), 201

    @app.get("/progress/<name>")
    def get_progress(name):
        if not client_exists(name):
            return _error("Client not found", 404)
        rows = get_db().execute(
            "SELECT week, adherence FROM progress "
            "WHERE client_name=? ORDER BY id", (name,)).fetchall()
        history = [dict(r) for r in rows]
        average = (round(sum(r["adherence"] for r in history) / len(history), 1)
                   if history else None)
        return jsonify({"name": name, "history": history,
                        "average_adherence": average})

    # ----- workouts -----
    @app.post("/workouts")
    def add_workout():
        data = request.get_json(silent=True) or {}
        name = str(data.get("name", "")).strip()
        wtype = data.get("workout_type")
        duration = _number(data.get("duration_min"), 1, 600)
        when = data.get("date") or date.today().isoformat()
        try:
            date.fromisoformat(when)
        except (TypeError, ValueError):
            return _error("date must be YYYY-MM-DD")
        if not name:
            return _error("name is required")
        if wtype not in WORKOUT_TYPES:
            return _error("workout_type must be one of: "
                          + ", ".join(sorted(WORKOUT_TYPES)))
        if duration is None:
            return _error("duration_min must be between 1 and 600")
        if not client_exists(name):
            return _error("Client not found", 404)
        db = get_db()
        db.execute(
            "INSERT INTO workouts "
            "(client_name, date, workout_type, duration_min, notes) "
            "VALUES (?,?,?,?,?)",
            (name, when, wtype, int(duration), data.get("notes", "")))
        db.commit()
        return jsonify({"name": name, "date": when, "workout_type": wtype,
                        "duration_min": int(duration)}), 201

    @app.get("/workouts/<name>")
    def get_workouts(name):
        if not client_exists(name):
            return _error("Client not found", 404)
        rows = get_db().execute(
            "SELECT date, workout_type, duration_min, notes FROM workouts "
            "WHERE client_name=? ORDER BY date DESC", (name,)).fetchall()
        return jsonify([dict(r) for r in rows])

    # ----- body metrics -----
    @app.post("/metrics")
    def add_metrics():
        data = request.get_json(silent=True) or {}
        name = str(data.get("name", "")).strip()
        weight = _number(data.get("weight"), 1, 500)
        height = _number(data.get("height"), 50, 260)
        if not name:
            return _error("name is required")
        if weight is None or height is None:
            return _error("weight (kg) and height (cm) are required")
        if not client_exists(name):
            return _error("Client not found", 404)
        bmi = calculate_bmi(weight, height)
        db = get_db()
        db.execute(
            "INSERT INTO metrics (client_name, date, weight, height) "
            "VALUES (?,?,?,?)",
            (name, date.today().isoformat(), weight, height))
        db.commit()
        return jsonify({"name": name, "bmi": bmi,
                        "category": bmi_category(bmi)}), 201

    @app.errorhandler(404)
    def not_found(_e):
        return _error("Resource not found", 404)

    @app.errorhandler(405)
    def bad_method(_e):
        return _error("Method not allowed", 405)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
