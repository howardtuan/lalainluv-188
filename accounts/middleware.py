from urllib.parse import urlencode
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from .services import needs_social_binding, provider_options, safe_destination


class SocialBindingMiddleware:
    """Only a completed OAuth connection grants normal members account access."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        match = request.resolver_match
        name = match.url_name if match else ''
        if name in ('google_login', 'line_login'):
            provider = name.removesuffix('_login')
            if not any(p['id'] == provider and p['enabled'] for p in provider_options(request)):
                messages.info(request, '此社群登入尚未啟用，請聯絡商店管理員完成設定。')
                return redirect('accounts:connections' if request.user.is_authenticated else 'account_login')
        if not needs_social_binding(request.user):
            return None
        # Allow OAuth callbacks, email verification/recovery and logout, not profile or commerce writes.
        allowed = {
            'account_login', 'account_signup', 'account_logout', 'account_email',
            'account_email_verification_sent', 'account_confirm_email', 'account_reauthenticate',
            'account_reset_password', 'account_reset_password_done', 'account_reset_password_from_key',
            'account_reset_password_from_key_done', 'account_inactive',
            'google_login', 'google_callback', 'line_login', 'line_callback',
            'socialaccount_connections', 'socialaccount_signup',
            'socialaccount_login_error', 'socialaccount_login_cancelled', 'health_check',
        }
        if name in allowed or (match and match.view_name == 'accounts:connections'):
            return None
        if request.path.startswith(('/static/', '/media/', '/manage/login/', '/manage/logout/')):
            return None
        destination = safe_destination(request, request.get_full_path())
        request.session['social_binding_next'] = destination
        url = reverse('accounts:connections') + '?' + urlencode({'next': destination})
        if request.content_type == 'application/json':
            return JsonResponse({'success': False, 'message': '請先綁定 LINE 或 Google 後再使用會員功能。', 'redirect': url}, status=403)
        return redirect(url)
