from django import forms
from django.utils.translation import gettext_lazy as _
from sources.models import LiveSource
from regions.models import Region

class LiveSourceForm(forms.ModelForm):
    class Meta:
        model = LiveSource
        fields = [
            'region', 'name', 'source_type', 'recording_enabled',
            'rtsp_url', 'rtsp_username', 'rtsp_password',
            'building', 'floor', 'room'
        ]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Apply Bootstrap classes
        for name, field in self.fields.items():
            if name == 'recording_enabled':
                field.widget.attrs.update({'class': 'form-check-input'})
            elif name == 'region' or name == 'source_type':
                field.widget.attrs.update({'class': 'form-select'})
            else:
                field.widget.attrs.update({'class': 'form-control'})

        # Restrict/Hide region for Region Admin
        if user and user.is_region_admin():
            self.fields['region'].required = False
            self.fields['region'].widget = forms.HiddenInput()
        else:
            self.fields['region'].widget.attrs.update({'class': 'form-select'})
            self.fields['region'].queryset = Region.objects.all()
            self.fields['region'].label = _("Region")

    def clean(self):
        cleaned_data = super().clean()
        source_type = cleaned_data.get('source_type')
        rtsp_url = cleaned_data.get('rtsp_url')

        if source_type == LiveSource.SourceTypes.IP_CAMERA:
            if not rtsp_url:
                self.add_error('rtsp_url', _('RTSP URL is required for IP Camera sources.'))
        return cleaned_data
