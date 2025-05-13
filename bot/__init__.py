from os import path as ospath, mkdir, system, getenv
from logging import INFO, ERROR, FileHandler, StreamHandler, basicConfig, getLogger
from traceback import format_exc
from asyncio import Queue, Lock

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pyrogram import Client
from pyrogram.enums import ParseMode
from dotenv import load_dotenv
from uvloop import install

install()
basicConfig(format="[%(asctime)s] [%(name)s | %(levelname)s] - %(message)s [%(filename)s:%(lineno)d]",
            datefmt="%m/%d/%Y, %H:%M:%S %p",
            handlers=[FileHandler('log.txt'), StreamHandler()],
            level=INFO)

getLogger("pyrogram").setLevel(ERROR)
LOGS = getLogger(__name__)

load_dotenv('config.env')

ani_cache = {
    'fetch_animes': True,
    'ongoing': set(),
    'completed': set()
}
ffpids_cache = list()

ffLock = Lock()
ffQueue = Queue()
ff_queued = dict()

class Var:
    API_ID, API_HASH, BOT_TOKEN = getenv("API_ID"), getenv("API_HASH"), getenv("BOT_TOKEN")
    MONGO_URI = getenv("MONGO_URI")
    
    if not BOT_TOKEN or not API_HASH or not API_ID or not MONGO_URI:
        LOGS.critical('Important Variables Missing. Fill Up and Retry..!! Exiting Now...')
        exit(1)

    RSS_ITEMS = getenv("RSS_ITEMS", "https://subsplease.org/rss/?r=1080").split()
    FSUB_CHATS = list(map(int, getenv('FSUB_CHATS').split()))
    BACKUP_CHANNEL = getenv("BACKUP_CHANNEL") or ""
    MAIN_CHANNEL = int(getenv("MAIN_CHANNEL"))
    LOG_CHANNEL = int(getenv("LOG_CHANNEL") or 0)
    FILE_STORE = int(getenv("FILE_STORE"))
    ADMINS = list(map(int, getenv("ADMINS", "").split()))
    SEND_STICKER = getenv('SEND_STICKER', 'True').lower() == 'true'
    STICKER_ID = getenv('STICKER_URL', 'CAACAgUAAyEFAASgAaywAAIrRWgUTnv8oPmkNTURJLgG3viWKaeHAALcEAAC3vioVI8x8-QnQkJbNgQ')
    STICKER_INTERVAL = int(getenv('STICKER_INTERVAL', 2))
    
    SEND_SCHEDULE = getenv("SEND_SCHEDULE", "False").lower() == "true"
    BRAND_UNAME = getenv("BRAND_UNAME", "@GenAnimeOfc")
    FFCODE_1080 = getenv("FFCODE_1080") or """ffmpeg -i '{}' -progress '{}' -preset veryfast -c:v libx264 -s 1920x1080 -pix_fmt yuv420p -crf 30 -c:a libopus -b:a 32k -c:s copy -map 0 -ac 2 -ab 32k -vbr 2 -level 3.1 '{}' -y"""
    FFCODE_720 = getenv("FFCODE_720") or """ffmpeg -i '{}' -progress '{}' -preset superfast -c:v libx264 -s 1280x720 -pix_fmt yuv420p -crf 30 -c:a libopus -b:a 32k -c:s copy -map 0 -ac 2 -ab 32k -vbr 2 -level 3.1 '{}' -y"""
    FFCODE_480 = getenv("FFCODE_480") or """ffmpeg -i '{}' -progress '{}' -preset superfast -c:v libx264 -s 854x480 -pix_fmt yuv420p -crf 30 -c:a libopus -b:a 32k -c:s copy -map 0 -ac 2 -ab 32k -vbr 2 -level 3.1 '{}' -y"""
    FFCODE_360 = getenv("FFCODE_360") or """ffmpeg -i '{}' -progress '{}' -preset superfast -c:v libx264 -s 640x360 -pix_fmt yuv420p -crf 30 -c:a libopus -b:a 32k -c:s copy -map 0 -ac 2 -ab 32k -vbr 2 -level 3.1 '{}' -y"""
    FFCODE_HDRi = getenv("FFCODE_HDRi") or """ffmpeg -i '{}' -progress '{}' -preset superfast -c:v libx264 -s 1920x1080 -pix_fmt yuv420p -crf 30 -c:a libopus -b:a 32k -c:s copy -map 0 -ac 2 -ab 32k -vbr 2 -level 3.1 '{}' -y"""
    QUALS = getenv("QUALS", "360 480 720 1080 HDRi").split()
    
    AS_DOC = getenv("AS_DOC", "True").lower() == "true"
    THUMB = getenv("THUMB")
    ANIME = getenv("ANIME", "Is It Wrong to Try to Pick Up Girls in a Dungeon?")
    CUSTOM_BANNER = getenv("CUSTOM_BANNER", "https://envs.sh/LyC.jpg")        
    AUTO_DEL = getenv("AUTO_DEL", "True").lower() == "true"
    DEL_TIMER = int(getenv("DEL_TIMER", "1800"))
    START_PHOTO = getenv("START_PHOTO", "https://preview.redd.it/6dq40vj38ya91.png?width=1920&format=png&auto=webp&s=24a6a912b10a3bfe1da72adf3bcbfbe9ab5e31f7")
    START_MSG = getenv("START_MSG", "<blockquote><b>ʜᴇʏ {first_name}</b>,</blockquote>\n<i><blockquote>ɪ'ᴍ ᴀɴ ᴀᴜᴛᴏ ᴀɴɪᴍᴇ ꜱᴛᴏʀᴇ & ᴇɴᴄᴏᴅɪɴɢ ʙᴏᴛ, ʙᴜɪʟᴛ ᴡɪᴛʜ ʟᴏᴠᴇ.</blockquote></i>\n\n<blockquote>❝ ᴛʜᴇ ᴅɪꜰꜰᴇʀᴇɴᴄᴇ ʙᴇᴛᴡᴇᴇɴ ᴛʜᴇ ᴡɪɴɴᴇʀꜱ ᴀɴᴅ ʟᴏꜱᴇʀꜱ ɪꜱ ʜᴏᴡ ᴛʜᴇʏ ᴅᴇᴀʟ ᴡɪᴛʜ ᴛʜᴇɪʀ ꜰᴀᴛᴇ. ❞</blockquote>\n<blockquote>― <i>ᴋɪʏᴏᴛᴀᴋᴀ ᴀʏᴀɴᴏᴋᴏᴊɪ</i></blockquote>")
    START_BUTTONS = getenv("START_BUTTONS", "ᴍᴀɪɴ-ᴄʜᴀɴɴᴇʟ|https://telegram.me/genanimeofc sᴜᴘᴘᴏʀᴛ|https://telegram.me/genanimeofcchat")

if Var.THUMB and not ospath.exists("thumb.jpg"):
    system(f"wget -q {Var.THUMB} -O thumb.jpg")
    LOGS.info("Thumbnail has been Saved!!")
if not ospath.isdir("encode/"):
    mkdir("encode/")
if not ospath.isdir("thumbs/"):
    mkdir("thumbs/")
if not ospath.isdir("downloads/"):
    mkdir("downloads/")

try:
    bot = Client(name="AutoAniAdvance", api_id=Var.API_ID, api_hash=Var.API_HASH, bot_token=Var.BOT_TOKEN, plugins=dict(root="bot/modules"), parse_mode=ParseMode.HTML)
    bot_loop = bot.loop
    sch = AsyncIOScheduler(timezone="Asia/Kolkata", event_loop=bot_loop)
except Exception as ee:
    LOGS.error(str(ee))
    exit(1)
