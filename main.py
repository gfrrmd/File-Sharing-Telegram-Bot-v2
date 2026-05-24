import os
import string
import random
import asyncio
from pyrogram import Client, filters
from pyrogram.enums import ChatMemberStatus
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatMemberUpdated
from pyrogram.errors import UserNotParticipant, ChatAdminRequired, ChannelPrivate

# ===================== KONFIGURASI =====================
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))
DB_CHANNEL = int(os.environ.get("DB_CHANNEL"))

# Force Join Channels — pisah koma jika lebih dari 1
# Contoh: -1001234567890,-1009876543210
RAW_CHANNELS = os.environ.get("FORCE_JOIN_CHANNELS", "")
FORCE_JOIN_CHANNELS = [
    int(ch.strip()) for ch in RAW_CHANNELS.split(",") if ch.strip()
]

app = Client("file_sharing_bot_v2", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# db_links : { code: message_id_di_db_channel }
# db_sent  : { user_id: [msg_id_1, msg_id_2, ...] } ← log semua media yang dikirim ke user
db_links = {}
db_sent  = {}


def generate_code(length=10):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))


def log_sent(user_id: int, msg_id: int):
    """Catat message_id media yang dikirim ke user."""
    if user_id not in db_sent:
        db_sent[user_id] = []
    db_sent[user_id].append(msg_id)


async def revoke_all_media(client, user_id: int):
    """
    Hapus semua media yang pernah dikirim bot ke user.
    Dibagi per batch 100 (batas Telegram API per request).
    """
    msg_ids = db_sent.pop(user_id, [])
    if not msg_ids:
        return 0

    deleted = 0
    for i in range(0, len(msg_ids), 100):
        batch = msg_ids[i:i + 100]
        try:
            await client.delete_messages(chat_id=user_id, message_ids=batch)
            deleted += len(batch)
        except Exception:
            pass
        await asyncio.sleep(0.3)

    return deleted


# ===================== FORCE JOIN LOGIC =====================

async def check_force_join(client, user_id):
    """Kembalikan list channel_id yang BELUM di-join oleh user."""
    not_joined = []
    for channel_id in FORCE_JOIN_CHANNELS:
        try:
            member = await client.get_chat_member(channel_id, user_id)
            if member.status not in (
                ChatMemberStatus.MEMBER,
                ChatMemberStatus.ADMINISTRATOR,
                ChatMemberStatus.OWNER
            ):
                not_joined.append(channel_id)
        except UserNotParticipant:
            not_joined.append(channel_id)
        except (ChatAdminRequired, ChannelPrivate):
            not_joined.append(channel_id)
        except Exception:
            not_joined.append(channel_id)
    return not_joined


async def build_join_buttons(client, not_joined_channels, original_code=None):
    """Tombol join langsung (tanpa approval) per channel."""
    buttons = []
    for ch_id in not_joined_channels:
        title = "Channel"
        invite = None
        try:
            chat = await client.get_chat(ch_id)
            title = chat.title
        except Exception:
            pass
        try:
            # Link langsung join, tanpa approval
            invite = await client.export_chat_invite_link(ch_id)
        except Exception:
            invite = f"https://t.me/c/{str(ch_id).replace('-100', '')}"

        buttons.append([
            InlineKeyboardButton(f"🔔 Join {title}", url=invite)
        ])

    callback_data = f"check_join:{original_code}" if original_code else "check_join:none"
    buttons.append([
        InlineKeyboardButton("✅ Sudah Join, Coba Lagi", callback_data=callback_data)
    ])
    return InlineKeyboardMarkup(buttons)


# ===================== AUTO REVOKE: DETEKSI USER KELUAR CHANNEL =====================

@app.on_chat_member_updated()
async def on_member_updated(client, update: ChatMemberUpdated):
    """Deteksi user yang keluar / di-kick dari force join channel."""
    if not FORCE_JOIN_CHANNELS or update.chat.id not in FORCE_JOIN_CHANNELS:
        return

    new_status = update.new_chat_member.status if update.new_chat_member else None
    old_status = update.old_chat_member.status if update.old_chat_member else None

    was_active = old_status in (ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    now_gone   = new_status in (ChatMemberStatus.LEFT, ChatMemberStatus.BANNED)

    if not (was_active and now_gone):
        return

    user = update.new_chat_member.user
    user_id = user.id

    # Hapus semua media yang pernah dikirim bot ke user ini
    deleted_count = await revoke_all_media(client, user_id)

    # Notifikasi ke user
    try:
        await client.send_message(
            chat_id=user_id,
            text=(
                "⛔ **Akses Dicabut!**\n\n"
                "Kamu telah keluar dari channel yang diperlukan.\n"
                f"**{deleted_count} media** telah dihapus dari chat ini.\n\n"
                "Jika ingin mengakses kembali, silakan join ulang channel dan minta link baru ke Admin."
            )
        )
    except Exception:
        pass

    # Notifikasi ke admin
    try:
        username = f"@{user.username}" if user.username else user.first_name
        channel_name = update.chat.title or str(update.chat.id)
        await client.send_message(
            chat_id=ADMIN_ID,
            text=(
                "🔔 **Notif Auto Revoke**\n\n"
                f"👤 User: {username} (`{user_id}`)\n"
                f"📢 Keluar dari: **{channel_name}**\n"
                f"🗑️ Media dihapus: **{deleted_count} pesan**"
            )
        )
    except Exception:
        pass


# ===================== USER INTERFACE =====================

@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    if len(message.command) > 1:
        code = message.command[1]
        msg_id = db_links.get(code)

        if msg_id:
            if FORCE_JOIN_CHANNELS:
                not_joined = await check_force_join(client, message.from_user.id)
                if not_joined:
                    buttons = await build_join_buttons(client, not_joined, original_code=code)
                    await message.reply_text(
                        "⚠️ **Akses Ditolak!**\n\n"
                        "Kamu harus join semua channel berikut terlebih dahulu "
                        "untuk bisa mengakses file ini:",
                        reply_markup=buttons
                    )
                    return

            # Sudah join semua → kirim file & catat ke db_sent
            try:
                sent = await client.copy_message(
                    chat_id=message.chat.id,
                    from_chat_id=DB_CHANNEL,
                    message_id=msg_id,
                    protect_content=True
                )
                log_sent(message.from_user.id, sent.id)
            except Exception:
                await message.reply_text("❌ Gagal mengambil file. Pastikan bot adalah Admin di Channel Database.")
        else:
            await message.reply_text("❌ Link kadaluwarsa atau tidak valid.")

    else:
        if message.from_user.id == ADMIN_ID:
            await message.reply_text(
                "👋 **Halo Admin!**\n\nKirim foto, video, atau dokumen ke sini "
                "untuk diubah menjadi link sharing otomatis.\n\n"
                f"📌 Force Join aktif untuk **{len(FORCE_JOIN_CHANNELS)} channel**.\n"
                f"📦 Total user tracked: **{len(db_sent)}**"
            )
        else:
            await message.reply_text(
                "🙏 **Selamat Datang!**\n\nBot ini hanya bisa digunakan jika kamu memiliki "
                "link file yang sah dari Admin."
            )


# ===================== CALLBACK: CEK ULANG JOIN =====================

@app.on_callback_query(filters.regex(r"^check_join:.+"))
async def recheck_join(client, callback_query):
    data = callback_query.data
    code = data.split(":", 1)[1] if ":" in data else "none"
    user_id = callback_query.from_user.id

    not_joined = await check_force_join(client, user_id)

    if not_joined:
        await callback_query.answer("❌ Kamu belum join semua channel!", show_alert=True)
        buttons = await build_join_buttons(client, not_joined, original_code=code)
        try:
            await callback_query.message.edit_reply_markup(reply_markup=buttons)
        except Exception:
            pass
    else:
        await callback_query.answer("✅ Verifikasi berhasil!", show_alert=True)
        if code != "none":
            msg_id = db_links.get(code)
            if msg_id:
                try:
                    await callback_query.message.edit_text("✅ Akses diizinkan! Mengirim file...")
                    sent = await client.copy_message(
                        chat_id=callback_query.message.chat.id,
                        from_chat_id=DB_CHANNEL,
                        message_id=msg_id,
                        protect_content=True
                    )
                    log_sent(callback_query.from_user.id, sent.id)
                except Exception as e:
                    await callback_query.message.edit_text(f"❌ Gagal mengirim file: {str(e)}")
            else:
                await callback_query.message.edit_text("❌ Link sudah kadaluwarsa. Minta link baru ke Admin.")
        else:
            await callback_query.message.edit_text("✅ Kamu sudah terverifikasi! Silakan klik link filenya lagi.")


# ===================== ADMIN INTERFACE (UPLOAD) =====================

@app.on_message(filters.private & filters.user(ADMIN_ID) & ~filters.command(["start", "help"]))
async def admin_upload_handler(client, message):
    try:
        stored_msg = await message.copy(DB_CHANNEL)
        code = generate_code()
        db_links[code] = stored_msg.id

        bot = await client.get_me()
        link = f"https://t.me/{bot.username}?start={code}"

        await message.reply_text(
            f"✅ **Berhasil Disimpan!**\n\n"
            f"🔗 **Link Sharing:**\n`{link}`\n\n"
            f"⚠️ *File diproteksi (Anti-Forward & Anti-Screenshot)*",
            disable_web_page_preview=True
        )
    except Exception as e:
        await message.reply_text(f"❌ Gagal upload: {str(e)}")


# Tolak upload jika bukan admin
@app.on_message(filters.private & ~filters.user(ADMIN_ID) & (filters.document | filters.video | filters.photo))
async def non_admin_reject(client, message):
    await message.reply_text("🚫 **Akses Ditolak.** Kamu tidak punya izin untuk upload file ke bot ini.")


app.run()
