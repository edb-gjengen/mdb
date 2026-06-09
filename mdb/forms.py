from django import forms
from django.core.exceptions import ValidationError
from django.forms import ModelChoiceField, NumberInput
from django.utils.safestring import mark_safe

from mdb.models import Interface, Ip4Address


class SerialNumberInput(NumberInput):
    """Number input for DNS SOA serials (YYYYMMDDXX).

    Renders wide enough to show the full 10-digit serial and adds a button
    that prefills the field with today's date plus the next available XX
    counter (incrementing if the field already holds today's serial).
    """

    def __init__(self, attrs=None):
        default_attrs = {"style": "width: 12em"}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)

    def render(self, name, value, attrs=None, renderer=None):
        field = super().render(name, value, attrs, renderer)
        field_id = (attrs or {}).get("id", "id_%s" % name)
        extra = """
<button type="button" class="button" style="margin-left: 0.5em;"
        onclick="mdbBumpSerial('__ID__')">Today + next serial</button>
<script>
if (typeof window.mdbBumpSerial === 'undefined') {
    window.mdbBumpSerial = function (inputId) {
        var input = document.getElementById(inputId);
        if (!input) { return; }
        var now = new Date();
        var today = '' + now.getFullYear()
            + String(now.getMonth() + 1).padStart(2, '0')
            + String(now.getDate()).padStart(2, '0');
        var current = (input.value || '').trim();
        var xx = 1;
        if (current.length === 10 && current.slice(0, 8) === today) {
            xx = Math.min(parseInt(current.slice(8), 10) + 1, 99);
        }
        input.value = today + String(xx).padStart(2, '0');
    };
}
</script>
""".replace(
            "__ID__", field_id
        )
        return mark_safe(field + extra)


class Ip4ModelChoiceField(ModelChoiceField):
    def label_from_instance(self, obj):
        if not hasattr(obj, "interface"):
            return obj.address

        return "{} ({})".format(obj.address, obj.interface.host.hostname)


class InterfaceForm(forms.ModelForm):
    model = Interface

    def clean(self):
        macaddr = self.cleaned_data["macaddr"]
        ip4address = self.cleaned_data["ip4address"]

        for interface in Interface.objects.filter(macaddr=macaddr):
            subnet = interface.ip4address.subnet
            if subnet == ip4address.subnet and interface != self.instance:
                raise ValidationError("Macaddr already in this subnet")

    def __init__(self, *args, **kwargs):
        super(InterfaceForm, self).__init__(*args, **kwargs)

        # Join Ip4Address with tables interface and host,
        # before printing the select labels that walk those two relations.
        queryset = Ip4Address.objects.select_related("interface", "interface__host")
        self.fields["ip4address"] = Ip4ModelChoiceField(queryset=queryset)
