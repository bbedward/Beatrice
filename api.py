import aiohttp
import asyncio

BINANCE_URL = 'https://www.binance.com/api/v3/ticker/price?symbol=NANOBTC'
KUCOIN_URL = 'https://api.kucoin.com/v1/open/tick?symbol=NANO-BTC'
NANEX_URL = 'https://nanex.co/api/public/ticker/btcnano'
CMC_URL = 'https://api.coinmarketcap.com/v2/ticker/1567/'
CMC_BTC_URL = 'https://api.coinmarketcap.com/v2/ticker/1/'
BANANO_URL = 'https://api.creeper.banano.cc/ticker'

async def json_get(reqUrl):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(reqUrl, timeout=10) as resp:
                jsonResp = await resp.json()
                return jsonResp
    except BaseException:
        return None

async def get_banano_price():
    response = await json_get(BANANO_URL)
    if response is not None:
        banpernan = 1 / float(response['data']['quotes']['NANO']['price'])
        usdprice = float(response['data']['quotes']['USD']['price'])
        nanovol = float(response['data']['quotes']['NANO']['volume_24h'])
        return (banpernan, usdprice, nanovol)
    else:
        return (None, None, None)

async def get_binance_price():
    response = await json_get(BINANCE_URL)
    if response is not None:
        return ("BINANCE", float(response["price"]))
    else:
        return None

async def get_kucoin_price():
    response = await json_get(KUCOIN_URL)
    if response is not None:
        return ("KUCOIN", float(response["data"]["lastDealPrice"]))
    else:
        return None

async def get_nanex_price():
    response = await json_get(NANEX_URL)
    if response is not None:
        return ("NANEX", 1 / float(response["last_trade"]))
    else:
        return None

async def get_cmc_data():
    response = await json_get(CMC_URL)
    if response is None:
        return None
    rank = response["data"]["rank"]
    usd = "${0:,.2f}".format(float(response["data"]["quotes"]["USD"]["price"]))
    mcap = "${0:,}".format(int(response["data"]["quotes"]["USD"]["market_cap"]))
    volume = "${0:,}".format(int(response["data"]["quotes"]["USD"]["volume_24h"]))
    resp = ""
    resp += "```\nRank       : {0}".format(rank)
    resp += "\nPrice      : {0}".format(usd)
    resp += "\nMarket Cap : {0}".format(mcap)
    resp += "\nVolume(24H): {0}```".format(volume)
    return resp

async def get_btc_usd():
	response = await json_get(CMC_BTC_URL)
	if response is None:
		return None
	return "${0:,.2f}".format(float(response["data"]["quotes"]["USD"]["price"]))

async def get_all_prices():
    """Fires all price requests simultaneously and exits after getting all results. Returns array of results"""
    tasks = [
        get_binance_price(),
        get_kucoin_price(),
        get_nanex_price(),
    ]

    ret = []

    while len(tasks):
        done, tasks = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            result = task.result()
            if result is not None:
                ret.append(task.result())
    # Sort by price
    ret.sort(key=lambda tup: tup[1], reverse=True)
    return ret



