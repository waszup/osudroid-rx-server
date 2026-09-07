"""Integration smoke test against an isolated PostgreSQL database and real HTTP server."""
import asyncio
import hashlib
import io
import json
import math
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
import zipfile

import asyncpg
import requests
import socketio

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:8080"
RESULTS = []


def check(condition, message):
    if not condition:
        raise AssertionError(message)
    RESULTS.append(message)
    print("PASS:", message, flush=True)


def post(path, **kwargs):
    response = requests.post(BASE + path, timeout=30, **kwargs)
    check(response.status_code == 200, path + " HTTP 200")
    return response


def main():
    artifacts = ROOT / "work"
    artifacts.mkdir(exist_ok=True)
    log = (artifacts / "server.log").open("w", encoding="utf-8")
    process = subprocess.Popen([sys.executable, "main.py"], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    try:
        for _ in range(90):
            if process.poll() is not None:
                raise RuntimeError("Server stopped during startup; inspect server.log")
            try:
                if requests.get(BASE + "/healthz", timeout=1).status_code == 200:
                    break
            except requests.RequestException:
                pass
            time.sleep(1)
        else:
            raise RuntimeError("Server failed readiness check")
        check(requests.get(BASE + "/healthz", timeout=5).json()["status"] == "ok", "PostgreSQL-backed health endpoint")
        homepage = requests.get(BASE + "/", timeout=5)
        check(homepage.status_code == 200 and "waszup" in homepage.text, "Home page renders")
        update = requests.get(BASE + "/api/update.php/", timeout=5)
        check(update.status_code == 200 and "version_code" in update.json(), "Update endpoint returns JSON")
        check(requests.get(BASE + "/user/avatar/0.png/", timeout=5).headers.get("Content-Type", "").startswith("image/png"), "Default avatar available")
        check(requests.get(BASE + "/multi/getrooms/", timeout=5).json() == [], "Multiplayer routes loaded")
        sock = socketio.Client()
        sock.connect(BASE, transports=["polling"])
        check(sock.connected, "Socket.IO connection established")
        sock.disconnect()

        username = "ci" + secrets.token_hex(5)
        password = secrets.token_urlsafe(24)
        register = post("/api/register.php/", data={"username": username, "password": password, "email": username + "@example.com"})
        check("Account Created" in register.text, "Registration creates account")
        duplicate = post("/api/register.php/", data={"username": username, "password": password, "email": username + "@example.com"})
        check(duplicate.text.startswith("FAILED"), "Duplicate username rejected")
        wire_password = hashlib.md5((password + "taikotaiko").encode()).hexdigest()
        invalid = post("/api/login.php/", data={"username": username, "password": "wrong", "version": "9"})
        check(invalid.text.startswith("FAILED"), "Incorrect password rejected")
        login = post("/api/login.php/", data={"username": username, "password": wire_password, "version": "9"})
        check(login.text.startswith("SUCCESS\n"), "Game protocol 9 login succeeds")
        fields = login.text.splitlines()[1].split()
        uid, ssid = fields[0], fields[1]
        check(requests.get(BASE + "/user/profile.php/", params={"id": uid}, timeout=10).status_code == 200, "Profile renders")
        for data in ({"userID": uid}, {"userID": "invalid"}, {"userID": "9999999", "ssid": "wrong"}):
            check(post("/api/submit.php/", data=data).text.startswith("FAILED"), "Invalid score session rejected")
        check(post("/api/upload.php/", data={"replayID": "../escape"}).text.startswith("FAILED"), "Unauthenticated replay upload rejected")

        public_md5 = "233f55099932d0696a3ef192041bc30d"
        public_map = requests.get(BASE + "/api/v2/md5/" + public_md5 + "/", timeout=30)
        check(public_map.status_code == 200 and public_map.json().get("ranked") == 1, "Public beatmap lookup works without an osu API key")
        public_info = requests.get(BASE + "/api/beatmap/", params={"bid": 75}, timeout=40)
        check(public_info.status_code == 200, "Beatmap details and download succeed")
        public_file = Path("/srv/odrx_storage/beatmaps/75.osu")
        check(public_file.exists() and hashlib.md5(public_file.read_bytes()).hexdigest() == public_md5, "Downloaded public beatmap matches its checksum")

        beatmap = """osu file format v14

[General]
AudioFilename: test.mp3
Mode: 0

[Metadata]
Title:CI fixture
Artist:waszup
Creator:CI
Version:Test
BeatmapID:900001
BeatmapSetID:900001

[Difficulty]
HPDrainRate:5
CircleSize:4
OverallDifficulty:8
ApproachRate:8
SliderMultiplier:1.4
SliderTickRate:1

[TimingPoints]
0,500,4,2,1,100,1,0

[HitObjects]
"""
        beatmap += "\n".join(f"{64 + (i % 5) * 80},{64 + (i % 3) * 80},{1000 + i * 250},1,0,0:0:0:0:" for i in range(40)) + "\n"
        md5 = hashlib.md5(beatmap.encode()).hexdigest()
        Path("/srv/odrx_storage/beatmaps/900001.osu").write_text(beatmap)

        async def seed():
            conn = await asyncpg.connect(os.environ["DATABASE_URL"])
            try:
                await conn.execute("""INSERT INTO maps
                    (id,set_id,artist,title,version,creator,last_update,total_length,max_combo,status,mode,bpm,cs,od,ar,hp,star,md5)
                    VALUES (900001,900001,'waszup','CI fixture','Test','CI',0,11,40,1,0,120,4,8,8,5,1,$1)""", md5)
            finally:
                await conn.close()
        asyncio.run(seed())
        payload = io.BytesIO()
        with zipfile.ZipFile(payload, "w") as archive:
            archive.writestr("CI.txt", "Storage fixture; not a gameplay replay")
        replay = payload.getvalue()
        mods = json.dumps([{"acronym": "RX", "settings": {}}], separators=(",", ":"))
        data = " ".join([mods, "123456", "40", "SS", "0", "40", "0", "0", "0", "0", "0", "0", "1.0", str(int(time.time())), "true", username])
        submitted = post("/api/submit.php/", data={"userID": uid, "ssid": ssid, "hash": md5, "data": data},
            files={"replayFile": ("fixture.odr", replay, "application/octet-stream")})
        check(submitted.text.startswith("SUCCESS\n"), "RX score submission succeeds: " + submitted.text[:100])

        async def inspect_score():
            conn = await asyncpg.connect(os.environ["DATABASE_URL"])
            try:
                return await conn.fetchrow("SELECT id,playerid,pp FROM scores WHERE playerid=$1 ORDER BY id DESC LIMIT 1", int(uid))
            finally:
                await conn.close()
        saved = asyncio.run(inspect_score())
        check(saved is not None and saved["playerid"] == int(uid), "Score persisted to correct account")
        check(math.isfinite(saved["pp"]) and saved["pp"] > 0, "RX pp calculation returns finite positive result")
        downloaded = requests.get(BASE + f"/api/upload/{saved['id']}.odr/", timeout=10)
        check(downloaded.status_code == 200 and downloaded.content == replay, "Replay round trip preserves bytes")
        print("ALL INTEGRATION CHECKS PASSED", flush=True)
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        log.close()
        (artifacts / "smoke-results.json").write_text(json.dumps(RESULTS, indent=2))


if __name__ == "__main__":
    main()
