import asyncio

from beatrice.store.models import ImageEntry, Sequence

KINDS = ("meme", "pup", "meow", "fridge")


def _entries(kind: str) -> list[ImageEntry]:
    return list(ImageEntry.select().where(ImageEntry.kind == kind).order_by(ImageEntry.id))


def _advance_sequence(kind: str, count: int) -> int:
    sequence, created = Sequence.get_or_create(name=kind)
    if created:
        return 1
    position = sequence.index + 1
    if position > count:
        position = 1
    Sequence.update(index=position).where(Sequence.name == kind).execute()
    return position


def _next_entry(kind: str) -> ImageEntry | None:
    entries = _entries(kind)
    if not entries:
        return None
    return entries[_advance_sequence(kind, len(entries)) - 1]


def _add_entry(kind: str, url: str, author: str, title: str) -> bool:
    exists = ImageEntry.select().where((ImageEntry.kind == kind) & (ImageEntry.url == url)).count()
    if exists:
        return False
    return ImageEntry(kind=kind, url=url, author=author, title=title).save() > 0


def _remove_entry(kind: str, ident: str) -> bool:
    matches_id = ImageEntry.id == int(ident) if ident.isdigit() else False
    query = ImageEntry.delete().where(
        (ImageEntry.kind == kind) & ((ImageEntry.url == ident) | matches_id)
    )
    return query.execute() > 0


async def list_entries(kind: str) -> list[ImageEntry]:
    return await asyncio.to_thread(_entries, kind)


async def next_entry(kind: str) -> ImageEntry | None:
    return await asyncio.to_thread(_next_entry, kind)


async def add_entry(kind: str, url: str, author: str, title: str) -> bool:
    return await asyncio.to_thread(_add_entry, kind, url, author, title)


async def remove_entry(kind: str, ident: str) -> bool:
    return await asyncio.to_thread(_remove_entry, kind, ident)
