import datetime
from peewee import SqliteDatabase, Model, CharField, IntegerField, DateTimeField

db = SqliteDatabase('discord.db')

### Logic
def meme_exists(url):
    return Meme.select().where(Meme.url == url).count() > 0

def pup_exists(url):
    return Pup.select().where(Pup.url == url).count() > 0

def get_meme_sequence():
    try:
        memeSeq = Sequence.select().where(Sequence.name == 'meme').get()
        memeCount = Meme.select().count()
        curSeq = memeSeq.index + 1
        if curSeq > memeCount:
            curSeq = 1
        Sequence.update(index=curSeq).where(Sequence.name == 'meme').execute()
        return curSeq
    except Sequence.DoesNotExist:
        memeSeq = Sequence(name='meme')
        memeSeq.save()
        return 1

def get_pup_sequence():
    try:
        pupSeq = Sequence.select().where(Sequence.name == 'pup').get()
        pupCount = Pup.select().count()
        curSeq = pupSeq.index + 1
        if curSeq > pupCount:
            curSeq = 1
        Sequence.update(index=curSeq).where(Sequence.name == 'pup').execute()
        return curSeq
    except Sequence.DoesNotExist:
        pupSeq = Sequence(name='pup')
        pupSeq.save()
        return 1

def get_memes():
    memes = Meme.select().order_by(Meme.created_at.desc())
    return_data = []
    for m in memes:
        return_data.append({'id':m.id, 'url':m.url})
    return return_data

def get_pups():
    pups = Pup.select().order_by(Pup.created_at.desc())
    return_data = []
    for p in pups:
        return_data.append({'id':p.id, 'url':p.url})
    return return_data

def get_next_meme():
    memes = get_memes()
    if len(memes) == 0:
        return None
    return memes[get_meme_sequence() - 1]

def get_next_pup():
    pups = get_pups()
    if len(pups) == 0:
        return None
    return pups[get_pup_sequence() - 1]

def add_meme(url):
    if meme_exists(url):
        return False
    m = Meme(url=url)
    return m.save() > 0

def add_pup(url):
    if pup_exists(url):
        return False
    p = Pup(url=url)
    return p.save() > 0

def remove_meme(id):
    try:
        m = Meme.select().where((Meme.id == id) | (Meme.url == id)).get()
        m.delete_instance()
        return True
    except Meme.DoesNotExist:
        return False

def remove_pup(id):
    try:
        p = Pup.select().where((Pup.id == id) | (Pup.url == id)).get()
        p.delete_instance()
        return True
    except Pup.DoesNotExist:
        return False

### Models
class BaseModel(Model):
    class Meta:
        database = db

class Meme(BaseModel):
    """Represents a meme in the database"""
    url = CharField()
    created_at = DateTimeField(default=datetime.datetime.now())

    class Meta:
        db_table = 'meme_list'

class Pup(BaseModel):
    """Represents a pup in the database"""
    url = CharField()
    created_at = DateTimeField(default=datetime.datetime.now())

    class Meta:
        db_table = 'pup_list'

class Sequence(BaseModel):
    """Represents current meme/pup sequence"""
    name = CharField()
    index = IntegerField(default=1)

    class Meta:
        db_table = 'sequences'

### Initialization
def create_db():
    db.connect()
    db.create_tables([Meme, Pup, Sequence], safe=True)

create_db()
