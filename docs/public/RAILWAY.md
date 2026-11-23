# Deploy edunaij on Railway

This hosts the complete Django app, including the landing page, school registration and platform dashboard. No separate frontend hosting is needed. Use the repository's Dockerfile; it installs the tested Python 3.14 dependencies and starts Gunicorn on Railway's PORT. It does not bake administrator credentials or a database into the image.

## 1. Create the project

Sign in at https://railway.com with GitHub. Create a project from **Lureocreatives2/Edunaij-School-Portals**, branch **main**. Use the repository root as the source directory. Railway detects Dockerfile automatically. Leave build and start overrides empty. Initial deployment may fail until the variables below are supplied; configure them and redeploy.

Add a PostgreSQL service to the same project. On the edunaij web service, add a reference variable named DATABASE_URL pointing to Postgres's DATABASE_URL, normally `${{Postgres.DATABASE_URL}}`. The namespace must match your actual database service name. Do not copy the public database password into GitHub.

The default profile uses a shared PostgreSQL cache and synchronous tasks, avoiding a separate Redis bill. Keep one web replica. If you later add Redis, reference its REDIS_URL and redeploy. Add a dedicated worker before moving tasks out of the web process.

## 2. Add web-service variables

Use the web service's Variables editor, not a public repository file:

| Variable | Value |
| --- | --- |
| RAILWAY_DEPLOYMENT | True |
| DEBUG | False |
| DJANGO_SETTINGS_MODULE | config.settings |
| SECRET_KEY | A newly generated, private random value; keep it stable |
| DATABASE_URL | Reference to the PostgreSQL service |
| PROMETHEUS_EXPORT_MIGRATIONS | False |
| USE_PAYMENT_OPTIONS | False |
| USE_STRIPE | False |
| MEDIA_ROOT | /app/media for a temporary demo; see persistent uploads below |
| ALLOW_EPHEMERAL_MEDIA | True **only for a demo without an upload volume** |
| BOOTSTRAP_PLATFORM_OWNER | True for the first successful deployment |
| DJANGO_SUPERUSER_USERNAME | edunaij-owner |
| DJANGO_SUPERUSER_EMAIL | Your owner email, e.g. opeyemiolamide882@gmail.com |
| DJANGO_SUPERUSER_PASSWORD | Your own strong, unique initial password |

Generate SECRET_KEY locally with `python -c "import secrets; print(secrets.token_urlsafe(64))"`. Put it directly into Railway. Do not share it or use the example local-development key. Changing it affects sessions and encrypted MFA secrets.

Under **Settings > Networking**, generate a public domain. Under deployment settings set **Healthcheck Path** to `/health/` and **Healthcheck Timeout** to 300 seconds. Railway supplies RAILWAY_PUBLIC_DOMAIN automatically; the app adds that exact host to the platform, allowed hosts and CSRF origins. If you generate a domain after a deployment has started, redeploy so the process sees it. Do not use wildcard allowed hosts. Health probes also accept Railway's documented healthcheck.railway.app hostname.

## 3. Create and secure the platform owner

Startup checks settings, applies migrations, creates the shared cache table, creates the initial owner if opted in, collects assets, then starts Gunicorn. It never changes the password of an existing owner and refuses to promote an existing school account.

After a successful deployment, remove BOOTSTRAP_PLATFORM_OWNER and all three DJANGO_SUPERUSER_* variables, and redeploy. Then open `https://YOUR-DOMAIN/platform/login/`, sign in with your email and chosen password, enroll your authenticator and save the recovery codes offline. The school approval list is `/platform/registrations/`.

You can alternatively create the owner interactively with `python manage.py createsuperuser` through Railway SSH if available on your plan. Do not expose an HTTP endpoint to create administrators. Local users, Nice College records and uploads do not automatically transfer to Railway.

## 4. Decide where uploads live

The free demo variables above explicitly allow temporary uploads. Files in /app/media are lost when the app container is replaced. Database rows and accounts survive only while the PostgreSQL volume is retained. Do not upload real CAC documents, student photos or school records to this demo configuration.

For durable uploads, attach a **separate web-service volume** at `/data`, set MEDIA_ROOT=/data/media and remove ALLOW_EPHEMERAL_MEDIA. Railway supplies RAILWAY_VOLUME_MOUNT_PATH. Its volumes are root-owned; for this image Railway documents setting RAILWAY_RUN_UID=0 when a non-root image needs access to a volume. Review that permission tradeoff or arrange ownership for UID 10001 before using real records. The default image runs as UID 10001 without a volume.

Railway's currently documented Free plan permits only one volume. A Railway PostgreSQL service normally uses that volume, so PostgreSQL plus a second upload volume may require upgrading. To remain within the free allocation with durable uploads, use an external PostgreSQL provider and reserve the Railway volume for web uploads, subject to both providers' limits and network availability. Shared object storage is another future integration; it is not configured by this profile. Do not attach the web volume over /app or use SQLite on the ephemeral filesystem.

## 5. Configure email through HTTPS

Railway Free, Trial and Hobby block outbound SMTP. This project includes a Resend HTTPS email backend using the existing requests dependency. Set RESEND_API_KEY to your private provider key and DEFAULT_FROM_EMAIL to a sender verified with Resend. This automatically enables delivery on Railway. Without a key, delivery is disabled using Django's dummy backend; recovery links are not printed to deployment logs. School registration can be demonstrated, but email notifications and password recovery are unavailable until configured.

Provider free quotas and sandbox recipient restrictions still apply. Verify delivery and recovery in your own inbox before inviting schools. This sends transactional messages; it does not provision school mailboxes. Keep SCHOOL_EMAIL_DOMAIN unset until actual domain/provider provisioning is ready.

## 6. Verify and monitor

Check `/`, `/platform/register/`, `/accounts/login/` and `/health/`. Health should return HTTP 200 with database and cache checks marked ok. Test owner MFA, a fictional school registration, approval, two school tenants and protected uploads. Back up the database and durable media separately and test restoration. Read build and runtime logs if deployment fails; redact credentials before sharing errors.

For custom platform domains, add the hostname to ALLOWED_HOSTS and PLATFORM_HOSTS and its HTTPS origin to CSRF_TRUSTED_ORIGINS. School domains belong in ALLOWED_HOSTS and CSRF_TRUSTED_ORIGINS, and must map to their school tenant; keep them out of PLATFORM_HOSTS. Domain availability depends on your Railway plan.

Free is usage-limited, not unlimited hosting: Railway currently documents $5 trial usage for 30 days, then a Free plan with $1 monthly usage. Switching to Free after trial may need action in the Plans page. Services sleep and stop when credits run out; trial data retention is limited. Review the current dashboard and retention terms, and export demo data before expiry. No paid service is created by this repository preparation.

## Local verification

Run `python scripts/verify_railway.py` to check production host routing, PostgreSQL/cache settings, storage guards and production asset serving without a Railway account. Run `python scripts/check_project.py` for regressions. These checks do not validate a Linux image build, hosted PostgreSQL connectivity, provider email delivery or actual Railway provisioning.

## Official references

- https://docs.railway.com/builds/dockerfiles
- https://docs.railway.com/variables/reference
- https://docs.railway.com/deployments/healthchecks
- https://docs.railway.com/volumes
- https://docs.railway.com/networking/outbound-networking
- https://docs.railway.com/pricing/free-plan
- https://resend.com/docs/api-reference/emails/send-email
