"""Opt-in initial owner creation; never promote or change an existing account."""
import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.db import transaction


class Command(BaseCommand):
    help = 'Create the first platform owner from private deployment variables when explicitly enabled.'

    def handle(self, *args, **options):
        if os.environ.get('BOOTSTRAP_PLATFORM_OWNER', '').lower() not in {'true', '1'}:
            return
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME', '').strip()
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', '').strip().lower()
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', '')
        if not username or not email or not password:
            raise CommandError('Owner bootstrap requires username, email and password variables.')
        User = get_user_model()
        existing = User.objects.filter(username__iexact=username).first()
        if existing:
            if not existing.is_superuser or not existing.is_active or existing.email.lower() != email:
                raise CommandError('Owner bootstrap conflicts with an existing account; no changes made.')
            self.stdout.write('Platform owner already exists; password unchanged.')
            return
        if User.objects.filter(email__iexact=email).exists():
            raise CommandError('Owner email is already registered; no account was promoted.')
        user = User(username=username, email=email, is_staff=True, is_superuser=True)
        try:
            validate_email(email)
            User._meta.get_field('username').clean(username, user)
            validate_password(password, user=user)
        except ValidationError:
            raise CommandError('Owner details or password failed validation; use a valid email and a strong unique password.') from None
        with transaction.atomic():
            User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS('Platform owner created. Remove bootstrap password variables and enroll MFA.'))
