import asyncio
import json
import logging
import time

from web3 import AsyncHTTPProvider, AsyncWeb3, Web3

from beatrice.services.prices import COINGECKO_URLS, json_get

logger = logging.getLogger(__name__)

RPC_ENDPOINTS = {
    "ethereum": "https://eth.llamarpc.com",
    "polygon": "https://polygon-rpc.com/",
    "arbitrum": "https://arb1.arbitrum.io/rpc",
    "binance-smart-chain": "https://bsc-dataseed1.binance.org/",
    "fantom": "https://rpcapi.fantom.network",
}

NETWORK_SCAN = {
    "ethereum": "etherscan.com",
    "polygon": "polygonscan.com",
    "arbitrum": "arbiscan.io",
    "binance-smart-chain": "bscscan.com",
    "fantom": "ftmscan.com",
}

WBAN_ADDRESS = "0xe20B9e246db5a0d21BF9209E4858Bc9A3ff7A034"

FARM_CONFIGS = {
    "binance-smart-chain": {
        "benis": "0x1E30E12e82956540bf870A40FD1215fC083a3751",
        "pools": [
            {"pid": 0, "lp": WBAN_ADDRESS, "pair": "wBAN"},
            {"pid": 1, "lp": "0x6011c6BAe36F2a2457dC69Dc49068a1E8Ad832DD", "pair": "wBAN-BNB"},
            {"pid": 2, "lp": "0x7898466CACf92dF4a4e77a3b4d0170960E43b896", "pair": "wBAN-BUSD"},
            {"pid": 3, "lp": "0x351A295AfBAB020Bc7eedcB7fd5A823c01A95Fda", "pair": "wBAN-BUSD"},
            {"pid": 4, "lp": "0x76B1aB2f84bE3C4a103ef1d2C2a74145414FFA49", "pair": "wBAN-USDC"},
        ],
    },
    "polygon": {
        "benis": "0xefa4aED9Cf41A8A0FcdA4e88EfA2F60675bAeC9F",
        "pools": [
            {"pid": 0, "lp": "0xb556feD3B348634a9A010374C406824Ae93F0CF8", "pair": "wBAN-WETH"},
        ],
    },
    "fantom": {
        "benis": "0xD91f84D4E2d9f4fa508c61356A6CB81a306e5287",
        "pools": [
            {"pid": 0, "lp": "0x6bADcf8184a760326528b11057C00952811f77af", "pair": "wBAN-USDC"},
            {"pid": 1, "lp": "0x1406E49b5B0dA255307FE25cC21C675D4Ffc73e0", "pair": "wBAN-FTM"},
        ],
    },
    "ethereum": {
        "benis": "0xD91f84D4E2d9f4fa508c61356A6CB81a306e5287",
        "pools": [
            {"pid": 0, "lp": "0x1f249F8b5a42aa78cc8a2b66EE0bb015468a5f43", "pair": "wBAN-ETH"},
        ],
    },
    "arbitrum": {
        "benis": "0x8cd4DED2b49736B1a1Dbe18B9EB4BA6b6BF28227",
        "pools": [
            {"pid": 0, "lp": "0xBD80923830B1B122dcE0C446b704621458329F1D", "pair": "wBAN-ETH"},
        ],
    },
}

ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    }
]

PAIR_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "totalSupply",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "getReserves",
        "outputs": [
            {"name": "reserve0", "type": "uint112"},
            {"name": "reserve1", "type": "uint112"},
            {"name": "blockTimestampLast", "type": "uint32"},
        ],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "token0",
        "outputs": [{"name": "", "type": "address"}],
        "type": "function",
    },
]

_abi_cache: dict[str, str] = {}


def _provider(network: str) -> AsyncWeb3:
    return AsyncWeb3(AsyncHTTPProvider(RPC_ENDPOINTS[network]))


async def _pool_tvl(network: str, benis_address: str, lp_address: str, wban_price: float) -> float:
    try:
        w3 = _provider(network)
        benis_address = Web3.to_checksum_address(benis_address)
        lp_address = Web3.to_checksum_address(lp_address)

        if lp_address.lower() == WBAN_ADDRESS.lower():
            token = w3.eth.contract(address=lp_address, abi=ERC20_ABI)
            balance = await token.functions.balanceOf(benis_address).call()
            return balance * wban_price / 1e18

        lp = w3.eth.contract(address=lp_address, abi=PAIR_ABI)
        staked = await lp.functions.balanceOf(benis_address).call()
        if staked <= 0:
            return 0
        total_supply = await lp.functions.totalSupply().call()
        reserves = await lp.functions.getReserves().call()
        token0 = await lp.functions.token0().call()
        wban_reserve = reserves[0] if token0.lower() == WBAN_ADDRESS.lower() else reserves[1]
        return (staked / total_supply) * 2 * wban_reserve * wban_price / 1e18
    except Exception as exc:
        logger.error("Error fetching TVL for %s %s: %s", network, lp_address, exc)
        return -1


async def _fetch_contract_abi(network: str, contract_address: str) -> str:
    cached = _abi_cache.get(network)
    if cached is not None:
        return cached
    response = await json_get(
        f"https://api.{NETWORK_SCAN[network]}/api"
        f"?module=contract&action=getabi&address={contract_address}"
    )
    abi = response["result"]
    _abi_cache[network] = abi
    return abi


def _alloc_point_index(contract_abi: list) -> int | None:
    for entry in contract_abi:
        if entry["type"] != "function" or entry["name"] != "poolInfo":
            continue
        for index, output in enumerate(entry["outputs"]):
            if output["name"] == "allocPoint":
                return index
    return None


async def _fetch_rewards(network: str, contract_address: str, pool_id: int) -> float:
    contract_address = Web3.to_checksum_address(contract_address)
    try:
        contract_abi = json.loads(await _fetch_contract_abi(network, contract_address))
        w3 = _provider(network)
        if not await w3.is_connected():
            return -1
        contract = w3.eth.contract(address=contract_address, abi=contract_abi)
        try:
            pool_info = await contract.functions.poolInfo(int(pool_id)).call()
            alloc_point = pool_info[_alloc_point_index(contract_abi)]
            if alloc_point <= 0:
                return 0
            end_time = await contract.functions.endTime().call()
            start_time = await contract.functions.startTime().call()
            if end_time < time.time() or start_time > time.time():
                return 0
            total_alloc_point = await contract.functions.totalAllocPoint().call()
            wban_per_second = await contract.functions.wbanPerSecond().call()
            return wban_per_second * alloc_point / total_alloc_point * 365 * 24 * 3600 // 10**18
        except Exception:
            _abi_cache.pop(network, None)
    except Exception:
        _abi_cache.pop(network, None)
    return -1


async def _network_farms(network: str, wban_price: float) -> tuple[str, list | None]:
    config = FARM_CONFIGS[network]
    farms = []
    for pool in config["pools"]:
        try:
            tvl = await _pool_tvl(network, config["benis"], pool["lp"], wban_price)
            if tvl <= 0:
                continue
            rewards = await _fetch_rewards(network, config["benis"], pool["pid"])
            apr = round(rewards * wban_price / tvl * 100, 1) if rewards > 0 else None
            farms.append((pool["pair"], round(tvl), apr))
        except Exception as exc:
            logger.error("Error processing pool %s on %s: %s", pool["pair"], network, exc)
            continue
    return network, farms


async def get_wban_farms() -> list[tuple[str, list]] | None:
    cg_response = await json_get(COINGECKO_URLS["BANANO"])
    if cg_response is None or "market_data" not in cg_response:
        return None
    wban_price = float(cg_response["market_data"]["current_price"]["usd"])

    results = await asyncio.gather(
        *(_network_farms(network, wban_price) for network in FARM_CONFIGS)
    )
    return [(network, farms) for network, farms in results if farms]
