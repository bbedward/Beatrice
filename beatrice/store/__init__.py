from peewee import SqliteDatabase

database = SqliteDatabase(None)


def init(path: str) -> None:
    database.init(path, pragmas={"journal_mode": "wal"})
    database.connect()
