import aiohttp
import asyncio
import redis
import json
import util
import settings

logger = util.get_logger("api")

CG_BTC_CACHE_KEY = 'beatrice_btccache'
CG_NANO_CACHE_KEY = 'beatrice_nanocache'
CG_BAN_CACHE_KEY = 'beatrice_banocache'

CGNANO_URL = 'https://api.coingecko.com/api/v3/coins/nano?localization=false&tickers=true&market_data=true&community_data=false&developer_data=false&sparkline=false'
CGBTC_URL = 'https://api.coingecko.com/api/v3/coins/bitcoin?localization=false&tickers=false&market_data=true&community_data=false&developer_data=false&sparkline=false'
BANANO_URL = 'https://api.coingecko.com/api/v3/coins/banano?localization=false&tickers=true&market_data=true&community_data=false&developer_data=false&sparkline=false'

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
    response = rd.get(CG_BAN_CACHE_KEY)
    if response is None:
        response = await json_get(BANANO_URL)
        if response is not None and 'market_data' in response:
            rd.set(CG_BAN_CACHE_KEY, json.dumps(response), ex=300) # Cache result for 5 minutes
    else:
        response = json.loads(response.decode('utf-8'))
    if response is not None and 'market_data' in response:
        # Get price and volume
        xrb_prices = []
        for t in response['tickers']:
            if t['target'] == 'XRB':
                xrb_prices.append(float(t['last']))
        banpernan = sum(xrb_prices) / len(xrb_prices)
        satprice = float(response["market_data"]["current_price"]["btc"])
        usdprice = float(response["market_data"]["current_price"]["usd"])
        volumebtc = float(response["market_data"]["total_volume"]["btc"])
        # Other data
        circ_supply = float(response['market_data']['circulating_supply'])
        rank = response['market_cap_rank']
        mcap = float(response['market_data']['market_cap']['usd'])
        ret = {
            "xrb":banpernan,
            "satoshi":satprice,
            "volume":volumebtc,
            "supply":circ_supply,
            "rank": rank,
            "usdprice": usdprice,
            "mcap": mcap,
            "change": float(response['market_data']['price_change_24h'])
        }
        if settings.VESPRICE:
            bolivardb = redis.StrictRedis(host='localhost', port=6379, db=2)
            ret['bolivar'] = usdprice * float(bolivardb.hget("prices", "dolartoday:usd-ves").decode('utf-8'))
        return ("BANANO", ret)
    else:
        return None

async def get_nano_price():
    response = rd.get(CG_NANO_CACHE_KEY)
    if response is None:
        response = await json_get(CGNANO_URL)
        if response is not None and 'market_data' in response:
            rd.set(CG_NANO_CACHE_KEY, json.dumps(response), ex=300) # Cache result for 5 minutes
    else:
        response = json.loads(response.decode('utf-8'))
    if response is not None and 'market_data' in response:
        # Get price and volume
        volumebtc = float(response["market_data"]["total_volume"]["btc"])
        kucoinprice = 0
        binanceprice = 0
        for t in response['tickers']:
            if t['market']['identifier'] == 'kucoin' and t['target'] == 'BTC':
                kucoinprice = float(t['last'])
            elif t['market']['identifier'] == 'binance' and t['target'] == 'BTC':
                binanceprice = float(t['last'])
        usdprice = float(response["market_data"]["current_price"]["usd"])
        # Other data
        circ_supply = float(response['market_data']['circulating_supply'])
        rank = response['market_cap_rank']
        mcap = float(response['market_data']['market_cap']['usd'])
        ret = {
            "kucoin":kucoinprice,
            "binance":binanceprice,
            "volume":volumebtc,
            "supply":circ_supply,
            "rank": rank,
            "usdprice": usdprice,
            "mcap":mcap
        }
        if settings.VESPRICE:
            bolivardb = redis.StrictRedis(host='localhost', port=6379, db=2)
            ret['bolivar'] = usdprice * float(bolivardb.hget("prices", "dolartoday:usd-ves").decode('utf-8'))
        return ("NANO", ret)
    else:
        return None

async def get_btc_usd():
    response = rd.get(CG_BTC_CACHE_KEY)
    if response is None:
        response = await json_get(CGBTC_URL)
        if response is not None and 'market_data' in response:
            rd.set(CG_BTC_CACHE_KEY, json.dumps(response), ex=300) # Cache for 5 minutes
    else:
        response = json.loads(response.decode('utf-8'))
    if response is None or 'market_data' not in response:
        return None
    usdprice = float(response["market_data"]["current_price"]["usd"])
    return ("BTC", {"usdprice":usdprice})

async def get_all_prices():
    """Fires all price requests simultaneously and exits after getting all results. Returns array of results"""
    tasks = [
        get_nano_price(),
        get_banano_price(),
        get_btc_usd()
    ]

    ret = []

    while len(tasks):
        done, tasks = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            result = task.result()
            if result is not None:
                ret.append(task.result())
    return ret

