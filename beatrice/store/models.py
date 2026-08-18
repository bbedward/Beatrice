import datetime

from peewee import CharField, DateTimeField, IntegerField, Model

from beatrice.store import database


def utcnow() -> datetime.datetime:
    # Stored naive: peewee's DateTimeField round-trips without tzinfo.
    return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)


class BaseModel(Model):
    class Meta:
        database = database


class ImageEntry(BaseModel):
    kind = CharField(index=True)
    url = CharField()
    author = CharField()
    title = CharField()
    created_at = DateTimeField(default=utcnow)

    class Meta:
        table_name = "image_entries"
        indexes = ((("kind", "url"), True),)


class Sequence(BaseModel):
    name = CharField()
    index = IntegerField(default=1)

    class Meta:
        table_name = "sequences"


class SilenceList(BaseModel):
    user_id = CharField()
    expiration = DateTimeField(default=None, null=True)
    server_id = IntegerField()

    class Meta:
        table_name = "silencelist"
