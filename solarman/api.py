"""
Api
"""

import http.client
import json
import logging
import sys


class SolarmanApi:
    """
    Connect to the Solarman API and return PV data
    """

    def __init__(self, config, realtime=True):
        self.config = config
        self.station_id = config["stationId"]
        self.url = config["url"]
        self.token = self.get_token(
            self.config["appid"],
            self.config["secret"],
            self.config["username"],
            self.config["passhash"],
        )
        if not realtime:
            return

        self.station_realtime = self.get_station_realtime()
        self.device_current_data_inverter = self.get_device_current_data(
            self.config["inverterId"]
        )
        self.device_current_data_logger = self.get_device_current_data(
            self.config["loggerId"]
        )

        try:
            self.device_current_data_meter = self.get_device_current_data(
                self.config["meterId"]
            )
        except KeyError:
            self.device_current_data_meter = None

    def get_token(self, appid, secret, username, passhash):
        """
        Get a token from the API
        :return: access_token
        """
        try:
            conn = http.client.HTTPSConnection(self.url, timeout=60)
            payload = json.dumps(
                {"appSecret": secret, "email": username, "password": passhash}
            )
            headers = {"Content-Type": "application/json"}
            url = f"/account/v1.0/token?appId={appid}&language=en"
            conn.request("POST", url, payload, headers)
            res = conn.getresponse()
            data = json.loads(res.read())
            logging.debug("Received token")
            return data["access_token"]
        except Exception as error:  # pylint: disable=broad-except
            logging.error("Unable to fetch token: %s", str(error))
            sys.exit(1)

    def post(self, path, body):
        """
        POST a JSON body to an authenticated API endpoint
        :return: decoded JSON response
        """
        conn = http.client.HTTPSConnection(self.url, timeout=60)
        payload = json.dumps(body)
        headers = {
            "Content-Type": "application/json",
            "Authorization": "bearer " + self.token,
        }
        conn.request("POST", path, payload, headers)
        res = conn.getresponse()
        data = json.loads(res.read())
        return data

    def get_station_realtime(self):
        """
        Return station realtime data
        :return: realtime data
        """
        return self.post(
            "/station/v1.0/realTime?language=en", {"stationId": self.station_id}
        )

    def get_station_base(self):
        """
        Return station base information (capacity, start date, price, ...)
        :return: base data
        """
        return self.post(
            "/station/v1.0/base?language=en", {"stationId": self.station_id}
        )

    def get_station_history(self, time_type, start_time, end_time):
        """
        Return station history data
        :param time_type: 2 = day (max. 31 days), 3 = month (max. 12 months), 4 = year
        :param start_time: start, as YYYY-MM-DD, YYYY-MM or YYYY
        :param end_time: end, in the same format as start_time
        :return: history data
        """
        return self.post(
            "/station/v1.0/history?language=en",
            {
                "stationId": self.station_id,
                "timeType": time_type,
                "startTime": start_time,
                "endTime": end_time,
            },
        )

    def get_device_current_data(self, device_sn):
        """
        Return device current data
        :return: current data
        """
        return self.post(
            "/device/v1.0/currentData?language=en", {"deviceSn": device_sn}
        )

    def get_device_alerts(self, device_sn, start_timestamp, end_timestamp):
        """
        Return device alerts raised between two unix timestamps
        :return: alert data
        """
        return self.post(
            "/device/v1.0/alertList?language=en",
            {
                "deviceSn": device_sn,
                "startTimestamp": start_timestamp,
                "endTimestamp": end_timestamp,
                "page": 1,
                "size": 100,
            },
        )


class ConstructData:  # pylint: disable=too-few-public-methods
    """
    Return restructured and separated device current data
    Original data is removed
    :return: new current data
    """

    def __init__(self, data):
        self.data = data
        self.device_current_data = self.construct_data()

    def construct_data(self):
        """
        Return restructured and separated device current data
        """
        new_data_list = {}
        try:
            for i in self.data["dataList"]:
                del i["key"]
                name = i["name"]
                name = name.replace(" ", "_")
                del i["name"]
                new_data_list[name] = i["value"]
            del self.data["dataList"]
        except KeyError:
            pass
        return new_data_list
