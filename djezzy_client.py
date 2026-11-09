import math
import re
import time
from datetime import datetime

import httpx

from config import CLIENT_ID, CLIENT_SECRET, DJEZZY_PROXY_URL, OFFERS_LIST

BASE_URL = "https://apim.djezzy.dz"
FORM = {"Content-Type": "application/x-www-form-urlencoded"}
JSON_CT = {"Content-Type": "application/json"}


def _json(res):
    try:
        return res.json()
    except Exception:
        return None


def _message(res) -> str:
    data = _json(res)
    if isinstance(data, dict):
        return str(data.get("message") or "").lower()
    return ""


def _fmt2(value) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "0.00"


def _num(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _parse_time_ms(value):
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp() * 1000
    except Exception:
        return None


class DjezzyClient:
    """نفس منطق عميل جازي الأصلي، تم نقله إلى بايثون كما هو."""

    def __init__(self, user_data=None):
        self.headers = {
            "Host": "apim.djezzy.dz",
            "User-Agent": "MobileApp/3.0.0",
            "Accept": "application/json",
            "Connection": "Keep-Alive",
        }
        self.access_token = user_data.get("token") if user_data else None
        self.refresh_token = user_data.get("refreshToken") if user_data else None
        # استخدام البروكسي حصرياً لطلبات جازي
        self.http = httpx.AsyncClient(
            base_url=BASE_URL,
            timeout=30.0,
            headers=self.headers,
            proxy=DJEZZY_PROXY_URL,
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self.http.aclose()

    def _auth(self, extra=None):
        headers = dict(extra or {})
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    async def _get(self, url, headers=None):
        return await self.http.get(url, headers=self._auth(headers))

    async def _post(self, url, content, headers=None):
        return await self.http.post(url, content=content, headers=self._auth(headers))

    def _tokens(self):
        return {"t": self.access_token, "rt": self.refresh_token}

    @staticmethod
    def normalize_phone(p) -> str:
        p = re.sub(r"\D", "", str(p))
        if p.startswith("213"):
            return p
        if p.startswith("0"):
            return "213" + p[1:]
        return "213" + p

    async def send_otp(self, p) -> bool:
        p = self.normalize_phone(p)
        try:
            payload = f"msisdn={p}&scope=smsotp&client_id={CLIENT_ID}"
            r = await self._post("/mobile-api/oauth2/registration", payload, FORM)
            return r.status_code in (200, 201, 204)
        except Exception:
            return False

    async def login(self, p, o):
        p = self.normalize_phone(p)
        payload = (
            f"grant_type=mobile&client_id={CLIENT_ID}&client_secret={CLIENT_SECRET}"
            f"&scope=openid&mobileNumber={p}&otp={o}"
        )
        try:
            r = await self._post("/mobile-api/oauth2/token", payload, FORM)
        except Exception:
            return {"success": False}
        return {"success": True, "data": _json(r) or {}} if r.status_code == 200 else {"success": False}

    async def refresh_auth_token(self):
        if not self.refresh_token:
            return {"success": False}
        payload = (
            f"scope=openid&client_secret={CLIENT_SECRET}&client_id={CLIENT_ID}"
            f"&grant_type=refresh_token&refresh_token={self.refresh_token}"
        )
        try:
            r = await self._post("/mobile-api/oauth2/token", payload, FORM)
            data = _json(r) or {}
            if r.status_code == 200 and data.get("access_token"):
                self.access_token = data["access_token"]
                if data.get("refresh_token"):
                    self.refresh_token = data["refresh_token"]
                return {"success": True, "token": self.access_token, "refreshToken": self.refresh_token}
        except Exception:
            pass
        return {"success": False}

    async def get_details(self, phone, retry=True):
        msisdn = self.normalize_phone(phone)
        try:
            balance_url = (
                f"/mobile-api/api/v1/subscribers/main-balance/{msisdn}"
                "?include=surprise-products,subscription-type-illegibility,connected-products,"
                "subscription-history,flash-products,supplementary-informations,available-services"
            )
            bal_res = await self._get(balance_url)

            if bal_res.status_code == 401 and retry:
                refreshed = await self.refresh_auth_token()
                if refreshed["success"]:
                    return await self.get_details(phone, False)

            if bal_res.status_code == 200:
                data = _json(bal_res) or {}
                main_balance, due, sim_type = "0", "0", ""

                inner = data.get("data") if isinstance(data, dict) else None
                if inner:
                    main_balance = inner.get("mainBalance") or "0"
                    due = inner.get("due") or "0"
                    sub_type = (inner.get("customerInformations") or {}).get("subscriptionType")
                    if sub_type and sub_type.get("name"):
                        n = sub_type["name"]
                        sim_type = n.get("ar") or n.get("fr") or n.get("en") or ""

                msg = f"📱 الشريحة: {sim_type}\n💰 الرصيد الأساسي: {_fmt2(main_balance)} دج\n"
                if _num(due) > 0:
                    msg += f"💸 التسبيق (دين): {_fmt2(due)} دج\n"
                msg += "\n📦 باقاتك الفعالة:\n"

                subs_res = await self._get(f"/mobile-api/api/v1/subscribers/connected-products-balances/{msisdn}")
                subs = _json(subs_res)

                found_bundles = False
                if subs_res.status_code == 200 and isinstance(subs, list):
                    for sub in subs:
                        cn = sub.get("commercialName")
                        if cn:
                            name = cn.get("ar") or cn.get("fr") or cn.get("en") or sub.get("code")
                        else:
                            name = sub.get("code")
                        msg += f"🔹 {name}\n"

                        for bal in sub.get("balances") or []:
                            remaining = _num(bal.get("remaining") or 0)
                            unit = bal.get("usageUnit") or ""
                            u_type = bal.get("usageType") or ""
                            unlimited = bal.get("unlimited") or False

                            if unlimited:
                                msg += f"  📈 {u_type}: غير محدود\n"
                                found_bundles = True
                            elif remaining > 0:
                                if unit in ("MB", "GB") or u_type == "DATA":
                                    size = f"{remaining / 1024:.2f} جيجا" if unit == "MB" else f"{remaining:.2f} {unit}"
                                    msg += f"  🌐 إنترنت: {size}\n"
                                elif u_type == "VOICE":
                                    msg += f"  📞 مكالمات: {math.floor(remaining)} دقيقة\n"
                                elif u_type == "SMS":
                                    msg += f"  ✉️ رسائل: {math.floor(remaining)} رسالة\n"
                                else:
                                    shown = int(remaining) if remaining.is_integer() else remaining
                                    msg += f"  📉 باقي: {shown} {unit}\n"
                                found_bundles = True

                        expiry = (sub.get("expiryAt") or "").replace("T", " ").split(".")[0]
                        if expiry:
                            msg += f"  ⏳ تنتهي: {expiry}\n"
                        msg += "➖\n"

                if not found_bundles:
                    msg += "🔸 لا توجد باقات مفعلة حالياً."
                return {"success": True, "msg": msg, "newTokens": self._tokens()}
            return {"success": False, "msg": "⚠️ تعذر جلب البيانات. يرجى تسجيل الدخول مجدداً."}
        except Exception:
            return {"success": False, "msg": "⛔ خطأ في الاتصال بخوادم جازي."}

    async def activate_internet_offer(self, phone, code, retry=True):
        msisdn = self.normalize_phone(phone)
        info = OFFERS_LIST.get(code, {"name": code, "price": "???"})
        try:
            await self._get(f"/mobile-api/api/v1/services/shake/{msisdn}")

            url = f"/mobile-api/api/v1/subscribers/activate-product/{msisdn}"
            payload = f'{{"packageCode":"{code}"}}'
            res = await self._post(url, payload, JSON_CT)

            if res.status_code == 401 and retry:
                refreshed = await self.refresh_auth_token()
                if refreshed["success"]:
                    return await self.activate_internet_offer(phone, code, False)

            msg_str = _message(res)

            if res.status_code in (200, 201) or "success" in msg_str:
                return {"msg": f"✅ تم!\n📦 {info['name']}\n💰 خُصم: {info['price']}", "newTokens": self._tokens()}

            if res.status_code == 402 or "insuffisant" in msg_str or "balance" in msg_str:
                return {"msg": f"⚠️ رصيد غير كافٍ لتفعيل العرض.\nالمطلوب: {info['price']}", "newTokens": self._tokens()}

            return {
                "msg": f"❌ فشل التفعيل.\nالرد: {res.status_code}\nالسبب: {msg_str or 'غير معروف'}",
                "newTokens": self._tokens(),
            }
        except Exception:
            return {"msg": "⛔ خطأ في الاتصال بالسيرفر.", "newTokens": None}

    async def get_walk_win_remaining_time(self, phone):
        msisdn = self.normalize_phone(phone)
        try:
            res = await self._get(
                f"/mobile-api/api/v1/subscribers/subscription-history/{msisdn}",
                {"Accept": "application/json"},
            )
            data = _json(res)
            if res.status_code == 200 and isinstance(data, dict) and isinstance(data.get("data"), list):
                latest = 0
                for pkg in data["data"]:
                    p_code = str(pkg.get("packageCode") or "").upper()
                    if "WALK" in p_code and pkg.get("subscriptionDateTime"):
                        t = _parse_time_ms(pkg["subscriptionDateTime"])
                        if t is not None and t > latest:
                            latest = t
                if latest > 0:
                    week_ms = 604800000
                    remaining = (latest + week_ms) - time.time() * 1000
                    if remaining > 0:
                        days = math.floor(remaining / 86400000)
                        hours = math.floor((remaining % 86400000) / 3600000)
                        mins = math.floor((remaining % 3600000) / 60000)
                        secs = math.floor((remaining % 60000) / 1000)

                        if days > 0:
                            time_str = f"{days}ي و {hours}س"
                        elif hours > 0:
                            time_str = f"{hours}س و {mins}د"
                        elif mins > 0:
                            time_str = f"{mins}د و {secs}ث"
                        else:
                            time_str = f"{secs}ث"
                        return f"⏳ لم يمر أسبوع بعد.\nالوقت المتبقي: {time_str}"
            return None
        except Exception:
            return None

    async def activate_walk_win(self, phone, retry=True):
        msisdn = self.normalize_phone(phone)
        url = f"/mobile-api/api/v1/services/walk/activate-reward/{msisdn}"
        payload = '{"packageCode":"GIFTWALKWIN2GO"}'
        try:
            res = await self._post(url, payload, JSON_CT)
            msg_str = _message(res)

            if res.status_code == 401 and "unauthorized product" not in msg_str and retry:
                refreshed = await self.refresh_auth_token()
                if refreshed["success"]:
                    return await self.activate_walk_win(phone, False)

            if res.status_code in (200, 201) or "success" in msg_str:
                return {"msg": "🎉 تم تفعيل (2GB) بنجاح!", "newTokens": self._tokens()}

            if res.status_code == 402 or "not enough" in msg_str or "balance" in msg_str:
                return {"msg": "⚠️ غير مؤهل (يجب استهلاك 100 دج).", "newTokens": self._tokens()}

            history_msg = await self.get_walk_win_remaining_time(phone)
            if history_msg:
                return {"msg": history_msg, "newTokens": self._tokens()}

            return {
                "msg": "⚠️ غير مؤهل للتفعيل حالياً.\n(تلميح: يجب استهلاك 100 دج على الأقل).",
                "newTokens": self._tokens(),
            }
        except Exception:
            return {"msg": "⛔ خطأ في الاتصال بخوادم جازي.", "newTokens": None}


async def check_proxy_ip():
    """نفس فحص: curl -x PROXY https://api.ipify.org/"""
    async with httpx.AsyncClient(proxy=DJEZZY_PROXY_URL, timeout=20.0) as c:
        r = await c.get("https://api.ipify.org/")
        return r.text.strip()
