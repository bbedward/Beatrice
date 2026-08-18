import redis.asyncio as redis


def create_client(host: str) -> redis.Redis:
    return redis.Redis(host=host, port=6379, decode_responses=True)
