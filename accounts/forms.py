from django import forms
from .models import UserProfile

class UserProfileForm(forms.ModelForm):
    first_name = forms.CharField(label='姓名', max_length=30, required=False)
    email = forms.EmailField(label='Email（登入帳號）', required=True, disabled=True)

    class Meta:
        model = UserProfile
        fields = ['phone', 'address', 'line_id']
        labels = {
            'phone': '電話',
            'address': '地址',
            'line_id': 'LINE ID',
        }
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '例：0912345678'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': '收件地址'}),
            'line_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'LINE ID（選填，不代表已完成登入綁定）'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['first_name'].initial = user.first_name
            self.fields['email'].initial = user.email
        self.fields['first_name'].widget.attrs.update({'class': 'form-control'})
        self.fields['email'].widget.attrs.update({'class': 'form-control'})
