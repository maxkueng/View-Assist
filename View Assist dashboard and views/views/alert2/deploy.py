#!/usr/bin/env python3
"""Regenerate the alert2 view and push it into the view-assist dashboard.

Runs gen_alert2_view.py, replaces the path=alert2 view in the dashboard's
storage config over the Lovelace websocket API, then reloads the tablet
webviews (they never pick up storage-dashboard edits on their own).

Auth: long-lived access token (HA profile -> Security -> Long-lived access
tokens) in $HA_TOKEN, or in ~/.config/view-assist/ha-token.

  ./deploy.py               # regenerate + deploy + refresh tablets
  ./deploy.py --no-refresh  # leave the tablet webviews alone
"""
import argparse
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import aiohttp

HA_URL = os.environ.get("HA_URL", "http://10.42.42.54:8123")
DASHBOARD = "view-assist"
VIEW_PATH = "alert2"
HERE = Path(__file__).resolve().parent
VIEW_FILE = HERE / "alert2_view.json"
TOKEN_FILE = Path.home() / ".config" / "view-assist" / "ha-token"
REFRESH_BUTTONS = ["button.vaca_2b468c768_refresh", "button.vaca_06c2c3ae0_refresh"]


def token():
    tok = os.environ.get("HA_TOKEN", "").strip()
    if not tok and TOKEN_FILE.exists():
        tok = TOKEN_FILE.read_text().strip()
    if not tok:
        sys.exit(f"no token: set $HA_TOKEN or put one in {TOKEN_FILE}")
    return tok


async def ws_cmd(ws, msg_id, **msg):
    await ws.send_json({"id": msg_id, **msg})
    while True:
        resp = await ws.receive_json()
        if resp.get("id") != msg_id:
            continue
        if not resp.get("success"):
            sys.exit(f"{msg['type']} failed: {resp.get('error')}")
        return resp.get("result")


async def deploy(refresh):
    view = json.loads(VIEW_FILE.read_text())
    tok = token()
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(f"{HA_URL}/api/websocket") as ws:
            if (await ws.receive_json())["type"] != "auth_required":
                sys.exit("unexpected websocket greeting")
            await ws.send_json({"type": "auth", "access_token": tok})
            if (await ws.receive_json())["type"] != "auth_ok":
                sys.exit("auth failed: token rejected")

            config = await ws_cmd(ws, 1, type="lovelace/config", url_path=DASHBOARD, force=True)
            views = config.get("views", [])
            idx = [i for i, v in enumerate(views) if v.get("path") == VIEW_PATH]
            if len(idx) != 1:
                sys.exit(f"expected exactly one view with path={VIEW_PATH}, found {len(idx)}")
            views[idx[0]] = view
            await ws_cmd(ws, 2, type="lovelace/config/save", url_path=DASHBOARD, config=config)

        ver = view["cards"][0].get("variables", {}).get("alertsstackversion", "?")
        print(f"deployed {VIEW_FILE.name} v{ver} -> {DASHBOARD}/{VIEW_PATH}")

        if refresh:
            headers = {"Authorization": f"Bearer {tok}"}
            for ent in REFRESH_BUTTONS:
                async with session.post(f"{HA_URL}/api/services/button/press",
                                        headers=headers, json={"entity_id": ent}) as resp:
                    print(f"refresh {ent}: {'ok' if resp.status == 200 else f'HTTP {resp.status}'}")
            print("note: a refresh lands the tablets on home, not the held view")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="deploy the alert2 view")
    ap.add_argument("--no-refresh", action="store_true", help="don't reload the tablet webviews")
    args = ap.parse_args()
    subprocess.run([sys.executable, str(HERE / "gen_alert2_view.py")], check=True)
    asyncio.run(deploy(refresh=not args.no_refresh))
