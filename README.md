# ACEest Fitness & Gym

![CI](https://github.com/2025tm93214/aceest-fitness-gym/actions/workflows/main.yml/badge.svg)

A Flask web service for fitness and gym management, with an automated
CI/CD workflow using **Git/GitHub, Pytest, Docker, GitHub Actions and Jenkins**.

The application is a web port of the original ACEest Tkinter desktop
application. The ten legacy versions (v1.0 to v3.2.4) are kept in
[`legacy/`](legacy/) so the project history stays traceable.

## Features

- Program catalogue: Fat Loss (`FL`), Muscle Gain (`MG`), Beginner (`BG`)
- Client management with automatic daily-calorie estimate (weight x program factor)
- Weekly adherence tracking with average
- Workout logging and history
- Body metrics with BMI and category
- SQLite persistence, JSON validation and error responses

## Project structure

```
.
├── app.py                      Flask application (app factory + routes)
├── requirements.txt            Pinned dependencies
├── tests/test_app.py           Pytest suite
├── Dockerfile                  Container image definition
├── .dockerignore
├── Jenkinsfile                 Jenkins pipeline definition
├── .github/workflows/main.yml  GitHub Actions CI pipeline
├── setup.cfg                   flake8 and pytest configuration
└── legacy/                     Original Tkinter versions (reference only)
```

## Local setup and execution

Requires Python 3.9+.

```bash
git clone https://github.com/2025tm93214/aceest-fitness-gym.git
cd aceest-fitness-gym

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python app.py                      # serves on http://localhost:5000
```

Try it:

```bash
curl http://localhost:5000/programs
curl -X POST http://localhost:5000/clients \
     -H "Content-Type: application/json" \
     -d '{"name":"Arun","age":28,"weight":70,"program":"FL"}'
```

## API reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` , `/health` | Service status |
| GET | `/programs` , `/programs/<code>` | Program catalogue |
| POST | `/clients` | Create or update a client (`name, age, weight, program`) |
| GET | `/clients` , `/clients/<name>` | List or fetch clients |
| DELETE | `/clients/<name>` | Remove a client |
| POST | `/progress` | Log weekly adherence (`name, adherence` 0-100) |
| GET | `/progress/<name>` | Adherence history and average |
| POST | `/workouts` | Log workout (`name, workout_type, duration_min, date?, notes?`) |
| GET | `/workouts/<name>` | Workout history |
| POST | `/metrics` | Log `weight` (kg) and `height` (cm); returns BMI |

Valid `workout_type` values: `Strength`, `Hypertrophy`, `Cardio`, `Mobility`.

## Running tests manually

```bash
pytest -v          # run the suite
flake8 .           # lint (legacy/ is excluded)
```

Tests use an isolated temporary SQLite database per test, so they never touch real data.

### Inside Docker

```bash
docker build -t aceest-fitness .
docker run --rm aceest-fitness pytest -v      # tests in the container
docker run -p 5000:5000 aceest-fitness        # run the app
```

## Docker

The image is based on `python:3.12-slim`. Dependencies are installed before the
source is copied, so rebuilds reuse the cached layer. The app runs as a non-root
user under gunicorn, `legacy/` and other non-runtime files are excluded through
`.dockerignore`, and the SQLite database lives in `/data` (mount a volume there
to persist data: `-v aceest-data:/data`).

## CI/CD overview

### GitHub Actions (`.github/workflows/main.yml`)

Triggered on **every push and pull request**:

1. **Build & Lint**: sets up Python, installs dependencies, compiles sources
   (syntax check) and runs `flake8`.
2. **Docker Build & Test** (runs only if stage 1 passes): builds the Docker image
   and runs the Pytest suite inside the container, so tests run in the same
   environment that gets shipped.

### Jenkins (`Jenkinsfile`)

Jenkins is the secondary build and validation layer:

1. **Checkout**: pulls the latest code from GitHub.
2. **Clean Build Environment**: deletes and recreates a virtual environment and
   installs dependencies from scratch, so nothing stale is reused.
3. **Lint**: runs `flake8`.
4. **Unit Tests**: runs Pytest.
5. **Docker Build**: builds the image (skipped with a message if the Docker daemon is not
   accessible to the Jenkins user; the image build and containerised tests are verified in GitHub Actions).

**Jenkins job setup:** New Item, Pipeline, "Pipeline script from SCM", Git, set
the repository URL, branch `*/main`, script path `Jenkinsfile`, then Build Now.

## Branching and commits

- `main` is the stable branch. Work happens on `feature/*` and `docs/*`
  branches merged through pull requests.
- Commits follow Conventional Commits (`feat:`, `fix:`, `test:`, `build:`,
  `ci:`, `docs:`).
