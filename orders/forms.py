from django import forms
from .models import Order, Wish

class CheckoutForm(forms.ModelForm):
    def clean_recipient_phone(self):
        import re
        value = self.cleaned_data['recipient_phone'].strip()
        if not re.fullmatch(r'[+\d\s()\-]{8,20}', value):
            raise forms.ValidationError('請輸入有效的聯絡電話。')
        return value

    def clean_recipient_address(self):
        value = self.cleaned_data['recipient_address'].strip()
        if len(value) < 8:
            raise forms.ValidationError('請填寫完整的收件地址。')
        return value

    class Meta:
        model = Order
        fields = ['recipient_name', 'recipient_phone', 'recipient_address', 'note']
        widgets = {
            'recipient_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '收件人姓名'}),
            'recipient_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '聯絡電話'}),
            'recipient_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': '收件地址'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': '備註（選填）'}),
        }

class WishForm(forms.ModelForm):
    def clean_reference_image(self):
        image = self.cleaned_data.get('reference_image')
        if image and image.size > 5 * 1024 * 1024:
            raise forms.ValidationError('圖片需小於 5 MB。')
        if image and getattr(image, 'image', None) and image.image.format not in ('JPEG', 'PNG', 'WEBP'):
            raise forms.ValidationError('請上傳 JPG、PNG 或 WebP 圖片。')
        return image

    class Meta:
        model = Wish
        fields = ['wish_type', 'title', 'description', 'reference_image', 'reference_url']
        widgets = {
            'wish_type': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '例：想找拉拉熊日本限定玩偶'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': '請詳細描述您想要的商品...'}),
            'reference_image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'reference_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': '參考連結（選填）'}),
        }
