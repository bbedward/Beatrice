import requests
import redis
import os
import json

rdata = redis.StrictRedis(host=os.getenv(
    'REDIS_HOST', 'localhost'), port=6379)

dolartoday_price = "https://dolartoday.com/wp-admin/admin-ajax.php"

# Form data to be sent with the request
data = {
    "action": "dt_currency_calculator_handler",
    "amount": 1
}


def dolartoday_bolivar():
    response = json.loads(requests.post(url=dolartoday_price, data=data).text)
    if "Dólar Bitcoin" not in response:
        print("Invalid response " + str(response))
        return
    # Get the "Dólar Bitcoin" value
    bitcoin_dollar_value = response["Dólar Bitcoin"]

    # Extract the numerical value from the string
    bolivarprice = float(bitcoin_dollar_value.split()[1])
    if bolivarprice is None:
        print("Couldn't find localbitcoin_ref price")
        return
    print(rdata.hset("prices", "dolartoday:usd-ves", bolivarprice),
          "DolarToday USD-VES", bolivarprice)

dolartoday_bolivar()
print("DolarToday USD-VES:", rdata.hget("prices",
                                        "dolartoday:usd-ves").decode('utf-8'))