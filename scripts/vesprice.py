import os
import sys

import redis
import requests

RATES_URL = "https://open.er-api.com/v6/latest/USD"
VES_RATE_KEY = ("prices", "usd-ves")

rdata = redis.StrictRedis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=6379,
    password=os.getenv("REDIS_PASSWORD") or None,
)


def usd_ves_rate() -> float | None:
    try:
        response = requests.get(RATES_URL, timeout=30).json()
    except (requests.RequestException, ValueError) as exc:
        print(f"Request failed: {exc}")
        return None
    if not isinstance(response, dict) or response.get("result") != "success":
        print(f"Invalid response: {response}")
        return None
    rate = response.get("rates", {}).get("VES")
    if not isinstance(rate, (int, float)):
        print("No VES rate in response")
        return None
    return float(rate)


rate = usd_ves_rate()
# Non-zero exit keeps the CronJob's OnFailure retry behavior for transient failures.
if rate is None:
    sys.exit(1)
rdata.hset(*VES_RATE_KEY, rate)
print("USD-VES:", rate)
