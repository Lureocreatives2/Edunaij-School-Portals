# edunaij

Multi-tenant school management for Nigerian schools, with a separate platform-owner dashboard for organisations, subscriptions and release announcements.

**Status: active development.** Local development is supported. Production deployment and live billing require environment-specific validation.

## Features

- Platform controls for schools, plans, subscription status, suspension and release notices.
- School administration, students, teachers, classes and guardian relationships.
- Learning, grading, results and reports.
- Tenant-aware permissions and protected school records.
- Paystack callback validation and payment matching.

Release notices communicate changes; they do not deploy code. Plan configuration alone does not establish recurring billing. Legacy Stripe, SSLCommerz and Braintree checkout paths are disabled pending verification.

## Quickstart

The working environment uses Python 3.14.4 and Django 6.0.8. The requirements snapshot records that environment; it is not a hash lock. Local settings use SQLite, in-memory caching and synchronous background tasks, so PostgreSQL and a running Redis server are not required.

Fork and clone this repository, then open its folder. In Windows PowerShell:

```powershell
py -3.14 -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe scripts/setup_local.py
.venv/Scripts/python.exe manage.py migrate
.venv/Scripts/python.exe manage.py createsuperuser
.venv/Scripts/python.exe manage.py runserver 127.0.0.1:8000
```

On macOS/Linux, create the environment with `python3.14 -m venv .venv` and use `.venv/bin/python` for subsequent commands.

Open [the platform login](http://127.0.0.1:8000/platform/login/) and use the superuser you created. No accounts, passwords or school records are bundled. Local email is printed in the terminal. The setup helper creates `envs/.env` with a unique secret and never overwrites existing configuration.

## Platform and school accounts

Platform owners manage organisations and subscriptions. School administrators operate within their school. Public signup never grants platform-owner access.

The sample reserves localhost and 127.0.0.1 for the platform. School onboarding requires a tenant, its institute, offered classes and an administrator linked to that tenant and institute. Use `/admin/` for advanced setup. Configure a school subdomain or verified domain before inviting users. A school host such as school.localhost must resolve to this server and be permitted by host/origin settings. Do not assign a platform host to a school.

## Checks and source package

```powershell
.venv/Scripts/python.exe scripts/check_project.py
.venv/Scripts/python.exe scripts/package_source.py
```

The package command creates a curated ZIP, file manifest and SHA256 checksum under `dist/`, excluding databases, secrets, uploads, backups and internal reports. Review it before sharing. See [contributing](CONTRIBUTING.md), [architecture](docs/public/ARCHITECTURE.md), [deployment](docs/public/DEPLOYMENT.md) and [GitHub publishing guidance](docs/public/GITHUB.md).

## Licensing and provenance

edunaij is owned by the project maintainer. All rights reserved. This is not an open-source release; permission from the owner is required for reuse, modification or redistribution, except where applicable law or hosting-platform terms permit otherwise. See [LICENSE](LICENSE). Third-party components retain their own licences; see [third-party notices](THIRD_PARTY_NOTICES.md).

## Roadmap

Priorities include complete school onboarding, repeatable production deployment, provider subscription reconciliation, accessibility review and broader end-to-end coverage. Existing Docker and performance configurations are historical references, not a verified production recipe. See [security reporting](SECURITY.md).

## Developer and partnerships

Developed by **Adeshina Opeyemi**. For school onboarding, product enquiries or partnership opportunities, contact [opeyemiolamide882@gmail.com](mailto:opeyemiolamide882@gmail.com).

GitHub: [Lureocreatives2](https://github.com/Lureocreatives2).
