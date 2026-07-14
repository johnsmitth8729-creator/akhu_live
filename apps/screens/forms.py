from django import forms
from django.utils.translation import gettext_lazy as _
from screens.models import Computer
from regions.models import Region

class ComputerForm(forms.ModelForm):
    name = forms.CharField(
        label=_("Computer Name"),
        widget=forms.TextInput(attrs={'placeholder': _('e.g., Exam PC-01')})
    )
    asset_number = forms.CharField(
        label=_("Asset Number"),
        widget=forms.TextInput(attrs={'placeholder': _('e.g., AKHU-PC-2026-001')})
    )
    os = forms.CharField(
        label=_("Operating System"),
        initial="Windows 11",
        widget=forms.TextInput(attrs={'placeholder': _('e.g., Windows 11')})
    )
    department = forms.CharField(
        label=_("Department"),
        widget=forms.TextInput(attrs={'placeholder': _('e.g., Computer Science')})
    )
    building = forms.CharField(
        label=_("Building"),
        widget=forms.TextInput(attrs={'placeholder': _('e.g., Block B')})
    )
    floor = forms.CharField(
        label=_("Floor"),
        widget=forms.TextInput(attrs={'placeholder': _('e.g., 2nd Floor')})
    )
    room = forms.CharField(
        label=_("Room"),
        widget=forms.TextInput(attrs={'placeholder': _('e.g., Lab 202')})
    )
    description = forms.CharField(
        label=_("Description"),
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': _('Optional machine details')})
    )

    class Meta:
        model = Computer
        fields = [
            'region', 'name', 'asset_number', 'os', 'department', 
            'building', 'floor', 'room', 'description'
        ]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Style with bootstrap classes
        for name, field in self.fields.items():
            if name != 'region':
                field.widget.attrs.update({'class': 'form-control'})

        # Restrict/Hide region selector for Region Admins
        if user and user.is_region_admin():
            self.fields['region'].required = False
            self.fields['region'].widget = forms.HiddenInput()
        else:
            self.fields['region'].widget.attrs.update({'class': 'form-select'})
            self.fields['region'].queryset = Region.objects.all()
            self.fields['region'].label = _("Region")
