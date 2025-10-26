import asyncio
import json
import aiohttp
import os
import urllib3
urllib3.disable_warnings()
from config import *

CHANNELS = {
    "500k-1m": 1431896893402648617,
    "1m-10m": 1429903951775404262,
    "10m-100m": 1429904415095128134,
    "100m+": 1429904829177790605
}

DATA_FILE = "data.json"
HEADERS = {
    "Authorization": DISCORD_TOKEN,
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/json"
}

MAX_FETCH = 20  # fetch up to 10 from each channel every loop
last_msg_id = {name: None for name in CHANNELS.keys()}


def append_to_json(data):
    """Add to front of file"""
    if not data:
        return

    existing = []
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except:
            pass

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data + existing, f, ensure_ascii=False, indent=2)


async def fetch_channel(session, name, chan_id):
    params = {"limit": MAX_FETCH}
    if last_msg_id[name]:
        params["after"] = last_msg_id[name]

    url = f"https://discord.com/api/v10/channels/{chan_id}/messages"
    async with session.get(url, headers=HEADERS, params=params) as r:
        if r.status != 200:
            return []

        msgs = await r.json()
        if msgs:
            last_msg_id[name] = msgs[0]["id"]
        return [m for m in msgs if m.get("embeds")]


def minimal_clean(m):
    """Only update title + color"""
    for e in m.get("embeds", []):
        e["title"] = "NeonHub | Notifier"
        e["color"] = 0xef00ff
    return m


async def main():
    print("[✅] Ultra-fast alternating enabled...")

    async with aiohttp.ClientSession() as session:
        while True:
            new_total = 0
            per_channel = {}
            new_batch = []

            for name, chan_id in CHANNELS.items():
                msgs = await fetch_channel(session, name, chan_id)
                msgs = msgs[:MAX_FETCH]

                per_channel[name] = len(msgs)
                new_total += len(msgs)

                new_batch.extend(minimal_clean(m) for m in msgs)

            if new_total > 0:
                append_to_json(new_batch)

                print(f"\n[+] {new_total} new embed data")
                for name, count in per_channel.items():
                    if count > 0:
                        print(f"  {count} from {name}")

            # 🔥 NO DELAY AT ALL — runs instantly!


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped.")
