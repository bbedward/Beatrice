"""One-time setup: hide privileged slash commands from non-admin members.

Discord only allows command-permission writes with a user OAuth2 Bearer token,
never a bot token, so this script walks a Manage Guild holder through a local
OAuth consent flow and then denies @everyone / allows admin roles per command.

Prerequisites:
  - Developer Portal -> OAuth2 -> Redirects: add http://localhost:8765/callback
  - env: APP_ID, CLIENT_SECRET, BOT_TOKEN, GUILD_ID, ADMIN_ROLE_IDS (comma-separated)
"""

import http.server
import os
import sys
import threading
import urllib.parse

import requests

API = "https://discord.com/api/v10"
REDIRECT_URI = "http://localhost:8765/callback"
PRIVILEGED = {
    "kick",
    "ban",
    "mute",
    "unmute",
    "arrest",
    "release",
    "troll",
    "untroll",
    "citizenship",
    "deport",
    "images",
}

auth_code: str | None = None
code_received = threading.Event()


class CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        global auth_code
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        codes = params.get("code")
        if not codes:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Missing code parameter")
            return
        auth_code = codes[0]
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Authorized. You can close this tab.")
        code_received.set()

    def log_message(self, *args) -> None:
        pass


def require_env(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        sys.exit(f"missing required env var {key}")
    return value


def obtain_bearer_token(app_id: str, client_secret: str) -> str:
    server = http.server.HTTPServer(("localhost", 8765), CallbackHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    consent_url = (
        "https://discord.com/oauth2/authorize"
        f"?client_id={app_id}&response_type=code"
        f"&redirect_uri={urllib.parse.quote(REDIRECT_URI, safe='')}"
        "&scope=applications.commands.permissions.update"
    )
    print(f"Open this URL and authorize (must have Manage Guild):\n\n{consent_url}\n")
    if not code_received.wait(timeout=300):
        sys.exit("timed out waiting for OAuth callback")
    server.shutdown()
    response = requests.post(
        f"{API}/oauth2/token",
        data={
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": REDIRECT_URI,
        },
        auth=(app_id, client_secret),
        timeout=30,
    )
    if response.status_code != 200:
        sys.exit(f"token exchange failed: {response.status_code} {response.text}")
    return response.json()["access_token"]


def fetch_guild_commands(app_id: str, guild_id: str, bot_token: str) -> list[dict]:
    response = requests.get(
        f"{API}/applications/{app_id}/guilds/{guild_id}/commands",
        headers={"Authorization": f"Bot {bot_token}"},
        timeout=30,
    )
    if response.status_code != 200:
        sys.exit(f"command list failed: {response.status_code} {response.text}")
    return response.json()


def build_permissions(guild_id: str, role_ids: list[str], user_ids: list[str]) -> list[dict]:
    everyone_deny = [{"id": guild_id, "type": 1, "permission": False}]
    role_allows = [{"id": role_id, "type": 1, "permission": True} for role_id in role_ids]
    user_allows = [{"id": user_id, "type": 2, "permission": True} for user_id in user_ids]
    return everyone_deny + role_allows + user_allows


def main() -> None:
    app_id = require_env("APP_ID")
    client_secret = require_env("CLIENT_SECRET")
    bot_token = require_env("BOT_TOKEN")
    guild_id = require_env("GUILD_ID")
    role_ids = [r for r in require_env("ADMIN_ROLE_IDS").split(",") if r]
    user_ids = [u for u in os.environ.get("ADMIN_USER_IDS", "").split(",") if u]

    bearer = obtain_bearer_token(app_id, client_secret)
    commands = fetch_guild_commands(app_id, guild_id, bot_token)
    permissions = build_permissions(guild_id, role_ids, user_ids)

    for command in commands:
        if command["name"] not in PRIVILEGED:
            continue
        response = requests.put(
            f"{API}/applications/{app_id}/guilds/{guild_id}/commands/{command['id']}/permissions",
            headers={"Authorization": f"Bearer {bearer}"},
            json={"permissions": permissions},
            timeout=30,
        )
        if response.status_code != 200:
            print(f"FAILED /{command['name']}: {response.status_code} {response.text}")
            continue
        print(f"hidden from non-admins: /{command['name']}")


if __name__ == "__main__":
    main()
