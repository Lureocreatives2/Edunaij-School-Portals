"""Run project checks using the current interpreter."""
import argparse
import os
import subprocess
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--quick', action='store_true')
    args = parser.parse_args()
    commands = [['check'], ['migrate', '--check'], ['makemigrations', '--check', '--dry-run']]
    if not args.quick:
        commands.append(['test', 'django_school_management.platform_control.tests', 'django_school_management.accounts.test_signup', 'django_school_management.accounts.test_admin_mfa', 'django_school_management.accounts.test_ui', 'django_school_management.learning.tests', 'django_school_management.tenants.test_sensitive_records', 'django_school_management.tenants.test_isolation', 'django_school_management.students.api.test_security', 'django_school_management.tenants.tests', '--noinput'])
    for command in commands:
        # The dedicated MFA tests explicitly enable the policy.
        env = dict(os.environ, ADMIN_MFA_REQUIRED='False') if command[0] == 'test' else None
        subprocess.run([sys.executable, 'manage.py', *command], cwd=ROOT, check=True, env=env)
if __name__ == '__main__':
    main()
