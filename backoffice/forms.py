import uuid
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils.text import slugify
from core.models import Banner, SiteConfig
from products.models import Product, Category, ProductImage
from orders.models import Order, Wish


class StaffLoginForm(AuthenticationForm):
    username = forms.CharField(label='管理員帳號', widget=forms.TextInput(attrs={'autofocus': True, 'autocomplete': 'username'}))
    password = forms.CharField(label='密碼', strip=False, widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}))

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_staff:
            raise forms.ValidationError('帳號或密碼不正確，或此帳號沒有管理權限。', code='invalid_login')


def validate_image(image):
    if image and hasattr(image, 'content_type'):
        if image.size > 5 * 1024 * 1024:
            raise forms.ValidationError('圖片請小於 5 MB。')
        if image.image.format not in ('JPEG', 'PNG', 'WEBP', 'GIF'):
            raise forms.ValidationError('請上傳 JPG、PNG、WebP 或 GIF 圖片。')
        if image.image.width * image.image.height > 25_000_000:
            raise forms.ValidationError('圖片尺寸過大，請縮小至 2,500 萬像素以下。')
    return image


class ProductForm(forms.ModelForm):
    version = forms.CharField(widget=forms.HiddenInput, required=False)

    class Meta:
        model = Product
        fields = ['name', 'category', 'description', 'price', 'original_price', 'stock', 'image', 'is_active', 'is_new', 'is_hot']
        widgets = {'description': forms.Textarea(attrs={'rows': 5}), 'image': forms.ClearableFileInput(attrs={'accept': 'image/jpeg,image/png,image/webp,image/gif'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['version'].initial = self.instance.updated_at.isoformat()
        self.fields['image'].help_text = 'JPG、PNG、WebP、GIF，最多 5 MB；建議正方形商品照。'
        self.fields['stock'].help_text = '可販售庫存；送出訂單會扣除，取消未出貨訂單會自動回補。'

    def clean_image(self):
        return validate_image(self.cleaned_data.get('image'))

    def clean(self):
        data = super().clean()
        if self.instance.pk and data.get('version') != self.instance.updated_at.isoformat():
            raise forms.ValidationError('商品或庫存剛被更新，請重新載入頁面後再修改，避免覆蓋新訂單的庫存。')
        if data.get('price') is not None and data['price'] <= 0:
            self.add_error('price', '售價必須大於 0。')
        if data.get('original_price') is not None and data['original_price'] < 0:
            self.add_error('original_price', '原價不可小於 0。')
        if not self.instance.pk:
            self.instance.slug = (slugify(data.get('name', ''), allow_unicode=True)[:40] or 'product') + '-' + uuid.uuid4().hex[:8]
        return data


class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ['image', 'order']

    def clean_image(self):
        return validate_image(self.cleaned_data.get('image'))


ProductImageFormSet = forms.inlineformset_factory(
    Product, ProductImage, form=ProductImageForm, extra=1, can_delete=True, max_num=10, validate_max=True,
)


class BannerForm(forms.ModelForm):
    class Meta:
        model = Banner
        fields = ['title', 'description', 'image', 'mobile_image', 'button_text', 'link', 'order', 'is_active']
        widgets = {'title': forms.Textarea(attrs={'rows': 2}), 'description': forms.Textarea(attrs={'rows': 3})}
        help_texts = {
            'image': '首頁輪播圖片，最多 5 MB。可使用正方形照片；前台會保留完整圖片。',
            'mobile_image': '選填，手機會優先顯示此圖；未上傳時沿用主圖。',
            'order': '數字越小越前面；第一張也是可替換的廣告。',
            'link': '選填完整 https:// 網址；留空會前往商品列表。',
        }

    def clean_image(self):
        return validate_image(self.cleaned_data.get('image'))

    def clean_mobile_image(self):
        return validate_image(self.cleaned_data.get('mobile_image'))

    def clean_link(self):
        value = self.cleaned_data.get('link', '')
        if value and not value.startswith(('https://', 'http://')):
            raise forms.ValidationError('連結只接受 http 或 https 網址。')
        return value


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'slug', 'description', 'order', 'is_active']
        widgets = {'description': forms.Textarea(attrs={'rows': 3})}


class OrderUpdateForm(forms.ModelForm):
    version = forms.CharField(widget=forms.HiddenInput)

    class Meta:
        model = Order
        fields = ['status', 'tracking_number', 'admin_note']
        widgets = {'admin_note': forms.Textarea(attrs={'rows': 4})}
        help_texts = {'admin_note': '僅管理員可見，不會顯示給會員。', 'tracking_number': '出貨後提供會員查詢用。'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['version'].initial = self.instance.updated_at.isoformat()


class WishReplyForm(forms.ModelForm):
    class Meta:
        model = Wish
        fields = ['status', 'admin_reply']
        widgets = {'admin_reply': forms.Textarea(attrs={'rows': 5})}


class SiteConfigForm(forms.ModelForm):
    class Meta:
        model = SiteConfig
        fields = ['site_name', 'line_url', 'instagram_url', 'gmail', 'about_us', 'notice']
        widgets = {'about_us': forms.Textarea(attrs={'rows': 6}), 'notice': forms.Textarea(attrs={'rows': 6})}
