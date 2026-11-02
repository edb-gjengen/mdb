import pytest
from freezegun import freeze_time

from mdb.utils import format_domain_serial_and_add_one


@freeze_time("2026-11-02")
@pytest.mark.parametrize(
    ("serial", "expected"),
    [
        (2026110205, 2026110206),  # today: next number
        (2025010107, 2026110201),  # an earlier day: today's first
        (1, 2026110201),  # not a date at all
        (2026110298, 2026110299),
        (2026110299, 2026110300),  # used to stay at 99, so the change never synced
        (2026110300, 2026110301),  # ahead of today: never goes back
        (2026110505, 2026110506),
        (None, 2026110201),
        ("garbage", 2026110201),
    ],
)
def test_next_serial(serial, expected):
    assert format_domain_serial_and_add_one(serial) == expected


@freeze_time("2026-11-02")
def test_serial_always_increases():
    serial = 2026110290
    for _ in range(30):
        new = format_domain_serial_and_add_one(serial)
        assert new > serial
        serial = new
