from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned
from django.utils.http import url_has_allowed_host_and_scheme
from allauth.socialaccount.adapter import get_adapter
from allauth.socialaccount.models import SocialAccount, SocialApp

SUPPORTED_PROVIDERS = ('line', 'google')


def needs_social_binding(user):
    return bool(
        settings.REQUIRE_SOCIAL_BINDING and user.is_authenticated and not user.is_staff
        and not SocialAccount.objects.filter(user=user, provider__in=SUPPORTED_PROVIDERS).exists()
    )


def safe_destination(request, value, default='/'):
    if value and value.startswith('/') and not value.startswith('//') and url_has_allowed_host_and_scheme(
        value, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return value
    return default


def provider_options(request):
    if hasattr(request, '_social_provider_options'):
        return request._social_provider_options
    options = []
    for provider, label in (('line', 'LINE'), ('google', 'Google')):
        try:
            app = get_adapter(request).get_app(request, provider=provider)
            enabled = bool(app.client_id and app.secret)
        except (SocialApp.DoesNotExist, MultipleObjectsReturned):
            enabled = False
        options.append({'id': provider, 'label': label, 'enabled': enabled})
    request._social_provider_options = options
    return options
