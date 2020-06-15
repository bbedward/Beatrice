import logging
import logging.handlers
import aioredis
import os

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

async def get_redis():
	global redis
	if redis:
		return redis
	lr = await aioredis.create_redis_pool((os.getenv('REDIS_HOST', 'localhost'), 6379), encoding='utf-8', minsize=2, maxsize=50)
	redis = lr
	return redis
	