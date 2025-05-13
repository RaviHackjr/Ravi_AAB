from asyncio import gather, create_task, sleep as asleep, Event
from asyncio.subprocess import PIPE
from os import path as ospath, system
from aiofiles import open as aiopen
from aiofiles.os import remove as aioremove
from traceback import format_exc
from base64 import urlsafe_b64encode
from time import time
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import re
from bot import bot, bot_loop, Var, ani_cache, ffQueue, ffLock, ff_queued
from .tordownload import TorDownloader
from .database import db
from .func_utils import getfeed, encode, editMessage, sendMessage, convertBytes
from .text_utils import TextEditor
from .ffencoder import FFEncoder
from .tguploader import TgUploader
from .reporter import rep
import datetime
import asyncio

def clean_anime_title(title: str) -> str:
    cleaned_title = re.sub(r'^\[.*?\]\s*', '', title)
    cleaned_title = re.sub(r'\s*-\s*\d+\s*\(.*?\)', '', cleaned_title)
    cleaned_title = re.sub(r'\[.*?\]', '', cleaned_title)
    cleaned_title = cleaned_title.replace('.mkv', '').strip()

    return cleaned_title

btn_formatter = {
    'HDRi':'𝗛𝗗𝗥𝗶𝗽',
    '1080':'𝟭𝟬𝟴𝟬𝗣', 
    '720':'𝟳𝟮𝟬𝗣',
    '480':'𝟰𝟴𝟬𝗣',
    '360':'𝟯𝟲𝟬𝗣'
}

async def send_sticker_to_channel(channel, sticker_id):
    if Var.SEND_STICKER and sticker_id:
        try:
            await bot.send_sticker(channel, sticker_id)
        except Exception as e:
            print(f"Failed to send sticker: {e}")

async def mirror_to_main_channel(post_msg, photo_url, caption, channel_to_use):
    try:
        if channel_to_use == Var.MAIN_CHANNEL:
            return

        chat_info = await bot.get_chat(channel_to_use)
        raw_channel_id = str(chat_info.id).replace("-100", "")
        post_link = f"https://t.me/c/{raw_channel_id}/{post_msg.id}"

        if chat_info.username:
            buttons = InlineKeyboardMarkup([
                InlineKeyboardButton("✧ Dᴏᴡɴʟᴏᴀᴅ ✧", url=post_link)
            ])
        else:
            invite_link = chat_info.invite_link or await bot.export_chat_invite_link(channel_to_use)
            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✧ Dᴏᴡɴʟᴏᴀᴅ", url=post_link),
                    InlineKeyboardButton("Jᴏɪɴ Cʜᴀɴɴᴇʟ ✧", url=invite_link)
                ]
            ])

        await bot.send_photo(
            Var.MAIN_CHANNEL,
            photo=post_msg.photo.file_id if post_msg.photo else photo_url,
            caption=caption,
            reply_markup=buttons
        )

        if channel_to_use != Var.MAIN_CHANNEL:
            await send_sticker_to_channel(channel_to_use, Var.STICKER_ID)

    except Exception as e:
        await rep.report(f"Mirror Error: {e}", "error")

async def fetch_animes():
    await rep.report("Fetching Anime Started !!!", "info")
    while True:
        await asleep(5)
        if ani_cache['fetch_animes']:
            for link in Var.RSS_ITEMS:
                if (info := await getfeed(link, 0)):
                    bot_loop.create_task(get_animes(info.title, info.link))

async def get_animes(name, torrent, force=False):
    try:
        aniInfo = TextEditor(name)
        await aniInfo.load_anilist()
        ani_id, ep_no = aniInfo.adata.get('id'), aniInfo.pdata.get("episode_number")

        if ani_id not in ani_cache['ongoing']:
            ani_cache['ongoing'].add(ani_id)
        elif not force:
            return
        if not force and ani_id in ani_cache['completed']:
            return

        if force or (not (ani_data := await db.getAnime(ani_id)) \
            or (ani_data and not (qual_data := ani_data.get(ep_no))) \
            or (ani_data and qual_data and not all(qual for qual in qual_data.values()))):
            
            if "[Batch]" in name:
                await rep.report(f"Torrent Skipped!\n\n{name}", "warning")
                return
                
            await rep.report(f"New Anime Torrent Found!\n\n{name}", "info")
            
            cleaned_name = clean_anime_title(name)
            
            custom_channel = await db.get_anime_channel(cleaned_name)
            channel_to_use = custom_channel or Var.MAIN_CHANNEL

            post_msg = None
            anime_name = name
            photo_path = None
            
            if Var.ANIME in anime_name:
                photo_url = Var.CUSTOM_BANNER 
            else:
                photo_url = await aniInfo.get_poster()
                
            if photo_path is not None:
                with open(photo_path, 'rb') as photo_file:
                    post_msg = await bot.send_photo(
                        channel_to_use,
                        photo=photo_url,
                        caption=await aniInfo.get_caption()
                    )
            elif 'photo_url' in locals():
                post_msg = await bot.send_photo(
                    channel_to_use,
                    photo=photo_url,
                    caption=await aniInfo.get_caption()
                )
            
            await mirror_to_main_channel(
                post_msg=post_msg,
                photo_url=photo_url,
                caption=post_msg.caption.html if post_msg.caption else "",
                channel_to_use=channel_to_use
            )
            
            await asleep(1.5)
            print(f"Using channel: {channel_to_use} for anime: {cleaned_name}")
            await asleep(1.5)
            stat_msg = await bot.send_message(
                chat_id=channel_to_use, 
                text=f"<blockquote>‣ <b>Anime Name :</b> <b><i>{name}</i></b></blockquote>\n\n<pre><i>Downloading...</i></pre>"
            )
            
            dl = await TorDownloader("./downloads").download(torrent, name)
            if not dl or not ospath.exists(dl):
                await rep.report(f"File Download Incomplete, Try Again", "error")
                await stat_msg.delete()
                return

            await send_sticker_to_channel(channel_to_use, Var.STICKER_ID)
            await asleep(Var.STICKER_INTERVAL)

            post_id = post_msg.id
            ffEvent = Event()
            ff_queued[post_id] = ffEvent
            if ffLock.locked():
                await editMessage(stat_msg, f"<blockquote>‣ <b>Anime Name :</b> <b><i>{name}</i></b></blockquote>\n\n<pre><i>Queued to Encode...</i></pre>")
                await rep.report("Added Task to Queue...", "info")
            await ffQueue.put(post_id)
            await ffEvent.wait()
            
            await ffLock.acquire()
            btns = []
            for qual in Var.QUALS:
                filename = await aniInfo.get_upname(qual)
                await editMessage(stat_msg, f"<blockquote>‣ <b>Anime Name :</b> <b><i>{name}</i></b></blockquote>\n\n<pre><i>Ready to Encode...</i></pre>")
                
                await asleep(1.5)
                await rep.report("Starting Encode...", "info")
                try:
                    out_path = await FFEncoder(stat_msg, dl, filename, qual).start_encode()
                except Exception as e:
                    await rep.report(f"Error: {e}, Cancelled, Retry Again !", "error")
                    await stat_msg.delete()
                    ffLock.release()
                    return
                await rep.report("Successfully Compressed Now Going To Upload...", "info")
                
                await editMessage(stat_msg, f"<blockquote>‣ <b>Anime Name :</b> <b><i>{filename}</i></b></blockquote>\n\n<pre><i>Ready to Upload...</i></pre>")
                await asleep(1.5)
                try:
                    msg = await TgUploader(stat_msg).upload(out_path, qual)
                except Exception as e:
                    await rep.report(f"Error: {e}, Cancelled, Retry Again !", "error")
                    await stat_msg.delete()
                    ffLock.release()
                    return
                await rep.report("Successfully Uploaded File into Channel...", "info")
                
                msg_id = msg.id
                link = f"https://telegram.me/OngoingNovaBot?start={await encode('get-'+str(msg_id * abs(Var.FILE_STORE)))}"
                
                if post_msg:
                    if len(btns) != 0 and len(btns[-1]) == 1:
                        btns[-1].insert(1, InlineKeyboardButton(f"{btn_formatter[qual]}", url=link))
                    else:
                        btns.append([InlineKeyboardButton(f"{btn_formatter[qual]}", url=link)])
                    await editMessage(post_msg, post_msg.caption.html if post_msg.caption else "", InlineKeyboardMarkup(btns))

                await db.saveAnime(ani_id, ep_no, qual, post_id)
                bot_loop.create_task(extra_utils(msg_id, out_path))
            ffLock.release()
            
            await stat_msg.delete()
            await aioremove(dl)
        ani_cache['completed'].add(ani_id)
    except Exception as error:
        await rep.report(format_exc(), "error")


async def extra_utils(msg_id, out_path):
    msg = await bot.get_messages(Var.FILE_STORE, message_ids=msg_id)

    if Var.BACKUP_CHANNEL != 0:
        for chat_id in Var.BACKUP_CHANNEL.split():
            await msg.copy(int(chat_id))
            
    # MediaInfo, ScreenShots, Sample Video ( Add-ons Features )

