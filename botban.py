import asyncio
import sqlite3
import logging
import re
from telethon import TelegramClient, events, Button
from telethon.tl.types import ChannelParticipantsAdmins
from langdetect import detect, LangDetectException

API_ID = 29068923
API_HASH = '72035fc7d10fc5bd2847e23ecad1a850'
BOT_TOKEN = '7785664924:AAFIYaUND55b2-hHhJ0zSiM1nD02BpZj6l0'
DB_PATH = 'bot.db'
SUPER_ADMIN = 'Leonardo2004'
logging.basicConfig(level=logging.INFO)



# Alfabetos permitidos: Latin (incluye inglés, español, etc.), Han (chino), Hiragana/Katakana (japonés)
ALLOWED_PATTERNS = re.compile(r'[\u0000-\u007F\u0080-\u00FF\u0100-\u017F\u0180-\u024F\u0250-\u02AF\u0300-\u036F\u0370-\u03FF\u0400-\u04FF\u0500-\u052F\u1E00-\u1EFF\u2E80-\u2FD5\u3400-\u4DBF\u4E00-\u9FFF\u3040-\u309F\u30A0-\u30FF]+')

# Función simplificada para detectar cualquier carácter prohibido
def contains_forbidden(text: str) -> bool:
    # Si hay algún carácter que NO esté en los rangos permitidos → prohibido
    return not bool(ALLOWED_PATTERNS.fullmatch(text))

# === DB ===
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS admins(user_id INTEGER PRIMARY KEY, username TEXT UNIQUE)')
    c.execute('CREATE TABLE IF NOT EXISTS free_users(user_id INTEGER PRIMARY KEY, username TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS banned_words(word TEXT PRIMARY KEY)')
    conn.commit()
    conn.close()

init_db()

# === Utilidades DB ===
def add_admin(uid, uname=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO admins(user_id, username) VALUES(?,?)", (uid, uname))
    conn.commit()
    conn.close()

def remove_admin(uid):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM admins WHERE user_id=? AND username!=?", (uid, SUPER_ADMIN))
    conn.commit()
    conn.close()

def get_admins():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id FROM admins")
    return [row[0] for row in c.fetchall()]

def is_admin(uid):
    return uid in get_admins()

def add_free(uid, uname=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO free_users(user_id, username) VALUES(?,?)", (uid, uname))
    conn.commit()
    conn.close()

def remove_free(uid):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM free_users WHERE user_id=?", (uid,))
    conn.commit()
    conn.close()

def get_free():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id FROM free_users")
    return [row[0] for row in c.fetchall()]

def is_free(uid):
    return uid in get_free()

def add_word(w):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO banned_words(word) VALUES(?)", (w.lower(),))
    conn.commit()
    conn.close()

def remove_word(w):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM banned_words WHERE word=?", (w.lower(),))
    conn.commit()
    conn.close()

def get_words():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT word FROM banned_words")
    return [row[0] for row in c.fetchall()]

# === Misc ===
def detect_lang(text):
    try:
        return detect(text) in {'ru', 'hi'}
    except LangDetectException:
        return False

# === Cliente ===
client = TelegramClient('bot_id', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
states = {}

# === Menú ===
async def menu(event):
    if not is_admin(event.sender_id):
        return
    await event.respond(
        "🛡️ Panel Admin:",
        buttons=[
            [Button.inline("➕ Añadir palabra", b"addword")],
            [Button.inline("➖ Quitar palabra", b"delword")],
            [Button.inline("📋 Ver palabras", b"listwords")],
            [Button.inline("✅ Añadir usuario libre", b"addfree")],
            [Button.inline("❌ Quitar usuario libre", b"removefree")],
            [Button.inline("👥 Ver usuarios libres", b"listfree")],
            [Button.inline("👑 Añadir admin", b"addadmin")],
            [Button.inline("👑 Quitar admin", b"removeadmin")],
            [Button.inline("📋 Ver admins", b"listadmins")],
            [Button.inline("❓ Ayuda", b"help")]
        ]
    )

@client.on(events.NewMessage(pattern=r'^/(start|help)$'))
async def start_help(event):
    if is_admin(event.sender_id):
        await menu(event)

# === Callbacks ===
@client.on(events.CallbackQuery)
async def cb(event):
    uid = event.sender_id
    if not is_admin(uid):
        return
    data = event.data.decode()
    if data == 'menu':
        states.pop(uid, None)
        await menu(event)
    elif data == 'cancel':
        states.pop(uid, None)
        await menu(event)
    elif data in {'addword', 'delword', 'addfree', 'removefree', 'addadmin', 'removeadmin'}:
        states[uid] = data
        msg = {
            'addword': "✏️ Escribe la palabra a banear:",
            'delword': "✏️ Escribe la palabra a quitar:",
            'addfree': "✏️ Escribe el ID del usuario libre:",
            'removefree': "✏️ Escribe el ID del usuario a quitar de libres:",
            'addadmin': "✏️ Escribe el ID del nuevo admin:",
            'removeadmin': "✏️ Escribe el ID del admin a quitar:"
        }[data]
        await event.edit(msg, buttons=[Button.inline("Cancelar", b"cancel")])
    elif data == 'listwords':
        words = get_words()
        txt = "📋 Palabras:\n" + "\n".join(words) if words else "Vacío"
        await event.edit(txt, buttons=[Button.inline("🔙 Menú", b"menu")])
    elif data == 'listfree':
        free = get_free()
        txt = "👥 Libres:\n" + "\n".join(map(str, free)) if free else "Vacío"
        await event.edit(txt, buttons=[Button.inline("🔙 Menú", b"menu")])
    elif data == 'listadmins':
        admins = get_admins()
        txt = "👑 Admins:\n" + "\n".join(map(str, admins)) if admins else "Vacío"
        await event.edit(txt, buttons=[Button.inline("🔙 Menú", b"menu")])
    elif data == 'help':
        txt = (
            "📖 **Ayuda**\n\n"
            "• Solo admins pueden usar el bot.\n"
            "• Leonardo2004 es super-admin.\n"
            "• Usa ID (número) para agregar/quitar."
        )
        await event.edit(txt, buttons=[Button.inline("🔙 Menú", b"menu")])

@client.on(events.NewMessage(pattern=r'^/checkperm$'))
async def check_perm(event):
    me = await event.client.get_me()
    bot_member = await event.client.get_permissions(event.chat_id, me.id)
    await event.reply(
        f"Permisos actuales:\n"
        f"DeleteMessages: {bot_member.delete_messages}\n"
        f"RestrictMembers: {bot_member.ban_users}"
    )
    
# === Comando /syncadmins ===
@client.on(events.NewMessage(pattern=r'^/syncadmins$'))
async def sync_admins(event):
    if not event.is_group:
        await event.reply("Este comando solo funciona en grupos.")
        return
    if not is_admin(event.sender_id):
        return  # silencio total

    chat_admins = await event.client.get_participants(
        event.chat_id,
        filter=ChannelParticipantsAdmins
    )
    added = []
    for admin in chat_admins:
        if admin.bot or admin.deleted:
            continue
        if admin.username and is_super_admin(admin.username):
            continue  # ignorar super-admin
        add_admin(admin.id, admin.username)
        added.append(str(admin.id))
    await event.reply(
        f"✅ Administradores sincronizados:\n{', '.join(added) if added else 'Ninguno nuevo'}"
    )

def is_super_admin(username):
    return username and username.lower() == SUPER_ADMIN.lower()
    
# === Texto privado ===
@client.on(events.NewMessage(func=lambda e: e.is_private and is_admin(e.sender_id)))
async def text_handler(event):
    uid = event.sender_id
    state = states.get(uid)
    if not state:
        return
    value = event.text.strip()
    if value.isdigit():
        target_id = int(value)
    else:
        await event.respond("❗️ Debes enviar un número (ID).")
        return
    if state == 'addword':
        add_word(value)
        await event.respond("✅ Palabra añadida.", buttons=[Button.inline("🔙 Menú", b"menu")])
    elif state == 'delword':
        remove_word(value)
        await event.respond("✅ Palabra eliminada.", buttons=[Button.inline("🔙 Menú", b"menu")])
    elif state == 'addfree':
        add_free(target_id)
        await event.respond("✅ Usuario libre añadido.", buttons=[Button.inline("🔙 Menú", b"menu")])
    elif state == 'removefree':
        remove_free(target_id)
        await event.respond("✅ Usuario libre quitado.", buttons=[Button.inline("🔙 Menú", b"menu")])
    elif state == 'addadmin':
        if target_id == event.sender_id:
            await event.respond("❌ No puedes auto-promover.")
        else:
            add_admin(target_id)
            await event.respond("✅ Admin añadido.", buttons=[Button.inline("🔙 Menú", b"menu")])
    elif state == 'removeadmin':
        if target_id == event.sender_id:
            await event.respond("❌ No puedes auto-remover.")
        else:
            remove_admin(target_id)
            await event.respond("✅ Admin quitado.", buttons=[Button.inline("🔙 Menú", b"menu")])
    states.pop(uid, None)

# --- Función para extraer texto de cualquier media ---
def extract_text_from_media(message) -> str:
    text_parts = []
    # Caption
    if message.message:
        text_parts.append(message.message)
    # Título del archivo (si existe)
    if message.media and hasattr(message.media, 'document') and message.media.document:
        for attr in message.media.document.attributes:
            if hasattr(attr, 'file_name'):
                text_parts.append(attr.file_name)
            if hasattr(attr, 'title'):
                text_parts.append(attr.title)
    return " ".join(text_parts)

# --- Handler ÚNICO para mensajes + media ---
@client.on(events.NewMessage(func=lambda e: e.is_group and not is_admin(e.sender_id)))
async def ban_media(event):
    uid = event.sender_id
    chat_id = event.chat_id
    texto_completo = extract_text_from_media(event.message)

    # 1. Palabras prohibidas
    for w in get_words():
        if w.lower() in texto_completo.lower():
            razon = f"Palabra prohibida: {w}"
            break
    else:
        # 2. Idioma/caracteres prohibidos
        if contains_forbidden(texto_completo):
            razon = "Descripción/caracteres no latinos/chinos/japoneses"
        else:
            return  # todo OK

    try:
        await event.delete()
    except Exception as e:
        logging.warning(f"Delete error: {e}")

    try:
        await client.edit_permissions(chat_id, uid, view_messages=False)
        user = await event.get_user()
        await event.respond(
            f"🚫 @{user.username} baneado.\n📄 Razón: {razon}",
            buttons=[[Button.inline("🔄 Desbanear", f"unban_{uid}")]]
        )
    except Exception as e:
        logging.warning(f"Ban error: {e}")

# === Nuevo miembro ===
@client.on(events.ChatAction)
async def ban_join(event):
    if not event.is_group or not (event.user_joined or event.user_added):
        return
    uid = event.user_id
    if is_admin(uid) or is_free(uid):
        return
    user = await event.get_user()
    nombre = f"{user.first_name or ''} {user.last_name or ''}".strip()
    if detect_lang(nombre):
        await client.edit_permissions(event.chat_id, uid, view_messages=False)
        await event.reply(
            f"🚫 @{user.username} baneado.\n📄 Razón: Nombre no permitido.",
            buttons=[[Button.inline("🔄 Desbanear", f"unban_{uid}")]]
        )
# === Desbanear callback ===
@client.on(events.CallbackQuery())
async def unban_cb(event):
    if not is_admin(event.sender_id):
        return
    data = event.data.decode()
    if data.startswith('unban_'):
        uid = int(data.split('_')[1])
        try:
            await client.edit_permissions(event.chat_id, uid, view_messages=True)
            await event.edit("✅ Desbaneado.", buttons=[Button.inline("🔙 Menú", b"menu")])
        except:
            await event.edit("❌ Error al desbanear.", buttons=[Button.inline("🔙 Menú", b"menu")])

# === Inicio ===
if __name__ == '__main__':
    print("🤖 Bot con ID-only iniciado...")
    # Registrar super-admin
    try:
        super = client.loop.run_until_complete(client.get_entity(SUPER_ADMIN))
        add_admin(super.id, SUPER_ADMIN)
    except:
        pass
    client.run_until_disconnected()