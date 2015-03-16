from django.core.validators import RegexValidator
import re

# http://en.wikipedia.org/wiki/Hostname#Restrictions_on_valid_host_names
hostname_re = re.compile(r'^(?!-)[-a-z0-9]+(?<!-)$', re.IGNORECASE)
validate_hostname = RegexValidator(
    regex=hostname_re,
    message=u'Enter a valid hostname',
    code='invalid')

macaddr_re = re.compile(r'^([0-9A-F]{2}[:]){5}([0-9A-F]{2})$', re.IGNORECASE)
validate_macaddr = RegexValidator(
    regex=macaddr_re,
    message=u'Enter a valid MAC address',
    code='invalid')
