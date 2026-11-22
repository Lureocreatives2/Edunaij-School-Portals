# Dependency review — 22 November 2026

## Findings and changes

GitHub reported 525 open Dependabot alerts. The runtime requirements accounted for 108 alerts, with repeated findings through the two requirements entry points. An obsolete requirements list accounted for another 203 alerts.

An independent pip-audit scan confirmed 108 known advisories across 14 packages in the original runtime snapshot. The updated snapshot contains 135 packages, with zero skipped packages and zero known advisories returned by the scanner.

| Package | Previous pin | Updated pin |
| --- | --- | --- |


Removed unused PyPDF2, WeasyPrint, social-auth-app-django and social-auth-core dependencies after checking application imports, migrations and installed package requirements. The report pipeline continues to use xhtml2pdf and pypdf. Sign-in continues to use django-allauth.

Retired the unused legacy requirements file and bundled jQuery File Upload demo from deployable source. Previous versions remain in Git history. Local diagnostic copies are kept under ignored dist/security-audit/.

Replaced bundled jQuery 2.1.4 and 3.4.1 references with official jQuery 3.8.0. Updated the older lightbox's load-event calls for compatibility. Vendor copyright and licence headers are preserved. Deployment asset collection clears earlier output so retired bundles are removed from the served static directory.

## Verification

- The patched requirements resolved successfully with pip and installed in the development environment.
- pip check reported no broken requirements.
- All 113 project regression tests passed, including image decoding, PDF generation, JWT options preservation and expiry checks.
- Render settings, deployment checks, frontend collection and production asset-serving checks passed. The existing optional HSTS policy warnings remain documented in RENDER.md.
- JavaScript syntax checks passed for jQuery and the lightbox compatibility update. Interactive browser testing of legacy school-page plugins remains outstanding.

Run the Python dependency scan with:

```text
python -m pip install pip-audit==2.10.1
python -m pip_audit -r requirements.txt --no-deps --disable-pip --progress-spinner off
```

The snapshot pins transitive dependencies as well as direct packages. The CI scan runs on requirements changes and weekly. Dependabot checks Python and GitHub Actions updates weekly. Keep the resolved snapshot complete when introducing new dependencies.

## Follow-up

The manually bundled Bootstrap 4 and other legacy frontend plugins still need a separate compatibility and security review. The zero-advisory result above covers the Python snapshot. Migrating Bootstrap requires checking the school forms, tables, modals and navigation against the newer API.

A fresh Linux installation and hosted service verification remain part of the Render rollout.

## Sources

- [PyPA pip-audit](https://github.com/pypa/pip-audit)
- [GitHub Dependabot alerts for edunaij](https://github.com/Lureocreatives2/Edunaij-School-Portals/security/dependabot)
- [Pillow advisory and patched version](https://github.com/advisories/GHSA-5x8w-8jj5-q52h)
- [PyJWT advisory and patched version](https://github.com/advisories/GHSA-ffc3-869f-jxw9)
- [Official jQuery releases](https://releases.jquery.com/jquery/)
