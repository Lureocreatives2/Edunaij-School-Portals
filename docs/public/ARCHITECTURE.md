# Architecture

config/ contains Django settings and routing. Applications live in django_school_management/. Shared helpers, middleware, templates and assets live in utilities/, permission_handlers/, context_processors/, templates/ and static/.

The request host selects the school tenant. Reserved platform hosts have no school tenant. Domain selection must be combined with record-level school and user relationship checks; a record identifier is never sufficient authority.

Platform-owner access is separate from school administration. Ordinary signup does not grant superuser privileges. Local settings use SQLite, in-memory caching and eager Celery tasks. Production requires separate operational configuration. Runtime credentials, uploaded files and database contents are excluded from source packages.
