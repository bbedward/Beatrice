import aiohttp
import asyncio
import json
import util
import settings

logger = util.get_logger("discord")

CG_BTC_CACHE_KEY = 'beatrice_btccache'
CG_NANO_CACHE_KEY = 'beatrice_nanocache'
CG_BAN_CACHE_KEY = 'beatrice_banocache'
CG_STATUS_CACHE_KEY = 'beatrice_statuscache'

CGNANO_URL = 'https://api.coingecko.com/api/v3/coins/nano?localization=false&tickers=true&market_data=true&community_data=false&developer_data=false&sparkline=false'
CGBTC_URL = 'https://api.coingecko.com/api/v3/coins/bitcoin?localization=false&tickers=false&market_data=true&community_data=false&developer_data=false&sparkline=false'
BANANO_URL = 'https://api.coingecko.com/api/v3/coins/banano?localization=false&tickers=true&market_data=true&community_data=false&developer_data=false&sparkline=false'

async def json_get(reqUrl,headers=""):
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(reqUrl, timeout=10) as resp:
                jsonResp = await resp.json()
                return jsonResp
    except BaseException:
        return None

# Gets and returns simple Banano price information
async def get_status():
    redis = await util.get_redis()
    response = await redis.get(CG_STATUS_CACHE_KEY)
    if response is None:
        cg_response = await json_get(BANANO_URL)
        if cg_response is not None and 'market_data' in cg_response:
            usd_prices = []
            sat_prices = []
            for t in cg_response['tickers']:
                        if t['target'] == 'USDT' and t['market']['name'] == 'CoinEx':
                            usd_prices.append(float(t['last']))
                            sat_prices.append(float(t['converted_last']['btc']*100000000))
            usdprice = sum(usd_prices) / len(usd_prices)
            satprice = sum(sat_prices) / len(sat_prices)
            ret = {
                "satoshi": satprice,
                "usdprice": usdprice
            }
            await redis.set(CG_STATUS_CACHE_KEY, json.dumps(ret), expire=300) # Cache result for 5 minutes
            return ret
        else:
            return None
    else:
        return json.loads(response)

async def get_banano_price():
    redis = await util.get_redis()
    response = await redis.get(CG_BAN_CACHE_KEY)
    if response is None:
        response = await json_get(BANANO_URL)
        if response is not None and 'market_data' in response:
            await redis.set(CG_BAN_CACHE_KEY, json.dumps(response), expire=300) # Cache result for 5 minutes
    else:
        response = json.loads(response)
    if response is not None and 'market_data' in response:
        # Get price and volume
        banpernan = float(response['market_data']['market_cap']['btc']) / float(await redis.get("nano-btc-price"))
        usd_prices = []
        sat_prices = []
        for t in response['tickers']:
                    if t['target'] == 'USDT' and t['market']['name'] == 'CoinEx':
                        usd_prices.append(float(t['last']))
                        sat_prices.append(float(t['converted_last']['btc']*100000000))
        usdprice = sum(usd_prices) / len(usd_prices)
        satprice = sum(sat_prices) / len(sat_prices)
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
            bolivardb = await util.get_redis()
            bolivarprice = await bolivardb.hget("prices", "dolartoday:usd-ves")
            if bolivarprice is not None:
                ret['bolivar'] = usdprice * float(bolivarprice)

        return ("BANANO", ret)
    else:
        return None

async def get_nano_price():
    redis = await util.get_redis()
    response = await redis.get(CG_NANO_CACHE_KEY)
    if response is None:
        response = await json_get(CGNANO_URL)
        if response is not None and 'market_data' in response:
            await redis.set(CG_NANO_CACHE_KEY, json.dumps(response), expire=300) # Cache result for 5 minutes
    else:
        response = json.loads(response)
    if response is not None and 'market_data' in response:
        # Cache nano-btc price
        await redis.set("nano-btc-price", f"{response['market_data']['market_cap']['btc']:.16f}")
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
            bolivardb = await util.get_redis()
            bolivarprice = await bolivardb.hget("prices", "dolartoday:usd-ves")
            if bolivarprice is not None:
                ret['bolivar'] = usdprice * float(bolivarprice)
        return ("NANO", ret)
    else:
        return None

async def get_btc_usd():
    redis = await util.get_redis()
    response = await redis.get(CG_BTC_CACHE_KEY)
    if response is None:
        response = await json_get(CGBTC_URL)
        if response is not None and 'market_data' in response:
            await redis.set(CG_BTC_CACHE_KEY, json.dumps(response), expire=300) # Cache for 5 minutes
    else:
        response = json.loads(response)
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

async def getFODLJSON(username):
    fahAPI = "https://api2.foldingathome.org/user/"+username
    bMinerAPI = "https://bananominer.com/user_name/"+username
    fahBonusAPI = "https://api2.foldingathome.org/bonus?user="+username

    tasks = [
        json_get(fahAPI),
        json_get(bMinerAPI),
        json_get(fahBonusAPI)
    ]
    ret = [{},{},[]]
    while len(tasks):
        done, tasks = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            result = task.result()
            if result is not None:
                if "users" in result: #simplest way to tell the json apart by results that I see...
                    ret[0] = result
                elif  "user" in result or "error" in result: #and "expired" in task.result()[0]
                    ret[1] = result
                else:
                    ret[2] = result
    return ret


async def getNetworkFarm(network):
    """
    Queries Zapper API for running wban farms on specified network    
    """
    resp = await json_get(f"https://api.zapper.xyz/v2/apps/banano/positions?network={network}&groupId=farm",headers={'accept': '*/*','Authorization': f'Basic {settings.ZAPPER_API}'})
    return network,resp

async def getWBANFARM():
    output = [] 
    #Start off by querying the API to find out all networks wban is listed on
    #Hopefully this means that if a new network is added there won't be a need to update this 
    r = await json_get(f"https://api.zapper.xyz/v2/apps/banano",headers={'accept': '*/*','Authorization': f'Basic {settings.ZAPPER_API}'})
    networks = []
    if r is None or 'supportedNetworks' not in r:
        return None    

    #Gather all the found networks
    for net in r["supportedNetworks"]:
        networks.append(net["network"])

    tasks = [] 

    #Create a task for each network 
    for network in networks:
        tasks.append(getNetworkFarm(network))
    
    while len(tasks):
        done, tasks = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            network,result = task.result()
            #Verify the task worked 
            if result is not None and len(result) > 0:
                farms = []
                #Go through all the farms for this network 
                for farm in result:
                    try: 
                        #Get the information on current network 
                        network = farm["network"]
                        if farm["key"] in ["1470554045", "3793781140"]: # Patch out (by farm-id) Bsc busd-wban and FTM farm as both have ended 
                            continue
                        if bool(farm["dataProps"]["isActive"]): #Ensure farm is active, 
                            for tokens in farm["tokens"]: #Recover the token pairs used in the network 
                                if tokens["metaType"] == "supplied" and tokens["type"] == "app-token" :
                                    tokens_in_farm = []
                                    for token in tokens["tokens"]:
                                        tokens_in_farm.append(token["symbol"])
                                    if len(tokens_in_farm) > 1 and tokens_in_farm[1] == "wBAN": #Some basic ordering, such that wban comes first 
                                        tokens_in_farm[0],tokens_in_farm[1] = tokens_in_farm[1],tokens_in_farm[0]
                            token_string = "-".join(tokens_in_farm) #Get a string representation of the pair 
                            #Get TVL and APR, round them 
                            try: #Naming of these may change, adapt in those cases.
                                tvl = int(farm["dataProps"]["liquidity"])
                            except:
                                try:
                                    tvl = int(farm["dataProps"]["totalValueLocked"])
                                except:
                                    tvl = "API Error"
                            try:
                                apr = round(farm["dataProps"]["apy"],1)
                            except:
                                try:
                                    apr = round(100 * float(farm["dataProps"]["yearlyROI"]),1)
                                except: 
                                    apr = "API Error"
                            farms.append((token_string,tvl,apr))
                    except:
                        return None
                #Add information of this network to output 
                if len(farms) > 0:
                    output.append((network,farms))
            else:
                #Zapper returned an empty list. Network may still have a farm running though.
                output.append((network,[]))
    return output 
