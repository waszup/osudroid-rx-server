"""Create local secrets without overwriting any existing configuration."""
from pathlib import Path
import secrets

base = Path(__file__).resolve().parent
text = (base / ".env.example").read_text(encoding="utf-8")
for key in ("POSTGRES_PASSWORD", "LOGIN_KEY", "WL_KEY"):
    text = text.replace(key + "=\n", key + "=" + secrets.token_hex(32) + "\n")
with (base / ".env").open("x", encoding="utf-8") as stream:
    stream.write(text)
print("Local .env created. Keep this file private.")
