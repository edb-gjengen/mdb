from django.core.validators import RegexValidator
import re
# http://en.wikipedia.org/wiki/Hostname#Restrictions_on_valid_host_names
hostname_re = re.compile(r'^(?!-)[-a-z0-9]+(?<!-)$', re.IGNORECASE)
validate_hostname = RegexValidator(hostname_re, u'Enter a valid hostname', 'invalid')
