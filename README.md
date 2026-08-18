# Beatrice

BANANO/NANO community utility and moderation bot for Discord.

Slash-command bot built on discord.py 2.x. Runs with **zero privileged intents** — no message
content, no members, no presence.

## Features

- `/price` — BANANO/NANO/BTC market data from CoinGecko
- `/meme` `/pup` `/meow` `/fridge` — curated image rotations, managed via `/gallery add|remove|list`
- `/farms` — wBAN farm TVL/APR from on-chain queries across five networks
- `/fodl` — Folding@Home / Bananominer client verification
- `/mute` `/unmute` — role-based mutes persisted in SQLite; a background sweep expires timed
  mutes and re-applies the role to users who rejoin to evade it
- `/kick` `/ban` — moderation with audit-log reasons, multi-target via the `more` option,
  and rate alerting through redis counters
- `/arrest` `/release` `/troll` `/untroll` `/citizenship` `/deport` `/images allow|deny`

## Requirements

- Python 3.13+
- Redis
- [uv](https://docs.astral.sh/uv/)

## Running

```
cp .env.example .env   # fill in BOT_TOKEN and your guild's IDs
uv sync
set -a; source .env; set +a
uv run python -m beatrice
```

Command trees are synced per-guild on startup, so slash commands appear immediately in every
server the bot is in.

## Development

```
uv run ruff check .
uv run ruff format .
```

Deployment is Docker + kustomize; see `Dockerfile` and `kubernetes/`.
