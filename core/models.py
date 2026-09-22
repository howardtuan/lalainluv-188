from django.db import models

class SiteConfig(models.Model):
    """網站全域設定（單例模式）"""
    site_name = models.CharField('網站名稱', max_length=100, default='Lalainluv')
    line_url = models.URLField('LINE 連結', blank=True, default='')
    instagram_url = models.URLField('Instagram 連結', blank=True, default='')
    gmail = models.EmailField('Gmail 信箱', blank=True, default='')
    about_us = models.TextField('關於我們', blank=True, default='')
    notice = models.TextField('注意事項', blank=True, default='')

    class Meta:
        verbose_name = '網站設定'
        verbose_name_plural = '網站設定'

    def __str__(self):
        return self.site_name

    def save(self, *args, **kwargs):
        # Singleton: ensure only one instance
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_config(cls):
        config, _ = cls.objects.get_or_create(pk=1)
        return config

class Banner(models.Model):
    """首頁滑動廣告"""
    title = models.CharField('標題', max_length=200)
    image = models.ImageField('圖片', upload_to='banners/')
    mobile_image = models.ImageField('手機版圖片（選填）', upload_to='banners/', blank=True)
    button_text = models.CharField('按鈕文字', max_length=40, default='逛逛拉拉熊選物')
    link = models.URLField('連結', blank=True, default='')
    description = models.TextField('說明', blank=True, default='')
    order = models.PositiveIntegerField('排序', default=0)
    is_active = models.BooleanField('啟用', default=True)
    created_at = models.DateTimeField('建立時間', auto_now_add=True)

    class Meta:
        verbose_name = '廣告橫幅'
        verbose_name_plural = '廣告橫幅'
        ordering = ['order', '-created_at']

    def __str__(self):
        return self.title
