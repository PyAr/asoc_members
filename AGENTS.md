# AGENTS.md

This file provides core instructions for OpenCode agents working in the `asoc_members` repository (Python Argentina Membership Management System).

## Build, Test, and Development Commands

- **Bootstrap / Setup**: `make bootstrap` (first time or after dependency changes; runs `docker compose up -d` and installs `config/requirements-dev.txt` / dependencies in the container)
- **Run Locally**: `make run` (starts services, runs migrations, and serves on `0.0.0.0:8127`)
- **Run Tests**: `make test` (runs full Django test suite via Docker)
  - Focused Test: `make test ARGS="-k members.tests.ReportCompleteTests"`
- **Stop Services**: `make stop`
- **Clean Environment**: `make clean`
- **Django Management & Utilities**:
  - Django shell plus: `make shell_plus`
  - Docker shell: `make dockershell`
  - Create superuser: `make createsuperuser`
  - Make migrations: `make migrations`
  - Run migrations: `make migrate`
  - Load test data: `make load_members_testdata`
  - Load providers test data: `make load_providers_test_data`

## Architecture & Codebase Layout

- **Framework**: Django web application running inside Docker (`docker-compose.yml`) with `django-configurations`.
- **Entrypoint**: `website/manage.py`.
- **Core Apps & URL Map**:
  - `website/members/`: Main business logic for membership management, payments (MercadoPago integrations, invoicing, quotas, reports).
    - Routes (`/`): `/solicitud-alta/`, `/reportes/`, `/reportes/deudas`, `/reportes/completos`, `/reportes/incompletos`, `/reportes/ingcuotas`, `/reportes/ingdinero`, `/reportes/miembros`, `/reportes/miembros/<pk>/`.
  - `website/events/`: Management of events, sponsors, expenses, and providers.
    - Routes (`/eventos/`): `/eventos/`, `/eventos/eventos/`, `/eventos/eventos/<pk>/configuracion/`, `/eventos/eventos/<pk>/patrocinios/`, `/eventos/eventos/<pk>/gastos/`, etc.
  - `website/pyar_auth/`: Authentication views/forms.
    - Routes (`/cuentas/`): `/cuentas/login/`, `/cuentas/logout/`, `/cuentas/perfil/`, `/cuentas/clave/`, etc.
  - `website/website/`: Django project settings (`settings.py`), URL router (`urls.py`), and WSGI config.
- **Configuration**: Environment variables managed via `.env.dist` / `local_settings.py.example`.
- **Docker Setup**: Application runs inside Docker containers (`docker compose`). Use `make` commands.

## Coding Conventions & Gotchas

- **PEP8 & Style**: PEP8 enforced via `.flake8` (line width limit: 99 columns).
- **Language**:
  - Variable names, docstrings, and code comments must be in **English**.
  - Docstrings must start with an uppercase letter and end with a period (`"""This is a docstring."""`).
  - **URLs** must be written in **Spanish** (for SEO purposes, per issue #163).
- **Database & Migrations**: Every model change requires a corresponding migration (`make migrations`).
- **Tests**: Add unit/integration tests for new features and bug fixes when possible.
- **Versioning & Releases**:
  - When preparing a new release for production, tag the commit in git (e.g. `git tag -a vX.Y.Z -m "Release vX.Y.Z"`).
  - Update the `image` tag in `docker-compose.yml` (e.g. `image: asoc_members:vX.Y.Z`) to keep the Docker image version in sync with the git tag.
- **Development Workflow & UX Guidelines**:
  - **Tests Execution**: Do not run test suites automatically unless explicitly requested by the user.
  - **PR Management**: Do not push or create pull requests on GitHub until the user explicitly gives final approval.
  - **UI/UX Consistency**: Ensure uniform container max-widths (`max-width: 88%`), consistent vertical margins/spacings between headers and breadcrumbs, and matching column orders and terminology across all tables and modules.
