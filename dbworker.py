import sqlite3
import asyncio
import datetime


DBNAME = "settings.db"


def with_connection(func):
    def inner(*args, **kwargs):
        with sqlite3.connect(DBNAME) as conn:
            return func(conn, conn.cursor(), *args, **kwargs)

    return inner


@with_connection
def get_resended_messages_for_reply(conn, cur, original_chat, original_message, resended_chat, session):
    query = "SELECT resended_message FROM messages WHERE session = ? AND deleted = ? AND resended_chat = ? AND original_message = ? AND original_chat = ?"
    cur.execute(query, (session, False, resended_chat, original_message, original_chat))
    result = cur.fetchone()
    return result[0]


@with_connection
def set_group_name(conn, cur, group_id, session, name):
    query = "UPDATE channel_groups SET name = ? WHERE session = ? AND id = ?"
    cur.execute(query, (name, session, group_id))
    return conn.commit()


@with_connection
def get_session_groups_and_channels(conn, cur, session):
    query = "SELECT id, name FROM channel_groups WHERE session = ?"
    cur.execute(query, (session, ))
    groups = [{'id': raw[0], 'name': raw[1], 'channels': []} for raw in cur.fetchall()]
    for group in groups:
        query = "SELECT channel FROM channels_in_groups WHERE group_id = ? AND session = ?"
        cur.execute(query, (group['id'], session))
        for raw in cur.fetchall():
            query = "SELECT chat_id FROM channels WHERE id = ?"
            cur.execute(query, (raw[0], ))
            group['channels'].extend([channel_raw[0] for channel_raw in cur.fetchall()])
    return groups


@with_connection
def get_group_name(conn, cur, group_id, session_id):
    query = "SELECT name FROM channel_groups WHERE id = ? AND session = ?"
    cur.execute(query, (group_id, session_id))
    return cur.fetchone()[0]


@with_connection
def get_group_channels(conn, cur, group, session):
    query = "SELECT channel FROM channels_in_groups WHERE group_id = ? AND session = ?"
    cur.execute(query, (group, session))
    channels = cur.fetchall()
    channels = [channel[0] for channel in channels]
    result = []
    for channel in channels:
        query = "SELECT chat_id FROM channels WHERE id = ?"
        cur.execute(query, (channel, ))
        result.append(cur.fetchone()[0])

    return result


@with_connection
def add_channel_to_group(conn, cur, channel, group, session):
    query = "SELECT id FROM channels WHERE chat_id = ? AND session = ?"
    cur.execute(query, (channel, session))
    channel_fetch = cur.fetchone()
    channel_id = int(channel_fetch[0]) if channel_fetch else None
    if not channel_id: raise ValueError(f"Добавьте канал {channel_fetch} в БД")
    query = "SELECT id FROM channel_groups WHERE session = ?"
    cur.execute(query, (session, ))
    session_groups = [int(raw[0]) for raw in cur.fetchall()]
    if group not in session_groups:
        raise ValueError("Данной группы нет в БД, или она вам не принадлежит")
    query = "INSERT INTO channels_in_groups (group_id, channel, session) VALUES (?, ?, ?)"
    print(query)
    cur.execute(query, (group, channel_id, session))
    return conn.commit()


@with_connection
def add_channel_group(conn, cur, name, session):
    query = "INSERT INTO channel_groups (name, session) VALUES (?, ?)"
    cur.execute(query, (name, session))
    conn.commit()
    return cur.lastrowid


@with_connection
def get_ligaments(conn, cur, session):
    query = "SELECT * FROM ligaments WHERE session = ?"
    cur.execute(query, (session, ))
    results = cur.fetchall()
    returnable = []
    for id, channel, source, hashtag, session in results:
        query = "SELECT chat_id FROM channels WHERE id = ?"
        cur.execute(query, (channel, ))
        channel_id = cur.fetchone()[0]
        query = "SELECT chat_id FROM sources WHERE id = ?"
        cur.execute(query, (source, ))
        source_id = cur.fetchone()[0]
        returnable.append({
            'id': id,
            'channel': channel_id,
            'source' : source_id,
            'hashtag': hashtag
            })
    return returnable


@with_connection
def delete_ligament(conn, cur, session_id, id):
    query = "DELETE FROM ligaments WHERE session = ? AND id = ?"
    cur.execute(query, (session_id, id))
    conn.commit()


@with_connection
def change_sent_messages(conn, cur, id, new_value):
    query = "UPDATE added_users SET sent_messages = ? WHERE id = ?"
    cur.execute(query, (new_value, id))
    conn.commit()


@with_connection
def kick_user_from_db(conn, cur, id):
    query = "DELETE FROM added_users WHERE id = ?"
    cur.execute(query, (id, ))
    conn.commit()


@with_connection
def add_session_added_user(conn, cur, session, time_to_kick, group_id, user_id):
    now = datetime.datetime.now()
    query = "INSERT INTO added_users (session, user_id, "\
            "group_id, datetime_tokick) VALUES (?, ?, ?, ?)"
    cur.execute(query, (
        session, user_id, group_id,
        time_to_kick.strftime("%d/%m/%Y %H:%M:%S")
    ))
    conn.commit()


@with_connection
def get_session_added_users(conn, cur, session):
    query = "SELECT id, user_id, group_id, datetime_tokick, sent_messages FROM added_users WHERE session = ?"
    cur.execute(query, (session, ))
    results = cur.fetchall()
    return results


@with_connection
def add_session(conn, cur, session_name):
    query = "INSERT INTO sessions (session_name) VALUES (?)"
    cur.execute(query, (session_name, ))
    conn.commit()


@with_connection
def add_ligament(conn, cur, session, channel, source, hashtag):
    query = "SELECT id FROM channels WHERE session = ? AND chat_id = ?"
    cur.execute(query, (session, channel))
    channel = cur.fetchone()
    channel_id = int(channel[0]) if channel else None
    if not channel_id:
        raise ValueError("Добавьте канал в БД")
    query = "SELECT id FROM sources WHERE session = ? AND chat_id = ?"
    cur.execute(query, (session, source))
    source = cur.fetchone()
    source_id = int(source[0]) if source else None
    if not source_id:
        raise ValueError("Добавьте источник в БД")
    query = "INSERT INTO ligaments (channel, source, hashtag, session)"\
            " VALUES (?, ?, ?, ?)"
    cur.execute(query, (channel_id, source_id, hashtag, session))
    conn.commit()
    return cur.lastrowid


@with_connection
def change_hashtag(conn, cur, id, hashtags, session):
    query = "UPDATE ligaments SET hashtag = ? WHERE id = ? AND session = ?"
    cur.execute(query, (hashtags, id, session))
    conn.commit()


@with_connection
def add_source(conn, cur, session, chat_id):
    query = "INSERT INTO sources (session, chat_id) VALUES (?, ?)"
    cur.execute(query, (session, chat_id))
    conn.commit()


@with_connection
def set_watermark(conn, cur, session, chat_id, status, text=None, color=None):
    if not (text and color):
        query = "UPDATE channels SET watermarks = ? WHERE session = ? AND chat_id = ?"
        cur.execute(query, (status, session, chat_id))
    else:
        query = "UPDATE channels SET watermarks = ?, watermark_text = ?, watermark_color = ? WHERE session = ? AND chat_id = ?"
        cur.execute(query, (status, text, color, session, chat_id))
    conn.commit()


@with_connection
def add_channel(conn, cur, session, chat_id):
    query = "INSERT INTO channels (chat_id, session, watermarks) VALUES (?, ?, ?)"
    cur.execute(query, (chat_id, session, False))
    conn.commit()


@with_connection
def get_resended_messages(conn, cur, session):
    query = "SELECT original_chat, original_message, resended_chat, resended_message FROM messages WHERE session = ? AND deleted = ?"
    cur.execute(query, (session, False))
    results = cur.fetchall()
    return results


@with_connection
def message_in_resendeds(conn, cur, original_chat, original_message, session):
    query = "SELECT resended_chat, resended_message FROM messages WHERE original_chat = ? AND original_message = ? AND session = ?"
    cur.execute(query, (
        original_chat, original_message, session
    ))
    results = cur.fetchall()
    return bool(len(results)), results


@with_connection
def save_resends(conn, cur, original_message, resended_message, session_id):
    query = "INSERT INTO messages "\
            "(original_chat, original_message, resended_chat, resended_message, session)"\
            " VALUES (?, ?, ?, ?, ?)"
    cur.execute(query, (
        original_message.chat.id, original_message.message_id,
        resended_message.chat.id, resended_message.message_id,
        session_id))
    conn.commit()


@with_connection
def get_running(conn, cur, session_name):
    query = "SELECT is_running FROM sessions WHERE session_name = ?"
    cur.execute(query, (session_name, ))
    return bool(cur.fetchone()[0])


@with_connection
def get_session_id(conn, cur, session_name):
    query = "SELECT id FROM sessions WHERE session_name = ?"
    cur.execute(query, (session_name, ))
    session_id, *is_running = cur.fetchone()
    return session_id


@with_connection
def get_channels(conn, cur, session_id):
    query = "SELECT chat_id, id, watermarks, watermark_text, watermark_color FROM channels WHERE session = ?"
    cur.execute(query, (session_id, ))
    channels = [{"channel_id": int(raw[0]),
                 "id": int(raw[1]),
                 "watermarks": bool(raw[2]),
                 'watermark_text': raw[3],
                 'watermark_color': raw[4]} for raw in cur.fetchall()]
    for channel in channels:
        channel['sources'] = channel.get('sources', [])
        channel['hashtags'] = channel.get("hashtags", {})
        query = "SELECT source, hashtag FROM ligaments WHERE channel = ? AND session = ?"
        cur.execute(query, (channel["id"], session_id))
        results = cur.fetchall()
        query = "SELECT chat_id FROM sources WHERE id = ?"
        for source_id, hashtag in results:
            cur.execute(query, (source_id, ))
            chat_id = cur.fetchone()[0]
            channel['sources'].append(int(chat_id))
            channel['hashtags'][str(chat_id)] = hashtag
    return channels


@with_connection
def get_sources(conn, cur, session_id):
    query = "SELECT chat_id FROM sources WHERE session = ?"
    cur.execute(query, (session_id, ))
    results = [ raw[0] for raw in cur.fetchall()]
    return results

