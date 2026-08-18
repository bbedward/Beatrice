from beatrice import logs, redisdb, store
from beatrice.bot import Beatrice
from beatrice.config import Settings


def main() -> None:
    logs.configure()
    settings = Settings.from_env()
    store.init(settings.db_path)
    bot = Beatrice(settings, redisdb.create_client(settings.redis_host))
    bot.run(settings.bot_token, log_handler=None)


if __name__ == "__main__":
    main()
