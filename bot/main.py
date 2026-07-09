import asyncio
import logging
from datetime import datetime
import os
from fpdf import FPDF

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode, ButtonStyle
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import database as db


TOKEN = "YOUR_BOT_TOKEN"
SUPERADMIN_ID = ["YOUR_TG_ID_TYPE_INT"]

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


class AdminStates(StatesGroup):
    waiting_for_op_id = State()
    waiting_for_del_op_id = State()
    waiting_for_broadcast = State()
    waiting_for_pdf_id = State()
    waiting_for_template = State()
    waiting_for_op_own_phone = State()


def btn(builder: InlineKeyboardBuilder, text: str, callback_data: str | None = None, url: str | None = None, style: ButtonStyle | None = None):
    kwargs = {"text": text}
    if callback_data is not None:
        kwargs["callback_data"] = callback_data
    if url is not None:
        kwargs["url"] = url
    if style is not None:
        kwargs["style"] = style
    builder.button(**kwargs)


@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()

    if message.from_user.id == SUPERADMIN_ID:
        role = "superadmin"
    else:
        user = await db.get_user(message.from_user.id)
        role = user[3] if user else "client"

    await db.add_user(
        user_id=message.from_user.id,
        username=message.from_user.username or "",
        full_name=message.from_user.full_name,
        role=role
    )

    user = await db.get_user(message.from_user.id)
    if user[4] == 1:
        return await message.answer("Siz botdan cheklangansiz.")

    if role == "client":
        welcome = await db.get_setting("welcome_msg") or "Assalomu alaykum! luxRaqamlar support botiga xush kelibsiz."
        builder = InlineKeyboardBuilder()
        btn(builder, "⭐ Mening Operatorlarim", "my_favorite_ops", style=ButtonStyle.PRIMARY)
        await message.answer(
            f"👋 <b>{welcome}</b>\n\n"
            "Siz o'z savolingizni yoki muammongizni yozib qoldirishingiz mumkin. "
            "Bizning operatorlarimiz tez orada sizga javob berishadi. 👇\n\n"
            "<i>Istalgan dardingizni matn ko'rinishida yozing...</i>",
            reply_markup=builder.as_markup()
        )
    else:
        await send_admin_panel(message, role)


async def send_admin_panel(message: types.Message, role: str, edit=False):
    builder = InlineKeyboardBuilder()

    text = "<i>Sizda bu panelga kirish huquqi yo'q.</i>"
    if role == "superadmin":
        btn(builder, "🟢 Operator Qo'shish", "admin_add_op", style=ButtonStyle.SUCCESS)
        btn(builder, "🔴 Operator O'chirish", "admin_del_op", style=ButtonStyle.DANGER)
        btn(builder, "📊 Operatorlar Reytingi", "admin_stats", style=ButtonStyle.PRIMARY)
        btn(builder, "📈 Tizim Statistikasi", "admin_sys_stats", style=ButtonStyle.PRIMARY)
        btn(builder, "📢 Xabar Tarqatish", "admin_broadcast", style=ButtonStyle.SUCCESS)
        btn(builder, "📥 Chatlardan PDF olish", "admin_pdf", style=ButtonStyle.PRIMARY)
        builder.adjust(2, 2, 1, 1)
        text = "👑 <b>SuperAdmin Paneliga Xush Kelibsiz!</b>\n\nQuyidagi menyudan kerakli bo'limni tanlang:"
    elif role == "operator":
        btn(builder, "📬 Ochiq Murojaatlar", "op_open_tickets", style=ButtonStyle.PRIMARY)
        btn(builder, "🔴 🔒 Faol suhbatni yakunlash", "op_end_chat", style=ButtonStyle.DANGER)
        btn(builder, "📈 Mening Statistikam", "op_stats", style=ButtonStyle.PRIMARY)
        btn(builder, "🟡 📝 Shablonlar (Tezkor)", "op_templates", style=ButtonStyle.SUCCESS)
        btn(builder, "🗂 Mening Arxivim", "op_history", style=ButtonStyle.PRIMARY)
        btn(builder, "🔄 🟢/🔴 Holatni o'zgartirish", "op_toggle_status", style=ButtonStyle.SUCCESS)
        btn(builder, "📞 Telefon raqam qo'shish", "op_add_phone", style=ButtonStyle.PRIMARY)
        builder.adjust(1, 1, 2, 2, 1)
        text = "🎧 <b>Operator Paneliga Xush Kelibsiz!</b>\n\nQuyidagi menyudan kerakli bo'limni tanlang:"

    if edit:
        await message.edit_text(text, reply_markup=builder.as_markup())
    else:
        await message.answer(text, reply_markup=builder.as_markup())


# ================= SUPER ADMIN HANDLERS =================
@dp.callback_query(F.data == "admin_add_op")
async def ask_op_id(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("🟢 <b>Yangi operator ma'lumotlarini quyidagi tartibda yuboring:</b>\n"
                                     "<code>ID Ism [Telefon]</code>\n\n"
                                     "<i>Masalan:</i>\n"
                                     "<code>123456789 Alisher</code>\n"
                                     "<code>123456789 Ali +998901234567</code>")
    await state.set_state(AdminStates.waiting_for_op_id)


@dp.message(AdminStates.waiting_for_op_id)
async def process_op_id(message: types.Message, state: FSMContext):
    parts = message.text.split()
    if not parts or not parts[0].isdigit():
        return await message.answer("⚠️ Iltimos, birinchi bo'lib faqat raqamlardan iborat ID yuboring.")

    if len(parts) < 2:
        return await message.answer("⚠️ Iltimos, operatorning ismini ham kiriting.\nMasalan: <code>123456789 Alisher</code>")

    op_id = int(parts[0])
    name = parts[1]
    phone = parts[2] if len(parts) > 2 else None

    user = await db.get_user(op_id)
    if user:
        await db.update_user_role(op_id, "operator")
        await db.update_user_name(op_id, name)
        if phone:
            await db.update_operator_phone(op_id, phone)
    else:
        await db.add_user(op_id, f"Operator_{op_id}", name, "operator")
        if phone:
            await db.update_operator_phone(op_id, phone)

    phone_text = f" Telefon: {phone}" if phone else " Telefon qo'shilmadi."
    await message.answer(f"✅ <b>{name}</b> ({op_id}) operator etib tayinlandi!{phone_text}")
    await state.clear()
    await send_admin_panel(message, "superadmin")


@dp.callback_query(F.data == "admin_del_op")
async def ask_del_op_id(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("🔴 <b>O'chiriladigan operatorning Telegram ID sini yuboring:</b>\n<i>(Faqat raqamlar)</i>")
    await state.set_state(AdminStates.waiting_for_del_op_id)


@dp.message(AdminStates.waiting_for_del_op_id)
async def process_del_op_id(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("⚠️ Iltimos, faqat raqamlardan iborat ID yuboring.")

    op_id = int(message.text)
    await db.update_user_role(op_id, "client")
    await message.answer(f"✅ <b>{op_id}</b> ID egasidan operator huquqi olib tashlandi!")
    await state.clear()
    await send_admin_panel(message, "superadmin")


@dp.callback_query(F.data == "admin_sys_stats")
async def show_sys_stats(callback: types.CallbackQuery):
    stats = await db.get_system_stats()
    text = "📈 <b>Tizim Statistikasi:</b>\n\n"
    text += f"👥 Jami foydalanuvchilar: {stats['users']}\n"
    text += f"🎧 Jami operator/adminlar: {stats['operators']}\n"
    text += f"🎫 Jami murojaatlar: {stats['tickets']}\n"
    text += f"⏳ Ochiq (kutilayotgan) murojaatlar: {stats['open_tickets']}\n"

    builder = InlineKeyboardBuilder()
    btn(builder, "🔙 Orqaga", "back_admin", style=ButtonStyle.PRIMARY)
    await callback.message.edit_text(text, reply_markup=builder.as_markup())


@dp.callback_query(F.data == "admin_stats")
async def show_all_stats(callback: types.CallbackQuery):
    ops = await db.get_operators()
    text = "📊 <b>Operatorlar Reytingi:</b>\n\n"
    for op in ops:
        score, count = op[7], op[8]
        role = "👑" if op[3] == "superadmin" else "🎧"
        text += f"{role} <b>{op[2]}</b> (ID: {op[0]})\n"
        text += f"⭐ Ballar: {score} | 👥 Ovozlar: {count}\n"
        if count > 0:
            text += f"📈 O'rtacha baho: {round(score / count, 1)} / 5\n"
        text += "〰️〰️〰️〰️〰️〰️〰️〰️\n"

    builder = InlineKeyboardBuilder()
    btn(builder, "🔙 Orqaga", "back_admin", style=ButtonStyle.PRIMARY)
    await callback.message.edit_text(text, reply_markup=builder.as_markup())


@dp.callback_query(F.data == "admin_broadcast")
async def ask_broadcast_msg(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("📢 <b>Barcha foydalanuvchilar uchun xabarni yuboring:</b>\n<i>(Rasm, video yoki matn ko'rinishida bo'lishi mumkin)</i>")
    await state.set_state(AdminStates.waiting_for_broadcast)


@dp.message(AdminStates.waiting_for_broadcast)
async def process_broadcast_msg(message: types.Message, state: FSMContext):
    clients = await db.get_all_clients()
    sent = 0
    await message.answer(f"⏳ <b>Xabar yuborish boshlandi... Kuting.</b>\nJami: {len(clients)}")
    for client_id in clients:
        try:
            await message.send_copy(client_id)
            sent += 1
            await asyncio.sleep(0.05)
        except:
            pass
    await message.answer(f"✅ <b>Xabar {sent} ta foydalanuvchiga muvaffaqiyatli yuborildi!</b>")
    await state.clear()
    await send_admin_panel(message, "superadmin")


@dp.callback_query(F.data == "admin_pdf")
async def show_pdf_options(callback: types.CallbackQuery):
    ops = await db.get_operators()
    builder = InlineKeyboardBuilder()
    for op in ops:
        btn(builder, f"👨‍💻 {op[2]}", f"pdf_op_{op[0]}", style=ButtonStyle.PRIMARY)
    btn(builder, "📂 Barcha chatlar", "pdf_op_all", style=ButtonStyle.SUCCESS)
    btn(builder, "🔙 Orqaga", "back_admin", style=ButtonStyle.PRIMARY)
    builder.adjust(1)
    await callback.message.edit_text("📥 <b>Qaysi operatorning suhbatlarini PDF qilib yuklab olamiz?</b>", reply_markup=builder.as_markup())


@dp.callback_query(F.data.startswith("pdf_op_"))
async def process_pdf_op(callback: types.CallbackQuery, state: FSMContext):
    op_id_str = callback.data.split("_")[2]
    await callback.message.edit_text("⏳ <b>PDF fayl tayyorlanmoqda, iltimos kuting...</b>")

    if op_id_str == "all":
        messages = await db.get_all_messages_for_pdf()
        title = "BARCHA OPERATORLAR CHATLARI"
    else:
        op_id = int(op_id_str)
        messages = await db.get_messages_by_operator(op_id)
        user = await db.get_user(op_id)
        op_name = user[2] if user else str(op_id)
        title = f"{op_name.upper()} CHATLARI"

    if not messages:
        builder = InlineKeyboardBuilder()
        btn(builder, "🔙 Orqaga", "admin_pdf", style=ButtonStyle.PRIMARY)
        return await callback.message.edit_text("🚫 <b>Ushbu operatorning suhbatlari topilmadi.</b>", reply_markup=builder.as_markup())

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, text=f"LUXRAQAMLAR - {title}", ln=True, align="C")
    pdf.cell(200, 10, text="-" * 50, ln=True)

    current_ticket_id = -1
    for msg in messages:
        t_id, sender, text, time_str, client_id, operator_id = msg
        if t_id != current_ticket_id:
            pdf.cell(200, 10, text="", ln=True)
            pdf.cell(200, 10, text=f"===== TICKET #{t_id} (Client: {client_id} | OP: {operator_id or 'None'}) =====", ln=True)
            current_ticket_id = t_id

        safe_text = str(text).encode("latin-1", "replace").decode("latin-1")
        pdf.cell(200, 10, text=f"[{time_str}] ID {sender}:", ln=True)
        pdf.multi_cell(0, 10, text=safe_text)
        pdf.cell(200, 5, text="", ln=True)

    filename = f"report_{op_id_str}.pdf"
    pdf.output(filename)
    file = types.FSInputFile(filename)
    await callback.message.answer_document(file)
    os.remove(filename)

    await show_pdf_options(callback)


# ================= OPERATOR HANDLERS =================
@dp.callback_query(F.data == "op_open_tickets")
async def show_open_tickets(callback: types.CallbackQuery):
    tickets = await db.get_open_tickets()
    if not tickets:
        builder = InlineKeyboardBuilder()
        btn(builder, "🔙 Orqaga", "back_admin", style=ButtonStyle.PRIMARY)
        return await callback.message.edit_text("🟢 <b>Hozircha hech kim qabul qilmagan yangi murojaatlar yo'q!</b>", reply_markup=builder.as_markup())

    text = "📬 <b>Ochiq Murojaatlar Ro'yxati:</b>\n\n"
    builder = InlineKeyboardBuilder()

    for t in tickets:
        t_id, c_id, uname, created_at = t
        client_name = f"@{uname}" if uname else f"ID: {c_id}"
        btn(builder, f"🟢 ✅ Qabul qilish #{t_id} ({client_name})", f"accept_{t_id}", style=ButtonStyle.SUCCESS)
        text += f"🎫 <b>#{t_id}</b> | 👤 {client_name}\n🕒 Vaqt: {created_at}\n\n"

    btn(builder, "🔙 Orqaga", "back_admin", style=ButtonStyle.PRIMARY)
    builder.adjust(1)
    await callback.message.edit_text(text, reply_markup=builder.as_markup())


@dp.callback_query(F.data == "op_stats")
async def show_op_stats(callback: types.CallbackQuery):
    op_id = callback.from_user.id
    stats = await db.get_operator_detailed_stats(op_id)
    fav_count = await db.get_favorites_count(op_id)

    text = f"📈 <b>Sizning shaxsiy statistikangiz:</b>\n\n"
    text += f"✅ Yopilgan chatlar (Jami): {stats['closed_tickets']}\n"
    text += f"⭐ To'plangan umumiy ballar: {stats['total_score']}\n"
    text += f"👥 Reyting qoldirgan mijozlar: {stats['ratings_count']}\n"
    text += f"🔥 O'rtacha baho: {stats['avg_score']} / 5\n"
    text += f"❤️ Sevimli operatorlarga qo'shilgan: {fav_count} marta\n"

    builder = InlineKeyboardBuilder()
    btn(builder, "🔙 Orqaga", "back_admin", style=ButtonStyle.PRIMARY)
    await callback.message.edit_text(text, reply_markup=builder.as_markup())


@dp.callback_query(F.data == "op_history")
async def op_history(callback: types.CallbackQuery):
    op_id = callback.from_user.id
    history = await db.get_operator_history(op_id)

    if not history:
        builder = InlineKeyboardBuilder()
        btn(builder, "🔙 Orqaga", "back_admin", style=ButtonStyle.PRIMARY)
        return await callback.message.edit_text("🗂 <b>Sizda arxivlangan yopilgan chatlar tarixi yo'q.</b>", reply_markup=builder.as_markup())

    text = "🗂 <b>Sizning yopilgan chatlaringiz (So'nggi 20 ta):</b>\n\n"
    for h in history:
        text += f"🎫 #{h[0]} | Mijoz ID: {h[1]} | 🕒 {h[3]}\n"

    builder = InlineKeyboardBuilder()
    btn(builder, "🔙 Orqaga", "back_admin", style=ButtonStyle.PRIMARY)
    await callback.message.edit_text(text, reply_markup=builder.as_markup())


@dp.callback_query(F.data == "op_toggle_status")
async def op_toggle_status(callback: types.CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    is_online = user[5]
    new_status = not is_online
    await db.update_operator_status(callback.from_user.id, new_status)
    status_text = "🟢 ONLINE (Tayyor)" if new_status else "🔴 OFFLINE (Band)"
    await callback.answer(f"Holatingiz o'zgardi! Endi siz: {status_text}", show_alert=True)


@dp.callback_query(F.data == "op_add_phone")
async def ask_op_own_phone(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("📞 <b>O'z telefon raqamingizni yuboring:</b>\n<i>Masalan: +998901234567</i>")
    await state.set_state(AdminStates.waiting_for_op_own_phone)


@dp.message(AdminStates.waiting_for_op_own_phone)
async def process_op_own_phone(message: types.Message, state: FSMContext):
    await db.update_operator_phone(message.from_user.id, message.text.strip())
    await message.answer(f"✅ <b>Telefon raqamingiz muvaffaqiyatli saqlandi:</b> {message.text.strip()}")
    await state.clear()
    await send_admin_panel(message, "operator")


@dp.callback_query(F.data == "op_templates")
async def op_templates(callback: types.CallbackQuery, state: FSMContext):
    templates = await db.get_templates(callback.from_user.id)
    text = "📝 <b>Sizning tezkor javob shablonlaringiz:</b>\n<i>Ushbu shablonlar orqali mijoz bilan chat qurishda tezda xabar yuborish mumkin</i>\n\n"
    builder = InlineKeyboardBuilder()

    if templates:
        for t in templates:
            text += f"🔹 {t[1]}\n"
            btn(builder, f"🟡 📤 Yuborish: {t[1][:15]}...", f"tpl_send_{t[0]}", style=ButtonStyle.PRIMARY)
    else:
        text += "<i>Hozircha shablonlar yo'q. Yangisini qo'shing.</i>\n"

    btn(builder, "🟢 ➕ Yangi Shablon", "add_template", style=ButtonStyle.SUCCESS)
    btn(builder, "🔙 Orqaga", "back_admin", style=ButtonStyle.PRIMARY)
    builder.adjust(1)
    await callback.message.edit_text(text, reply_markup=builder.as_markup())


@dp.callback_query(F.data == "add_template")
async def add_template(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("📝 <b>Yangi shablon matnini yuboring:\nMasalan: Hurmatli mijoz muammo tez orada hal qilinadi.</b>")
    await state.set_state(AdminStates.waiting_for_template)


@dp.message(AdminStates.waiting_for_template)
async def process_template(message: types.Message, state: FSMContext):
    await db.add_template(message.from_user.id, message.text)
    await message.answer("✅ <b>Shablon muvaffaqiyatli saqlandi!</b>")
    await state.clear()
    user = await db.get_user(message.from_user.id)
    await send_admin_panel(message, user[3])


@dp.callback_query(F.data.startswith("tpl_send_"))
async def send_template_to_chat(callback: types.CallbackQuery):
    tpl_id = int(callback.data.split("_")[2])

    import aiosqlite
    async with aiosqlite.connect(db.DB_NAME) as connection:
        async with connection.execute("SELECT text FROM templates WHERE id = ?", (tpl_id,)) as cursor:
            tpl = await cursor.fetchone()

    if not tpl:
        return await callback.answer("Shablon topilmadi")

    text = tpl[0]

    user = await db.get_user(callback.from_user.id)
    role = user[3]
    op_name = user[2]
    
    active_ticket = await db.get_active_ticket(callback.from_user.id, role)
    if not active_ticket:
        return await callback.answer("Hozirda sizda ochiq mijoz suhbati yo'q!", show_alert=True)

    client_id = active_ticket[1]
    ticket_id = active_ticket[0]

    await db.save_message(ticket_id, callback.from_user.id, text)
    
    builder = InlineKeyboardBuilder()
    op_phone = user[9] if len(user) > 9 and user[9] else "+998 33 000 0000"
    btn(builder, f"🔴 📞 Qo'ng'iroq qilish", f"call_phone_{callback.from_user.id}", style=ButtonStyle.DANGER)
    
    content_text = f"🎧 <b>{op_name}:</b>\n\n{text}"
    
    await bot.send_message(client_id, content_text, reply_markup=builder.as_markup())
    await bot.send_message(callback.from_user.id, f"➡️ <b>Mijozga Tezkor Yuborildi:</b>\n<i>{text}</i>")
    await callback.answer("Tezkor xabar mijozga muvaffaqiyatli yetkazildi.")


@dp.callback_query(F.data == "back_admin")
async def back_to_admin(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    user = await db.get_user(callback.from_user.id)
    if user:
        await send_admin_panel(callback.message, user[3], edit=True)
    else:
        await callback.answer("Sizning ma'lumotlaringiz topilmadi. /start buyrug'ini bering.", show_alert=True)


# ================= MESSAGING & CORE =================
@dp.message()
async def handle_all_messages(message: types.Message):
    if message.text and message.text.startswith("/"):
        return

    user = await db.get_user(message.from_user.id)
    if not user:
        await db.add_user(
            user_id=message.from_user.id,
            username=message.from_user.username or "",
            full_name=message.from_user.full_name,
            role="client"
        )
        user = await db.get_user(message.from_user.id)

    if user[4] == 1:
        return await message.answer("❌ <b>Siz botdan bloklangansiz!</b>")

    role = user[3]

    if role == "client":
        active_ticket = await db.get_active_ticket(message.from_user.id, "client")
        text_to_save = message.text or message.caption or "Media fayl"
        username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name

        if active_ticket:
            op_id = active_ticket[2]
            await db.save_message(active_ticket[0], message.from_user.id, text_to_save)

            builder = InlineKeyboardBuilder()
            btn(builder, "🟡 📝 Shablonlar", "op_templates", style=ButtonStyle.SUCCESS)
            btn(builder, "🔴 🔒 Yakunlash", "op_end_chat", style=ButtonStyle.DANGER)

            content_text = f"👤 <b>Mijoz:</b> {username}\n\n"
            if message.text:
                await bot.send_message(op_id, content_text + message.text, reply_markup=builder.as_markup())
            elif message.photo or message.video or message.document or message.voice or message.audio:
                await bot.copy_message(op_id, message.chat.id, message.message_id, caption=content_text + str(message.caption or ""), reply_markup=builder.as_markup())
            else:
                await bot.send_message(op_id, content_text + "[Qo'llab-quvvatlanmaydigan fayl]", reply_markup=builder.as_markup())
        else:
            ticket_id = await db.create_ticket(message.from_user.id)
            await db.save_message(ticket_id, message.from_user.id, text_to_save)

            operators = await db.get_operators(online_only=True)

            builder = InlineKeyboardBuilder()
            btn(builder, "🟢 ✅ Qabul qilish", f"accept_{ticket_id}", style=ButtonStyle.SUCCESS)

            content_text = f"🔔 <b>YANGI MUROJAAT</b> (T-ID: {ticket_id})\n\n👤 Mijoz: <b>{username}</b>\n\n"

            op_count = 0
            for op in operators:
                if op[3] == "superadmin":
                    continue
                try:
                    if message.text:
                        await bot.send_message(op[0], content_text + message.text, reply_markup=builder.as_markup())
                    elif message.photo or message.video or message.document or message.voice or message.audio:
                        await bot.copy_message(op[0], message.chat.id, message.message_id, caption=content_text + str(message.caption or ""), reply_markup=builder.as_markup())
                    else:
                        await bot.send_message(op[0], content_text + "[Qo'llab-quvvatlanmaydigan fayl]", reply_markup=builder.as_markup())
                    op_count += 1
                except:
                    pass

            if op_count > 0:
                await message.answer("⏳ <b>Xabaringiz navbatdagi operatorlarga yuborildi. Iltimos qisqa vaqt kuting...</b>")
            else:
                await message.answer("❗️ <b>Hozirda barcha operatorlar oflayn yoki band.</b> Xabaringiz navbatga qabul qilindi.")

    elif role in ["operator", "superadmin"]:
        active_ticket = await db.get_active_ticket(message.from_user.id, "operator")
        if active_ticket:
            client_id = active_ticket[1]
            op_name = message.from_user.full_name
            text_to_save = message.text or message.caption or "Media fayl"

            await db.save_message(active_ticket[0], message.from_user.id, text_to_save)

            builder = InlineKeyboardBuilder()
            op_phone_text = user[9] if len(user) > 9 and user[9] else "+998 33 000 0000"
            btn(builder, f"🔴 📞 Qo'ng'iroq qilish", f"call_phone_{message.from_user.id}", style=ButtonStyle.DANGER)

            content_text = f"🎧 <b>{op_name}:</b>\n\n"
            if message.text:
                await bot.send_message(client_id, content_text + message.text, reply_markup=builder.as_markup())
            elif message.photo or message.video or message.document or message.voice or message.audio:
                await bot.copy_message(client_id, message.chat.id, message.message_id, caption=content_text + str(message.caption or ""), reply_markup=builder.as_markup())
            else:
                await bot.send_message(client_id, content_text + "[Qo'llab-quvvatlanmaydigan fayl]", reply_markup=builder.as_markup())
        else:
            await message.answer("⚠️ <b>Sizda hozirda ochiq mijoz suhbati yo'q.</b> Yangi murojaatlarni qabul qiling degan xabar kelishini kuting.")


@dp.callback_query(F.data.startswith("accept_"))
async def accept_ticket(callback: types.CallbackQuery):
    ticket_id = int(callback.data.split("_")[1])
    operator_id = callback.from_user.id

    active_ticket = await db.get_active_ticket(operator_id, "operator")
    if active_ticket:
        return await callback.answer("⚠️ Avval joriy ochiq suhbatni yakunlang!", show_alert=True)

    success = await db.take_ticket(ticket_id, operator_id)
    if success:
        await callback.message.edit_text(f"{callback.message.text}\n\n✅ <b>Siz qabul qildingiz. Mijoz bn chat ochildi.</b>\nEndi javob yozishingiz mumkin.")

        builder = InlineKeyboardBuilder()
        btn(builder, "🔴 🔒 Murojaatni Yakunlash", f"client_end_{ticket_id}", style=ButtonStyle.DANGER)

        ticket_info = await db.get_ticket(ticket_id)
        if ticket_info:
            await bot.send_message(
                ticket_info[1],
                f"✅ <b>Operator murojaatingizni qabul qildi!</b>\nEndi qancha vaqt kutsangiz shuncha javob tezlashadi, savollaringizni yozib boring.",
                reply_markup=builder.as_markup()
            )
    else:
        await callback.message.edit_text(f"{callback.message.text}\n\n❌ <b>Ushbu murojaat allaqachon boshqa operator tomonidan qabul qilingan yoki yopilgan.</b>")


@dp.callback_query(F.data == "op_end_chat")
async def op_end_chat(callback: types.CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    active_ticket = await db.get_active_ticket(callback.from_user.id, user[3])

    if not active_ticket:
        return await callback.answer("Sizda faol suhbat mavjud emas!", show_alert=True)

    await execute_close_ticket(active_ticket[0], active_ticket[1], active_ticket[2], callback)


@dp.callback_query(F.data.startswith("client_end_"))
async def client_end_chat(callback: types.CallbackQuery):
    ticket_id = int(callback.data.split("_")[2])
    ticket = await db.get_ticket(ticket_id)

    if not ticket or ticket[3] == "closed":
        return await callback.answer("Ushbu suhbat allaqachon yopilgan.", show_alert=True)

    await execute_close_ticket(ticket_id, ticket[1], ticket[2], callback)


async def execute_close_ticket(ticket_id, client_id, op_id, callback):
    await db.close_ticket(ticket_id)
    await callback.message.delete()

    if op_id:
        try:
            await bot.send_message(op_id, f"🔴 <b>Mijoz bilan suhbat muvaffaqiyatli yopildi.</b> (T-ID: {ticket_id})\nEndi yangi murojaatlarni kuting.")
        except:
            pass

    builder = InlineKeyboardBuilder()
    btn(builder, "🔥 Juda Zo'r", f"rate_{ticket_id}_5_{op_id}", style=ButtonStyle.SUCCESS)
    btn(builder, "👍 O'rtacha", f"rate_{ticket_id}_3_{op_id}", style=ButtonStyle.PRIMARY)
    btn(builder, "👎 Yoqimsiz", f"rate_{ticket_id}_1_{op_id}", style=ButtonStyle.DANGER)
    btn(builder, "⭐ Mening operatorim ro'yxatiga qo'shish", f"fav_{op_id}", style=ButtonStyle.SUCCESS)
    builder.adjust(3, 1)

    try:
        await bot.send_message(
            client_id,
            "🤝 <b>Murojaat yopildi!</b>\n\nIltimos, operatorimiz bilan suhbatingiz va yordamni baholang:",
            reply_markup=builder.as_markup()
        )
    except:
        pass


@dp.callback_query(F.data.startswith("rate_"))
async def rate_operator(callback: types.CallbackQuery):
    _, ticket_id, score, op_id = callback.data.split("_")
    ticket_id, score = int(ticket_id), int(score)

    if op_id != "None":
        success = await db.save_rating(ticket_id, callback.from_user.id, int(op_id), score)
        if success:
            await callback.message.edit_text(f"{callback.message.text}\n\n✅ <b>Bahoingiz qabul qilindi!</b>\nYangi savol tugilishi bn yana yozishingiz mumkin.")
        else:
            await callback.message.edit_text("⚠️ <b>Siz bu chat uchun baho berib bo'lgansiz.</b> Rahmat!")


@dp.callback_query(F.data.startswith("fav_"))
async def add_fav(callback: types.CallbackQuery):
    op_id = callback.data.split("_")[1]
    if op_id != "None":
        await db.add_favorite_operator(callback.from_user.id, int(op_id))
        await callback.answer("⭐ Sevimli operatorlar ro'yxatiga muvaffaqiyatli qoshildi!", show_alert=True)
    else:
        await callback.answer("Kechirasiz, suhbat to'liq ulanmagan.", show_alert=True)





@dp.callback_query(F.data.startswith("call_phone_"))
async def call_phone_handler(callback: types.CallbackQuery):
    op_id = int(callback.data.split("_")[2])
    user = await db.get_user(op_id)
    if user and len(user) > 9 and user[9]:
        phone = user[9]
    else:
        phone = "+998 33 000 0000"
    
    await bot.send_contact(
        chat_id=callback.from_user.id,
        phone_number=phone,
        first_name=user[2] if user and len(user) > 2 else "Operator"
    )
    await callback.message.answer(f"📞 <b>Qo'ng'iroq qilish uchun yuqoridagi raqamdan foydalaning.</b>")
    await callback.answer()


@dp.callback_query(F.data == "my_favorite_ops")
async def show_my_favorite_ops(callback: types.CallbackQuery):
    ops = await db.get_favorite_operators(callback.from_user.id)
    if not ops:
        return await callback.answer("⭐ Sizda hozircha sevimli operatorlar saqlanmagan.", show_alert=True)
    
    builder = InlineKeyboardBuilder()
    for op in ops:
        op_id, full_name, phone = op
        btn(builder, f"👤 {full_name}", f"myfavop_{op_id}")
    builder.adjust(1)
    await callback.message.answer("<b>⭐ Sevimli operatorlaringiz ro'yxati:</b>", reply_markup=builder.as_markup())
    await callback.answer()


@dp.callback_query(F.data.startswith("myfavop_"))
async def handle_fav_op_click(callback: types.CallbackQuery):
    op_id = int(callback.data.split("_")[1])
    user = await db.get_user(op_id)
    if not user:
        return await callback.answer("⚠️ Operator topilmadi.", show_alert=True)
    
    phone = user[9] if len(user) > 9 and user[9] else "+998 33 000 0000"
    await bot.send_contact(
        chat_id=callback.from_user.id,
        phone_number=phone,
        first_name=user[2] if len(user) > 2 else "Operator"
    )
    await callback.message.answer("📞 <b>Siz tanlagan operator raqami!</b>")
    await callback.answer()

async def main():
    await db.init_db()
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
