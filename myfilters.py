from dbworker import get_running, get_sources

from pyrogram import filters
from pyrogram.types import Message


command_add_channel = filters.regex(r"/add_channel-[0-9]+$")
command_add_this_channel = filters.regex(r"/add_this_channel")
command_watermark_this = filters.regex(r"/watermark_this_color([0-9ABCDEFabcdef]+|default)text[.\w\s]+")
command_watermark_channel = filters.regex(r"/watermark-[0-9]+color([0-9ABCDEFabcdef]+|default)text[.\w\s@%^&*<>\[\]()!#№:;|+-\\/\"`~=]+")
command_unwatermark_this = filters.regex(r"/unwatermark_this")
command_unwatermark_channel = filters.regex(r"/unwatermark-[0-9]+")
command_set_hashtag = filters.regex(r"/set_hashtag_to[0-9]+text")
command_add_source = filters.regex(r"/add_source-?[0-9]+")
command_bind = filters.regex(r"/bind-[0-9]+and-?[0-9]+")
command_delete_bind = filters.regex(r"/delete_bind[0-9]+")
command_show_binds = filters.regex(r"^/show_binds$")
command_show_groups = filters.regex(r"^/show_groups$")
command_send_id = filters.regex(r"^/get_id$")
command_add_channel_group = filters.regex(r"/add_channel_group_name=[\w\s]+")
command_set_group_name = filters.regex(r"/change_group\d+_name=[\w\s]+")
command_add_channel_to_group = filters.regex(r"/add_channel-[0-9]+_to_group[0-9]+")
command_add_channels_to_group = filters.regex(r"/add_many_channels(-?[\d\s])+_to_group[0-9]+")
command_add_user_to_group = filters.regex(r'/kick_user[\d]+_from_group[\d]+_after[\d]+')
command_add_users_to_group = filters.regex(r'/kick_many_users[\d\s]+_from_group[\d]+_after[\d]+')
command_add_for_time = filters.regex(r"/add_user[0-9]+to-[0-9]+for[0-9]+")


def filter_running_bot(session_name):
    return get_running(session_name)


def filter_source_chats(msg: Message, session_id):
    return msg.chat.id in get_sources(session_id) if msg.chat else False
