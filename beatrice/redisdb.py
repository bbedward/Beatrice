import redis.asyncio as redis


def create_client(host: str, password: str | None) -> redis.Redis:
    return redis.Redis(host=host, port=6379, password=password, decode_responses=True)
