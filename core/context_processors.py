from .models import SiteConfig
from products.models import Category

def site_config(request):
    return {'site_config': SiteConfig.get_config(), 'store_categories': Category.objects.filter(is_active=True)}
