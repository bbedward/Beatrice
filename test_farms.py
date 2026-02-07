"""
Verification script for on-chain wBAN farm queries.
Tests CoinGecko price fetch, Web3 RPC connectivity, and on-chain contract queries.

Usage: python test_farms.py
"""
import asyncio
import aiohttp
from web3 import Web3
from web3.eth import AsyncEth

BANANO_URL = 'https://api.coingecko.com/api/v3/coins/banano?localization=false&tickers=false&market_data=true&community_data=false&developer_data=false&sparkline=false'

RPC_ENDPOINTS = {
    'binance-smart-chain': 'https://bsc-dataseed1.binance.org/',
    'polygon': 'https://polygon-rpc.com/',
    'fantom': 'https://rpcapi.fantom.network',
    'ethereum': 'https://eth.llamarpc.com',
    'arbitrum': 'https://arb1.arbitrum.io/rpc',
}

WBAN_ADDRESS = '0xe20B9e246db5a0d21BF9209E4858Bc9A3ff7A034'

# BSC Benis contract for testing
TEST_BENIS = '0x1E30E12e82956540bf870A40FD1215fC083a3751'
TEST_LP = '0x6011c6BAe36F2a2457dC69Dc49068a1E8Ad832DD'  # wBAN-BNB LP

ERC20_ABI = [{"constant":True,"inputs":[{"name":"account","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"type":"function"}]

PAIR_ABI = [
    {"constant":True,"inputs":[{"name":"account","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"type":"function"},
    {"constant":True,"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"type":"function"},
    {"constant":True,"inputs":[],"name":"getReserves","outputs":[{"name":"reserve0","type":"uint112"},{"name":"reserve1","type":"uint112"},{"name":"blockTimestampLast","type":"uint32"}],"type":"function"},
    {"constant":True,"inputs":[],"name":"token0","outputs":[{"name":"","type":"address"}],"type":"function"},
]


async def test_coingecko():
    print("=== Test 1: CoinGecko wBAN Price ===")
    async with aiohttp.ClientSession() as session:
        async with session.get(BANANO_URL, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            data = await resp.json()
            price = float(data['market_data']['current_price']['usd'])
            print(f"  wBAN price: ${price:.6f}")
            assert price > 0, "Price should be positive"
            print("  PASS")
            return price


async def test_rpc_connectivity():
    print("\n=== Test 2: RPC Connectivity ===")
    for network, rpc in RPC_ENDPOINTS.items():
        w3 = Web3(Web3.AsyncHTTPProvider(rpc), modules={'eth': (AsyncEth,)})
        connected = await w3.is_connected()
        block = await w3.eth.block_number
        print(f"  {network}: connected={connected}, block={block}")
        assert connected, f"Should be connected to {network}"
    print("  PASS")


async def test_onchain_queries():
    print("\n=== Test 3: On-Chain Contract Queries (BSC) ===")
    w3 = Web3(Web3.AsyncHTTPProvider(RPC_ENDPOINTS['binance-smart-chain']), modules={'eth': (AsyncEth,)})

    benis = Web3.to_checksum_address(TEST_BENIS)
    lp_addr = Web3.to_checksum_address(TEST_LP)

    # Query LP token balanceOf(benis)
    lp = w3.eth.contract(address=lp_addr, abi=PAIR_ABI)
    staked = await lp.functions.balanceOf(benis).call()
    print(f"  LP staked in Benis: {staked}")

    total_supply = await lp.functions.totalSupply().call()
    print(f"  LP totalSupply: {total_supply}")

    reserves = await lp.functions.getReserves().call()
    print(f"  Reserves: {reserves[0]}, {reserves[1]}")

    token0 = await lp.functions.token0().call()
    print(f"  token0: {token0}")

    # Query wBAN balanceOf(benis) for single-staking check
    wban = w3.eth.contract(address=Web3.to_checksum_address(WBAN_ADDRESS), abi=ERC20_ABI)
    wban_balance = await wban.functions.balanceOf(benis).call()
    print(f"  wBAN balance in Benis: {wban_balance / 1e18:.2f}")

    print("  PASS")


async def main():
    print("wBAN Farms Verification Script\n")
    try:
        price = await test_coingecko()
        await test_rpc_connectivity()
        await test_onchain_queries()
        print("\n=== All tests passed! ===")
    except Exception as e:
        print(f"\n=== FAILED: {e} ===")
        raise


if __name__ == '__main__':
    asyncio.run(main())
