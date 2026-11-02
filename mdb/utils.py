import datetime


def format_domain_serial_and_add_one(serial):
    """Return the serial after `serial`, in the YYYYMMDDnn form where it can be.

    The serial must always increase, or named and dhcpd ignore the change. Today's first
    serial is used while it is higher. Otherwise the serial goes up by one: past nn = 99
    it carries into the date (2026110299 -> 2026110300), and a serial already ahead of
    today, from that carry or a dynamic update, keeps counting from where it is.
    """
    today_first = int(datetime.date.today().strftime("%Y%m%d")) * 100 + 1
    try:
        return max(int(serial) + 1, today_first)
    except TypeError, ValueError:
        return today_first
