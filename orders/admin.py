from django.contrib import admin
from .models import CartItem, Order, OrderItem, Wish

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'product_name', 'quantity', 'price', 'subtotal']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'user', 'status', 'total_amount', 'recipient_name', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['order_number', 'recipient_name', 'user__email']
    list_editable = ['status']
    readonly_fields = ['order_number', 'total_amount', 'created_at', 'updated_at']
    inlines = [OrderItemInline]
    ordering = ['-created_at']

@admin.register(Wish)
class WishAdmin(admin.ModelAdmin):
    list_display = ['title', 'wish_type', 'user', 'status', 'created_at']
    list_filter = ['wish_type', 'status', 'created_at']
    search_fields = ['title', 'description', 'user__email']
    list_editable = ['status']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'quantity', 'created_at']
