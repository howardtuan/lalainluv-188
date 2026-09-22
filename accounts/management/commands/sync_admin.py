from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.db import transaction


class Command(BaseCommand):
    help = 'Create/update the local administrator from .env, never logging the password.'

    @transaction.atomic
    def handle(self, *args, **options):
        username, password = settings.ADMIN_USERNAME, settings.ADMIN_PASSWORD
        if not username and not password:
            self.stdout.write('Admin credentials not configured; no account changed.')
            return
        if not username or not password:
            raise CommandError('Set both ADMIN_USERNAME and ADMIN_PASSWORD in .env.')
        User = get_user_model()
        user = User.objects.select_for_update().filter(username=username).first()
        if user and not user.is_staff:
            raise CommandError('Refusing to promote an existing customer. Choose a dedicated admin username.')
        if User.objects.exclude(pk=user.pk if user else None).filter(email__iexact=settings.ADMIN_EMAIL).exists():
            raise CommandError('ADMIN_EMAIL belongs to another account. Use a dedicated administrator email.')
        user = user or User(username=username)
        user.email = settings.ADMIN_EMAIL
        try:
            validate_email(user.email)
            validate_password(password, user=user)
        except ValidationError:
            raise CommandError('Set a valid ADMIN_EMAIL and a strong ADMIN_PASSWORD (at least 12 characters recommended).')
        user.is_staff = user.is_superuser = user.is_active = True
        if not user.check_password(password):
            user.set_password(password)
        user.save()
        self.stdout.write(self.style.SUCCESS('Administrator synchronized from .env. Password is stored hashed in the database.'))
