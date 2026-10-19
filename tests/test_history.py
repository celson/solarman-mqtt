"""
Tests for the history line protocol export
"""

import datetime
import unittest
from zoneinfo import ZoneInfo

from solarman.history import day_ranges, info_line, month_ranges, to_lines

TZ = ZoneInfo("America/Sao_Paulo")


class TestRanges(unittest.TestCase):
    """Request ranges stay within the API limits"""

    def test_day_ranges(self):
        ranges = day_ranges(datetime.date(2026, 9, 1), datetime.date(2026, 10, 19))
        self.assertEqual(
            ranges, [("2026-09-01", "2026-10-01"), ("2026-10-02", "2026-10-19")]
        )

    def test_month_ranges(self):
        ranges = month_ranges(datetime.date(2022, 4, 12), datetime.date(2023, 5, 2))
        self.assertEqual(ranges, [("2022-04", "2023-03"), ("2023-04", "2023-05")])

    def test_single_day(self):
        day = datetime.date(2026, 10, 19)
        self.assertEqual(day_ranges(day, day), [("2026-10-19", "2026-10-19")])
        self.assertEqual(month_ranges(day, day), [("2026-10", "2026-10")])


class TestLines(unittest.TestCase):
    """History items become line protocol at the start of their period"""

    def test_day(self):
        items = [{"year": 2026, "month": 10, "day": 19, "generationValue": 22.6, "fullPowerHours": 4.11}]
        self.assertEqual(
            to_lines(items, "day", 123, TZ),
            ["solarman_station_history,station=123,period=day generation_kwh=22.6,full_power_hours=4.11 1792378800"],
        )

    def test_year_without_hours(self):
        items = [{"year": 2023, "month": 0, "day": 0, "generationValue": 6982.1, "fullPowerHours": None}]
        self.assertEqual(
            to_lines(items, "year", 123, TZ),
            ["solarman_station_history,station=123,period=year generation_kwh=6982.1 1672542000"],
        )

    def test_empty_item(self):
        self.assertEqual(to_lines([{"year": 2026, "generationValue": None}], "year", 1, TZ), [])


class TestInfoLine(unittest.TestCase):
    """Station base information becomes a single point"""

    def test_info(self):
        base = {"installedCapacity": 5.5, "mergeElectricPrice": 1.13, "ownerName": "x"}
        self.assertEqual(
            info_line(base, 123, 1792378800.5),
            "solarman_station_info,station=123 installed_capacity_kw=5.5,electricity_price=1.13 1792378800",
        )

    def test_info_empty(self):
        self.assertIsNone(info_line({}, 123, 0))


if __name__ == "__main__":
    unittest.main()
