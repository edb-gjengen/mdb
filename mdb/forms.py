from django import forms
from django.core.exceptions import ValidationError
from django.forms import ModelChoiceField

from mdb.models import Interface, Ip4Address


class Ip4ModelChoiceField(ModelChoiceField):
    def label_from_instance(self, obj):
        if not hasattr(obj, 'interface'):
            return obj.address

        return "{} ({})".format(obj.address, obj.interface.host.hostname)


class InterfaceForm(forms.ModelForm):
    model = Interface

    def clean(self):
        macaddr = self.cleaned_data['macaddr']
        ip4address = self.cleaned_data['ip4address']

        if Interface.objects.filter(macaddr=macaddr).exists():
            for interface in Interface.objects.filter(macaddr=macaddr):
                subnet = interface.ip4address.subnet
                if subnet == ip4address.subnet and interface != self.instance:
                    raise ValidationError('Macaddr already in this subnet')

    def __init__(self, *args, **kwargs):
        super(InterfaceForm, self).__init__(*args, **kwargs)

        # Join Ip4Address with tables interface and host,
        # before printing the select labels that walk those two relations.
        queryset = Ip4Address.objects.select_related('interface', 'interface__host')
        self.fields['ip4address'] = Ip4ModelChoiceField(queryset=queryset)
