import os
from dataclasses import dataclass


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise KeyError(f"Missing required environment variable: {name}")
    return value


def _int(name: str) -> int:
    return int(_require(name))


def _ints(name: str) -> frozenset[int]:
    raw = os.environ.get(name, "")
    return frozenset(int(part) for part in raw.replace(",", " ").split() if part)


def _bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "yes")


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str
    admin_role_ids: frozenset[int]
    admin_user_ids: frozenset[int]
    super_user_ids: frozenset[int]
    alert_user_id: int
    no_spam_channel_ids: frozenset[int]
    muzzled_role_id: int
    images_role_id: int
    arrest_role_id: int
    citizen_role_id: int
    troll_role_id: int
    kick_log_channel_id: int
    jail_channel_id: int
    reaction_purge_channel_id: int
    ves_price_enabled: bool
    redis_host: str
    redis_password: str | None
    db_path: str
    msg_rights: str
    msg_release: str
    msg_citizenship: str
    msg_deport: str
    msg_troll: str
    msg_untroll: str

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            bot_token=_require("BOT_TOKEN"),
            admin_role_ids=_ints("ADMIN_ROLE_IDS"),
            admin_user_ids=_ints("ADMIN_USER_IDS"),
            super_user_ids=_ints("SUPER_USER_IDS"),
            alert_user_id=_int("ALERT_USER_ID"),
            no_spam_channel_ids=_ints("NO_SPAM_CHANNEL_IDS"),
            muzzled_role_id=_int("MUZZLED_ROLE_ID"),
            images_role_id=_int("IMAGES_ROLE_ID"),
            arrest_role_id=_int("ARREST_ROLE_ID"),
            citizen_role_id=_int("CITIZEN_ROLE_ID"),
            troll_role_id=_int("TROLL_ROLE_ID"),
            kick_log_channel_id=_int("KICK_LOG_CHANNEL_ID"),
            jail_channel_id=_int("JAIL_CHANNEL_ID"),
            reaction_purge_channel_id=_int("REACTION_PURGE_CHANNEL_ID"),
            ves_price_enabled=_bool("VES_PRICE_ENABLED"),
            redis_host=os.environ.get("REDIS_HOST", "localhost"),
            redis_password=os.environ.get("REDIS_PASSWORD") or None,
            db_path=os.environ.get("DB_PATH", "discord.db"),
            msg_rights=_require("MSG_RIGHTS"),
            msg_release=_require("MSG_RELEASE"),
            msg_citizenship=_require("MSG_CITIZENSHIP"),
            msg_deport=_require("MSG_DEPORT"),
            msg_troll=_require("MSG_TROLL"),
            msg_untroll=_require("MSG_UNTROLL"),
        )
