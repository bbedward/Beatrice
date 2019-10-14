import logging
import logging.handlers
import aioredis

def get_logger(name, log_file='debug.log'):
	formatter = logging.Formatter('%(asctime)s [%(name)s] -%(levelname)s- %(message)s')
	logger = logging.getLogger(name)
	logger.setLevel(logging.DEBUG)
	file_handler = logging.handlers.TimedRotatingFileHandler(log_file, when='midnight', backupCount=0)
	file_handler.setLevel(logging.DEBUG)
	file_handler.setFormatter(formatter)
	logger.handlers = []
	logger.addHandler(file_handler)
	console_handler = logging.StreamHandler()
	console_handler.setFormatter(formatter)
	logger.addHandler(console_handler)
	logger.propagate = False
	return logger

redis = None
redisdb2 = None

async def get_redis(db=None):
	global redis
	global redisdb2
	if redis and db is None:
		return redis
	elif redisdb2 and db == 2:
		return redisdb2
	lr = await aioredis.create_redis_pool(('localhost', 6379), db=db, encoding='utf-8', minsize=2, maxsize=50)
	if db is None:
		redis = lr
		return redis
	elif db == 2:
		redisdb2 = lr
		return redisdb2
	