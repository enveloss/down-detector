from os import getenv
from dotenv import load_dotenv

load_dotenv()

MODE = getenv("MODE", "production")
BOT_TOKEN = getenv("BOT_TOKEN")
REPORT_CHAT_ID = getenv("REPORT_CHAT_ID")
ADMINS = getenv("ADMINS", "").replace(' ', '').split(',')
