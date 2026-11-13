# Deployment readiness

The README quickstart is the local setup path. Existing Docker and process configurations have not been validated as a complete production deployment.

Before accepting school data:

1. Confirm the owner's permission for your deployment and establish a maintainer/security contact.
2. Configure DEBUG=False, a unique secret, explicit hosts/origins and dedicated PLATFORM_HOSTS. Inspect production settings and run `python manage.py check --deploy` against them.
3. Configure PostgreSQL, Redis/workers, SMTP and private file storage. Apply migrations and collect static assets.
4. Establish HTTPS, secret storage, monitoring, backups and a tested restore process.
5. Verify multiple tenants and every role, including invitations and account recovery.
6. Verify provider sandbox callbacks, amount/currency/customer matching, retries and subscription reconciliation. Do not enable unverified legacy payment providers.
7. Test suspension, upgrades and rollback in staging.

Release announcements do not update servers. Deploy code through the hosting pipeline.

Keep PLATFORM_HOSTS set to a dedicated hostname you control (also include it in ALLOWED_HOSTS). With this setting, the platform owner login, platform controls and Django admin reject requests from school hosts. Leave session and CSRF cookie domains unset so browsers keep cookies on the host that issued them. Give each administrator an individual account. Production requires authenticator app MFA by default. Apply migrations, sign in through the platform or school sign-in, enroll an authenticator and save the recovery codes offline. Keep the previous Django secret in SECRET_KEY_FALLBACKS during a key rotation until authenticator records have been re-encrypted or their owners have re-enrolled.

Set SCHOOL_EMAIL_DOMAIN to an email domain you control to assign stable school and approved official addresses. An address reservation alone does not configure DNS, a mailbox or forwarding. The UI displays mailbox setup as pending until provider provisioning is integrated. Keep the domain stable after sharing addresses.
