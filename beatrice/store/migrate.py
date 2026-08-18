import logging
import sqlite3

from beatrice.store import database
from beatrice.store.models import ImageEntry, Sequence, SilenceList

logger = logging.getLogger(__name__)

LEGACY_TABLES = {
    "meme_list": "meme",
    "pup_list": "pup",
    "meow_list": "meow",
    "fridge_list": "fridge",
}


def _backup(path: str) -> None:
    target = f"{path}.pre-migration.bak"
    source_conn = sqlite3.connect(path)
    target_conn = sqlite3.connect(target)
    try:
        with target_conn:
            source_conn.backup(target_conn)
    finally:
        source_conn.close()
        target_conn.close()
    logger.info("backed up database to %s", target)


def run() -> None:
    version = database.execute_sql("PRAGMA user_version").fetchone()[0]
    if version >= 1:
        database.create_tables([ImageEntry, Sequence, SilenceList], safe=True)
        return

    path = database.database
    legacy_present = [t for t in LEGACY_TABLES if t in database.get_tables()]
    if legacy_present and path and path != ":memory:":
        _backup(path)

    database.create_tables([ImageEntry, Sequence, SilenceList], safe=True)
    with database.atomic():
        for table in legacy_present:
            kind = LEGACY_TABLES[table]
            source_count = database.execute_sql(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            cursor = database.execute_sql(
                f"INSERT OR IGNORE INTO image_entries (kind, url, author, title, created_at) "
                f"SELECT ?, url, author, title, created_at FROM {table} ORDER BY id",
                (kind,),
            )
            if cursor.rowcount != source_count:
                logger.warning(
                    "%s: %s of %s rows skipped (duplicate url or constraint violation)",
                    table,
                    source_count - cursor.rowcount,
                    source_count,
                )
            database.execute_sql(f"ALTER TABLE {table} RENAME TO {table}_legacy")
            logger.info("migrated %s rows from %s", cursor.rowcount, table)
        database.execute_sql("PRAGMA user_version = 1")
    logger.info("database schema at version 1")
