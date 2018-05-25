import datetime
from peewee import SqliteDatabase, Model, CharField, IntegerField, DateTimeField

db = SqliteDatabase('discord.db')

### Logic
def meme_exists(url):
    return Meme.select().where(Meme.url == url).count() > 0

def pup_exists(url):
    return Pup.select().where(Pup.url == url).count() > 0

def meow_exists(url):
    return Meow.select().where(Meow.url == url).count() > 0

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

def get_meow_sequence():
    try:
        meowSeq = Sequence.select().where(Sequence.name == 'meow').get()
        meowCount = Meow.select().count()
        curSeq = meowSeq.index + 1
        if curSeq > meowCount:
            curSeq = 1
        Sequence.update(index=curSeq).where(Sequence.name == 'meow').execute()
        return curSeq
    except Sequence.DoesNotExist:
        meowSeq = Sequence(name='meow')
        meowSeq.save()
        return 1
def format_result(id, url, author, title):
    return {"id":id, "url":url, "author":author, "title":title}

def get_memes():
    memes = Meme.select().order_by(Meme.created_at.desc())
    return_data = []
    for m in memes:
        return_data.append(format_result(m.id, m.url, m.author, m.title))
    return return_data

def get_pups():
    pups = Pup.select().order_by(Pup.created_at.desc())
    return_data = []
    for p in pups:
        return_data.append(format_result(p.id, p.url, p.author, p.title))
    return return_data

def get_meows():
    meows = Meow.select().order_by(Meow.created_at.desc())
    return_data = []
    for m in meows:
        return_data.append(format_result(m.id, m.url, m.author, m.title))
    return return_data

def get_next_meme():
    sequence = get_meme_sequence()
    meme = Meme.select().order_by(Meme.created_at.desc()).offset(sequence).limit(1)
    if meme.count() == 0:
        return None
    meme = meme.get()
    return format_result(meme.id, meme.url, meme.author, meme.title)

def get_next_pup():
    sequence = get_pup_sequence()
    pup = Pup.select().order_by(Pup.created_at.desc()).offset(sequence).limit(1)
    if pup.count() == 0:
        return None
    pup = pup.get()
    return format_result(pup.id, pup.url, pup.author, pup.title)

def get_next_meow():
    sequence = get_meow_sequence()
    meow = Meow.select().order_by(Meow.created_at.desc()).offset(sequence).limit(1)
    if meow.count() == 0:
        return None
    meow = meow.get()
    return format_result(meow.id, meow.url, meow.author, meow.title)

def add_meme(url, author, title):
    if meme_exists(url):
        return False
    m = Meme(url=url, author=author, title=title)
    return m.save() > 0

def add_pup(url, author, title):
    if pup_exists(url):
        return False
    p = Pup(url=url, author=author, title=title)
    return p.save() > 0

def add_meow(url, author, title):
    if meow_exists(url):
        return False
    m = Meow(url=url, author=author, title=title)
    return m.save() > 0

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

def remove_meow(id):
    try:
        m = Meow.select().where((Meow.id == id) | (Meow.url == id)).get()
        m.delete_instance()
        return True
    except Meow.DoesNotExist:
        return False

### Models
class BaseModel(Model):
    class Meta:
        database = db

class Meme(BaseModel):
    """Represents a meme in the database"""
    url = CharField()
    author = CharField()
    title = CharField()
    created_at = DateTimeField(default=datetime.datetime.now())

    class Meta:
        db_table = 'meme_list'

class Pup(BaseModel):
    """Represents a pup in the database"""
    url = CharField()
    author = CharField()
    title = CharField()
    created_at = DateTimeField(default=datetime.datetime.now())

    class Meta:
        db_table = 'pup_list'

class Meow(BaseModel):
    """Represents a meow in the database"""
    url = CharField()
    author = CharField()
    title = CharField()
    created_at = DateTimeField(default=datetime.datetime.now())

    class Meta:
        db_table = 'meow_list'

class Sequence(BaseModel):
    """Represents current meme/pup sequence"""
    name = CharField()
    index = IntegerField(default=1)

    class Meta:
        db_table = 'sequences'

### Initialization
def create_db():
    db.connect()
    db.create_tables([Meme, Pup, Sequence, Meow], safe=True)

create_db()
