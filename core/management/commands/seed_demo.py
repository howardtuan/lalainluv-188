from pathlib import Path
import os
from django.core.management.base import BaseCommand
from django.core.files import File
from django.conf import settings
from django.contrib.sites.models import Site
from django.db import transaction
from products.models import Product, Category
from core.models import SiteConfig

# Original generic demo entries only. Retain records for existing order references.
LEGACY_DEMO_SLUGS = ('daisy-cup', 'teacup-cat', 'little-teddy', 'cream-bunny')

PRODUCTS = [
    {
        'slug': 'rilakkuma-lab-mug', 'name': '拉拉熊實驗室・燒杯馬克杯',
        'category': 'lifestyle', 'image': 'lab-mug.jpg', 'price': 680, 'stock': 12,
        'description': 'Rilakkuma Lab 拉拉熊實驗室系列。透明燒杯造型搭配拉拉熊與夥伴圖案，為日常飲品加一點實驗室的趣味。',
        'source': 'https://shop.san-x.co.jp/jp/product_list/details/209454',
    },
    {
        'slug': 'rilakkuma-mood-collection', 'name': '拉拉熊 stay with me・心情吊飾盲盒',
        'category': 'blind-boxes', 'image': 'mood-collection.png', 'price': 390, 'stock': 18,
        'description': 'stay with me 系列的「今日心情玩偶收藏」。拉拉熊、小白熊、小雞與茶小熊，以不同表情陪伴你的每一天。全 4 款，隨機單入；圖片展示系列款式，單次購買並非整套。',
        'source': 'https://www.san-x.co.jp/ja/blog/2025/09/-stay-with-me.html',
    },
    {
        'slug': 'rilakkuma-fluffy-plush', 'name': '拉拉熊 くまきゅんDays・絨毛玩偶 M',
        'category': 'dolls', 'image': 'plush.jpg', 'price': 780, 'stock': 15,
        'description': '茶小熊的 くまきゅんDays 系列，拉拉熊款 M 尺寸絨毛玩偶。毛茸茸的外型與趴躺姿勢，陪你享受悠閒的休息時光。',
        'source': 'https://shop.san-x.co.jp/jp/product_list/details/185228',
    },
    {
        'slug': 'rilakkuma-raincoat', 'name': '拉拉熊 雨過天晴・雨衣玩偶',
        'category': 'dolls', 'image': 'raincoat.jpg', 'price': 890, 'stock': 20,
        'description': '「雨のち晴れのリラックマ」雨過天晴系列，拉拉熊穿上輕透藍色雨衣。圓圓的耳朵與熟悉的放鬆表情，把下雨天也變得可愛。',
        'source': 'https://shop.san-x.co.jp/jp/product_list/details/178707',
    },
]


class Command(BaseCommand):
    help = 'Seed the Rilakkuma catalog; preserve existing products and retire only the old generic demo entries.'

    @transaction.atomic
    def handle(self, *args, **options):
        site = Site.objects.get(pk=settings.SITE_ID)
        if site.domain == 'example.com':
            site.domain = os.environ.get('SITE_DOMAIN', 'localhost:8080')
            site.name = 'Lalainluv'
            site.save()
        SiteConfig.get_config()
        categories = {}
        for position, (slug, name, description) in enumerate([
            ('dolls', '拉拉熊玩偶', '拉拉熊的柔軟陪伴，讓每一天都能懶洋洋。'),
            ('blind-boxes', '盲盒收藏', '拉拉熊與夥伴的收藏系列，把驚喜慢慢集齊。'),
            ('lifestyle', '生活周邊', '從杯子到日常小物，讓拉拉熊陪你一起生活。'),
        ]):
            categories[slug], _ = Category.objects.update_or_create(
                slug=slug, defaults={'name': name, 'description': description, 'order': position})
        retired = Product.objects.filter(
            slug__in=LEGACY_DEMO_SLUGS, description__contains='此為網站展示商品',
        ).update(is_active=False, is_new=False, is_hot=False)
        created_count = 0
        for entry in PRODUCTS:
            product, created = Product.objects.get_or_create(slug=entry['slug'], defaults={
                'name': entry['name'], 'category': categories[entry['category']],
                'price': entry['price'], 'stock': entry['stock'],
                'is_new': True, 'is_hot': True,
                'description': entry['description'] + '\n\n此為網站展示商品；售價與庫存為示範資料，正式代購前請確認報價、規格及供貨情況。\n商品圖片與資料參考：San-X。',
            })
            if created:
                image_path = Path(settings.BASE_DIR) / 'static' / 'images' / 'rilakkuma' / entry['image']
                with image_path.open('rb') as handle:
                    product.image.save(f"{entry['slug']}{image_path.suffix}", File(handle), save=True)
                created_count += 1
        self.stdout.write(self.style.SUCCESS(
            f'Rilakkuma catalog ready; {created_count} products added, {retired} legacy demo entries retired.'))
