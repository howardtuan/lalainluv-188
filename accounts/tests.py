from pathlib import Path

from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount
from django.conf import settings
from django.contrib.auth import get_user_model
from django.template.loader import get_template
from django.templatetags.static import static
from django.test import SimpleTestCase, TestCase, override_settings


class AccountTemplateResolutionTests(SimpleTestCase):
    def test_storefront_templates_override_allauth_defaults(self):
        template_dir = settings.BASE_DIR / 'accounts' / 'templates' / 'account'
        for template_path in template_dir.glob('*.html'):
            with self.subTest(template=template_path.name):
                resolved = get_template(f'account/{template_path.name}')
                self.assertEqual(Path(resolved.origin.name), template_path)


@override_settings(
    ALLOWED_HOSTS=['testserver'],
    SECURE_SSL_REDIRECT=False,
    ACCOUNT_RATE_LIMITS=False,
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
)
class StorefrontThemeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            'theme-member', 'theme@example.com', 'Storefront-test-9265!'
        )
        EmailAddress.objects.create(
            user=cls.user, email=cls.user.email, verified=True, primary=True
        )
        SocialAccount.objects.create(user=cls.user, provider='google', uid='theme-google')

    def assert_storefront_theme(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'base.html')
        self.assertContains(response, f'href="{static("css/style.css")}"', count=1)
        self.assertContains(response, f'src="{static("js/main.js")}"', count=1)
        self.assertContains(response, 'name="viewport"', count=1)
        self.assertContains(response, 'id="main"', count=1)
        self.assertContains(response, 'id="memberToggle"', count=1)
        self.assertContains(response, 'id="sidebar"', count=1)

    def test_public_pages_share_the_storefront_layout(self):
        for route in ('/', '/products/', '/orders/cart/', '/orders/wish/',
                      '/about/', '/notice/', '/accounts/login/',
                      '/accounts/signup/', '/accounts/password/reset/',
                      '/accounts/password/reset/done/',
                      '/accounts/password/reset/key/done/',
                      '/accounts/confirm-email/', '/accounts/inactive/'):
            with self.subTest(route=route):
                self.assert_storefront_theme(self.client.get(route))

    def test_protected_links_render_themed_login_and_keep_destination(self):
        for route in ('/orders/', '/orders/checkout/', '/accounts/profile/',
                      '/orders/wish/create/?type=japan_connect'):
            with self.subTest(route=route):
                response = self.client.get(route, follow=True)
                self.assert_storefront_theme(response)
                self.assertTemplateUsed(response, 'account/login.html')
                self.assertContains(response, f'name="next" value="{route}"')

    def test_validation_errors_keep_storefront_styles(self):
        for route, data in (
            ('/accounts/login/', {'login': 'not-an-email', 'password': ''}),
            ('/accounts/signup/', {'email': 'not-an-email', 'password1': 'x', 'password2': 'y'}),
            ('/accounts/password/reset/', {'email': 'not-an-email'}),
        ):
            with self.subTest(route=route):
                response = self.client.post(route, data)
                self.assertTrue(response.context['form'].errors)
                self.assert_storefront_theme(response)

    def test_account_pages_without_custom_templates_use_the_shared_layout(self):
        self.client.force_login(self.user)
        for route in ('/accounts/password/change/', '/accounts/email/'):
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assert_storefront_theme(response)
                self.assertTemplateUsed(response, 'allauth/layouts/base.html')
                self.assertContains(response, 'allauth-content')

    def test_member_pages_and_logout_share_the_storefront_layout(self):
        self.client.force_login(self.user)
        for route in ('/accounts/profile/', '/orders/', '/orders/wish/',
                      '/orders/wish/create/', '/accounts/logout/'):
            with self.subTest(route=route):
                self.assert_storefront_theme(self.client.get(route))

    def test_login_still_returns_to_the_requested_page(self):
        response = self.client.post('/accounts/login/', {
            'login': self.user.email,
            'password': 'Storefront-test-9265!',
            'next': '/orders/',
        }, follow=True)
        self.assertRedirects(response, '/orders/')
        self.assert_storefront_theme(response)
