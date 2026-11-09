from telegram import InlineKeyboardButton as Btn
from telegram import InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from config import OFFERS_LIST

CANCEL_TEXT = "❌ إلغاء"


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [Btn("💰 الرصيد", callback_data="BALANCE"), Btn("🌐 العروض", callback_data="OFFERS")],
        [Btn("🎁 الهدية", callback_data="WALK"), Btn("🚪 خروج", callback_data="LOGOUT")],
    ])


def result_menu(retry_action: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [Btn("🔄 تحديث", callback_data=retry_action), Btn("🏠 القائمة", callback_data="MENU")],
    ])


def offers_menu() -> InlineKeyboardMarkup:
    rows = [[Btn(o["name"], callback_data=f"BUY|{code}")] for code, o in OFFERS_LIST.items()]
    rows.append([Btn("🏠 القائمة الرئيسية", callback_data="MENU")])
    return InlineKeyboardMarkup(rows)


def confirm_menu(code: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [Btn("✅ تأكيد التفعيل", callback_data=f"OK|{code}")],
        [Btn("↩️ رجوع للعروض", callback_data="OFFERS")],
    ])


def after_buy_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [Btn("💰 الرصيد", callback_data="BALANCE"), Btn("🌐 عرض آخر", callback_data="OFFERS")],
        [Btn("🏠 القائمة", callback_data="MENU")],
    ])


def logout_confirm_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [Btn("✅ نعم، خروج", callback_data="LOGOUT_OK"), Btn("↩️ رجوع", callback_data="MENU")],
    ])


def login_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[Btn("🔑 تسجيل الدخول", callback_data="LOGIN")]])


def otp_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [Btn("🔁 إعادة إرسال الكود", callback_data="RESEND"), Btn("✏️ تغيير الرقم", callback_data="LOGIN")],
    ])


def phone_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton("📲 مشاركة رقمي", request_contact=True)], [CANCEL_TEXT]],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="0770123456",
    )
