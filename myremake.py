import asyncio
import re
import os
from functools import partial
from typing import List
import datetime
from time import time

from myfilters import (
    filter_source_chats, filter_running_bot, command_add_channel,
    command_add_this_channel, command_watermark_this,
    command_unwatermark_this, command_add_source, command_bind,
    command_send_id, command_watermark_channel, command_unwatermark_channel,
    command_add_for_time, command_set_hashtag, command_delete_bind,
    command_show_binds, command_add_channel_group, command_add_channels_to_group,
    command_add_channel_to_group, command_add_user_to_group, command_show_groups,
    command_set_group_name
)
from dbworker import (
    save_resends, message_in_resendeds, get_resended_messages,
    add_channel, add_source, add_ligament, set_watermark, get_session_id,
    get_sources, add_session, add_session_added_user, get_session_added_users,
    kick_user_from_db, change_hashtag
)
from utils import (
    resend_message, notification_template, check_forkicking_bot,
    get_sessions, add_channel_command, send_session_binds,
    add_this_channel, set_watermark_on, set_watermark_off,
    add_source_command, add_binding, send_chat_id, add_user_for_time,
    check_for_kicking, set_hashtag, delete_bind, call_adding_cgroup,
    call_adding_channel_to_group, add_channels_to_group, show_groups,
    change_group_name
)

from pyrogram import Client, filters, utils, idle
from pyrogram.types import Message
from pyrogram.handlers import MessageHandler, DeletedMessagesHandler
from pyrogram.errors.exceptions.forbidden_403 import ChatWriteForbidden
from pyrogram.errors.exceptions.not_acceptable_406 import AuthKeyDuplicated


sessions = get_sessions()

for session in sessions:
    add_session(session)

API_ID = 2096979
API_HASH = '2bb5d66a4618e7325a91aab04d22c071'

clients = {}
is_running = {}
last_mg_id = {}
media_group_filters = {}
running_bot_filters = {}
source_chats_filter = {}


def filter_media_groups(message: Message, session_name):
    global last_mg_id
    my_last_mg_id = last_mg_id[session_name]
    try:
        if message.media_group_id == my_last_mg_id:
            return False
        if message.media_group_id:
            last_mg_id[session_name] = message.media_group_id
        return True
    except Exception as e:
        print("Exception: {}\n".format(e))
        return False


async def message_deleted(client: Client, messages: List[Message], session_id, session_name):
    for message in messages:
        if not filter_source_chats(message, session_id):
            continue
        if not filter_running_bot(session_name):
            return
        resended, resended_messages = message_in_resendeds(
            message.chat.id, message.message_id, session_id
        )
        if not resended:
            continue
        for r_message in resended_messages:
            res_message = await client.get_messages(*r_message)
            await client.send_message(int(res_message.chat.id), "❌❌[DELETED]❌❌", reply_to_message_id=res_message.message_id)


async def message_edited(client: Client, message: Message, session_id, session_name):
    if not filter_source_chats(message, session_id):
        return
    if not filter_running_bot(session_name):
        return
    resended, resended_messages = message_in_resendeds(
        message.chat.id, message.message_id, session_id
    )
    if not resended:
        return
    for r_message in resended_messages:
        res_message = await client.get_messages(*r_message)
        await resend_message(client, message, session_id, reply_to_message_id=res_message.message_id, edited_message_id=message.message_id, def_hashtag="⚠️⚠️[EDITED]⚠️⚠️\n\n")


async def message_from_source(client: Client, message: Message, session_id, session_name):
    if not filter_source_chats(message, session_id):
        return
    if not filter_running_bot(session_name):
        return
    if not filter_media_groups(message, session_name):
        return

    resended_message = await resend_message(client, message, session_id)

    if resended_message:
        if not message.media_group_id and not isinstance(resended_message, list):
            save_resends(message, resended_message, session_id)
            return
        elif isinstance(resended_message, list) and not message.media_group_id:
            for res_mes in resended_message:
                save_resends(message, res_mes, session_id)
            return

        msgs = await message.get_media_group()
        
        for i, original_message in enumerate(msgs):
            save_resends(original_message, resended_message[i], session_id)


for SESSIONNAME in sessions:
    session_id = get_session_id(SESSIONNAME)
    clients[SESSIONNAME] = Client(SESSIONNAME, api_id=API_ID, api_hash=API_HASH)
    is_running[SESSIONNAME] = True
    last_mg_id[SESSIONNAME] = 0

    name = partial(filter_media_groups, session_name=SESSIONNAME)
    media_group_filters[SESSIONNAME] = name
    name = partial(filter_running_bot, session_name=SESSIONNAME)
    running_bot_filters[SESSIONNAME] = name
    name = partial(filter_source_chats, session_id=session_id)
    source_chats_filter[SESSIONNAME] = name

    clients[SESSIONNAME].add_handler(MessageHandler(
        partial(check_for_kicking, session_id=session_id),
        ~filters.edited), 2)
    clients[SESSIONNAME].add_handler(MessageHandler(
        partial(
            message_from_source, session_id=session_id,
            session_name=SESSIONNAME),
        ~filters.edited
    ), -1)
    clients[SESSIONNAME].add_handler(MessageHandler(
        partial(message_edited, session_id=session_id, session_name=SESSIONNAME),
        filters.edited
    ), -1)
    clients[SESSIONNAME].add_handler(MessageHandler(
        partial(add_channel_command, session_id=session_id), command_add_channel
    ), 1)
    clients[SESSIONNAME].add_handler(MessageHandler(
        partial(add_this_channel, session_id=session_id), command_add_this_channel
    ), 1)
    clients[SESSIONNAME].add_handler(MessageHandler(
        partial(set_watermark_on, session_id=session_id),
        command_watermark_this | command_watermark_channel
    ), 1)
    clients[SESSIONNAME].add_handler(MessageHandler(
        partial(set_watermark_off, session_id=session_id),
        command_unwatermark_this | command_unwatermark_channel
    ), 1)
    clients[SESSIONNAME].add_handler(MessageHandler(
        partial(add_source_command, session_id=session_id), command_add_source
    ), 1)
    clients[SESSIONNAME].add_handler(MessageHandler(
        partial(add_binding, session_id=session_id), command_bind
    ), 1)
    clients[SESSIONNAME].add_handler(MessageHandler(
        partial(send_session_binds, session_id=session_id), command_show_binds), 1)
    clients[SESSIONNAME].add_handler(MessageHandler(
        partial(delete_bind, session_id=session_id), command_delete_bind), 1)
    clients[SESSIONNAME].add_handler(MessageHandler(send_chat_id, command_send_id), 1)
    clients[SESSIONNAME].add_handler(MessageHandler(
        partial(call_adding_cgroup, session_id=session_id), command_add_channel_group), 1)
    clients[SESSIONNAME].add_handler(MessageHandler(
        partial(show_groups, session_id=session_id), command_show_groups), 1)
    clients[SESSIONNAME].add_handler(MessageHandler(
        partial(change_group_name, session_id=session_id), command_set_group_name), 1)
    clients[SESSIONNAME].add_handler(MessageHandler(
        partial(call_adding_channel_to_group, session_id=session_id), command_add_channel_to_group), 1)
    clients[SESSIONNAME].add_handler(MessageHandler(
        partial(add_channels_to_group, session_id=session_id), command_add_channels_to_group), 1)
    clients[SESSIONNAME].add_handler(MessageHandler(
        partial(add_user_for_time, session_id=session_id),
        command_add_user_to_group
    ), 1)
    clients[SESSIONNAME].add_handler(MessageHandler(
        partial(set_hashtag, session_id=session_id),
        command_set_hashtag
        ), 1)
    clients[SESSIONNAME].add_handler(MessageHandler(
        check_forkicking_bot,
        filters.user(496583471)
    ))
    clients[SESSIONNAME].add_handler(
        DeletedMessagesHandler(
            partial(message_deleted, session_id=session_id, session_name=SESSIONNAME)
        )
    )
    try:
        clients[SESSIONNAME].start()
    except AuthKeyDuplicated:
        print(SESSIONNAME, "has to be authorized again")
    else:
        clients[SESSIONNAME].send_message('me', "Я запущен")

idle()
for client in clients.values():
    client.stop()
