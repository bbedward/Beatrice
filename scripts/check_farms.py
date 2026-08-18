"""Manual probe: hits live CoinGecko and chain RPCs to verify /farms data end-to-end."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from beatrice.services import farms


async def main() -> None:
    results = await farms.get_wban_farms()
    if results is None:
        print("API Error fetching wBAN price")
        return
    if not results:
        print("No active wBAN farms found")
        return
    for network, pools in sorted(results):
        print(f"\n{network}")
        for pair, tvl, apr in pools:
            apr_str = f"{apr}% APR" if apr is not None else "Inactive"
            print(f"  {pair}: {apr_str} (${tvl:,} TVL)")


if __name__ == "__main__":
    asyncio.run(main())
