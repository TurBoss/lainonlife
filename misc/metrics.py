#!/usr/bin/env python3

# Radio and server metrics, for pretty graphs at https://lainon.life/graphs/.

from datetime import datetime
from influxdb import InfluxDBClient
import json
import psutil
import time
import urllib

def snapshot_icecast():
    """Return a snapshot of the icecast listener status."""

    f = urllib.request.urlopen("http://localhost:8000/status-json.xsl")
    stats = json.loads(f.read().decode("utf8"))

    channels = []
    for src in stats["icestats"]["source"]:
        channels.append({
            "channel": src["server_name"][:-6],
            "format": src["server_name"][-4:][:-1],
            "listeners": src["listeners"]
        })
    return channels


def get_format_list(snapshot):
    """Return the list of formats in a snapshot."""

    return {stream["format"] for stream in snapshot}


def get_channel_list(snapshot):
    """Return the list of channels in a snapshot."""

    return {stream["channel"] for stream in snapshot}


def get_upload():
    """Get the current upload, in bytes, since last boot."""

    return psutil.net_io_counters(pernic=False)[0]


def get_format_listeners(snapshot, fmt):
    """Get the number of listeners on a specific format, across all channels."""

    return sum([stream["listeners"] for stream in snapshot if stream["format"] == fmt])


def get_channel_listeners(snapshot, channel):
    """Get the number of listeners on a specific channel, across all formats."""

    return sum([stream["listeners"] for stream in snapshot if stream["channel"] == channel])


if __name__ == "__main__":
    client = InfluxDBClient()

    # Ensure the database exists
    client.create_database("lainon.life")

    # Gather the metrics
    now      = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    snapshot = snapshot_icecast()
    formats  = get_format_list(snapshot)
    channels = get_channel_list(snapshot)
    metrics  = [
        {"measurement": "upload_bytes", "time": now, "fields": {
            "total": get_upload()
        }},
        {"measurement": "format_listeners", "time": now, "fields": {
            fmt: get_format_listeners(snapshot, fmt) for fmt in formats
        }},
        {"measurement": "channel_listeners", "time": now, "fields": {
            ch: get_channel_listeners(snapshot, ch) for ch in channels
        }}
    ]

    # Write the metrics
    client.write_points(metrics, database="lainon.life")
