import aiohttp
import asyncio
import redis
import json
import util

logger = util.get_logger("api")

CACHE_MCAP_RESULT_KEY = 'beatrice_cmccache'
CACHE_CREEPER_KEY = 'beatrice_creepercache'

BINANCE_URL = 'https://www.binance.com/api/v3/ticker/price?symbol=NANOBTC'
KUCOIN_URL = 'https://api.kucoin.com/v1/open/tick?symbol=NANO-BTC'
NANEX_URL = 'https://nanex.co/api/public/ticker/btcnano'
CMC_URL = 'https://api.coinmarketcap.com/v2/ticker/1567/'
CMC_BTC_URL = 'https://api.coinmarketcap.com/v2/ticker/1/'
BANANO_URL = 'https://api.creeper.banano.cc/ticker'

rd = redis.Redis()

async def json_get(reqUrl):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(reqUrl, timeout=10) as resp:
                jsonResp = await resp.json()
                return jsonResp
    except BaseException:
        return None

async def get_banano_price():
    response = rd.get(CACHE_CREEPER_KEY)
    if response is None:
        response = await json_get(BANANO_URL)
    else:
        response = json.loads(response.decode('utf-8'))
    if response is not None and 'data' in response:
        rd.set(CACHE_CREEPER_KEY, json.dumps(response), ex=300) # Cache result for 5 minutes
        banpernan = 1 / float(response['data']['quotes']['NANO']['price'])
        usdprice = float(response['data']['quotes']['USD']['price'])
        nanovol = float(response['data']['quotes']['NANO']['volume_24h'])
        btcvol = float(response['data']['quotes']['BTC']['volume_24h'])
        circ_supply = float(response['data']['circulating_supply'])
        return (banpernan, float(response['data']['quotes']['BTC']['price']), usdprice, nanovol, btcvol, circ_supply)
    else:
        return (None, None, None, None, None, None)

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

async def get_cmc_ticker(limit):
    # Try to retrieve cached version first
    response = rd.get(CACHE_MCAP_RESULT_KEY)
    if response is None:
        # Not in cache, retrieve it from API
        response = None
        for i in range(12):
            i = 100 * i + 1
            result = await json_get(f'https://api.coinmarketcap.com/v2/ticker/?limit={limit}&start={i}')
            if response is None:
                response = result
            else:
                for k in result['data']:
                    response['data'][k] = result['data'][k]
        # Store result from API with an expiry of 1 hour
        rd.set(CACHE_MCAP_RESULT_KEY, json.dumps(response), ex=3600)
    else:
        response = json.loads(response.decode('utf-8'))
    return response


async def get_banano_rank(mcap, limit):
	ticker = await get_cmc_ticker(limit)
	if ticker is None:
		return "N/A"
	i = 1
	for key in ticker['data']:
		logger.info(int(ticker['data'][key]['quotes']['USD']['market_cap']))
		if int(ticker['data'][key]['quotes']['USD']['market_cap']) < mcap:
			return i
		else:
			i += 1
	return "N/A"

