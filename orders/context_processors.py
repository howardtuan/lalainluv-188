from django.db.models import Sum
from .models import CartItem


def cart_count(request):
    if request.user.is_authenticated:
        items = CartItem.objects.filter(user=request.user)
    elif request.session.session_key:
        items = CartItem.objects.filter(user__isnull=True, session_key=request.session.session_key)
    else:
        return {'cart_count': 0}
    return {'cart_count': items.aggregate(count=Sum('quantity'))['count'] or 0}
