# AGENTS.md

## Commands & Workflow
- **Bootstrap:** `make bootstrap` (first time or after dependency changes; runs `docker compose up -d` and installs `config/requirements-dev.txt`)
- **Run Locally:** `make run` (starts services, runs migrations, serves on `0.0.0.0:8127`)
- **Run Tests:** `make test` (runs full Django test suite via Docker)
- **Focused Test:** `make test ARGS="-k members.tests.ReportCompleteTests"`
- **Stop Services:** `make stop`
- **Clean Environment:** `make clean`
- **Django Management:** `docker compose exec web ./manage.py <command>` or via `make` shortcuts (`make migrate`, `make migrations`, `make createsuperuser`, `make shell_plus`, `make load_members_testdata`, `make load_providers_test_data`)

## Architecture & Conventions
- **Framework:** Django web application running inside Docker (`docker-compose.yml`).
- **Entrypoint:** `website/manage.py`.
- **Configuration:** Environment variables managed via `.env.dist` / `local_settings.py.example`.
- **Code Style:** PEP8 enforced via `.flake8`.
