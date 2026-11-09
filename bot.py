import asyncio
import re
import time
from collections import defaultdict
from datetime import datetime
from html import escape

from telegram import BotCommand, ReplyKeyboardRemove, Update
from telegram.constants import ChatAction, ParseMode
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import keyboards as kb
import storage
from config import BOT_TOKEN, DJEZZY_PROXY_URL, OFFERS_LIST, PORT, WEBHOOK_URL, log
from djezzy_client import DjezzyClient, check_proxy_ip

OTP_RESEND_COOLDOWN = 60
OTP_MAX_ATTEMPTS = 5
LINE = "━━━━━━━━━━━━━━"

_user_locks: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)


# =======================================================
# 🧰 أدوات مساعدة
# =======================================================
def card(title: str, body: str = "", footer: str = "") -> str:
    text = f"<b>{title}</b>\n{LINE}"
    if body:
        text += f"\n{escape(body.strip())}"
    if footer:
        text += f"\n{LINE}\n<i>{footer}</i>"
    return text


def now_str() -> str:
    return datetime.now().strftime("%H:%M")


def mask_phone(phone: str) -> str:
    p = str(phone)
    return f"{p[:4]}••••{p[-2:]}" if len(p) > 6 else p


def clean_phone(raw: str) -> str | None:
    p = re.sub(r"\D", "", raw or "")
    if p.startswith("213") and len(p) == 12:
        p = "0" + p[3:]
    return p if re.fullmatch(r"\d{9,10}", p) else None


async def show(update: Update, text: str, markup=None) -> None:
    """يعدّل نفس الرسالة عند الضغط على زر، أو يرسل رسالة جديدة عند كتابة أمر."""
    query = update.callback_query
    if query and query.message:
        try:
            await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)
            return
        except BadRequest as e:
            if "not modified" in str(e).lower():
                return
    await update.effective_chat.send_message(text, parse_mode=ParseMode.HTML, reply_markup=markup)


async def run_task(update: Update, context: ContextTypes.DEFAULT_TYPE, loading: str, task, render) -> None:
    """يعرض رسالة انتظار، ينفّذ الطلب، ثم يستبدلها بالنتيجة. ويمنع تكرار الطلب أثناء التنفيذ."""
    uid = update.effective_user.id
    lock = _user_locks[uid]
    if lock.locked():
        if update.callback_query:
            await update.callback_query.answer("⏳ يوجد طلب قيد التنفيذ، انتظر قليلاً...", show_alert=True)
        return

    async with lock:
        query = update.callback_query
        if query and query.message:
            message = query.message
            try:
                await message.edit_text(card(loading), parse_mode=ParseMode.HTML)
            except BadRequest:
                pass
        else:
            message = await update.effective_chat.send_message(card(loading), parse_mode=ParseMode.HTML)

        await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
        try:
            text, markup = render(await task())
        except Exception:
            log.exception("Task failed")
            text, markup = card("❌ حدث خطأ", "حاول مرة أخرى بعد قليل."), kb.main_menu()

        try:
            await message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)
        except BadRequest:
            await update.effective_chat.send_message(text, parse_mode=ParseMode.HTML, reply_markup=markup)


async def require_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await storage.get_user(update.effective_user.id)
    if not user:
        await show(update, card("⚠️ سجل دخولك أولاً", "يجب تسجيل الدخول برقم جازي للمتابعة."), kb.login_button())
    return user


# =======================================================
# 🏠 القائمة وتسجيل الدخول
# =======================================================
async def ask_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear()
    context.user_data["step"] = "PHONE"
    name = escape(update.effective_user.first_name or "")
    await update.effective_chat.send_message(
        f"<b>👋 أهلاً {name} في بوت جازي</b>\n{LINE}\n"
        "تحكم في خطك بسهولة:\n"
        "💰 الرصيد والباقات الفعالة\n"
        "🌐 تفعيل عروض الإنترنت\n"
        "🎁 هدية Walk & Win\n"
        f"{LINE}\n"
        "📱 <b>أرسل رقمك</b> (مثال: <code>0770123456</code>)\n"
        "أو اضغط على «مشاركة رقمي» بالأسفل.",
        parse_mode=ParseMode.HTML,
        reply_markup=kb.phone_keyboard(),
    )


async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await storage.get_user(update.effective_user.id)
    if not user:
        return await ask_login(update, context)
    await show(
        update,
        card("🏠 القائمة الرئيسية", f"📱 الرقم: {mask_phone(user['phone'])}", "اختر الخدمة من الأزرار 👇"),
        kb.main_menu(),
    )


async def send_otp_to(update: Update, context: ContextTypes.DEFAULT_TYPE, phone: str) -> None:
    chat = update.effective_chat
    await context.bot.send_chat_action(chat.id, ChatAction.TYPING)
    async with DjezzyClient() as client:
        ok = await client.send_otp(phone)

    if ok:
        context.user_data.update(step="OTP", phone=phone, otp_sent_at=time.time(), attempts=0)
        await chat.send_message("✅", reply_markup=ReplyKeyboardRemove())
        await chat.send_message(
            card("📩 تم إرسال الكود", f"أُرسل كود التحقق إلى {mask_phone(phone)}\nاكتب الكود هنا:"),
            parse_mode=ParseMode.HTML,
            reply_markup=kb.otp_menu(),
        )
    else:
        context.user_data["step"] = "PHONE"
        await chat.send_message(
            card("❌ تعذر إرسال الكود", "تأكد أن الرقم تابع لجازي ثم أعد المحاولة."),
            parse_mode=ParseMode.HTML,
            reply_markup=kb.phone_keyboard(),
        )


async def handle_otp(update: Update, context: ContextTypes.DEFAULT_TYPE, otp: str) -> None:
    try:
        await update.message.delete()
    except BadRequest:
        pass

    if not re.fullmatch(r"\d{4,8}", otp):
        await update.effective_chat.send_message("⚠️ الكود يجب أن يكون أرقاماً فقط.", reply_markup=kb.otp_menu())
        return

    phone = context.user_data.get("phone")
    lock = _user_locks[update.effective_user.id]
    if lock.locked():
        return
    async with lock:
        wait = await update.effective_chat.send_message(card("⏳ جاري التحقق..."), parse_mode=ParseMode.HTML)
        async with DjezzyClient() as client:
            res = await client.login(phone, otp)

        if res["success"]:
            data = res["data"]
            await storage.set_user(update.effective_user.id, phone, data.get("access_token"), data.get("refresh_token"))
            context.user_data.clear()
            await wait.edit_text(
                card("✅ تم تسجيل الدخول بنجاح", f"📱 الرقم: {mask_phone(phone)}", "اختر الخدمة من الأزرار 👇"),
                parse_mode=ParseMode.HTML,
                reply_markup=kb.main_menu(),
            )
            return

        context.user_data["attempts"] = context.user_data.get("attempts", 0) + 1
        left = OTP_MAX_ATTEMPTS - context.user_data["attempts"]
        if left <= 0:
            context.user_data.clear()
            await wait.edit_text(
                card("⛔ محاولات كثيرة", "تم إلغاء العملية، ابدأ من جديد."),
                parse_mode=ParseMode.HTML,
                reply_markup=kb.login_button(),
            )
            return
        await wait.edit_text(
            card("❌ الكود خاطئ", f"أعد كتابة الكود. المحاولات المتبقية: {left}"),
            parse_mode=ParseMode.HTML,
            reply_markup=kb.otp_menu(),
        )


# =======================================================
# ⚡ الخدمات
# =======================================================
async def do_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await require_user(update, context)
    if not user:
        return
    uid = update.effective_user.id

    async def task():
        async with DjezzyClient(user) as client:
            res = await client.get_details(user["phone"])
        await storage.save_tokens(uid, res)
        return res

    def render(res):
        if res.get("success"):
            return card("💰 رصيدك وباقاتك", res["msg"], f"🕒 آخر تحديث: {now_str()}"), kb.result_menu("BALANCE")
        return card("⚠️ تعذر جلب البيانات", res["msg"]), kb.main_menu()

    await run_task(update, context, "⏳ جاري جلب الرصيد...", task, render)


async def do_offers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_user(update, context):
        return
    await show(update, card("🌐 عروض الإنترنت", "اختر العرض الذي تريد تفعيله 👇"), kb.offers_menu())


async def do_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, code: str) -> None:
    if not await require_user(update, context):
        return
    offer = OFFERS_LIST.get(code)
    if not offer:
        return await do_offers(update, context)
    body = f"📦 {offer['name']}\n📝 {offer['desc']}\n💰 السعر: {offer['price']}"
    await show(update, card("🛒 تأكيد التفعيل", body, "سيتم خصم المبلغ من رصيدك"), kb.confirm_menu(code))


async def do_buy(update: Update, context: ContextTypes.DEFAULT_TYPE, code: str) -> None:
    user = await require_user(update, context)
    offer = OFFERS_LIST.get(code)
    if not user or not offer:
        return
    uid = update.effective_user.id

    async def task():
        async with DjezzyClient(user) as client:
            res = await client.activate_internet_offer(user["phone"], code)
        await storage.save_tokens(uid, res)
        return res

    def render(res):
        return card("🌐 نتيجة التفعيل", res["msg"]), kb.after_buy_menu()

    await run_task(update, context, f"⏳ جاري تفعيل: {offer['name']}", task, render)


async def do_walk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await require_user(update, context)
    if not user:
        return
    uid = update.effective_user.id

    async def task():
        async with DjezzyClient(user) as client:
            res = await client.activate_walk_win(user["phone"])
        await storage.save_tokens(uid, res)
        return res

    def render(res):
        return card("🎁 هدية Walk & Win", res["msg"]), kb.result_menu("WALK")

    await run_task(update, context, "⏳ جاري تفعيل الهدية...", task, render)


async def do_logout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await show(update, card("🚪 تسجيل الخروج", "هل تريد فعلاً تسجيل الخروج من حسابك؟"), kb.logout_confirm_menu())


async def do_logout_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await storage.delete_user(update.effective_user.id)
    context.user_data.clear()
    await show(update, card("🔒 تم الخروج", "تم حذف بيانات جلستك بنجاح."), kb.login_button())


async def do_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear()
    await update.effective_chat.send_message("❌ تم الإلغاء.", reply_markup=ReplyKeyboardRemove())
    if await storage.get_user(update.effective_user.id):
        await show_menu(update, context)
    else:
        await update.effective_chat.send_message("اضغط للبدء من جديد 👇", reply_markup=kb.login_button())


async def do_resend(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    phone = context.user_data.get("phone")
    if not phone:
        return await ask_login(update, context)
    left = int(OTP_RESEND_COOLDOWN - (time.time() - context.user_data.get("otp_sent_at", 0)))
    if left > 0:
        await update.callback_query.answer(f"⏳ انتظر {left} ثانية قبل إعادة الإرسال", show_alert=True)
        return
    await send_otp_to(update, context, phone)


async def do_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_chat.send_message(
        card(
            "ℹ️ المساعدة",
            "/start - البداية\n/menu - القائمة الرئيسية\n/balance - الرصيد\n/offers - العروض\n"
            "/gift - الهدية\n/logout - تسجيل الخروج\n/cancel - إلغاء العملية",
        ),
        parse_mode=ParseMode.HTML,
    )


# =======================================================
# 📨 استقبال الرسائل والأزرار
# =======================================================
async def on_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear()
    await show_menu(update, context)


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    data = query.data or ""
    action, _, arg = data.partition("|")

    if action in ("RESEND",):
        return await do_resend(update, context)
    await query.answer()

    routes = {
        "MENU": show_menu,
        "BALANCE": do_balance,
        "OFFERS": do_offers,
        "WALK": do_walk,
        "LOGOUT": do_logout,
        "LOGOUT_OK": do_logout_confirm,
        "LOGIN": ask_login,
    }
    if action in routes:
        return await routes[action](update, context)
    if action == "BUY":
        return await do_confirm(update, context, arg)
    if action == "OK":
        return await do_buy(update, context, arg)


async def on_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    contact = update.message.contact
    if contact.user_id != update.effective_user.id:
        await update.message.reply_text("⚠️ شارك رقمك أنت فقط باستعمال الزر.", reply_markup=kb.phone_keyboard())
        return
    phone = clean_phone(contact.phone_number)
    if not phone:
        await update.message.reply_text("⚠️ الرقم غير صالح، اكتبه يدوياً (مثال: 0770123456).")
        return
    await send_otp_to(update, context, phone)


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip()
    lower = text.lower()
    step = context.user_data.get("step")

    if lower in ("إلغاء", "الغاء", "cancel", "0", kb.CANCEL_TEXT):
        return await do_cancel(update, context)

    if step == "PHONE":
        phone = clean_phone(text)
        if not phone:
            await update.message.reply_text(
                "⚠️ رقم غير صالح. اكتب رقمك هكذا: 0770123456", reply_markup=kb.phone_keyboard()
            )
            return
        return await send_otp_to(update, context, phone)

    if step == "OTP":
        return await handle_otp(update, context, re.sub(r"\s", "", text))

    if not await storage.get_user(update.effective_user.id):
        return await ask_login(update, context)

    shortcuts = {
        ("1", "رصيد", "الرصيد"): do_balance,
        ("2", "عروض", "العروض"): do_offers,
        ("3", "هدية", "الهدية"): do_walk,
        ("4", "خروج"): do_logout,
    }
    for keys, handler in shortcuts.items():
        if lower in keys:
            return await handler(update, context)
    await show_menu(update, context)


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.error("Unhandled error", exc_info=context.error)


# =======================================================
# 🚀 التشغيل
# =======================================================
async def post_init(app: Application) -> None:
    await app.bot.set_my_commands([
        BotCommand("start", "البداية"),
        BotCommand("menu", "القائمة الرئيسية"),
        BotCommand("balance", "الرصيد والباقات"),
        BotCommand("offers", "عروض الإنترنت"),
        BotCommand("gift", "هدية Walk & Win"),
        BotCommand("logout", "تسجيل الخروج"),
        BotCommand("cancel", "إلغاء العملية"),
        BotCommand("help", "المساعدة"),
    ])
    me = await app.bot.get_me()
    log.info("🤖 Bot: @%s | 👥 Users: %s", me.username, await storage.count_users())
    if DJEZZY_PROXY_URL:
        try:
            log.info("🌍 Proxy IP: %s", await check_proxy_ip())
        except Exception as e:
            log.warning("⚠️ فشل فحص البروكسي: %s", e)


def main() -> None:
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .concurrent_updates(True)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", on_start))
    app.add_handler(CommandHandler("menu", show_menu))
    app.add_handler(CommandHandler("balance", do_balance))
    app.add_handler(CommandHandler("offers", do_offers))
    app.add_handler(CommandHandler("gift", do_walk))
    app.add_handler(CommandHandler("logout", do_logout))
    app.add_handler(CommandHandler("cancel", do_cancel))
    app.add_handler(CommandHandler("help", do_help))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.CONTACT, on_contact))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.add_error_handler(on_error)

    if WEBHOOK_URL:
        log.info("🚀 Telegram Bot running (webhook) on port %s", PORT)
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path="telegram",
            webhook_url=f"{WEBHOOK_URL.rstrip('/')}/telegram",
            drop_pending_updates=True,
        )
    else:
        log.info("🚀 Telegram Bot running (polling)")
        app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
