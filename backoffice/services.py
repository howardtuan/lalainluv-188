from django.core.exceptions import ValidationError
from products.models import Product
from orders.models import OrderStatusLog

TRANSITIONS = {
    'pending': {'confirmed', 'cancelled'},
    'confirmed': {'shipped', 'cancelled'},
    'shipped': {'completed'},
    'completed': set(), 'cancelled': set(),
}


def update_order(locked_order, data, actor):
    """Caller must hold the order row lock in an atomic transaction."""
    if data['version'] != locked_order.updated_at.isoformat():
        raise ValidationError('此訂單剛被更新，請重新載入後再儲存。')
    previous, new = locked_order.status, data['status']
    if new != previous and new not in TRANSITIONS[previous]:
        raise ValidationError('無法直接切換至此狀態。請依序確認、出貨、完成；取消及完成後不可重新啟用。')
    if new == 'cancelled' and previous != new and not locked_order.stock_restored:
        items = list(locked_order.items.all())
        products = {p.pk: p for p in Product.objects.select_for_update().filter(pk__in=[i.product_id for i in items if i.product_id]).order_by('pk')}
        for item in items:
            if item.product_id in products:
                product = products[item.product_id]
                product.stock += item.quantity
                product.save(update_fields=['stock', 'updated_at'])
        locked_order.stock_restored = True
    locked_order.status = new
    locked_order.tracking_number = data['tracking_number']
    locked_order.admin_note = data['admin_note']
    locked_order.save(update_fields=['status', 'tracking_number', 'admin_note', 'stock_restored', 'updated_at'])
    if previous != new:
        OrderStatusLog.objects.create(order=locked_order, actor=actor, previous_status=previous, status=new)
