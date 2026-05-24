import os
import string
import random
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant

# ===================== KONFIGURASI =====================
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))
DB_CHANNEL = int(os.environ.get("DB_CHANNEL"))

# ✅ Force Join Channels — isi dengan ID channel yang wajib di-join
# Bisa 1 atau lebih, contoh: [-1001234567890, -1009876543210]
RAW_CHANNELS = os.environ.get("FORCE_JOIN_CHANNELS", "")
FORCE_JOIN_CHANNELS = [
    int(ch.strip()) for ch in RAW_CHANNELS.split(",") if ch.strip()
]

app = Client("file_sharing_bot_v2", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Database sederhana dalam memori
db_links = {}


def generate_code(length=10):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))


# ===================== FORCE JOIN LOGIC =====================

async def check_force_join(client, user_id):
    """Kembalikan list channel_id yang BELUM di-join oleh user."""
    not_joined = []
    for channel_id in FORCE_JOIN_CHANNELS:
        try:
            member = await client.get_chat_member(channel_id, user_id)
            if member.status in ("kicked", "left"):
                not_joined.append(channel_id)
        except UserNotParticipant:
            not_joined.append(channel_id)
        except Exception:
            pass  # skip jika bot bukan admin di channel tersebut
    return not_joined


async def build_join_buttons(client, not_joined_channels, original_code=None):
    """Buat InlineKeyboardMarkup dengan tombol join untuk tiap channel."""
    buttons = []
    for ch_id in not_joined_channels:
        try:
            chat = await client.get_chat(ch_id)
            try:
                invite = await client.export_chat_invite_link(ch_id)
            except Exception:
                invite = f"https://t.me/c/{str(ch_id).replace('-100', '')}"
            buttons.append([
                InlineKeyboardButton(f"🔔 Join {chat.title}", url=invite)
            ])
        except Exception as e:
            buttons.append([
                InlineKeyboardButton(f"🔔 Join Channel", url=f"https://t.me/c/{str(ch_id).replace('-100', '')}")
            ])

    # Tombol cek ulang, bawa kode file agar bisa langsung kirim setelah join
    callback_data = f"check_join:{original_code}" if original_code else "check_join:none"
    buttons.append([
        InlineKeyboardButton("✅ Sudah Join, Coba Lagi", callback_data=callback_data)
    ])
    return InlineKeyboardMarkup(buttons)


# ===================== USER INTERFACE =====================

@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    if len(message.command) > 1:
        code = message.command[1]
        msg_id = db_links.get(code)

        if msg_id:
            # Cek force join terlebih dahulu
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

            # Sudah join semua → kirim file
            try:
                await client.copy_message(
                    chat_id=message.chat.id,
                    from_chat_id=DB_CHANNEL,
                    message_id=msg_id,
                    protect_content=True
                )
            except Exception as e:
                await message.reply_text("❌ Gagal mengambil file. Pastikan bot adalah Admin di Channel Database.")
        else:
            await message.reply_text("❌ Link kadaluwarsa atau tidak valid.")

    else:
        if message.from_user.id == ADMIN_ID:
            await message.reply_text(
                "👋 **Halo Admin!**\n\nKirim foto, video, atau dokumen ke sini "
                "untuk diubah menjadi link sharing otomatis.\n\n"
                f"📌 Force Join aktif untuk **{len(FORCE_JOIN_CHANNELS)} channel**."
            )
        else:
            await message.reply_text(
                "🙏 **Selamat Datang!**\n\nBot ini hanya bisa digunakan jika kamu memiliki "
                "link file yang sah dari Admin."
            )


# ===================== CALLBACK: CEK ULANG JOIN =====================

@app.on_callback_query(filters.regex(r"^check_join:.+"))
async def recheck_join(client, callback_query):
    data = callback_query.data  # format: "check_join:CODE"
    code = data.split(":", 1)[1] if ":" in data else "none"
    user_id = callback_query.from_user.id

    not_joined = await check_force_join(client, user_id)

    if not_joined:
        buttons = await build_join_buttons(client, not_joined, original_code=code)
        await callback_query.answer("❌ Kamu belum join semua channel!", show_alert=True)
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
                    await client.copy_message(
                        chat_id=callback_query.message.chat.id,
                        from_chat_id=DB_CHANNEL,
                        message_id=msg_id,
                        protect_content=True
                    )
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
