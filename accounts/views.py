from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import UserProfileForm
from django.views.decorators.http import require_http_methods
from allauth.socialaccount.models import SocialAccount
from .services import SUPPORTED_PROVIDERS, needs_social_binding, safe_destination
from django.contrib.auth import get_user_model
from django.db import transaction
from allauth.socialaccount.forms import DisconnectForm


@login_required
@require_http_methods(['GET', 'POST'])
@transaction.atomic
def manage_connections(request):
    # Serialize disconnects so simultaneous requests cannot remove both remaining accounts.
    get_user_model().objects.select_for_update().get(pk=request.user.pk)
    form = DisconnectForm(request.POST or None, request=request)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, '已解除指定帳號的連結。')
        return redirect('socialaccount_connections')
    return render(request, 'socialaccount/connections.html', {'form': form})


@login_required
@require_http_methods(['GET'])
def connections(request):
    destination = safe_destination(request, request.GET.get('next'), '/accounts/profile/')
    if 'next' in request.GET:
        request.session['social_binding_next'] = destination
    connected = list(SocialAccount.objects.filter(user=request.user, provider__in=SUPPORTED_PROVIDERS))
    return render(request, 'accounts/connections.html', {
        'connected_accounts': connected, 'connected_providers': [a.provider for a in connected],
        'binding_required': needs_social_binding(request.user), 'next_url': destination,
    })

@login_required
def profile(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user.profile, user=request.user)
        if form.is_valid():
            form.save()
            request.user.first_name = form.cleaned_data.get('first_name')
            request.user.email = form.cleaned_data.get('email')
            request.user.save()
            messages.success(request, '資料更新成功！')
            return redirect('accounts:profile')
    else:
        form = UserProfileForm(instance=request.user.profile, user=request.user)

    return render(request, 'accounts/profile.html', {'form': form})
