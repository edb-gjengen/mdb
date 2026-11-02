from django import forms
from django.core.exceptions import ValidationError
from django.forms import ModelChoiceField, NumberInput
from django.utils.safestring import mark_safe

from mdb.models import Interface, Ip4Address


class SerialNumberInput(NumberInput):
    """Number input for DNS SOA serials (YYYYMMDDXX).

    Renders wide enough to show the full 10-digit serial and adds a button
    that prefills the field with the next serial: today's first, or one more than
    the current serial when that is higher.
    """

    def __init__(self, attrs=None):
        default_attrs = {"style": "width: 12em"}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)

    def render(self, name, value, attrs=None, renderer=None):
        field = super().render(name, value, attrs, renderer)
        field_id = (attrs or {}).get("id", f"id_{name}")
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
        // As mdb.utils.format_domain_serial_and_add_one: never lower than the current
        // serial, so past XX = 99 it carries into the date.
        var current = parseInt((input.value || '').trim(), 10);
        var next = parseInt(today + '01', 10);
        if (!isNaN(current) && current + 1 > next) {
            next = current + 1;
        }
        input.value = String(next);
    };
}
</script>
""".replace("__ID__", field_id)
        return mark_safe(field + extra)


class Ip4ModelChoiceField(ModelChoiceField):
    def label_from_instance(self, obj):
        if not hasattr(obj, "interface"):
            return obj.address

        return f"{obj.address} ({obj.interface.host.hostname})"


class InterfaceForm(forms.ModelForm):
    class Meta:
        model = Interface
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        # Missing when the field itself failed validation, and the address is optional.
        macaddr = cleaned_data.get("macaddr")
        ip4address = cleaned_data.get("ip4address")
        if not macaddr or ip4address is None:
            return cleaned_data

        # dhcpd matches MAC addresses whatever their case.
        clashes = Interface.objects.filter(
            macaddr__iexact=macaddr, ip4address__subnet=ip4address.subnet
        ).exclude(pk=self.instance.pk)
        if clashes.exists():
            raise ValidationError("Macaddr already in this subnet")
        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Join Ip4Address with tables interface and host,
        # before printing the select labels that walk those two relations.
        queryset = Ip4Address.objects.select_related("interface", "interface__host")
        # Not required, as on the model: a host can have interfaces without IPv4.
        self.fields["ip4address"] = Ip4ModelChoiceField(
            queryset=queryset, required=False
        )
