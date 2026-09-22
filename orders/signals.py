from django.db import transaction
from django.db.models.signals import post_save
from django.contrib.auth.signals import user_logged_in
from django.contrib.auth import get_user_model
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from products.models import Product
from .models import CartItem, Order, Wish


def send_order_notification(order_id):
    order = Order.objects.prefetch_related('items').get(pk=order_id)
    lines = '\n'.join(f'{i.product_name} × {i.quantity}（單價 NT$ {i.price}）— 小計 NT$ {i.subtotal}' for i in order.items.all())
    send_mail(f'【Lalainluv】新訂單 {order.order_number}',
              f'訂單：{order.order_number}\n下單時間：{order.created_at}\n狀態：{order.get_status_display()}\n'
              f'會員：{order.customer_email or order.user.email}\n收件人：{order.recipient_name}\n'
              f'電話：{order.recipient_phone}\n地址：{order.recipient_address}\n備註：{order.note or "無"}\n'
              f'{lines}\n運費：NT$ {order.shipping_fee}\n合計：NT$ {order.total_amount}\n'
              '完整訂單已存入商店管理後台 /manage/orders/。本網站未串接金流，請人工聯繫確認。',
              settings.DEFAULT_FROM_EMAIL, [settings.ADMIN_EMAIL], fail_silently=True)


@receiver(post_save, sender=Wish)
def notify_admin_new_wish(sender, instance, created, **kwargs):
    if created:
        transaction.on_commit(lambda: send_mail(
            f'【Lalainluv】新許願 — {instance.get_wish_type_display()}',
            f'{instance.title}\n{instance.description}\n會員：{instance.user.email if instance.user else "未登入"}',
            settings.DEFAULT_FROM_EMAIL, [settings.ADMIN_EMAIL], fail_silently=True))


@receiver(user_logged_in)
def merge_guest_cart(sender, request, user, **kwargs):
    key = request.session.pop('guest_cart_key', None)
    if not key:
        return
    with transaction.atomic():
        get_user_model().objects.select_for_update().get(pk=user.pk)
        guest_items = list(CartItem.objects.filter(user__isnull=True, session_key=key))
        products = {p.pk: p for p in Product.objects.select_for_update().filter(pk__in=[i.product_id for i in guest_items]).order_by('pk')}
        for guest in guest_items:
            product = products[guest.product_id]
            item = CartItem.objects.filter(user=user, product=product).first()
            quantity = min(99, product.stock, guest.quantity + (item.quantity if item else 0))
            if product.is_active and quantity > 0:
                if item:
                    item.quantity = quantity
                    item.save(update_fields=['quantity'])
                else:
                    CartItem.objects.create(user=user, product=product, quantity=quantity)
            guest.delete()
