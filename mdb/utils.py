import datetime
import re


def format_domain_serial_and_add_one(serial):
    today = datetime.datetime.now()
    res = re.findall(r"^%4d%02d%02d(\d\d)$" % (
        today.year, today.month, today.day), str(serial), re.DOTALL)

    if len(res) == 0:
        """ This probably means that the serial is malformed
        or the date is wrong. We assume that if the date is wrong,
        it is in the past. Just create a new serial starting from 1."""
        return "%4d%02d%02d%02d" % \
            (today.year, today.month, today.day, 1)
    elif len(res) == 1:
        """ The serial contains todays date, just update it. """
        try:
            number = int(res[0])
        except ValueError:
            number = 1
        if number >= 99:
            """ This is bad... Just keep the number on 99.
            We also send a mail to sysadmins telling them that
            something is wrong..."""

        else:
            number += 1
        return "%4d%02d%02d%02d" % (
            today.year, today.month, today.day, number)
    else:
        """ Just return the first serial for today. """
        return "%4d%02d%02d%02d" % \
            (today.year, today.month, today.day, 1)
