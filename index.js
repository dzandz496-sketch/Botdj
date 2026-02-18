// =======================================================
// 🛠️ إصلاحات الشبكة الأساسية (Render/Fly Fix)
// =======================================================
const dns = require('dns');
try { dns.setDefaultResultOrder('ipv4first'); } catch(e) {}

const express = require('express');
const bodyParser = require('body-parser');
const axios = require('axios');
const crypto = require('crypto');
const fs = require('fs');
const https = require('https');

// =======================================================
// ⚙️ إعدادات البوت
// =======================================================
const PAGE_ACCESS_TOKEN = "EAARATjo0m58BQvA95yyZBpgE3ZBZCxWd8qKTBNdH5E7fU9QR7QojNBiSprpHiA0EsROSqUZCkslDXWg1BegWZCM97TyZAWvVrix7IEl0Y2JN6P50eUu7tuvRzYjhZAujGxq49PyGdeqTTMjLIme4FxUZAMFAyoJze6WHiUxfjZBOJWKGLZBiB5eE4NOLRZCfy2Q5zBsPiRoRRfDiwZDZD"; 
const VERIFY_TOKEN = "djezzy_bot_secure_pass"; 
const PORT = process.env.PORT || 3000;

// =======================================================
// 🎭 إعدادات التمويه (خداع سيرفر جيزي)
// =======================================================
// نقوم بتوليد IP جزائري عشوائي (نطاق جيزي/اتصالات الجزائر)
function getFakeAlgerianIP() {
    return `105.100.${Math.floor(Math.random() * 255)}.${Math.floor(Math.random() * 255)}`;
}

const fakeIP = getFakeAlgerianIP();

// رؤوس مخادعة لتبدو وكأن الطلب من هاتف في الجزائر
const SPOOF_HEADERS = {
    'User-Agent': 'Djezzy/2.7.0 (Android; 11; Mobile)', // إظهار أننا تطبيق موبايل
    'Accept': 'application/json',
    'X-Forwarded-For': fakeIP,       // خدعة 1: أنا من هذا الآي بي
    'Client-IP': fakeIP,             // خدعة 2
    'X-Real-IP': fakeIP,             // خدعة 3
    'CF-Connecting-IP': fakeIP,      // خدعة 4 (في حال كانوا يستخدمون كلاود فلير)
    'True-Client-IP': fakeIP
};

// =======================================================
// 🛠️ وكلاء الاتصال (Agents)
// =======================================================
// وكيل سريع لجيزي
const djezzyAgent = new https.Agent({ 
    family: 4, 
    keepAlive: true,
    rejectUnauthorized: false // تجاهل أخطاء الشهادات لزيادة القبول
});

// وكيل سريع لفيسبوك
const fbAgent = new https.Agent({ family: 4, keepAlive: true });

// =======================================================
// 🔐 التشفير
// =======================================================
const KEY_A = Buffer.from("af81e011f0fa89a0c43d252c66dbfc7914c6ab0b7678c003cb8fe70171d2e601", "hex");
const KEY_B = Buffer.from("0359807d1245e424a5b6991c9d4c08b59ad7bef6c02e84790ccb4e8ae9993e81", "hex");
const KEY_C = Buffer.from("b7abed31a7b180e6a931ebed7b0c5de13a754130a942b71fa1f8a3c31b134e06", "hex");

const ARRAY_D = ["djezzy", "apim", "csrf", "token", "api", "v1", "subscribers", "content", "services", "internal", "notification", "push", "message", "community", "user", "group", "assets", "settings", "order", "payment", "event", "events", "quiz", "subscriptions", "include"];
const ARRAY_E_HEX = ["79f2be6edcd84c3870c9b627516ce946", "99c9f40333cffe29518b42947422635b", "157f1f2b72de3471038ecc940f924b05", "74ef3238f91735234a458c8c55b918b9", "82dcd76a54b654941930396e7cb1ce84", "5f9b5efccc30cb023cfb39a42fa3cb8b", "f49cfb160e39fbdc3ff75a625357f741", "79f2be6edcd84c3870c9b627516ce946", "3e4d5dcfa89977e51eeaa9f411cde085", "d9969fc9dc7b424e277a264c1fd8a34d", "e1e23ce3f12d665572a0612f7c1b1a42"];
const ARRAY_E = ARRAY_E_HEX.map(x => Buffer.from(x, "hex"));

function generateCsrfToken() {
    try {
        let buffer = Buffer.alloc(0);
        const currentTime = BigInt(Date.now() - 1000);
        const combinedText = ARRAY_D.join("/");
        const cipherA = crypto.createCipheriv('aes-256-ecb', KEY_A, null);
        cipherA.setAutoPadding(true);
        let encryptedText = Buffer.concat([cipherA.update(combinedText, 'utf8'), cipherA.final()]);
        buffer = Buffer.concat([buffer, encryptedText]);
        for (let i = 0; i < ARRAY_E.length; i++) {
            const iv = ARRAY_E[i];
            const blockText = `block_${i}_${currentTime}`;
            const cipherC = crypto.createCipheriv('aes-256-cbc', KEY_C, iv);
            cipherC.setAutoPadding(true);
            const encryptedBlock = Buffer.concat([cipherC.update(blockText, 'utf8'), cipherC.final()]);
            buffer = Buffer.concat([buffer, encryptedBlock]);
            if (i < ARRAY_E.length - 1) {
                const decipherB = crypto.createDecipheriv('aes-256-cbc', KEY_B, iv);
                decipherB.setAutoPadding(false);
                const decryptedTemp = Buffer.concat([decipherB.update(encryptedBlock), decipherB.final()]);
                const cipherA2 = crypto.createCipheriv('aes-256-ecb', KEY_A, null);
                cipherA2.setAutoPadding(true);
                const reEncrypted = Buffer.concat([cipherA2.update(decryptedTemp), cipherA2.final()]);
                buffer = Buffer.concat([buffer, reEncrypted]);
            }
        }
        const timeBuffer = Buffer.alloc(8);
        timeBuffer.writeBigUInt64LE(currentTime);
        const cipherTime = crypto.createCipheriv('aes-256-ecb', KEY_A, null);
        cipherTime.setAutoPadding(true);
        const encryptedTime = Buffer.concat([cipherTime.update(timeBuffer), cipherTime.final()]);
        buffer = Buffer.concat([buffer, encryptedTime]);
        return buffer.toString('base64').replace(/\n/g, "").replace(/\r/g, "").replace(/ /g, "");
    } catch (error) { return null; }
}

const OFFERS_LIST = {
    "BTL500MBHOUR": { "name": "⚡ 1GB ساعة (40دج)", "price": "40 DA", "desc": "ساعة إنترنت بلا حدود" },
    "BTLINTSPEEDDAY2Go": { "name": "📅 4GB يومي (70دج)", "price": "70 DA", "desc": "24 ساعة إنترنت" },
    "DOVINTSPEEDDAY1GoPRE": { "name": "🔥 1GB يومي (100دج)", "price": "100 DA", "desc": "عرض خاص 24 ساعة" },
    "BTL500MBDAY": { "name": "🌊 3GB يومي (90دج)", "price": "90 DA", "desc": "تصفح مريح ليوم كامل" },
    "BTL1GBDAY": { "name": "🚀 4GB سوبر (140دج)", "price": "140 DA", "desc": "عرض السرعة القصوى" },
    "BTL4GBDAY": { "name": "💎 5GB ماكس (190دج)", "price": "190 DA", "desc": "الباقة اليومية الأضخم" },
    "ImtiyazSurpriseData2hfbPRE": { "name": "💙 فيسبوك (50دج)", "price": "50 DA", "desc": "4 ساعات فيسبوك" },
    "1GBFB3DAYInternet": { "name": "🔵 1GB فيسبوك (70دج)", "price": "70 DA", "desc": "صالح لمدة 3 أيام" },
    "2GBMONTH": { "name": "📆 3GB شهري (250دج)", "price": "250 DA", "desc": "باقة الشهر الاقتصادية" },
    "BTLDATA2WEEKS": { "name": "⏳ 4GB أسبوعين (400دج)", "price": "400 DA", "desc": "صالحة لمدة 15 يوم" }
};

const CLIENT_ID = "6E6CwTkp8H1CyQxraPmcEJPQ7xka";
const CLIENT_SECRET = "MVpXHW_ImuMsxKIwrJpoVVMHjRsa";
const DATA_FILE = "messenger_sessions.json";

// =======================================================
// 🧠 Djezzy API Client (مع التمويه)
// =======================================================
class DjezzyClient {
    constructor(userData = null) {
        this.baseURL = 'https://apim.djezzy.dz'; 
        // دمج الهيدرز الأصلية مع هيدرز التمويه
        this.headers = { ...SPOOF_HEADERS }; 
        
        this.accessToken = userData ? userData.token : null;
        this.cookies = userData && userData.cookies ? userData.cookies : {};
        
        this.axios = axios.create({ baseURL: this.baseURL, timeout: 25000, headers: this.headers, validateStatus: () => true, httpsAgent: djezzyAgent });
        
        this.axios.interceptors.request.use(config => {
            if (Object.keys(this.cookies).length > 0) config.headers['Cookie'] = Object.entries(this.cookies).map(([k, v]) => `${k}=${v}`).join('; ');
            if (this.accessToken) config.headers['Authorization'] = `Bearer ${this.accessToken}`;
            return config;
        });
        
        this.axios.interceptors.response.use(response => {
            if (response.headers['set-cookie']) response.headers['set-cookie'].forEach(c => this.cookies[c.split(';')[0].split('=')[0]] = c.split(';')[0].split('=')[1]);
            return response;
        });
    }

    normalizePhone(p) { p = p.toString().replace(/\D/g, ''); if (p.startsWith("213")) return p; if (p.startsWith("0")) return "213" + p.substring(1); return "213" + p; }
    
    async sendOtp(p) { 
        p = this.normalizePhone(p);
        let r = await this.axios.get("/oauth2/registration", { params: { msisdn: p, scope: "smsotp", client_id: CLIENT_ID } });
        if ([200, 201, 204].includes(r.status)) return true;
        r = await this.axios.post("/oauth2/registration", new URLSearchParams({ msisdn: p, scope: "smsotp", client_id: CLIENT_ID }));
        return [200, 201, 204].includes(r.status);
    }

    async login(p, o) {
        p = this.normalizePhone(p);
        const r = await this.axios.post("/oauth2/token", new URLSearchParams({ grant_type: "mobile", client_id: CLIENT_ID, client_secret: CLIENT_SECRET, scope: "openid", mobileNumber: p, otp: o }));
        return r.status === 200 ? { success: true, data: r.data } : { success: false };
    }

    async getDetails(p) {
        const url = `/djezzy-api/api/v1/subscribers/${this.normalizePhone(p)}`;
        const params = { include: "connected-products,connected-products.balances,connected-products.usages,subscription-types" };
        const r = await this.axios.get(url, { params: params, headers: { 'X-Csrf-Token': generateCsrfToken() } });

        if (r.status === 200) {
            const data = r.data;
            const attrs = data.data.attributes || {};
            const balance = attrs.balance || '0';
            const activationDate = (attrs['activation-time'] || "").split("T")[0] || "غير متوفر";
            let planName = "غير محدد";

            if (data.included) {
                data.included.forEach(item => {
                    if (item.type === 'subscription-types') {
                        const nameObj = item.attributes.name.text || {};
                        planName = nameObj.ar || nameObj.fr || "Djezzy";
                    }
                });
            }

            let msg = `💰 الرصيد الحالي: ${balance} دج\n📊 العرض: ${planName}\n📅 تاريخ التفعيل: ${activationDate}\n\n👇 الباقات المفعلة:\n`;
            let foundBundles = false;

            if (data.included) {
                const connectedProducts = data.included.filter(item => item.type === 'connected-products');
                let allProducts = [];
                connectedProducts.forEach(cp => {
                    if (cp.attributes && cp.attributes.products) allProducts.push(...cp.attributes.products);
                    else if (cp.attributes) allProducts.push(cp.attributes);
                });

                allProducts.forEach(prod => {
                    const nameObj = prod.name ? prod.name.text : {};
                    const pName = nameObj.ar || nameObj.fr;
                    if (pName) {
                        foundBundles = true;
                        msg += `📦 ${pName}\n`;
                        if (prod.balances) {
                            prod.balances.forEach(bal => {
                                const bNames = bal['balance-name'] ? bal['balance-name'].text : {};
                                const bName = bNames.ar || bNames.fr || "Internet";
                                if (bName.toLowerCase().includes("internet") || bName.includes("الإنترنت") || bName.toLowerCase().includes("data")) {
                                    const expiryFmt = (bal['expiry-at'] || "").replace('T', ' ').split('.')[0] || "غير محدد";
                                    msg += `   📉 المتبقي: ${bal['remaining-amount']} ${bal['unit']}\n   ⏳ ينتهي: ${expiryFmt}\n`;
                                }
                            });
                        }
                        msg += "────────────────\n";
                    }
                });
            }

            if (!foundBundles) msg += "🔸 لا توجد باقات مفعلة حالياً.";
            return { success: true, msg: msg };
        }
        return { success: false, msg: "⚠️ خطأ في جلب البيانات." };
    }

    async activateInternetOffer(phone, code) {
        const msisdn = this.normalizePhone(phone);
        const csrf = generateCsrfToken();
        const url = `/djezzy-api/api/v1/subscribers/${msisdn}/subscription-product?include=attributes`;
        const payload = { data: { id: code, type: "products" } };
        const info = OFFERS_LIST[code] || { name: code, price: "???" };

        try {
            const res = await this.axios.post(url, payload, { headers: { 'X-Csrf-Token': csrf } });
            let isSuccess = false;
            let isNoBalance = false;
            const msgJson = String(res.data.message || "").toLowerCase();
            const statusJson = String(res.data.status || "");

            if ([200, 201].includes(res.status)) {
                if (statusJson === "200" && (msgJson.includes("success") || msgJson.includes("successfully"))) isSuccess = true;
            }

            if (res.status === 402 || statusJson === "402" || msgJson.includes("balance") || msgJson.includes("enough") || msgJson.includes("crédit") || msgJson.includes("montant")) {
                isNoBalance = true;
            }

            if (isSuccess) return `✅ تم تفعيل العرض بنجاح!\n📦 الباقة: ${info.name}\n💰 تم خصم: ${info.price}`;
            if (isNoBalance) return `⚠️ عذراً، رصيدك غير كافٍ.\n\nلتفعيل باقة (${info.name})، تحتاج إلى رصيد: ${info.price}`;
            
            return `❌ فشلت العملية.\nرد النظام: ${res.data.message || "خطأ تقني غير معروف"}`;

        } catch (error) { return `⛔ خطأ في الاتصال بالسيرفر.`; }
    }

    async activateWalkWin(phone) {
        const msisdn = this.normalizePhone(phone);
        const csrf = generateCsrfToken();
        const url = `/djezzy-api/api/v1/subscribers/${msisdn}/subscription-product?include=attributes`;
        const payload = { data: { id: "GIFTWALKWIN", type: "products", meta: { services: { steps: 10000, code: "GIFTWALKWIN2GO", id: "WALKWIN" } } } };
        const res = await this.axios.post(url, payload, { headers: { 'X-Csrf-Token': csrf } });
        
        let innerStatus = "";
        let innerMsg = "";
        try {
            if (typeof res.data.message === 'string' && res.data.message.includes('{')) {
                const parsedInner = JSON.parse(res.data.message);
                innerStatus = String(parsedInner.status || "");
                innerMsg = String(parsedInner.message || "").toLowerCase();
            } else {
                innerMsg = String(res.data.message || "").toLowerCase();
            }
        } catch(e) { innerMsg = String(res.data.message || "").toLowerCase(); }

        if (res.status === 403 || innerStatus === "403" || innerStatus === "401" || innerMsg.includes("unauthorized subscription") || innerMsg.includes("unauthorized product")) {
            return "⏳ عذراً، لم يمر أسبوع بعد.\nيجب الانتظار حتى انتهاء المدة المحددة لتفعيل الهدية مجدداً.";
        }

        if (res.status === 402 || innerStatus === "402" || innerMsg.includes("not enough") || innerMsg.includes("balance")) {
             return "⚠️ غير مؤهل للحصول على الهدية.\nيجب عليك استهلاك 100 دج إنترنت على الأقل لتفعيل الهدية.";
        }

        if ([200, 201].includes(res.status)) {
            return "🎉 مبروك! تم تفعيل هدية المشي (2 GB) بنجاح.";
        }

        return "❌ فشلت العملية. يرجى المحاولة لاحقاً.";
    }
}

// =======================================================
// 🌐 خادم الويب
// =======================================================
const app = express();
app.use(bodyParser.json());

// ملف وهمي لضمان العمل على Render
if (!fs.existsSync(DATA_FILE)) { fs.writeFileSync(DATA_FILE, JSON.stringify({})); }

function loadData() { try { return JSON.parse(fs.readFileSync(DATA_FILE)); } catch (e) { return {}; } }
function saveData(d) { fs.writeFileSync(DATA_FILE, JSON.stringify(d, null, 4)); }
const userSteps = {};

app.get('/', (req, res) => res.send("🤖 Bot is Running on Render!"));

app.get('/webhook', (req, res) => {
    if (req.query['hub.mode'] === 'subscribe' && req.query['hub.verify_token'] === VERIFY_TOKEN) {
        res.status(200).send(req.query['hub.challenge']);
    } else res.sendStatus(403);
});

app.post('/webhook', (req, res) => {
    let body = req.body;
    if (body.object === 'page') {
        body.entry.forEach(function(entry) {
            let webhook_event = entry.messaging[0];
            let sender_psid = webhook_event.sender.id;
            sendTypingOn(sender_psid);
            if (webhook_event.message) handleMessage(sender_psid, webhook_event.message);
            else if (webhook_event.postback) handlePostback(sender_psid, webhook_event.postback);
        });
        res.status(200).send('EVENT_RECEIVED');
    } else res.sendStatus(404);
});

// استخدام الـ Agent في ردود فيسبوك لتسريع الاتصال
async function sendTypingOn(sender_psid) {
    try { 
        await axios.post(
            `https://graph.facebook.com/v12.0/me/messages?access_token=${PAGE_ACCESS_TOKEN}`, 
            { "recipient": { "id": sender_psid }, "sender_action": "typing_on" },
            { httpsAgent: fbAgent }
        ); 
    } catch(e) {}
}

async function callSendAPI(sender_psid, response) {
    try { 
        await axios.post(
            `https://graph.facebook.com/v12.0/me/messages?access_token=${PAGE_ACCESS_TOKEN}`, 
            { "recipient": { "id": sender_psid }, "message": response },
            { httpsAgent: fbAgent }
        ); 
    } catch (e) { console.error("Send Error:", e.response ? e.response.data : e.message); }
}

// =======================================================
// 💬 التحكم في الرسائل
// =======================================================
async function handleMessage(sender_psid, received_message) {
    let text = received_message.text;
    let db = loadData();
    const mainMenuQR = [
        { "content_type": "text", "title": "💰 رصيدي", "payload": "BALANCE" },
        { "content_type": "text", "title": "🌐 العروض", "payload": "OFFERS" },
        { "content_type": "text", "title": "🎁 Walk & Win", "payload": "WALK" },
        { "content_type": "text", "title": "🚪 خروج", "payload": "LOGOUT" }
    ];

    if (!db[sender_psid]) {
        if ((received_message.quick_reply && received_message.quick_reply.payload === 'LOGIN') || text === "📱 تسجيل الدخول") {
            userSteps[sender_psid] = "PHONE";
            await callSendAPI(sender_psid, { "text": "📱 الرجاء إدخال رقم الهاتف (07xx...) للبدء:" });
            return;
        }

        if (userSteps[sender_psid] === "PHONE") {
            if (/^\d{9,10}$/.test(text)) {
                let client = new DjezzyClient();
                let res = await client.sendOtp(text);
                if (res) {
                    userSteps[sender_psid] = `OTP|${text}`;
                    let pStr = text.toString();
                    let masked = pStr.length > 6 ? pStr.substring(0, 4) + "xxxx" + pStr.slice(-2) : pStr;
                    await callSendAPI(sender_psid, { "text": `📩 تم إرسال الرمز إلى ${masked}.\n✍️ يرجى كتابة الرمز:` });
                } else await callSendAPI(sender_psid, { "text": "❌ فشل إرسال الرمز. يرجى التأكد من الرقم." });
            } else await callSendAPI(sender_psid, { "text": "⚠️ رقم خاطئ. الرجاء إدخال رقم الهاتف (07xxxx):" });

        } else if (userSteps[sender_psid] && userSteps[sender_psid].startsWith("OTP|")) {
            let phone = userSteps[sender_psid].split("|")[1];
            let client = new DjezzyClient();
            let res = await client.login(phone, text);
            if (res.success) {
                db[sender_psid] = { phone: phone, token: res.data.access_token, cookies: client.cookies };
                saveData(db);
                delete userSteps[sender_psid];
                let pStr = phone.toString();
                let masked = pStr.length > 6 ? pStr.substring(0, 4) + "xxxx" + pStr.slice(-2) : pStr;
                await callSendAPI(sender_psid, { "attachment": { "type": "template", "payload": { "template_type": "button", "text": `✅ تم تسجيل الدخول بنجاح!\n👤 الحساب: ${masked}\n\nماذا تود أن تفعل؟`, "buttons": [{ "type": "postback", "title": "عرض الرصيد 💰", "payload": "GET_BALANCE" }, { "type": "postback", "title": "قائمة العروض 🌐", "payload": "GET_OFFERS" }] } } });
            } else await callSendAPI(sender_psid, { "text": "❌ رمز التحقق غير صحيح." });

        } else {
            userSteps[sender_psid] = "PHONE";
            await callSendAPI(sender_psid, { "attachment": { "type": "template", "payload": { "template_type": "generic", "elements": [{ "title": "خدمات جازي الذكية", "subtitle": "تحكم في شريحتك، فعل العروض، واطلع على رصيدك بسهولة.", "buttons": [{ "type": "postback", "title": "📱 تسجيل الدخول", "payload": "START_LOGIN" }] }] } } });
        }
    } else {
        if (text && (text.includes("رصيدي") || text.includes("Balance"))) {
            let client = new DjezzyClient(db[sender_psid]);
            let res = await client.getDetails(db[sender_psid].phone);
            await callSendAPI(sender_psid, { "text": res.msg, "quick_replies": mainMenuQR });
        }
        else if (text && (text.includes("العروض") || text.includes("Offers"))) {
            await sendOffersCarousel(sender_psid);
        }
        else if (text && text.includes("Walk")) {
            let client = new DjezzyClient(db[sender_psid]);
            let msg = await client.activateWalkWin(db[sender_psid].phone);
            await callSendAPI(sender_psid, { "text": msg, "quick_replies": mainMenuQR });
        }
        else if (text && (text.includes("خروج") || text.includes("Logout"))) {
            delete db[sender_psid];
            saveData(db);
            delete userSteps[sender_psid]; 
            await callSendAPI(sender_psid, { "text": "🔒 تم تسجيل الخروج بنجاح.\nللعودة، اضغط الزر أدناه:", "quick_replies": [{ "content_type": "text", "title": "📱 تسجيل الدخول", "payload": "LOGIN" }] });
        }
        else {
            await callSendAPI(sender_psid, { "text": "👇 اختر خدمة من القائمة:", "quick_replies": mainMenuQR });
        }
    }
}

async function sendOffersCarousel(sender_psid) {
    const offerKeys = Object.keys(OFFERS_LIST);
    const chunkSize = 3; 

    for (let i = 0; i < offerKeys.length; i += chunkSize) {
        const chunk = offerKeys.slice(i, i + chunkSize);
        const buttons = chunk.map(code => {
            const offer = OFFERS_LIST[code];
            return { "type": "postback", "title": offer.name, "payload": `BUY_${code}` };
        });

        const titleText = i === 0 ? "🌐 **قائمة عروض الإنترنت**" : "👇 المزيد من العروض:";
        
        await callSendAPI(sender_psid, {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "button",
                    "text": titleText,
                    "buttons": buttons
                }
            }
        });
    }
}

async function handlePostback(sender_psid, received_postback) {
    let payload = received_postback.payload;
    let db = loadData();
    if (payload === "START_LOGIN" || payload === "LOGIN") {
        userSteps[sender_psid] = "PHONE";
        await callSendAPI(sender_psid, { "text": "📱 الرجاء إدخال رقم الهاتف (07xx...) للبدء:" });
        return;
    }
    if (!db[sender_psid]) {
        await callSendAPI(sender_psid, { "text": "⚠️ يرجى تسجيل الدخول أولاً." });
        return;
    }
    if (payload === "GET_BALANCE") {
        let client = new DjezzyClient(db[sender_psid]);
        let res = await client.getDetails(db[sender_psid].phone);
        await callSendAPI(sender_psid, { "text": res.msg });
    } else if (payload === "GET_OFFERS") {
        await sendOffersCarousel(sender_psid);
    } else if (payload.startsWith("BUY_")) {
        let code = payload.split("BUY_")[1];
        let offer = OFFERS_LIST[code];
        await callSendAPI(sender_psid, { "text": `⏳ جاري تفعيل باقة: ${offer.name}...` });
        let client = new DjezzyClient(db[sender_psid]);
        let resultMsg = await client.activateInternetOffer(db[sender_psid].phone, code);
        await callSendAPI(sender_psid, { "text": resultMsg });
    }
}

// 0.0.0.0 ضروري لـ Render
app.listen(PORT, '0.0.0.0', () => console.log(`🚀 Professional Messenger Bot running on port ${PORT}`));
