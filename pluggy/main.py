# This is a sample Python script.
import asyncio
from datetime import datetime, timezone
from config import URL, TOKEN, ORG, BUCKET, TAPO_PASSWORD, TAPO_USERNAME
import influxdb_client, os, time
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import json
import logging
from json import JSONDecodeError
from tapo import ApiClient


logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s.%(msecs)03d %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

logger = logging.getLogger(__name__)
PLUGS = {
    'driving rig':
        {
            'ip_address': '192.168.0.51',
            'location': 'office',
        },
    'tv':
        {
            'ip_address': '192.168.0.52',
            'location': 'front room',
        },
    'heater':
        {
            'ip_address': '192.168.0.57',
            'location': 'office',
        },
    # 'heating rail': '192.168.0.59',
    # 'clothes dryer':
    #     {
    #         'ip_address': '192.168.0.59',
    #         'location': 'dining room',
    #     },
    'desk':
        {
            'ip_address': '192.168.0.60',
            'location': 'office',
        },
}


async def main():
    client = ApiClient(TAPO_USERNAME, TAPO_PASSWORD)

    for name, details in PLUGS.items():
        print(f"Starting {name} -> {details['ip_address']}")
        try:
            device = await client.p110(details['ip_address'])
        except Exception:
            print("Failed! Maybe the plug is off at the wall?")
            continue

        influx_client = influxdb_client.InfluxDBClient(url=URL, token=TOKEN, org=ORG)
        write_api = influx_client.write_api(write_options=SYNCHRONOUS)

        device_info = await device.get_device_info()
        #print(f"Device info: {device_info.to_dict()}")

        device_usage = await device.get_device_usage()
        #print(f"Device usage: {device_usage.to_dict()}")

        current_power = await device.get_current_power()
        #print(f"Current power: {current_power.to_dict()}")

        energy_usage = await device.get_energy_usage()
        #print(f"Energy usage: {energy_usage.to_dict()}")

        point = (
            Point("tapo")
            .tag("location", details['location'])
            .tag("name", name)
            .field("on", 1 if device_info.device_on else 0)
        )
        write_api.write(bucket=BUCKET, org=ORG, record=point)

        for date_range in ["past30", "past7", "today"]:
            point = (
                Point("tapo")
                .tag("location", details['location'])
                .tag("name", name)
                .tag("power_usage", date_range)
                .field(date_range, device_usage.to_dict()["power_usage"][date_range])
            )
            write_api.write(bucket=BUCKET, org=ORG, record=point)

        for date_range in ["past30", "past7", "today"]:
            point = (
                Point("tapo")
                .tag("location", details['location'])
                .tag("name", name)
                .tag("time_usage", date_range)
                .field(date_range, device_usage.to_dict()["time_usage"][date_range])
            )
            write_api.write(bucket=BUCKET, org=ORG, record=point)

        for reading, value in energy_usage.to_dict().items():
            #print(f'{reading} -> {value}')

            if reading == "local_time":
                continue

            point = (
                Point("tapo")
                .tag("location", details['location'])
                .tag("name", name)
                .field(reading, value)
            )
            write_api.write(bucket=BUCKET, org=ORG, record=point)

        print(f"Completed {name} -> {details}!")


if __name__ == '__main__':
    asyncio.run(main())
