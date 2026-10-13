import json
import os
import sys

import redis
import requests

rdata = redis.StrictRedis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=6379,
    password=os.getenv("REDIS_PASSWORD") or None,
)

dolartoday_price = "https://dolartoday.com/wp-admin/admin-ajax.php"

data = {"action": "dt_currency_calculator_handler", "amount": 1}


def dolartoday_bolivar() -> bool:
    try:
        response = json.loads(requests.post(url=dolartoday_price, data=data, timeout=30).text)
    except (requests.RequestException, ValueError) as exc:
        print(f"Request failed: {exc}")
        return False
    if "Dólar Bitcoin" not in response:
        print("Invalid response " + str(response))
        return False
    try:
        bolivarprice = float(response["Dólar Bitcoin"].split()[1])
    except (AttributeError, IndexError, ValueError):
        print("Couldn't parse price from " + str(response["Dólar Bitcoin"]))
        return False
    print(
        rdata.hset("prices", "dolartoday:usd-ves", bolivarprice), "DolarToday USD-VES", bolivarprice
    )
    return True


# Non-zero exit keeps the CronJob's OnFailure retry behavior for transient scrape failures.
if not dolartoday_bolivar():
    sys.exit(1)
print("DolarToday USD-VES:", rdata.hget("prices", "dolartoday:usd-ves").decode("utf-8"))
