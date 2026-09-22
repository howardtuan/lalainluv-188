from .services import provider_options


def social_auth(request):
    options = provider_options(request)
    return {'social_providers': options, 'social_login_available': any(p['enabled'] for p in options)}
