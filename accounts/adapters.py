from django.core.exceptions import ValidationError
from django.urls import reverse
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from .services import SUPPORTED_PROVIDERS, needs_social_binding, safe_destination


class StoreAccountAdapter(DefaultAccountAdapter):
    def get_login_redirect_url(self, request):
        if needs_social_binding(request.user):
            return reverse('accounts:connections')
        return super().get_login_redirect_url(request)

    def get_signup_redirect_url(self, request):
        if needs_social_binding(request.user):
            return reverse('accounts:connections')
        return super().get_signup_redirect_url(request)


class StoreSocialAccountAdapter(DefaultSocialAccountAdapter):
    def validate_disconnect(self, account, accounts):
        super().validate_disconnect(account, accounts)
        if not account.user.is_staff and not any(
            other.pk != account.pk and other.provider in SUPPORTED_PROVIDERS for other in accounts
        ):
            raise ValidationError('必須保留至少一個 LINE 或 Google 綁定，請先綁定另一個帳號。')

    def get_connect_redirect_url(self, request, socialaccount):
        return safe_destination(request, request.session.pop('social_binding_next', None), '/accounts/profile/')
