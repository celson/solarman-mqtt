"""
History - Export station production history as InfluxDB line protocol
"""

import datetime
from zoneinfo import ZoneInfo

MEASUREMENT = "solarman_station_history"

# API limits per request: 31 days or 12 months; years are not limited.
_MAX_DAYS = 31
_MAX_MONTHS = 12

_FIELDS = {
    "generationValue": "generation_kwh",
    "fullPowerHours": "full_power_hours",
}


def _add_months(day, months):
    index = day.year * 12 + day.month - 1 + months
    return datetime.date(index // 12, index % 12 + 1, 1)


def day_ranges(start, end):
    """
    Split [start, end] into ranges accepted by a daily history request
    :return: list of (YYYY-MM-DD, YYYY-MM-DD)
    """
    ranges = []
    while start <= end:
        stop = min(start + datetime.timedelta(days=_MAX_DAYS - 1), end)
        ranges.append((start.isoformat(), stop.isoformat()))
        start = stop + datetime.timedelta(days=1)
    return ranges


def month_ranges(start, end):
    """
    Split [start, end] into ranges accepted by a monthly history request
    :return: list of (YYYY-MM, YYYY-MM)
    """
    ranges = []
    start = start.replace(day=1)
    while start <= end:
        stop = min(_add_months(start, _MAX_MONTHS - 1), end.replace(day=1))
        ranges.append((start.strftime("%Y-%m"), stop.strftime("%Y-%m")))
        start = _add_months(stop, 1)
    return ranges


def to_lines(items, period, station_id, timezone):
    """
    Convert history items to InfluxDB line protocol, timestamped (in seconds)
    at the start of the period in the station timezone
    :param items: stationDataItems from a history request
    :param period: day, month or year
    :return: list of lines
    """
    lines = []
    for item in items:
        fields = ",".join(
            f"{name}={float(item[key])}"
            for key, name in _FIELDS.items()
            if item.get(key) is not None
        )
        if not fields:
            continue
        start = datetime.datetime(
            item["year"], item.get("month") or 1, item.get("day") or 1, tzinfo=timezone
        )
        lines.append(
            f"{MEASUREMENT},station={station_id},period={period} {fields} {int(start.timestamp())}"
        )
    return lines


class StationHistory:  # pylint: disable=too-few-public-methods
    """
    Collect the daily, monthly and yearly history of a station
    """

    def __init__(self, api):
        self.api = api
        base = api.get_station_base()
        self.timezone = ZoneInfo(
            (base.get("region") or {}).get("timezone") or "UTC"
        )
        self.start_operating = datetime.datetime.fromtimestamp(
            base["startOperatingTime"], self.timezone
        ).date()

    def lines(self, days=None):
        """
        Return the history as line protocol
        :param days: number of days back to export, or None for everything
        since the station started operating
        :return: list of lines
        """
        end = datetime.datetime.now(self.timezone).date()
        start = self.start_operating
        if days is not None:
            start = max(start, end - datetime.timedelta(days=days - 1))

        lines = []
        for first, last in day_ranges(start, end):
            lines += self._fetch(2, first, last, "day")
        for first, last in month_ranges(start, end):
            lines += self._fetch(3, first, last, "month")
        lines += self._fetch(4, str(start.year), str(end.year), "year")
        return lines

    def _fetch(self, time_type, start, end, period):
        data = self.api.get_station_history(time_type, start, end)
        if not data.get("success"):
            raise RuntimeError(
                f"history request {period} {start}..{end} failed: {data.get('msg')}"
            )
        return to_lines(
            data.get("stationDataItems") or [],
            period,
            self.api.station_id,
            self.timezone,
        )
