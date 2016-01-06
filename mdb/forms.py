from django import forms
from django.forms import ModelChoiceField

from mdb.models import Interface, Ip4Address


class Ipv4ModelChoiceField(ModelChoiceField):
    # def __init__(self, *args, **kwargs):
    #     super(Ipv4ModelChoiceField, self).__init__(*args, **kwargs)

    def label_from_instance(self, obj):
        # TODO improve those labelZ
        return obj.__str__()


class InterfaceForm(forms.ModelForm):
    model = Interface

    def __init__(self, *args, **kwargs):
        super(InterfaceForm, self).__init__(*args, **kwargs)

        self.fields['ip4address'] = Ipv4ModelChoiceField(queryset=Ip4Address.objects.select_related())
