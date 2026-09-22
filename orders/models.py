from django.db import models
from django.contrib.auth.models import User
from products.models import Product
import uuid
from django.utils import timezone

class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='cart_items', verbose_name='使用者')
    session_key = models.CharField('Session Key', max_length=40, blank=True, default='')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='商品')
    quantity = models.PositiveIntegerField('數量', default=1)
    created_at = models.DateTimeField('加入時間', auto_now_add=True)

    class Meta:
        verbose_name = '購物車項目'
        verbose_name_plural = '購物車項目'

    def __str__(self):
        return f'{self.product.name} x {self.quantity}'

    @property
    def subtotal(self):
        return self.product.price * self.quantity

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', '待確認'),
        ('confirmed', '已確認'),
        ('shipped', '已出貨'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
    ]

    order_number = models.CharField('訂單編號', max_length=20, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders', verbose_name='會員')
    status = models.CharField('狀態', max_length=20, choices=STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField('總金額', max_digits=10, decimal_places=0, default=0)
    shipping_fee = models.DecimalField('運費', max_digits=10, decimal_places=0, default=0)
    recipient_name = models.CharField('收件人姓名', max_length=100)
    recipient_phone = models.CharField('收件人電話', max_length=20)
    recipient_address = models.TextField('收件地址')
    note = models.TextField('備註', blank=True, default='')
    customer_email = models.EmailField('下單會員信箱', blank=True, default='')
    admin_note = models.TextField('管理員內部備註', blank=True, default='')
    tracking_number = models.CharField('物流單號', max_length=100, blank=True, default='')
    stock_restored = models.BooleanField('取消時已回補庫存', default=False, editable=False)
    created_at = models.DateTimeField('下單時間', auto_now_add=True)
    updated_at = models.DateTimeField('更新時間', auto_now=True)

    class Meta:
        verbose_name = '訂單'
        verbose_name_plural = '訂單'
        ordering = ['-created_at']

    def __str__(self):
        return self.order_number

    def save(self, *args, **kwargs):
        if not self.order_number:
            today = timezone.now().strftime('%Y%m%d')
            random_str = uuid.uuid4().hex[:6].upper()
            self.order_number = f'LL{today}{random_str}'
        super().save(*args, **kwargs)

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name='訂單')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, verbose_name='商品')
    product_name = models.CharField('商品名稱', max_length=200)
    quantity = models.PositiveIntegerField('數量', default=1)
    price = models.DecimalField('單價', max_digits=10, decimal_places=0)

    class Meta:
        verbose_name = '訂單項目'
        verbose_name_plural = '訂單項目'

    def __str__(self):
        return f'{self.product_name} x {self.quantity}'

    @property
    def subtotal(self):
        return self.price * self.quantity


class OrderStatusLog(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_logs')
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    previous_status = models.CharField(max_length=20, choices=Order.STATUS_CHOICES)
    status = models.CharField(max_length=20, choices=Order.STATUS_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

class Wish(models.Model):
    WISH_TYPES = [
        ('japan_connect', '日本連線'),
        ('custom', '客制需求'),
        ('product_wish', '商品許願'),
    ]
    STATUS_CHOICES = [
        ('pending', '待處理'),
        ('reviewing', '評估中'),
        ('quoted', '已報價'),
        ('completed', '已完成'),
        ('rejected', '無法處理'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='wishes', verbose_name='會員')
    wish_type = models.CharField('許願類型', max_length=20, choices=WISH_TYPES)
    title = models.CharField('標題', max_length=200)
    description = models.TextField('詳細說明')
    reference_image = models.ImageField('參考圖片', upload_to='wishes/', blank=True, null=True)
    reference_url = models.URLField('參考連結', blank=True, default='')
    status = models.CharField('狀態', max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_reply = models.TextField('管理員回覆', blank=True, default='')
    created_at = models.DateTimeField('建立時間', auto_now_add=True)
    updated_at = models.DateTimeField('更新時間', auto_now=True)

    class Meta:
        verbose_name = '許願'
        verbose_name_plural = '許願'
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.get_wish_type_display()}] {self.title}'
