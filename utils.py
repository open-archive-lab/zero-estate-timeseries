from datetime import datetime

import pytz


def get_tokyo_datetime():
    tokyo_tz = pytz.timezone("Asia/Tokyo")
    return datetime.now(tokyo_tz)
