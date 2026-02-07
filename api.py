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
            usdprice = float(cg_response['market_data']['current_price']['usd'])
            satprice = float(cg_response['market_data']['current_price']['btc']) * 100000000
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
        usdprice = float(response['market_data']['current_price']['usd'])
        satprice = float(response['market_data']['current_price']['btc']) * 100000000
        volumebtc = float(response["market_data"]["total_volume"]["btc"])
        # Other data
        circ_supply = float(response['market_data']['circulating_supply'])
        rank = response['market_cap_rank']
        mcap = float(response['market_data']['market_cap']['usd'])
        ret = {
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
        # Get price and volume
        usdprice = float(response["market_data"]["current_price"]["usd"])
        btcprice = float(response["market_data"]["current_price"]["btc"])
        volumebtc = float(response["market_data"]["total_volume"]["btc"])
        # Other data
        circ_supply = float(response['market_data']['circulating_supply'])
        rank = response['market_cap_rank']
        mcap = float(response['market_data']['market_cap']['usd'])
        ret = {
            "btcprice":btcprice,
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

# wBAN token address (same across all chains)
WBAN_ADDRESS = '0xe20B9e246db5a0d21BF9209E4858Bc9A3ff7A034'

# Hardcoded farm configs sourced from wban-dApp repo
FARM_CONFIGS = {
    'binance-smart-chain': {
        'benis': '0x1E30E12e82956540bf870A40FD1215fC083a3751',
        'pools': [
            {'pid': 0, 'lp': WBAN_ADDRESS, 'pair': 'wBAN'},
            {'pid': 1, 'lp': '0x6011c6BAe36F2a2457dC69Dc49068a1E8Ad832DD', 'pair': 'wBAN-BNB'},
            {'pid': 2, 'lp': '0x7898466CACf92dF4a4e77a3b4d0170960E43b896', 'pair': 'wBAN-BUSD'},
            {'pid': 3, 'lp': '0x351A295AfBAB020Bc7eedcB7fd5A823c01A95Fda', 'pair': 'wBAN-BUSD'},
            {'pid': 4, 'lp': '0x76B1aB2f84bE3C4a103ef1d2C2a74145414FFA49', 'pair': 'wBAN-USDC'},
        ]
    },
    'polygon': {
        'benis': '0xefa4aED9Cf41A8A0FcdA4e88EfA2F60675bAeC9F',
        'pools': [
            {'pid': 0, 'lp': '0xb556feD3B348634a9A010374C406824Ae93F0CF8', 'pair': 'wBAN-WETH'},
        ]
    },
    'fantom': {
        'benis': '0xD91f84D4E2d9f4fa508c61356A6CB81a306e5287',
        'pools': [
            {'pid': 0, 'lp': '0x6bADcf8184a760326528b11057C00952811f77af', 'pair': 'wBAN-USDC'},
            {'pid': 1, 'lp': '0x1406E49b5B0dA255307FE25cC21C675D4Ffc73e0', 'pair': 'wBAN-FTM'},
        ]
    },
    'ethereum': {
        'benis': '0xD91f84D4E2d9f4fa508c61356A6CB81a306e5287',
        'pools': [
            {'pid': 0, 'lp': '0x1f249F8b5a42aa78cc8a2b66EE0bb015468a5f43', 'pair': 'wBAN-ETH'},
        ]
    },
    'arbitrum': {
        'benis': '0x8cd4DED2b49736B1a1Dbe18B9EB4BA6b6BF28227',
        'pools': [
            {'pid': 0, 'lp': '0xBD80923830B1B122dcE0C446b704621458329F1D', 'pair': 'wBAN-ETH'},
        ]
    },
}

# Minimal ABIs for LP token queries
ERC20_ABI = [{"constant":True,"inputs":[{"name":"account","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"type":"function"}]

PAIR_ABI = [
    {"constant":True,"inputs":[{"name":"account","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"type":"function"},
    {"constant":True,"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"type":"function"},
    {"constant":True,"inputs":[],"name":"getReserves","outputs":[{"name":"reserve0","type":"uint112"},{"name":"reserve1","type":"uint112"},{"name":"blockTimestampLast","type":"uint32"}],"type":"function"},
    {"constant":True,"inputs":[],"name":"token0","outputs":[{"name":"","type":"address"}],"type":"function"},
]

async def get_pool_tvl(network, benis_address, lp_address, wban_price):
    """Calculate TVL for a farm pool using on-chain data."""
    try:
        w3 = Web3(Web3.AsyncHTTPProvider(rpc_endpoints[network]), modules={'eth': (AsyncEth,)})
        benis_address = Web3.to_checksum_address(benis_address)
        lp_address = Web3.to_checksum_address(lp_address)

        if lp_address.lower() == WBAN_ADDRESS.lower():
            # Single-staking pool: TVL = wBAN balance of benis * price
            token = w3.eth.contract(address=lp_address, abi=ERC20_ABI)
            balance = await token.functions.balanceOf(benis_address).call()
            return balance * wban_price / 1e18
        else:
            # LP pair pool
            lp = w3.eth.contract(address=lp_address, abi=PAIR_ABI)
            staked = await lp.functions.balanceOf(benis_address).call()
            if staked <= 0:
                return 0
            total_supply = await lp.functions.totalSupply().call()
            reserves = await lp.functions.getReserves().call()
            token0 = await lp.functions.token0().call()

            # Identify which reserve is wBAN
            if token0.lower() == WBAN_ADDRESS.lower():
                wban_reserve = reserves[0]
            else:
                wban_reserve = reserves[1]

            # TVL = (staked/totalSupply) * 2 * wban_reserve * price / 1e18
            return (staked / total_supply) * 2 * wban_reserve * wban_price / 1e18
    except Exception as e:
        logger.error(f"Error fetching TVL for {network} {lp_address}: {e}")
        return -1

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


async def getNetworkFarm(network, wban_price):
    """
    Queries on-chain contracts for running wban farms on specified network and computes APR and TVL.
    """
    if network not in FARM_CONFIGS:
        return network, None

    config = FARM_CONFIGS[network]
    benis = config['benis']
    farms = []

    for pool in config['pools']:
        try:
            tvl = await get_pool_tvl(network, benis, pool['lp'], wban_price)
            if tvl <= 0:
                continue

            ban_rewards = await fetch_rewards(network, benis, pool['pid'])
            if ban_rewards > 0:
                apr = round(ban_rewards * wban_price / tvl * 100, 1)
            else:
                apr = None

            farms.append((pool['pair'], round(tvl), apr))
        except Exception as e:
            logger.error(f"Error processing pool {pool['pair']} on {network}: {e}")
            continue

    return network, farms


async def getWbanFarms():
    """
    Fetches wBAN price from CoinGecko, then queries on-chain contracts for all networks
    to compute APR and TVL for each farm pool.
    """
    # Fetch wBAN price
    cg_response = await json_get(BANANO_URL)
    if cg_response is None or 'market_data' not in cg_response:
        return None
    wban_price = float(cg_response['market_data']['current_price']['usd'])

    output = []
    tasks = []

    for network in FARM_CONFIGS:
        tasks.append(getNetworkFarm(network, wban_price))

    while len(tasks):
        done, tasks = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            network, farms = task.result()
            if farms is None:
                output.append((network, []))
            elif len(farms) > 0:
                output.append((network, farms))
    return output