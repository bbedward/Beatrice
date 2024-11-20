import aiohttp
import asyncio
import json
import util
import settings
import time
from web3 import Web3
from web3.eth import AsyncEth

logger = util.get_logger("discord")

CG_BTC_CACHE_KEY = 'beatrice_btccache'
CG_NANO_CACHE_KEY = 'beatrice_nanocache'
CG_BAN_CACHE_KEY = 'beatrice_banocache'
CG_STATUS_CACHE_KEY = 'beatrice_statuscache'

CGNANO_URL = 'https://api.coingecko.com/api/v3/coins/nano?localization=false&tickers=true&market_data=true&community_data=false&developer_data=false&sparkline=false'
CGBTC_URL = 'https://api.coingecko.com/api/v3/coins/bitcoin?localization=false&tickers=false&market_data=true&community_data=false&developer_data=false&sparkline=false'
BANANO_URL = 'https://api.coingecko.com/api/v3/coins/banano?localization=false&tickers=true&market_data=true&community_data=false&developer_data=false&sparkline=false'
COINEX_BAN_URL = 'https://api.coinex.com/v1/market/ticker?market=BANANOUSDT'

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
        usdprice = await get_coinex_price()
        if usdprice is not None:
            # Get BTC price for satoshi calculation
            btc_response = await get_btc_usd()
            if btc_response is not None:
                btc_price = btc_response[1]['usdprice']
                satprice = (usdprice / btc_price) * 100000000
                ret = {
                    "satoshi": satprice,
                    "usdprice": usdprice
                }
                await redis.set(CG_STATUS_CACHE_KEY, json.dumps(ret), expire=300)
                return ret
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
        usdprice = await get_coinex_price()
        if usdprice is None:
            return None
        btc_response = await get_btc_usd()
        if btc_response is None:
            return None
        satprice = (usdprice / btc_response[1]['usdprice']) * 100000000
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

async def get_coinex_price():
    """Get Banano price directly from CoinEx API"""
    try:
        response = await json_get(COINEX_BAN_URL)
        if response is not None and response['code'] == 0:
            ticker = response['data']['ticker']
            return float(ticker['last'])
    except (KeyError, ValueError):
        return None
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


#RPC endpoints used to fetch contract data
rpc_endpoints = {
    'ethereum': 'https://eth.llamarpc.com',
    'polygon': 'https://polygon-rpc.com/',           
    'arbitrum': 'https://arb1.arbitrum.io/rpc',
    'binance-smart-chain': 'https://bsc-dataseed1.binance.org/',
    'fantom': 'https://rpcapi.fantom.network'
}

#Block explorer for various networks, used to fetch wban-farms contract ABI
network_scan = {
    'ethereum': 'etherscan.com',
    'polygon': 'polygonscan.com',           
    'arbitrum': 'arbiscan.io',
    'binance-smart-chain': 'bscscan.com',
    'fantom': 'ftmscan.com'
    
}

abi = None
#Fetch contract ABI using API call if not cached. (Cache is cleared on errors)
async def fetch_contract_abi(network, contract_address):
    global abi
    if abi is  None:
        response = await json_get(f"https://api.{network_scan[network]}/api?module=contract&action=getabi&address={contract_address}")
        abi = response['result']
    return abi


async def fetch_rewards(network, contract_address, pool_id):
    global abi
    contract_address = Web3.to_checksum_address(contract_address)
    try:
        contract_abi = json.loads(await fetch_contract_abi(network, contract_address))
        # Initialize web3 provider
        w3 = Web3(Web3.AsyncHTTPProvider(rpc_endpoints[network]), modules={'eth': (AsyncEth,)})
        if (await w3.is_connected()):
            contract = w3.eth.contract(address=contract_address, abi=contract_abi)
            try:
                # Parse contract ABI to find the correct index for allocPoint in poolInfo
                alloc_point_index = None
                for entry in contract_abi:
                    if entry['type'] == 'function' and entry['name'] == 'poolInfo':
                        for id, input_param in enumerate(entry['outputs']):
                            if input_param['name'] == 'allocPoint':
                                alloc_point_index = id
                                break
                        if alloc_point_index is not None:
                            break
            except Exception as e:
                print(f"Error fetching contract fields: {e}")
                alloc_point_index = -1
            try:
                pool_info = await contract.functions.poolInfo(int(pool_id)).call()
                alloc_point = pool_info[alloc_point_index]
                if alloc_point <= 0:
                    #Farm not active
                    return 0

                end_time = await contract.functions.endTime().call()
                start_time = await contract.functions.startTime().call()
                if end_time < time.time() or start_time > time.time():
                    #Farm not active
                    return 0
                
                total_alloc_point = await contract.functions.totalAllocPoint().call()
                wban_per_second = await contract.functions.wbanPerSecond().call()
                pool_wban_per_year = wban_per_second  * alloc_point / total_alloc_point * 365 * 24 * 60 * 60  // 10 ** 18
                return pool_wban_per_year 
            except Exception:
                abi = None
    except Exception:
        abi = None
    return -1 


async def getNetworkFarm(network):
    """
    Queries Zapper API for running wban farms on specified network and then fetch APR for that network.
    """
    resp = await json_get(f"https://api.zapper.xyz/v2/apps/banano/positions?network={network}&groupId=farm",headers={'accept': '*/*','Authorization': f'Basic {settings.ZAPPER_API}'})

    #Verify the task worked 
    if resp is not None and len(resp) > 0:
        farms = []

        #Go through all the farms for this network 
        for farm in resp:
            try: 
                ban_price = 0
                liquidity = 0
                if ":" in farm['key']:
                    # Networks that have migrated to new Zapper API:
                    contract, index = farm['key'].split(':')
                else:
                    # Networks still on older Zapper API:
                    contract = farm['address']
                    index = farm['dataProps']['poolIndex']
                    if not bool(farm['dataProps']['isActive']):
                        continue 

                for tokens in farm["tokens"]: #Recover the token pairs used in the network 
                    if tokens["metaType"] == "supplied" and tokens["type"] == "app-token" :
                        tokens_in_farm = []
                        for token in tokens["tokens"]:
                            tokens_in_farm.append(token["symbol"])
                            if token["symbol"] == "wBAN":
                                ban_price = float(token["price"])
                        if len(tokens_in_farm) > 1 and tokens_in_farm[1] == "wBAN": #Some basic ordering, such that wban comes first 
                            tokens_in_farm[0],tokens_in_farm[1] = tokens_in_farm[1],tokens_in_farm[0]
                        liquidity = round(float(tokens['dataProps']['liquidity']))
                token_string = "-".join(tokens_in_farm) #Get a string representation of the pair 

                #Fetch yearly rewards in ban
                ban_rewards = await fetch_rewards(network, contract, index)
                if ban_rewards == -1:
                    farms.append((token_string, liquidity, "API Error"))
                if ban_rewards > 0:
                    apr = round(ban_rewards * 100 * ban_price / liquidity, 1)
                    farms.append((token_string, liquidity, apr))
            except Exception:
                continue
    else:
        return network, None
    return network, farms


async def getWbanFarms():
    """
    Uses Zapper API to fetch networks with running wban farms.
    Then use combination of zapper API and onchain contract info to compute APR and TVL.
    """
    output = [] 
    #Start off by querying the API to find out all networks wban is on
    r = await json_get(f"https://api.zapper.xyz/v2/apps/banano",headers={'accept': '*/*','Authorization': f'Basic {settings.ZAPPER_API}'})
    networks = []
    if r is None or 'supportedNetworks' not in r:
        return None    

    #Gather all the found networks
    for net in r["supportedNetworks"]:
        networks.append(net["network"])

    tasks = [] 

    #Create a task for each network. This fetches all farms and computes their APRs
    for network in networks:
        tasks.append(getNetworkFarm(network))
    
    while len(tasks):
        done, tasks = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            network, farms = task.result()

            if farms is None:
                #Zapper returned an empty list. Network may still have a farm running though.
                output.append((network,[]))
            elif len(farms) > 0:
                output.append((network,farms))
    return output 
