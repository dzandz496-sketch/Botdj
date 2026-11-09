import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("djezzy-bot")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
DJEZZY_PROXY_URL = os.getenv("DJEZZY_PROXY_URL", "").strip() or None
# على Render يتم ضبط RENDER_EXTERNAL_URL تلقائياً، فيعمل البوت بنظام Webhook بدون إعداد إضافي
WEBHOOK_URL = (os.getenv("WEBHOOK_URL", "").strip() or os.getenv("RENDER_EXTERNAL_URL", "").strip()) or None
PORT = int(os.getenv("PORT", "8080"))
DATA_FILE = os.getenv("DATA_FILE", "telegram_sessions.json")

if not BOT_TOKEN or BOT_TOKEN == "ضع_توكن_البوت_هنا":
    log.error("❌ BOT_TOKEN غير موجود. أضفه في ملف .env")
    sys.exit(1)

if not DJEZZY_PROXY_URL:
    log.warning("⚠️ DJEZZY_PROXY_URL غير موجود، سيتم الاتصال بجازي بدون بروكسي.")

# =======================================================
# 🔑 مفاتيح Djezzy API
# =======================================================
CLIENT_ID = "87pIExRhxBb3_wGsA5eSEfyATloa"
CLIENT_SECRET = "uf82p68Bgisp8Yg1Uz8Pf6_v1XYa"

OFFERS_LIST = {
    "BTL500MBHOUR": {"name": "⚡ 1GB ساعة (40دج)", "price": "40 DA", "desc": "ساعة إنترنت بلا حدود"},
    "BTLINTSPEEDDAY2Go": {"name": "📅 4GB يومي (70دج)", "price": "70 DA", "desc": "24 ساعة إنترنت"},
    "DOVINTSPEEDDAY1GoPRE": {"name": "🔥 1GB يومي (100دج)", "price": "100 DA", "desc": "عرض خاص 24 ساعة"},
    "BTL500MBDAY": {"name": "🌊 3GB يومي (90دج)", "price": "90 DA", "desc": "تصفح مريح ليوم كامل"},
    "BTL1GBDAY": {"name": "🚀 4GB سوبر (140دج)", "price": "140 DA", "desc": "عرض السرعة القصوى"},
    "BTL4GBDAY": {"name": "💎 5GB ماكس (190دج)", "price": "190 DA", "desc": "الباقة اليومية الأضخم"},
    "ImtiyazSurpriseData2hfbPRE": {"name": "💙 فيسبوك (50دج)", "price": "50 DA", "desc": "4 ساعات فيسبوك"},
    "1GBFB3DAYInternet": {"name": "🔵 1GB فيسبوك (70دج)", "price": "70 DA", "desc": "صالح لمدة 3 أيام"},
    "2GBMONTH": {"name": "📆 3GB شهري (250دج)", "price": "250 DA", "desc": "باقة الشهر الاقتصادية"},
    "BTLDATA2WEEKS": {"name": "⏳ 4GB أسبوعين (400دج)", "price": "400 DA", "desc": "صالحة لمدة 15 يوم"},
}
