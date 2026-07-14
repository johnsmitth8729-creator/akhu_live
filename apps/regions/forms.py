from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from regions.models import Region

User = get_user_model()

class RegionCreationForm(forms.ModelForm):
    username = forms.CharField(
        max_length=150,
        label=_("Admin Username"),
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Enter username')})
    )
    password = forms.CharField(
        label=_("Admin Password"),
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': _('Enter password')})
    )
    name = forms.CharField(
        label=_("Region Name"),
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('e.g., Campus A')})
    )
    description = forms.CharField(
        label=_("Description"),
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('About this region')})
    )
    logo = forms.ImageField(
        label=_("Logo (Optional)"),
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Region
        fields = ['name', 'description', 'logo']

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError(_("A user account with this username already exists."))
        return username


class RegionUpdateForm(forms.ModelForm):
    name = forms.CharField(
        label=_("Region Name"),
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    description = forms.CharField(
        label=_("Description"),
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )
    logo = forms.ImageField(
        label=_("Logo"),
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )
    is_active = forms.BooleanField(
        label=_("Is Active"),
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = Region
        fields = ['name', 'description', 'logo', 'is_active']
