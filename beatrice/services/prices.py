import asyncio
import json

import aiohttp
from redis.asyncio import Redis

CACHE_TTL = 300
STATUS_CACHE_KEY = "beatrice_statuscache"
VES_RATE_KEY = ("prices", "dolartoday:usd-ves")

COINGECKO_URLS = {
    "BANANO": "https://api.coingecko.com/api/v3/coins/banano?localization=false&tickers=true&market_data=true&community_data=false&developer_data=false&sparkline=false",
    "NANO": "https://api.coingecko.com/api/v3/coins/nano?localization=false&tickers=true&market_data=true&community_data=false&developer_data=false&sparkline=false",
    "BTC": "https://api.coingecko.com/api/v3/coins/bitcoin?localization=false&tickers=false&market_data=true&community_data=false&developer_data=false&sparkline=false",
}

CACHE_KEYS = {
    "BANANO": "beatrice_banocache",
    "NANO": "beatrice_nanocache",
    "BTC": "beatrice_btccache",
}


async def json_get(url: str, headers: dict | None = None) -> dict | list | None:
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                return await resp.json()
    except Exception:
        return None


async def _coin_data(redis: Redis, symbol: str) -> dict | None:
    cached = await redis.get(CACHE_KEYS[symbol])
    if cached is not None:
        return json.loads(cached)
    response = await json_get(COINGECKO_URLS[symbol])
    if response is None or "market_data" not in response:
        return None
    await redis.set(CACHE_KEYS[symbol], json.dumps(response), ex=CACHE_TTL)
    return response


async def _ves_rate(redis: Redis) -> float | None:
    rate = await redis.hget(*VES_RATE_KEY)
    if rate is None:
        return None
    return float(rate)


async def get_status(redis: Redis) -> dict | None:
    cached = await redis.get(STATUS_CACHE_KEY)
    if cached is not None:
        return json.loads(cached)
    response = await json_get(COINGECKO_URLS["BANANO"])
    if response is None or "market_data" not in response:
        return None
    status = {
        "satoshi": float(response["market_data"]["current_price"]["btc"]) * 100_000_000,
        "usdprice": float(response["market_data"]["current_price"]["usd"]),
    }
    await redis.set(STATUS_CACHE_KEY, json.dumps(status), ex=CACHE_TTL)
    return status


async def _banano_price(redis: Redis, ves_enabled: bool) -> dict | None:
    response = await _coin_data(redis, "BANANO")
    if response is None:
        return None
    market = response["market_data"]
    usdprice = float(market["current_price"]["usd"])
    result = {
        "satoshi": float(market["current_price"]["btc"]) * 100_000_000,
        "volume": float(market["total_volume"]["btc"]),
        "supply": float(market["circulating_supply"]),
        "rank": response["market_cap_rank"] or "?",
        "usdprice": usdprice,
        "mcap": float(market["market_cap"]["usd"]),
        "change": float(market["price_change_24h"] or 0),
    }
    if ves_enabled:
        rate = await _ves_rate(redis)
        if rate is not None:
            result["bolivar"] = usdprice * rate
    return result


async def _nano_price(redis: Redis, ves_enabled: bool) -> dict | None:
    response = await _coin_data(redis, "NANO")
    if response is None:
        return None
    market = response["market_data"]
    usdprice = float(market["current_price"]["usd"])
    result = {
        "btcprice": float(market["current_price"]["btc"]),
        "volume": float(market["total_volume"]["btc"]),
        "supply": float(market["circulating_supply"]),
        "rank": response["market_cap_rank"] or "?",
        "usdprice": usdprice,
        "mcap": float(market["market_cap"]["usd"]),
    }
    if ves_enabled:
        rate = await _ves_rate(redis)
        if rate is not None:
            result["bolivar"] = usdprice * rate
    return result


async def _btc_price(redis: Redis) -> dict | None:
    response = await _coin_data(redis, "BTC")
    if response is None:
        return None
    return {"usdprice": float(response["market_data"]["current_price"]["usd"])}


async def get_all_prices(redis: Redis, ves_enabled: bool) -> dict[str, dict | None]:
    banano, nano, btc = await asyncio.gather(
        _banano_price(redis, ves_enabled),
        _nano_price(redis, ves_enabled),
        _btc_price(redis),
    )
    return {"BANANO": banano, "NANO": nano, "BTC": btc}
