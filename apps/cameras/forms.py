from django import forms
from django.utils.translation import gettext_lazy as _
from cameras.models import Camera
from regions.models import Region

class CameraForm(forms.ModelForm):
    name = forms.CharField(
        label=_("Camera Name"),
        widget=forms.TextInput(attrs={'placeholder': _('e.g., Back Entrance Cam')})
    )
    description = forms.CharField(
        label=_("Description"),
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': _('Short details about coverage')})
    )
    rtsp_url = forms.CharField(
        label=_("RTSP URL"),
        widget=forms.TextInput(attrs={'placeholder': _('rtsp://192.168.1.100:554/stream1')})
    )
    ip_address = forms.GenericIPAddressField(
        label=_("IP Address"),
        widget=forms.TextInput(attrs={'placeholder': _('e.g., 192.168.1.100')})
    )
    port = forms.IntegerField(
        label=_("Port"),
        initial=554,
        widget=forms.NumberInput(attrs={'placeholder': '554'})
    )
    username = forms.CharField(
        label=_("Username"),
        required=False,
        widget=forms.TextInput(attrs={'placeholder': _('RTSP credentials username')})
    )
    password = forms.CharField(
        label=_("Password"),
        required=False,
        widget=forms.PasswordInput(render_value=True, attrs={'placeholder': _('RTSP credentials password')})
    )
    building = forms.CharField(
        label=_("Building"),
        widget=forms.TextInput(attrs={'placeholder': _('e.g., Main Block')})
    )
    floor = forms.CharField(
        label=_("Floor"),
        widget=forms.TextInput(attrs={'placeholder': _('e.g., 1st Floor')})
    )
    room = forms.CharField(
        label=_("Room"),
        widget=forms.TextInput(attrs={'placeholder': _('e.g., Room 104')})
    )

    class Meta:
        model = Camera
        fields = [
            'region', 'name', 'description', 'rtsp_url', 
            'ip_address', 'port', 'username', 'password', 
            'building', 'floor', 'room'
        ]
        
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Apply form-control CSS classes to all fields
        for name, field in self.fields.items():
            if name != 'region':
                field.widget.attrs.update({'class': 'form-control'})
                
        # If user is a Region Admin, prevent selecting another region
        if user and user.is_region_admin():
            self.fields['region'].required = False
            self.fields['region'].widget = forms.HiddenInput()
        else:
            self.fields['region'].widget.attrs.update({'class': 'form-select'})
            self.fields['region'].queryset = Region.objects.all()
            self.fields['region'].label = _("Region")
