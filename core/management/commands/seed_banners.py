from pathlib import Path
from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Banner


class Command(BaseCommand):
    help = 'Initialize editable carousel images once; never overwrite administrator content.'

    @transaction.atomic
    def handle(self, *args, **options):
        if Banner.objects.exists():
            self.stdout.write('Existing banners preserved.')
            return
        rows = [
            ('和拉拉熊，\n一起慢慢過。', '把拉拉熊的慵懶可愛，收藏進日常。\n從日本帶回，屬於你的療癒小時光。', 'hero.jpg', '逛逛拉拉熊新品'),
            ('日常實驗，\n可愛多一點。', '有拉拉熊陪伴的一杯，\n連平凡日子都變得有趣。', 'lab-mug.jpg', '探索拉拉熊周邊'),
            ('今天也想，\n抱抱拉拉熊。', '熟悉的圓耳朵與放鬆表情，\n陪你度過懶洋洋的小日子。', 'plush.jpg', '收藏拉拉熊玩偶'),
        ]
        for order, (title, description, image, button) in enumerate(rows):
            banner = Banner(title=title, description=description, button_text=button, order=order)
            with (Path(settings.BASE_DIR) / 'static/images/rilakkuma' / image).open('rb') as source:
                banner.image.save(f'rilakkuma-banner-{order}.jpg', File(source), save=False)
            banner.save()
        self.stdout.write(self.style.SUCCESS('Created 3 editable homepage banners.'))
