from pathlib import Path
from quart import Blueprint, request
from objects import glob
from handlers.response import Failed, Success

bp = Blueprint("upload", __name__)
php_file = True


@bp.route("/", methods=["POST"])
async def upload_replay():
    form = await request.form
    try:
        player_id = int(form.get("userID", ""))
        replay_id = int(form.get("replayID", ""))
    except (ValueError, TypeError):
        return Failed("Invalid player or replay ID.")
    player = glob.players.get(id=player_id)
    if not player or not player.uuid or form.get("ssid") != player.uuid:
        return Failed("Invalid session.")
    score = await glob.db.fetch("SELECT playerid FROM scores WHERE id = $1", [replay_id])
    if not score or score["playerid"] != player.id:
        return Failed("Replay does not belong to this session.")
    file = (await request.files).get("uploadedfile")
    if file is None:
        return Failed("Replay missing.")
    data = file.read()
    if len(data) > 10 * 1024 * 1024 or not data.startswith(b"PK"):
        return Failed("Invalid replay.")
    path = Path("/srv/odrx_storage/replays") / f"{replay_id}.odr"
    try:
        with path.open("xb") as target:
            target.write(data)
    except FileExistsError:
        return Failed("Replay already exists.")
    return Success("Replay uploaded.")
