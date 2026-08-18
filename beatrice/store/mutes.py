import asyncio
import datetime

from beatrice.store.models import SilenceList


def _silenced(user_id: int) -> bool:
    return SilenceList.select().where(SilenceList.user_id == str(user_id)).count() > 0


def _silence(user_id: int, guild_id: int, expiration: datetime.datetime | None) -> bool:
    if _silenced(user_id):
        return False
    SilenceList(user_id=str(user_id), server_id=guild_id, expiration=expiration).save()
    return True


def _unsilence(user_id: int) -> bool:
    return SilenceList.delete().where(SilenceList.user_id == str(user_id)).execute() > 0


async def silenced(user_id: int) -> bool:
    return await asyncio.to_thread(_silenced, user_id)


async def silence(user_id: int, guild_id: int, expiration: datetime.datetime | None) -> bool:
    return await asyncio.to_thread(_silence, user_id, guild_id, expiration)


async def unsilence(user_id: int) -> bool:
    return await asyncio.to_thread(_unsilence, user_id)


async def all_silenced() -> list[SilenceList]:
    return await asyncio.to_thread(lambda: list(SilenceList.select()))
