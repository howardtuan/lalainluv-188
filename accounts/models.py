from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', verbose_name='使用者')
    phone = models.CharField('電話', max_length=20, blank=True, default='')
    address = models.TextField('地址', blank=True, default='')
    line_id = models.CharField('LINE ID', max_length=100, blank=True, default='')

    class Meta:
        verbose_name = '會員資料'
        verbose_name_plural = '會員資料'

    def __str__(self):
        return f'{self.user.email} 的資料'

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    try:
        instance.profile.save()
    except UserProfile.DoesNotExist:
        UserProfile.objects.create(user=instance)
