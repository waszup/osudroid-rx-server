import os
from dotenv import load_dotenv
import json

load_dotenv(override=False)

# Main server configuration
server_name = os.getenv("SERVER_NAME", "waszup osu!droid RX")
server_description = (
    "Server that aims to be a relax mod only version of osu!droid, for those people that like to play RX and wish it were ranked."
)
port = int(os.getenv("PORT", os.getenv("SERVER_PORT", "8080")))
ip = os.getenv("SERVER_IP", "127.0.0.1")
domain = os.getenv("SERVER_DOMAIN")
host = os.getenv("PUBLIC_URL", "").rstrip("/")

# Client configuration
online_version = 9
client_link = os.getenv("CLIENT_DOWNLOAD_URL", "https://github.com/waszup/odrx-client/actions/workflows/build-private-apk.yml")
client_version = os.getenv("CLIENT_VERSION", "waszup RX test")
client_version_code = int(os.getenv("CLIENT_VERSION_CODE", "0"))
client_changelog = os.getenv("CLIENT_CHANGELOG", "Private waszup server; protocol 9")
banner_url = os.getenv("BANNER_URL", "https://github.com/waszup/odrx-client")

# State toggles
legacy = False  # Enable to use legacy submit system
maintenance = False
disable_submit = False  # Disables play submissions and notifies users

# Cron job settings
cron_delay = 10  # Delay (in minutes) for updating user stats

# Ranking system configuration
pp = True  # Enable pp system
pp_leaderboard = True  # Show and sort leaderboard by pp
max_pp_value = 10000  # Max pp value for a play

# External service keys and URLs
osu_key = os.getenv("OSU_KEY", "")
db_url = os.getenv("DATABASE_URL", "")
submit_hook = os.getenv("SUBMIT_DISCORD", "")
wl_hook = os.getenv("WL_DISCORD", "")
wl_key = os.getenv("WL_KEY", "")
login_key = os.getenv("LOGIN_KEY", "")


# maybe will be used later
# not finished

# class ConfigValue():
#     def __init__(self, value=None, is_locked=False):
#         self.__value = value
#         self.__is_locked = is_locked

#     @property
#     def value(self):
#         return self.__value

#     @value.setter
#     def value(self, new_value):
#         if not self.__is_locked or self.__value == None:
#             self.__value = new_value
#         else:
#             raise ValueError("This config value is locked and cannot be changed.")

# class Config:
#     def __init__(self):
#         pass

#     def __setattr__(self, name, value):
#         if hasattr(self, name):
#             current_value = getattr(self, name)
#             current_value.value = value
#         else:
#             super().__setattr__(name, ConfigValue(value))

#     def __getattribute__(self, name):
#         if hasattr(self, name):
#             current_value = getattr(self, name)
#             return current_value.value
#         raise AttributeError(f"Config has no attribute '{name}'")

#     def load(self):
#         with open("config.json", "r") as f:
#             data = json.load(f)
#             for key, value in data.items():
#                 setattr(self, key, ConfigValue(value.get("value"), value.get("is_locked", False)))
