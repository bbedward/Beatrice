import logging
import aioredis
import os

def get_logger(name, log_file='debug.log'):
	logger = logging.getLogger(name)
	handler = logging.StreamHandler(sys.stdout)
	formatter = logging.Formatter("%(asctime)s;%(levelname)s;%(message)s", "%Y-%m-%d %H:%M:%S %z")
	handler.setFormatter(formatter)
	logger.addHandler(handler)
	return logger

redis = None

async def get_redis():
	global redis
	if redis:
		return redis
	lr = await aioredis.create_redis_pool((os.getenv('REDIS_HOST', 'localhost'), 6379), encoding='utf-8', minsize=2, maxsize=50)
	redis = lr
	return redis
	