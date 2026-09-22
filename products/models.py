from django.db import models
from django.utils.text import slugify
from django.templatetags.static import static
import uuid

class Category(models.Model):
    CATEGORY_TYPES = [
        ('hot_sale', '現正熱賣'),
        ('wish_pool', '許願池'),
    ]
    name = models.CharField('分類名稱', max_length=100)
    slug = models.SlugField('網址代碼', unique=True, allow_unicode=True)
    category_type = models.CharField('分類類型', max_length=20, choices=CATEGORY_TYPES, default='hot_sale')
    description = models.TextField('分類說明', blank=True, default='')
    order = models.PositiveIntegerField('排序', default=0)
    is_active = models.BooleanField('啟用', default=True)

    class Meta:
        verbose_name = '商品分類'
        verbose_name_plural = '商品分類'
        ordering = ['order']

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField('商品名稱', max_length=200)
    slug = models.SlugField('網址代碼', unique=True, allow_unicode=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products', verbose_name='分類')
    description = models.TextField('商品說明', blank=True, default='')
    price = models.DecimalField('售價', max_digits=10, decimal_places=0)
    original_price = models.DecimalField('原價', max_digits=10, decimal_places=0, null=True, blank=True)
    image = models.ImageField('主圖', upload_to='products/')
    stock = models.PositiveIntegerField('庫存', default=0)
    is_new = models.BooleanField('新品', default=False)
    is_hot = models.BooleanField('熱賣', default=False)
    is_active = models.BooleanField('上架', default=True)
    created_at = models.DateTimeField('建立時間', auto_now_add=True)
    updated_at = models.DateTimeField('更新時間', auto_now=True)

    class Meta:
        verbose_name = '商品'
        verbose_name_plural = '商品'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True) or str(uuid.uuid4())[:8]
        super().save(*args, **kwargs)

    @property
    def has_discount(self):
        return self.original_price and self.original_price > self.price

    @property
    def discount_percent(self):
        if self.has_discount:
            return int((1 - self.price / self.original_price) * 100)
        return 0

    @property
    def in_stock(self):
        return self.stock > 0

    @property
    def image_url(self):
        return self.image.url if self.image else static('images/rilakkuma/raincoat.jpg')

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images', verbose_name='商品')
    image = models.ImageField('圖片', upload_to='products/')
    order = models.PositiveIntegerField('排序', default=0)

    class Meta:
        verbose_name = '商品圖片'
        verbose_name_plural = '商品圖片'
        ordering = ['order']
