from django.contrib import admin
from .models import SiteConfig, Banner

@admin.register(SiteConfig)
class SiteConfigAdmin(admin.ModelAdmin):
    # Prevent adding/deleting (singleton)
    def has_add_permission(self, request):
        return not SiteConfig.objects.exists()
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ['title', 'order', 'is_active', 'created_at']
    list_editable = ['order', 'is_active']
    list_filter = ['is_active']
