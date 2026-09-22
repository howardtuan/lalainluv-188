"""Isolated browser smoke-test server; never creates test accounts in the real DB.

Run with .venv/Scripts/python scripts/preview_test_store.py, then Ctrl+C to
drop the uniquely named test database and temporary uploads. Loopback only.
The deliberately public fixture password is valid only for this test server.
"""
import os
import sys
import secrets
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
os.environ['DEBUG'] = 'True'

import django
django.setup()
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test.utils import setup_databases, teardown_databases
from django.test import override_settings
from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount
from orders.models import Order, OrderItem
from products.models import Product

settings.DATABASES['default']['TEST']['NAME'] = 'test_lalainluv_ui_' + secrets.token_hex(5)
with TemporaryDirectory(prefix='lalainluv-ui-') as media:
    with override_settings(MEDIA_ROOT=media, EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
                           ACCOUNT_RATE_LIMITS=False, SESSION_COOKIE_NAME='lalainluv_ui_session', CSRF_COOKIE_NAME='lalainluv_ui_csrf'):
        database = setup_databases(verbosity=0, interactive=False)
        try:
            call_command('seed_demo')
            call_command('seed_banners')
            User = get_user_model()
            User.objects.create_user('preview_admin', 'preview_admin@example.com', 'Preview-store-9265!', is_staff=True)
            member = User.objects.create_user('preview_member', 'preview_member@example.com', 'Preview-store-9265!')
            User.objects.create_user('preview_unbound', 'preview_unbound@example.com', 'Preview-store-9265!')
            EmailAddress.objects.create(user=member, email=member.email, primary=True, verified=True)
            SocialAccount.objects.create(user=member, provider='google', uid='simulated-ui-fixture-only')
            product = Product.objects.get(slug='rilakkuma-raincoat')
            order = Order.objects.create(user=member, customer_email=member.email,
                recipient_name='測試會員', recipient_phone='0900000000', recipient_address='台北市測試路 100 號',
                note='隔離測試訂單，請勿出貨', total_amount=1840, shipping_fee=60)
            OrderItem.objects.create(order=order, product=product, product_name=product.name, price=890, quantity=2)
            product.stock -= 2
            product.save()
            print('ISOLATED_TEST_SERVER http://127.0.0.1:8081/ — fixture accounts only', flush=True)
            call_command('runserver', '127.0.0.1:8081', use_reloader=False, verbosity=0)
        finally:
            teardown_databases(database, verbosity=0)
