from urllib.parse import parse_qs, urlparse
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount, SocialLogin
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.line.views import LineOAuth2Adapter
from orders.models import Order

OAUTH_TEST_PROVIDERS = {
    'google': {'APPS': [{'client_id': 'test-google-client', 'secret': 'test-google-secret'}],
               'SCOPE': ['profile', 'email'], 'OAUTH_PKCE_ENABLED': True},
    'line': {'APPS': [{'client_id': 'test-line-client', 'secret': 'test-line-secret'}], 'SCOPE': ['profile', 'openid']},
}


@override_settings(ALLOWED_HOSTS=['testserver'], SECURE_SSL_REDIRECT=False, ACCOUNT_RATE_LIMITS=False,
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend', SOCIALACCOUNT_PROVIDERS=OAUTH_TEST_PROVIDERS)
class SocialBindingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('binding-user', 'binding@example.com', 'Binding-test-9265!')
        EmailAddress.objects.create(user=self.user, email=self.user.email, verified=True, primary=True)

    def test_password_login_requires_binding_even_with_explicit_next(self):
        response = self.client.post('/accounts/login/', {'login': self.user.email, 'password': 'Binding-test-9265!', 'next': '/orders/'}, follow=True)
        self.assertTemplateUsed(response, 'accounts/connections.html')
        self.assertContains(response, '完成帳號綁定')
        self.assertEqual(self.client.session['social_binding_next'], '/orders/')

    def test_unbound_member_cannot_submit_order_or_bypass_with_line_id(self):
        self.user.profile.line_id = 'a-manually-entered-line-id'
        self.user.profile.save()
        self.client.force_login(self.user)
        self.assertEqual(self.client.post('/orders/checkout/', {'agree': 'on'}).status_code, 302)
        self.assertEqual(self.client.post('/orders/cart/add/123/', {}, content_type='application/json').status_code, 403)
        self.assertFalse(Order.objects.exists())

    def test_last_social_binding_cannot_be_removed(self):
        account = SocialAccount.objects.create(user=self.user, provider='google', uid='google-1')
        self.client.force_login(self.user)
        response = self.client.post(reverse('socialaccount_connections'), {'account': account.pk})
        self.assertContains(response, '必須保留至少一個')
        self.assertTrue(SocialAccount.objects.filter(pk=account.pk).exists())

    def test_one_of_two_bindings_can_be_removed(self):
        account = SocialAccount.objects.create(user=self.user, provider='google', uid='google-1')
        SocialAccount.objects.create(user=self.user, provider='line', uid='line-1')
        self.client.force_login(self.user)
        self.assertEqual(self.client.post(reverse('socialaccount_connections'), {'account': account.pk}).status_code, 302)
        self.assertEqual(self.user.socialaccount_set.count(), 1)

    def test_bindings_of_other_users_cannot_be_removed(self):
        other = get_user_model().objects.create_user('other-binding')
        account = SocialAccount.objects.create(user=other, provider='google', uid='other-google')
        self.client.force_login(self.user)
        response = self.client.post(reverse('socialaccount_connections'), {'account': account.pk})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(SocialAccount.objects.filter(pk=account.pk).exists())

    def test_connections_reject_external_return_urls(self):
        self.client.force_login(self.user)
        response = self.client.get('/accounts/connect/?next=//evil.example/path')
        self.assertEqual(response.context['next_url'], '/accounts/profile/')

    @override_settings(SOCIALACCOUNT_PROVIDERS={'google': {}, 'line': {}})
    def test_missing_oauth_credentials_show_disabled_options_not_fake_binding(self):
        self.client.force_login(self.user)
        response = self.client.get('/accounts/connect/')
        self.assertContains(response, 'Google · 尚未啟用')
        self.assertContains(response, 'LINE · 尚未啟用')
        self.assertFalse(self.user.socialaccount_set.exists())
        self.assertEqual(self.client.post('/accounts/google/login/').status_code, 302)

    def test_bad_oauth_state_does_not_create_binding(self):
        self.client.force_login(self.user)
        response = self.client.get('/accounts/google/login/callback/?code=fake&state=wrong')
        self.assertEqual(response.status_code, 401)
        self.assertFalse(self.user.socialaccount_set.exists())

    def oauth_callback(self, provider, uid, process='connect', email='provider@example.com'):
        adapter = GoogleOAuth2Adapter if provider == 'google' else LineOAuth2Adapter
        response = self.client.post(f'/accounts/{provider}/login/?process={process}')
        self.assertEqual(response.status_code, 302)
        params = parse_qs(urlparse(response.url).query)
        self.assertIn('state', params)
        if provider == 'google': self.assertIn('code_challenge', params)
        def verified_provider_response(instance, request, app, token, **kwargs):
            return SocialLogin(provider=instance.get_provider(), user=get_user_model()(email=email),
                account=SocialAccount(provider=provider, uid=uid),
                email_addresses=[EmailAddress(email=email, verified=True, primary=True)])
        # Mock only the external token/profile exchange, not application binding or login.
        with patch.object(adapter, 'get_access_token_data', return_value={'access_token': 'test-token'}), \
             patch.object(adapter, 'complete_login', autospec=True, side_effect=verified_provider_response):
            return self.client.get(f'/accounts/{provider}/login/callback/', {'code': 'test-code', 'state': params['state'][0]}, follow=True)

    def test_google_and_line_connect_then_direct_login_keep_same_customer(self):
        for provider in ('google', 'line'):
            with self.subTest(provider=provider):
                self.client.force_login(self.user)
                response = self.oauth_callback(provider, f'{provider}-uid')
                self.assertEqual(response.status_code, 200)
                account = SocialAccount.objects.get(provider=provider, uid=f'{provider}-uid')
                self.assertEqual(account.user_id, self.user.pk)
                self.client.logout()
                self.oauth_callback(provider, f'{provider}-uid', process='login')
                self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)

    def test_same_email_does_not_silently_link_to_existing_account(self):
        self.oauth_callback('google', 'unlinked-google', process='login', email=self.user.email)
        self.assertFalse(SocialAccount.objects.filter(user=self.user).exists())
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_social_identity_already_owned_by_someone_else_cannot_be_stolen(self):
        owner = get_user_model().objects.create_user('identity-owner', 'owner@example.com')
        account = SocialAccount.objects.create(user=owner, provider='google', uid='owned-google')
        self.client.force_login(self.user)
        self.oauth_callback('google', 'owned-google')
        account.refresh_from_db()
        self.assertEqual(account.user_id, owner.pk)
        self.assertFalse(SocialAccount.objects.filter(user=self.user).exists())
