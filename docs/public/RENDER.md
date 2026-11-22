# Deploy edunaij on Render

This deployment serves the landing page, school registration, sign-in and every dashboard from Django. WhiteNoise serves the CSS, JavaScript, classroom photos and product screenshot. No frontend build command is needed.

## Create the services

1. Sign in to Render and connect GitHub with access to Lureocreatives2/Edunaij-School-Portals.
2. Choose New > Blueprint and select the repository's main branch. Render reads render.yaml.
3. Review the web service, PostgreSQL, Key Value and persistent disk plans before confirming. The Blueprint uses paid resources. Check the current costs shown by Render.
4. Supply EMAIL_HOST, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD and DEFAULT_FROM_EMAIL for your SMTP provider. Use a verified sender. Port 587 with STARTTLS is configured. Never commit these values. Your public contact email can remain separate from the SMTP sender.
5. Apply the Blueprint. The build installs requirements, collects frontend assets and checks secure settings. Startup applies migrations before Gunicorn accepts traffic.
6. Open the web service's onrender.com address. Its hostname is added to ALLOWED_HOSTS, PLATFORM_HOSTS and CSRF_TRUSTED_ORIGINS automatically.
7. In the web service Shell, run `python manage.py createsuperuser`. Sign in at /platform/login/, enroll an authenticator and save your recovery codes offline.

The build does not create administrator accounts. Mailbox provisioning requires an email provider integration. SCHOOL_EMAIL_DOMAIN should stay unset until you have selected the domain to use for school addresses.

## School domains

The onrender.com hostname hosts the platform. Add each school's domain or subdomain to the Render service, configure its DNS and add the exact hostname to ALLOWED_HOSTS. Add its HTTPS origin to CSRF_TRUSTED_ORIGINS. Create its tenant/institute and connect the domain in the platform administration area. Keep school hosts out of PLATFORM_HOSTS. Your platform custom domain belongs in all three settings.

Example additional environment values after domain ownership and DNS are configured:

```text
ALLOWED_HOSTS=portal.example.org,school.example.org
PLATFORM_HOSTS=portal.example.org
CSRF_TRUSTED_ORIGINS=https://portal.example.org,https://school.example.org
```

## Verify the first deployment

- Open / and check the photos, motion, dashboard screenshot and email link.
- Submit a fictional registration and review it as a platform owner.
- Confirm /health/ returns HTTP 200 and the database/cache status is ok.
- Confirm administrator access requires MFA and school users cannot open platform controls.
- Test two school tenants and protected file access. Uploaded files are stored under /var/data/media and served through the existing permission checks.
- Test SMTP delivery and account recovery. Verify provider sandbox transactions before enabling payments.

## Operating this configuration

The initial profile uses one Gunicorn worker with two threads on one web instance with a persistent disk and synchronous Celery tasks. Uploads survive redeploys. Render disks limit horizontal scaling and can require deployment downtime. Move private media to shared object storage and add a worker before scaling background tasks or web instances.

PostgreSQL contains application records. The upload disk contains files. Back up both separately and test restoration. Review dependency alerts before accepting real school records. A passing local check does not verify Render service creation, PostgreSQL migrations, SMTP or DNS.

Keep SECRET_KEY stable. MFA encryption uses it. Maintain SECRET_KEY_FALLBACKS during rotation as described in DEPLOYMENT.md.

## Frontend hosting

Use this Render service for the complete frontend. The forms and dashboards use Django sessions, CSRF protection and server-rendered templates. Deploying those template files directly as a Netlify static site cannot execute their Django template tags or form handlers. If you later choose a separate marketing site on Netlify, its registration and sign-in links should point to the Render platform hostname.

## Sources

- https://render.com/docs/deploy-django
- https://render.com/docs/blueprint-spec
- https://render.com/docs/disks

Django reports HSTS subdomain and preload warnings by default. Enable those policies only after verifying HTTPS for every domain affected. The build fails on deployment errors and displays these policy warnings for review.
