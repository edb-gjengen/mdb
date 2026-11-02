import datetime
import re


def format_domain_serial_and_add_one(serial):
    today = datetime.datetime.now()
    res = re.findall(
        rf"^{today.year:4d}{today.month:02d}{today.day:02d}(\d\d)$",
        str(serial),
        re.DOTALL,
    )

    if len(res) == 0:
        """ This probably means that the serial is malformed
        or the date is wrong. We assume that if the date is wrong,
        it is in the past. Just create a new serial starting from 1."""
        return f"{today.year:4d}{today.month:02d}{today.day:02d}01"
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
        return f"{today.year:4d}{today.month:02d}{today.day:02d}{number:02d}"
    else:
        """ Just return the first serial for today. """
        return f"{today.year:4d}{today.month:02d}{today.day:02d}01"
