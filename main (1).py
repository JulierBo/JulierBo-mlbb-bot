
import json, os
from datetime import datetime
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Load environment variables from .env file
try:
    with open('.env', 'r') as f:
        for line in f:
            if '=' in line:
                key, value = line.strip().split('=', 1)
                os.environ[key] = value
except FileNotFoundError:
    pass

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID", "0"))
DATA_FILE = "data.json"

# Authorized users - only these users can use the bot
AUTHORIZED_USERS = set()

# User states for restricting actions after screenshot
user_states = {}

# AI states for users
ai_users = set()

# Bot maintenance mode
bot_maintenance = {
    "orders": True,    # True = enabled, False = disabled
    "topups": True,    # True = enabled, False = disabled
    "general": True    # True = enabled, False = disabled
}

def is_user_authorized(user_id):
    """Check if user is authorized to use the bot"""
    return str(user_id) in AUTHORIZED_USERS or int(user_id) == ADMIN_ID

def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump({"users": {}, "prices": {}}, f)
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_authorized_users():
    """Load authorized users from data file"""
    global AUTHORIZED_USERS
    data = load_data()
    AUTHORIZED_USERS = set(data.get("authorized_users", []))

def save_authorized_users():
    """Save authorized users to data file"""
    data = load_data()
    data["authorized_users"] = list(AUTHORIZED_USERS)
    save_data(data)

def load_prices():
    """Load custom prices from data file"""
    data = load_data()
    return data.get("prices", {})

def save_prices(prices):
    """Save prices to data file"""
    data = load_data()
    data["prices"] = prices
    save_data(data)

def validate_game_id(game_id):
    """Validate MLBB Game ID (6-10 digits)"""
    if not game_id.isdigit():
        return False
    if len(game_id) < 6 or len(game_id) > 10:
        return False
    return True

def validate_server_id(server_id):
    """Validate MLBB Server ID (3-5 digits)"""
    if not server_id.isdigit():
        return False
    if len(server_id) < 3 or len(server_id) > 5:
        return False
    return True

def is_banned_account(game_id):
    """
    Check if MLBB account is banned
    This is a simple example - in reality you'd need to integrate with MLBB API
    For now, we'll use some common patterns of banned accounts
    """
    # Add known banned account IDs here
    banned_ids = [
        "123456789",  # Example banned ID
        "000000000",  # Invalid pattern
        "111111111",  # Invalid pattern
    ]

    # Check if game_id matches banned patterns
    if game_id in banned_ids:
        return True

    # Check for suspicious patterns (all same digits, too simple patterns)
    if len(set(game_id)) == 1:  # All same digits like 111111111
        return True

    if game_id.startswith("000") or game_id.endswith("000"):
        return True

    return False

def get_price(diamonds):
    # Load custom prices first
    custom_prices = load_prices()
    if diamonds in custom_prices:
        return custom_prices[diamonds]
    
    # Default prices
    if diamonds.startswith("wp") and diamonds[2:].isdigit():
        n = int(diamonds[2:])
        if 1 <= n <= 10:
            return n * 6500
    table = {
        "11": 950, "22": 1900, "33": 2850, "56": 4200, "112": 8200,
        "86": 5100, "172": 10200, "257": 15300, "343": 20400,
        "429": 25500, "514": 30600, "600": 35700, "706": 40800,
        "878": 51000, "963": 56100, "1049": 61200, "1135": 66300,
        "1412": 81600, "2195": 122400, "3688": 204000,
        "5532": 306000, "9288": 510000, "12976": 714000,
        "55": 3500, "165": 10000, "275": 16000, "565": 33000
    }
    return table.get(diamonds)

def is_payment_screenshot(update):
    """
    Check if the image is likely a payment screenshot
    This is a basic validation - you can enhance it with image analysis
    """
    # For now, we'll accept all photos as payment screenshots
    # You can add image analysis here to check for payment app UI elements
    if update.message.photo:
        # Check if photo has caption containing payment keywords
        caption = update.message.caption or ""
        payment_keywords = ["kpay", "wave", "payment", "pay", "transfer", "လွှဲ", "ငွေ"]
        
        # Accept all photos for now, but you can add more validation here
        return True
    return False

def ai_reply(message_text):
    """
    Enhanced AI-like responses for common queries
    """
    message_lower = message_text.lower()
    
    # Greetings
    if any(word in message_lower for word in ["hello", "hi", "မင်္ဂလာပါ", "ဟယ်လို", "ဟိုင်း", "ကောင်းလား"]):
        return ("👋 မင်္ဂလာပါ! MLBB Diamond Top-up Bot မှ ကြိုဆိုပါတယ်!\n\n"
                "🤖 AI Assistant နဲ့ စကားပြောနေပါတယ်\n"
                "📱 Bot commands များ သုံးရန် `/start` နှိပ်ပါ\n"
                "🔊 AI နဲ့ ပိုများ စကားပြောချင်ရင် `/aistart` နှိပ်ပါ")
    
    # Help requests
    elif any(word in message_lower for word in ["help", "ကူညီ", "အကူအညီ", "မသိ", "လမ်းညွှန်"]):
        return ("🤖 **AI Assistant အကူအညီ** 🤖\n\n"
                "📱 **အသုံးပြုနိုင်တဲ့ commands:**\n"
                "• `/start` - Bot စတင်အသုံးပြုရန်\n"
                "• `/mmb gameid serverid amount` - Diamond ဝယ်ယူရန်\n"
                "• `/balance` - လက်ကျန်ငွေ စစ်ရန်\n"
                "• `/topup amount` - ငွေဖြည့်ရန်\n"
                "• `/price` - ဈေးနှုန်းများ ကြည့်ရန်\n"
                "• `/history` - မှတ်တမ်းများ ကြည့်ရန်\n"
                "• `/aistart` - AI နဲ့ စကားပြောရန်\n"
                "• `/stopai` - AI ကို ရပ်ရန်\n\n"
                "💡 အသေးစိတ် လိုအပ်ရင် admin ကို ဆက်သွယ်ပါ!")
    
    # Price inquiries
    elif any(word in message_lower for word in ["price", "ဈေး", "နှုန်း", "ကြေး", "စျေး"]):
        return ("💎 **Diamond ဈေးနှုန်းများ** 💎\n\n"
                "📊 လက်ရှိ ဈေးနှုန်းများ သိရှိလိုရင် `/price` command ကို သုံးပါ!\n\n"
                "🔥 **အထူး ကမ်းလှမ်းချက်များ:**\n"
                "• Weekly Pass: 6,500 MMK မှ\n"
                "• Diamond 11: 950 MMK\n"
                "• Diamond 86: 5,100 MMK\n"
                "• အကြီးဆုံး 12976 Diamonds: 714,000 MMK\n\n"
                "✨ မြန်ဆန်သော delivery - 5-30 မိနစ်!")
    
    # Diamond related
    elif any(word in message_lower for word in ["diamond", "မှတ်တံ", "ရတနာ", "ဒိုင်မွန်"]):
        return ("💎 **MLBB Diamond Top-up Service** 💎\n\n"
                "🎮 **လုပ်ဆောင်ချက်များ:**\n"
                "• Weekly Pass မှ 12976 Diamonds အထိ\n"
                "• ⚡ မြန်ဆန်သော delivery (5-30 မိနစ်)\n"
                "• 💳 အလွယ်တကူ ငွေဖြည့်မှု\n"
                "• 🔒 လုံခြုံသော transaction\n"
                "• 24/7 Customer Support\n\n"
                "📝 **မှာယူနည်း:**\n"
                "`/mmb gameid serverid amount`\n\n"
                "**ဥပမာ:** `/mmb 123456789 12345 wp1`")
    
    # Topup related
    elif any(word in message_lower for word in ["topup", "ငွေဖြည့်", "ငွေထည့်", "balance", "လက်ကျန်"]):
        return ("💳 **ငွေဖြည့်လုပ်ငန်းစဉ်** 💳\n\n"
                "🔢 **အဆင့်များ:**\n"
                "1️⃣ `/topup amount` ရေးပါ (အနည်းဆုံး 1,000 MMK)\n"
                "2️⃣ KPay/Wave ကို ငွေလွှဲပါ\n"
                "3️⃣ Payment Screenshot တင်ပါ\n"
                "4️⃣ Admin confirm စောင့်ပါ (24 နာရီအတွင်း)\n\n"
                "💰 **လက်ခံနိုင်တဲ့ Payment:**\n"
                "📱 KBZ Pay: 09678786528\n"
                "📱 Wave Money: 09673585480\n\n"
                "✅ လက်ကျန်ငွေ စစ်ရန် `/balance` သုံးပါ!")
    
    # Error/Problem related
    elif any(word in message_lower for word in ["error", "problem", "ပြဿနာ", "အမှား", "မရ", "ရမလာ"]):
        return ("🔧 **Technical Support** 🔧\n\n"
                "❗ **အမှား/ပြဿနာ ရှိပါသလား?**\n\n"
                "🔍 **စစ်ဆေးရမည့်အရာများ:**\n"
                "• Command format မှန်ကန်စွာ ရေးထားမလား\n"
                "• Bot အသုံးပြုခွင့် ရှိမရှိ\n"
                "• လက်ကျန်ငွေ လုံလောက်မလား\n"
                "• Account ban မဖြစ်နေမလား\n\n"
                "🔄 **ဖြေရှင်းနည်းများ:**\n"
                "• `/start` နှိပ်ပြီး ပြန်စမ်းကြည့်ပါ\n"
                "• Admin ကို ဆက်သွယ်ပါ\n"
                "• Bot restart စောင့်ပါ\n\n"
                "📞 24/7 Support ရရှိနိုင်ပါတယ်!")
    
    # Payment methods
    elif any(word in message_lower for word in ["kpay", "wave", "ငွေလွှဲ", "payment", "pay"]):
        return ("💳 **Payment Methods** 💳\n\n"
                "📱 **KBZ Pay (KPay)**\n"
                "Number: `09678786528`\n"
                "Name: Ma May Phoo Wai\n\n"
                "📱 **Wave Money**\n"
                "Number: `09673585480`\n"
                "Name: Nine Nine\n\n"
                "⚠️ **လေ့လာရန်:**\n"
                "• ငွေလွှဲပြီးရင် screenshot ကို တင်ပေးပါ\n"
                "• Name မှန်ကန်စွာ လွှဲပေးပါ\n"
                "• 24 နာရီအတွင်း confirm ရပါမယ်\n"
                "• မမှန်ကန်သော transfer များကို လက်မခံပါ")
    
    # Game related
    elif any(word in message_lower for word in ["mlbb", "mobile legend", "mobile legends", "game", "ဂိမ်း"]):
        return ("🎮 **Mobile Legends: Bang Bang** 🎮\n\n"
                "🔥 **ရပ်မနေပါနဲ့! ဒီကနေ diamonds တွေ ဝယ်ပါ!**\n\n"
                "⚡ **အမြန်ဆုံး Service:**\n"
                "• 5-30 မိနစ်အတွင်း delivery\n"
                "• Account safety 100% guaranteed\n"
                "• အတုမရှိ diamonds\n"
                "• Ban risk မရှိပါ\n\n"
                "💎 **ရရှိနိုင်တဲ့ Items:**\n"
                "• Weekly Pass (wp1-wp10)\n"
                "• Regular Diamonds (11-12976)\n"
                "• 2X Diamond Pass\n\n"
                "🎯 **Game ID နဲ့ Server ID သာ လိုအပ်ပါတယ်!**")
    
    # Thanks/Appreciation
    elif any(word in message_lower for word in ["thanks", "thank you", "ကျေးဇူး", "ကျေးဇူးတင်", "အားပေး"]):
        return ("😊 **ကျေးဇူးတင်ပါတယ်!** 🙏\n\n"
                "🎉 MLBB Diamond Top-up Bot ကို အသုံးပြုအားပေးတဲ့အတွက် ကျေးဇူးအများကြီး တင်ပါတယ်!\n\n"
                "💪 **ကျွန်တော်တို့ရဲ့ ကတိများ:**\n"
                "• အမြန်ဆုံး service\n"
                "• စိတ်ချရသော transaction\n"
                "• 24/7 customer support\n"
                "• အကောင်းဆုံး ဈေးနှုန်း\n\n"
                "🎮 **Happy Gaming!** 🎮\n"
                "မင်းရဲ့ MLBB journey မှာ ကျွန်တော်တို့လည်း ပါဝင်ခွင့်ရလို့ ဝမ်းသာပါတယ်!")
    
    # Bot features
    elif any(word in message_lower for word in ["bot", "ဘော့", "feature", "လုပ်ဆောင်ချက်"]):
        return ("🤖 **Advanced Bot Features** 🤖\n\n"
                "🚀 **AI-Powered Assistant:**\n"
                "• Intelligent conversation\n"
                "• 24/7 customer support\n"
                "• Multi-language support\n"
                "• Smart problem solving\n\n"
                "⚡ **Fast Processing:**\n"
                "• Instant order processing\n"
                "• Real-time balance updates\n"
                "• Quick payment confirmation\n"
                "• Auto delivery system\n\n"
                "🔒 **Security Features:**\n"
                "• Secure payment system\n"
                "• User authorization\n"
                "• Transaction history\n"
                "• Admin monitoring\n\n"
                "💡 `/aistart` နဲ့ AI နဲ့ ပိုများ စကားပြောနိုင်ပါတယ်!")
    
    # Order related
    elif any(word in message_lower for word in ["order", "အော်ဒါ", "မှာ", "ဝယ်"]):
        return ("🛒 **Order Management System** 🛒\n\n"
                "📋 **မှာယူနည်း:**\n"
                "`/mmb gameid serverid amount`\n\n"
                "**ဥပမာများ:**\n"
                "• `/mmb 123456789 12345 wp1` (Weekly Pass)\n"
                "• `/mmb 123456789 12345 86` (86 Diamonds)\n"
                "• `/mmb 123456789 12345 1412` (1412 Diamonds)\n\n"
                "✅ **Order Status များ:**\n"
                "• Processing: အတည်ပြုနေဆဲ\n"
                "• Completed: ပြီးမြောက်ပြီ\n\n"
                "📊 Order history ကြည့်ရန် `/history` သုံးပါ\n"
                "💳 လက်ကျန်ငွေ စစ်ရန် `/balance` သုံးပါ")
    
    # Time related
    elif any(word in message_lower for word in ["အချိန်", "time", "နာရီ", "မိနစ်", "မြန်", "ဖြန့်ခြင်း"]):
        return ("⏰ **Delivery Time Information** ⏰\n\n"
                "🚀 **မြန်ဆန်သော Service:**\n"
                "• Normal Orders: 5-30 မিနစ်\n"
                "• Peak Hours: 15-45 မိနစ်\n"
                "• Weekend: 10-60 မိနစ်\n\n"
                "📈 **အချိန်သက်သေများ:**\n"
                "• 95% orders delivered within 30 minutes\n"
                "• Average delivery time: 15 minutes\n"
                "• Fastest delivery: 3 minutes\n\n"
                "⚡ **မြန်ဆန်အောင် လုပ်နည်း:**\n"
                "• လက်ကျန်ငွေ အလုံအလောက် ရှိအောင်\n"
                "• Game ID နဲ့ Server ID မှန်ကန်အောင်\n"
                "• Peak time မဟုတ်တဲ့အချိန် မှာယူခြင်း")
    
    # Default response with more personality
    else:
        responses = [
            ("🤖 **AI Assistant** လေ့လာနေပါသေးတယ်!\n\n"
             "💭 သင့်မေးခွန်းကို ကောင်းကောင်း နားမလည်သေးပါ။\n\n"
             "💡 **လုပ်နိုင်တာများ:**\n"
             "• `/start` - Bot commands ကြည့်ရန်\n"
             "• `/aistart` - AI နဲ့ ပြောဆိုရန်\n"
             "• `/help` - အကူညီရယူရန်\n\n"
             "🙋‍♂️ Admin ကို ဆက်သွယ်လည်း ရပါတယ်!"),
            
            ("🎯 **သင့်မေးခွန်းကို ပိုရှင်းပြပေးပါ!**\n\n"
             "🤖 AI က အောက်ပါအကြောင်းအရာများကို နားလည်ပါတယ်:\n"
             "• MLBB Diamond orders\n"
             "• Payment methods\n"
             "• Bot commands\n"
             "• Technical support\n"
             "• Price information\n\n"
             "💬 ပိုရှင်းပြပြီး ပြန်မေးကြည့်ပါ!"),
            
            ("🌟 **AI Learning Mode** 🌟\n\n"
             "🧠 သင့်မေးခွန်းကနေ သင်ယူနေပါတယ်!\n\n"
             "📚 **အောက်ပါ keywords တွေ သုံးကြည့်ပါ:**\n"
             "• 'diamond' - Diamond အကြောင်း\n"
             "• 'price' - ဈေးနှုန်းများ\n"
             "• 'help' - အကူညီ\n"
             "• 'topup' - ငွေဖြည့်ခြင်း\n"
             "• 'order' - အော်ဒါများ\n\n"
             "🎮 MLBB နဲ့ ဆိုင်တဲ့ ဘာမဆို မေးလို့ရပါတယ်!")
        ]
        import random
        return random.choice(responses)

pending_topups = {}

async def check_pending_topup(user_id):
    """Check if user has pending topups"""
    data = load_data()
    user_data = data["users"].get(user_id, {})

    for topup in user_data.get("topups", []):
        if topup.get("status") == "pending":
            return True
    return False

async def send_pending_topup_warning(update: Update):
    """Send pending topup warning message"""
    await update.message.reply_text(
        "⏳ **Pending Topup ရှိနေပါတယ်!**\n\n"
        "❌ သင့်မှာ admin က approve မလုပ်သေးတဲ့ topup ရှိနေပါတယ်။\n\n"
        "**လုပ်ရမည့်အရာများ**:\n"
        "• Admin က topup ကို approve လုပ်ပေးတဲ့အထိ စောင့်ပါ\n"
        "• Approve ရပြီးမှ command တွေကို ပြန်အသုံးပြုနိုင်ပါမယ်\n\n"
        "📞 အရေးပေါ်ဆိုရင် admin ကို ဆက်သွယ်ပါ။\n"
        "💡 `/balance` နဲ့ status စစ်ကြည့်နိုင်ပါတယ်။",
        parse_mode="Markdown"
    )

async def check_maintenance_mode(command_type):
    """Check if specific command type is in maintenance mode"""
    return bot_maintenance.get(command_type, True)

async def send_maintenance_message(update: Update, command_type):
    """Send maintenance mode message"""
    if command_type == "orders":
        msg = "🔧 **အော်ဒါ လုပ်ဆောင်ချက် ယာယီ ပိတ်ထားပါ**\n\nAdmin က ပြန်ဖွင့်ပေးတဲ့အခါ အသုံးပြုနိုင်ပါမယ်။"
    elif command_type == "topups":
        msg = "🔧 **ငွေဖြည့်လုပ်ဆောင်ချက် ယာယီ ပိတ်ထားပါ**\n\nAdmin က ပြန်ဖွင့်ပေးတဲ့အခါ အသုံးပြုနိုင်ပါမယ်။"
    else:
        msg = "🔧 **Bot ယာယီ Maintenance ဖြစ်နေပါတယ်**\n\nAdmin က ပြန်ဖွင့်ပေးတဲ့အခါ အသုံးပြုနိုင်ပါမယ်။"
    
    await update.message.reply_text(msg)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    username = user.username or "-"
    name = f"{user.first_name} {user.last_name or ''}".strip()
    
    # Load authorized users
    load_authorized_users()
    
    # Check if user is authorized
    if not is_user_authorized(user_id):
        # Create keyboard with Owner contact button
        keyboard = [[InlineKeyboardButton("👑 Contact Owner", url=f"tg://user?id={ADMIN_ID}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🚫 **Bot အသုံးပြုခွင့် မရှိပါ!**\n\n"
            f"👋 မင်္ဂလာပါ `{name}`!\n"
            f"🆔 Your ID: `{user_id}`\n\n"
            "❌ သင်သည် ဤ bot ကို အသုံးပြုခွင့် မရှိသေးပါ။\n\n"
            "**လုပ်ရမည့်အရာများ**:\n"
            "• အောက်က 'Contact Owner' button ကို နှိပ်ပါ\n"
            "• Owner ထံ bot အသုံးပြုခွင့် တောင်းဆိုပါ\n"
            "• သင့် User ID ကို ပေးပို့ပါ\n\n"
            "✅ Owner က approve လုပ်ပြီးမှ bot ကို အသုံးပြုနိုင်ပါမယ်။",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        return

    data = load_data()

    # Check for pending topups first
    if await check_pending_topup(user_id):
        await send_pending_topup_warning(update)
        return

    if user_id not in data["users"]:
        data["users"][user_id] = {
            "name": name,
            "username": username,
            "balance": 0,
            "orders": [],
            "topups": []
        }
        save_data(data)

    # Clear any restricted state when starting
    if user_id in user_states:
        del user_states[user_id]

    # Create keyboard with Owner contact button
    keyboard = [[InlineKeyboardButton("👑 Contact Owner", url=f"tg://user?id={ADMIN_ID}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    msg = (
        f"👋 မင်္ဂလာပါ `{name}`!\n"
        f"🆔 Telegram User ID: `{user_id}`\n\n"
        "📱 MLBB Diamond Top-up Bot မှ ကြိုဆိုပါတယ်။\n\n"
        "**အသုံးပြုနိုင်တဲ့ command များ**:\n"
        "➤ `/mmb gameid serverid amount`\n"
        "➤ `/balance` - ဘယ်လောက်လက်ကျန်ရှိလဲ စစ်မယ်\n"
        "➤ `/topup amount` - ငွေဖြည့်မယ် (screenshot တင်ပါ)\n"
        "➤ `/price` - Diamond များရဲ့ ဈေးနှုန်းများ\n"
        "➤ `/history` - အော်ဒါမှတ်တမ်းကြည့်မယ်\n"
        "➤ `/aistart` - AI နဲ့ စကားပြောမယ်\n"
        "➤ `/stopai` - AI ကို ရပ်မယ်\n\n"
        "**📌 ဥပမာ**:\n"
        "`/mmb 123456789 12345 wp1`\n"
        "`/mmb 123456789 12345 86`\n\n"
        "လိုအပ်တာရှိရင် Owner ကို ဆက်သွယ်နိုင်ပါတယ်။ 😊"
    )
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=reply_markup)

async def mmb_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    # Check authorization
    load_authorized_users()
    if not is_user_authorized(user_id):
        keyboard = [[InlineKeyboardButton("👑 Contact Owner", url=f"tg://user?id={ADMIN_ID}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🚫 **အသုံးပြုခွင့် မရှိပါ!**\n\n"
            "Owner ထံ bot အသုံးပြုခွင့် တောင်းဆိုပါ။",
            reply_markup=reply_markup
        )
        return

    # Check maintenance mode
    if not await check_maintenance_mode("orders"):
        await send_maintenance_message(update, "orders")
        return

    # Check if user is restricted after screenshot
    if user_id in user_states and user_states[user_id] == "waiting_approval":
        await update.message.reply_text(
            "⏳ **Screenshot ပို့ပြီးပါပြီ!**\n\n"
            "❌ Admin က လက်ခံပြီးကြောင်း အတည်ပြုတဲ့အထိ commands တွေ အသုံးပြုလို့ မရပါ။\n\n"
            "⏰ Admin က approve လုပ်ပြီးမှ ပြန်လည် အသုံးပြုနိုင်ပါမယ်။\n"
            "📞 အရေးပေါ်ဆိုရင် admin ကို ဆက်သွယ်ပါ။",
            parse_mode="Markdown"
        )
        return

    # Check for pending topups first
    if await check_pending_topup(user_id):
        await send_pending_topup_warning(update)
        return

    args = context.args

    if len(args) != 3:
        await update.message.reply_text(
            "❌ အမှားရှိပါတယ်!\n\n"
            "**မှန်ကန်တဲ့ format**:\n"
            "`/mmb gameid serverid amount`\n\n"
            "**ဥပမာ**:\n"
            "`/mmb 123456789 12345 wp1`\n"
            "`/mmb 123456789 12345 86`",
            parse_mode="Markdown"
        )
        return

    game_id, server_id, amount = args

    # Validate Game ID
    if not validate_game_id(game_id):
        await update.message.reply_text(
            "❌ Game ID မှားနေပါတယ်!\n\n"
            "**Game ID requirements**:\n"
            "• ကိန်းဂဏန်းများသာ ပါရမည်\n"
            "• 6-10 digits ရှိရမည်\n\n"
            "**ဥပမာ**: `123456789`",
            parse_mode="Markdown"
        )
        return

    # Validate Server ID
    if not validate_server_id(server_id):
        await update.message.reply_text(
            "❌ Server ID မှားနေပါတယ်!\n\n"
            "**Server ID requirements**:\n"
            "• ကိန်းဂဏန်းများသာ ပါရမည်\n"
            "• 3-5 digits ရှိရမည်\n\n"
            "**ဥပမာ**: `8662`, `12345`",
            parse_mode="Markdown"
        )
        return

    # Check if account is banned
    if is_banned_account(game_id):
        await update.message.reply_text(
            "🚫 **Account Ban ဖြစ်နေပါတယ်!**\n\n"
            f"🎮 Game ID: `{game_id}`\n"
            f"🌐 Server ID: `{server_id}`\n\n"
            "❌ ဒီ account မှာ diamond topup လုပ်လို့ မရပါ။\n\n"
            "**အကြောင်းရင်းများ**:\n"
            "• Account suspended/banned ဖြစ်နေခြင်း\n"
            "• Invalid account pattern\n"
            "• MLBB မှ ပိတ်ပင်ထားခြင်း\n\n"
            "🔄 အခြား account သုံးပြီး ထပ်ကြိုးစားကြည့်ပါ။\n"
            "📞 ပြဿနာရှိရင် admin ကို ဆက်သွယ်ပါ။",
            parse_mode="Markdown"
        )

        # Notify admin about banned account attempt
        admin_msg = (
            f"🚫 **Banned Account Topup ကြိုးစားမှု**\n\n"
            f"👤 User: {update.effective_user.first_name}\n"
            f"🆔 User ID: `{user_id}`\n"
            f"🎮 Game ID: `{game_id}`\n"
            f"🌐 Server ID: `{server_id}`\n"
            f"💎 Amount: {amount}\n"
            f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            "⚠️ ဒီ account မှာ topup လုပ်လို့ မရပါ။"
        )

        try:
            await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode="Markdown")
        except:
            pass

        return

    price = get_price(amount)

    if not price:
        await update.message.reply_text(
            "❌ Diamond amount မှားနေပါတယ်!\n\n"
            "**ရရှိနိုင်တဲ့ amounts**:\n"
            "• Weekly Pass: wp1-wp10\n"
            "• Diamonds: 11, 22, 33, 56, 86, 112, 172, 257, 343, 429, 514, 600, 706, 878, 963, 1049, 1135, 1412, 2195, 3688, 5532, 9288, 12976",
            parse_mode="Markdown"
        )
        return

    data = load_data()
    user_balance = data["users"].get(user_id, {}).get("balance", 0)

    if user_balance < price:
        await update.message.reply_text(
            f"❌ လက်ကျန်ငွေ မလုံလောက်ပါ!\n\n"
            f"💰 လိုအပ်တဲ့ငွေ: {price:,} MMK\n"
            f"💳 သင့်လက်ကျန်: {user_balance:,} MMK\n"
            f"❗ လိုအပ်သေးတာ: {price - user_balance:,} MMK\n\n"
            "ငွေဖြည့်ရန် `/topup amount` သုံးပါ။",
            parse_mode="Markdown"
        )
        return

    # Process order
    order_id = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}"
    order = {
        "order_id": order_id,
        "game_id": game_id,
        "server_id": server_id,
        "amount": amount,
        "price": price,
        "status": "processing",
        "timestamp": datetime.now().isoformat()
    }

    # Deduct balance
    data["users"][user_id]["balance"] -= price
    data["users"][user_id]["orders"].append(order)
    save_data(data)

    # Notify admin
    admin_msg = (
        f"🔔 **အော်ဒါအသစ်ရောက်ပါပြီ!**\n\n"
        f"📝 Order ID: `{order_id}`\n"
        f"👤 User: {update.effective_user.first_name}\n"
        f"🆔 User ID: `{user_id}`\n"
        f"🎮 Game ID: `{game_id}`\n"
        f"🌐 Server ID: `{server_id}`\n"
        f"💎 Amount: {amount}\n"
        f"💰 Price: {price:,} MMK\n"
        f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode="Markdown")
    except:
        pass

    # Notify admin group
    await notify_group_order(order, update.effective_user.first_name or "Unknown")

    await update.message.reply_text(
        f"✅ **အော်ဒါ အောင်မြင်ပါပြီ!**\n\n"
        f"📝 Order ID: `{order_id}`\n"
        f"🎮 Game ID: `{game_id}`\n"
        f"🌐 Server ID: `{server_id}`\n"
        f"💎 Diamond: {amount}\n"
        f"💰 ကုန်ကျစရိတ်: {price:,} MMK\n"
        f"💳 လက်ကျန်ငွေ: {data['users'][user_id]['balance']:,} MMK\n\n"
        "⚠️ Diamonds များကို 5-30 မိနစ်အတွင်း ရရှိပါမယ်။\n"
        "📞 ပြဿနာရှိရင် admin ကို ဆက်သွယ်ပါ။",
        parse_mode="Markdown"
    )

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    # Check authorization
    load_authorized_users()
    if not is_user_authorized(user_id):
        keyboard = [[InlineKeyboardButton("👑 Contact Owner", url=f"tg://user?id={ADMIN_ID}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🚫 **အသုံးပြုခွင့် မရှိပါ!**\n\n"
            "Owner ထံ bot အသုံးပြုခွင့် တောင်းဆိုပါ။",
            reply_markup=reply_markup
        )
        return

    # Check if user is restricted after screenshot
    if user_id in user_states and user_states[user_id] == "waiting_approval":
        await update.message.reply_text(
            "⏳ **Screenshot ပို့ပြီးပါပြီ!**\n\n"
            "❌ Admin က လက်ခံပြီးကြောင်း အတည်ပြုတဲ့အထိ commands တွေ အသုံးပြုလို့ မရပါ။\n\n"
            "⏰ Admin က approve လုပ်ပြီးမှ ပြန်လည် အသုံးပြုနိုင်ပါမယ်။\n"
            "📞 အရေးပေါ်ဆိုရင် admin ကို ဆက်သွယ်ပါ။",
            parse_mode="Markdown"
        )
        return

    # Check for pending topups first
    if await check_pending_topup(user_id):
        await send_pending_topup_warning(update)
        return

    data = load_data()
    user_data = data["users"].get(user_id)

    if not user_data:
        await update.message.reply_text("❌ အရင်ဆုံး /start နှိပ်ပါ။")
        return

    balance = user_data.get("balance", 0)
    total_orders = len(user_data.get("orders", []))
    total_topups = len(user_data.get("topups", []))

    # Check for pending topups
    pending_topups_count = 0
    pending_amount = 0

    for topup in user_data.get("topups", []):
        if topup.get("status") == "pending":
            pending_topups_count += 1
            pending_amount += topup.get("amount", 0)

    # Escape special characters in name and username
    name = user_data.get('name', 'Unknown')
    username = user_data.get('username', 'None')

    # Remove or escape problematic characters for Markdown
    name = name.replace('*', '').replace('_', '').replace('`', '').replace('[', '').replace(']', '')
    username = username.replace('*', '').replace('_', '').replace('`', '').replace('[', '').replace(']', '')

    status_msg = ""
    if pending_topups_count > 0:
        status_msg = f"\n⏳ **Pending Topups**: {pending_topups_count} ခု ({pending_amount:,} MMK)\n❗ Diamond order ထားလို့မရပါ။ Admin approve စောင့်ပါ။"

    # Create inline keyboard with topup button
    keyboard = [[InlineKeyboardButton("💳 ငွေဖြည့်မယ်", callback_data="topup_button")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"💳 **သင့်ရဲ့ Account အချက်အလက်များ**\n\n"
        f"💰 လက်ကျန်ငွေ: `{balance:,} MMK`\n"
        f"📦 စုစုပေါင်း အော်ဒါများ: {total_orders}\n"
        f"💳 စုစုပေါင်း ငွေဖြည့်မှုများ: {total_topups}{status_msg}\n\n"
        f"👤 နာမည်: {name}\n"
        f"🆔 Username: @{username}",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def topup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    # Check authorization
    load_authorized_users()
    if not is_user_authorized(user_id):
        keyboard = [[InlineKeyboardButton("👑 Contact Owner", url=f"tg://user?id={ADMIN_ID}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🚫 **အသုံးပြုခွင့် မရှိပါ!**\n\n"
            "Owner ထံ bot အသုံးပြုခွင့် တောင်းဆိုပါ။",
            reply_markup=reply_markup
        )
        return

    # Check maintenance mode
    if not await check_maintenance_mode("topups"):
        await send_maintenance_message(update, "topups")
        return

    # Check if user is restricted after screenshot
    if user_id in user_states and user_states[user_id] == "waiting_approval":
        await update.message.reply_text(
            "⏳ **Screenshot ပို့ပြီးပါပြီ!**\n\n"
            "❌ Admin က လက်ခံပြီးကြောင်း အတည်ပြုတဲ့အထိ commands တွေ အသုံးပြုလို့ မရပါ။\n\n"
            "⏰ Admin က approve လုပ်ပြီးမှ ပြန်လည် အသုံးပြုနိုင်ပါမယ်။\n"
            "📞 အရေးပေါ်ဆိုရင် admin ကို ဆက်သွယ်ပါ။",
            parse_mode="Markdown"
        )
        return

    # Check for pending topups first
    if await check_pending_topup(user_id):
        await send_pending_topup_warning(update)
        return

    args = context.args

    if not args:
        # Create payment buttons
        keyboard = [
            [InlineKeyboardButton("📱 Copy KPay Number", callback_data="copy_kpay")],
            [InlineKeyboardButton("📱 Copy Wave Number", callback_data="copy_wave")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "❌ ငွေပမာဏ ထည့်ပါ!\n\n"
            "**ဥပမာ**: `/topup 50000`\n\n"
            "💳 ငွေလွှဲရန် အောက်က buttons များကို သုံးပါ။",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        return

    try:
        amount = int(args[0])
        if amount < 1000:
            await update.message.reply_text("❌ အနည်းဆုံး 1,000 MMK ဖြည့်ပါ။")
            return
    except ValueError:
        await update.message.reply_text("❌ ကိန်းဂဏန်းသာ ထည့်ပါ။")
        return

    # Store pending topup
    pending_topups[user_id] = {
        "amount": amount,
        "timestamp": datetime.now().isoformat()
    }

    # Create payment buttons
    keyboard = [
        [InlineKeyboardButton("📱 Copy KPay Number", callback_data="copy_kpay")],
        [InlineKeyboardButton("📱 Copy Wave Number", callback_data="copy_wave")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"💳 **ငွေဖြည့်လုပ်ငန်းစဉ်**\n\n"
        f"💰 ပမာဏ: `{amount:,} MMK`\n\n"
        "**လွှဲရမည့် Account များ**:\n"
        "📱 KBZ Pay: `09678786528`\n"
        "Name - **Ma May Phoo Wai**\n"
        "📱 Wave Money: `09673585480`\n"
        "Name - **Nine Nine**\n"
        "🏦 CB Bank: အသုံးပြုစဲမရှိသေးပါ\n\n"
        "💸 ငွေလွှဲပြီးရင် screenshot ကို ဒီမှာ တင်ပေးပါ။\n"
        "⏰ 24 နာရီအတွင်း confirm လုပ်ပါမယ်။",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    # Check authorization
    load_authorized_users()
    if not is_user_authorized(user_id):
        keyboard = [[InlineKeyboardButton("👑 Contact Owner", url=f"tg://user?id={ADMIN_ID}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🚫 **အသုံးပြုခွင့် မရှိပါ!**\n\n"
            "Owner ထံ bot အသုံးပြုခွင့် တောင်းဆိုပါ။",
            reply_markup=reply_markup
        )
        return

    # Check if user is restricted after screenshot
    if user_id in user_states and user_states[user_id] == "waiting_approval":
        await update.message.reply_text(
            "⏳ **Screenshot ပို့ပြီးပါပြီ!**\n\n"
            "❌ Admin က လက်ခံပြီးကြောင်း အတည်ပြုတဲ့အထိ commands တွေ အသုံးပြုလို့ မရပါ။\n\n"
            "⏰ Admin က approve လုပ်ပြီးမှ ပြန်လည် အသုံးပြုနိုင်ပါမယ်။\n"
            "📞 အရေးပေါ်ဆိုရင် admin ကို ဆက်သွယ်ပါ။",
            parse_mode="Markdown"
        )
        return

    # Get custom prices
    custom_prices = load_prices()
    
    price_msg = (
        "💎 **MLBB Diamond ဈေးနှုန်းများ**\n\n"
        "🎟️ **Weekly Pass**:\n"
        "• wp1 = 6,500 MMK\n"
        "• wp2 = 13,000 MMK\n"
        "• wp3 = 19,500 MMK\n"
        "• wp4 = 26,000 MMK\n"
        "• wp5 = 32,500 MMK\n"
        "• wp6 = 39,000 MMK\n"
        "• wp7 = 45,500 MMK\n"
        "• wp8 = 52,000 MMK\n"
        "• wp9 = 58,500 MMK\n"
        "• wp10 = 65,000 MMK\n\n"
        "💎 **Regular Diamonds**:\n"
        "• 11 = 950 MMK\n"
        "• 22 = 1,900 MMK\n"
        "• 33 = 2,850 MMK\n"
        "• 56 = 4,200 MMK\n"
        "• 86 = 5,100 MMK\n"
        "• 112 = 8,200 MMK\n"
        "• 172 = 10,200 MMK\n"
        "• 257 = 15,300 MMK\n"
        "• 343 = 20,400 MMK\n"
        "• 429 = 25,500 MMK\n"
        "• 514 = 30,600 MMK\n"
        "• 600 = 35,700 MMK\n"
        "• 706 = 40,800 MMK\n"
        "• 878 = 51,000 MMK\n"
        "• 963 = 56,100 MMK\n"
        "• 1049 = 61,200 MMK\n"
        "• 1135 = 66,300 MMK\n"
        "• 1412 = 81,600 MMK\n"
        "• 2195 = 122,400 MMK\n"
        "• 3688 = 204,000 MMK\n"
        "• 5532 = 306,000 MMK\n"
        "• 9288 = 510,000 MMK\n"
        "• 12976 = 714,000 MMK\n\n"
        "💎 **2X Diamond Pass**:\n"
        "• 55 = 3,500 MMK\n"
        "• 165 = 10,000 MMK\n"
        "• 275 = 16,000 MMK\n"
        "• 565 = 33,000 MMK\n\n"
    )
    
    # Add custom prices if any
    if custom_prices:
        price_msg += "🔥 **Special Prices**:\n"
        for item, price in custom_prices.items():
            price_msg += f"• {item} = {price:,} MMK\n"
        price_msg += "\n"
    
    price_msg += (
        "**📝 အသုံးပြုနည်း**:\n"
        "`/mmb gameid serverid amount`\n\n"
        "**ဥပမာ**:\n"
        "`/mmb 123456789 12345 wp1`\n"
        "`/mmb 123456789 12345 86`"
    )
    
    await update.message.reply_text(price_msg, parse_mode="Markdown")

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    # Check authorization
    load_authorized_users()
    if not is_user_authorized(user_id):
        keyboard = [[InlineKeyboardButton("👑 Contact Owner", url=f"tg://user?id={ADMIN_ID}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🚫 **အသုံးပြုခွင့် မရှိပါ!**\n\n"
            "Owner ထံ bot အသုံးပြုခွင့် တောင်းဆိုပါ။",
            reply_markup=reply_markup
        )
        return

    # Check if user is restricted after screenshot
    if user_id in user_states and user_states[user_id] == "waiting_approval":
        await update.message.reply_text(
            "⏳ **Screenshot ပို့ပြီးပါပြီ!**\n\n"
            "❌ Admin က လက်ခံပြီးကြောင်း အတည်ပြုတဲ့အထိ commands တွေ အသုံးပြုလို့ မရပါ။\n\n"
            "⏰ Admin က approve လုပ်ပြီးမှ ပြန်လည် အသုံးပြုနိုင်ပါမယ်။\n"
            "📞 အရေးပေါ်ဆိုရင် admin ကို ဆက်သွယ်ပါ။",
            parse_mode="Markdown"
        )
        return

    # Check for pending topups first
    if await check_pending_topup(user_id):
        await send_pending_topup_warning(update)
        return

    data = load_data()
    user_data = data["users"].get(user_id)

    if not user_data:
        await update.message.reply_text("❌ အရင်ဆုံး /start နှိပ်ပါ။")
        return

    orders = user_data.get("orders", [])
    topups = user_data.get("topups", [])

    if not orders and not topups:
        await update.message.reply_text("📋 သင့်မှာ မည်သည့် မှတ်တမ်းမှ မရှိသေးပါ။")
        return

    msg = "📋 **သင့်ရဲ့ မှတ်တမ်းများ**\n\n"

    if orders:
        msg += "🛒 **အော်ဒါများ** (နောက်ဆုံး 5 ခု):\n"
        for order in orders[-5:]:
            status_emoji = "✅" if order.get("status") == "completed" else "⏳"
            msg += f"{status_emoji} {order['order_id']} - {order['amount']} ({order['price']:,} MMK)\n"
        msg += "\n"

    if topups:
        msg += "💳 **ငွေဖြည့်များ** (နောက်ဆုံး 5 ခု):\n"
        for topup in topups[-5:]:
            status_emoji = "✅" if topup.get("status") == "approved" else "⏳"
            msg += f"{status_emoji} {topup['amount']:,} MMK - {topup.get('timestamp', 'Unknown')[:10]}\n"

    await update.message.reply_text(msg, parse_mode="Markdown")

async def aistart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    # Check authorization
    load_authorized_users()
    if not is_user_authorized(user_id):
        keyboard = [[InlineKeyboardButton("👑 Contact Owner", url=f"tg://user?id={ADMIN_ID}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🚫 **အသုံးပြုခွင့် မရှိပါ!**\n\n"
            "Owner ထံ bot အသုံးပြုခွင့် တောင်းဆိုပါ။",
            reply_markup=reply_markup
        )
        return

    ai_users.add(user_id)
    
    await update.message.reply_text(
        "🤖 **AI Assistant စတင်ပါပြီ!** 🤖\n\n"
        "🎉 ယခုအခါ AI နဲ့ စကားပြောနိုင်ပါပြီ!\n\n"
        "💬 **လုပ်နိုင်တာများ:**\n"
        "• MLBB အကြောင်း မေးခွန်းများ\n"
        "• Diamond ဈေးနှုန်းများ\n"
        "• Bot အသုံးပြုနည်း\n"
        "• Technical support\n"
        "• Payment information\n\n"
        "🔊 **AI ကို ရပ်ချင်ရင်** `/stopai` သုံးပါ\n"
        "📱 **Bot commands အတွက်** `/start` သုံးပါ\n\n"
        "💡 ဘာမဆို စကားပြောကြည့်ပါ! AI က ပြန်ဖြေပေးပါမယ်! 😊",
        parse_mode="Markdown"
    )

async def stopai_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id in ai_users:
        ai_users.remove(user_id)
        await update.message.reply_text(
            "🤖 **AI Assistant ရပ်လိုက်ပါပြီ!** 🤖\n\n"
            "😴 AI က အနားယူနေပါပြီ။\n\n"
            "🔄 **ပြန်စတင်ချင်ရင်** `/aistart` သုံးပါ\n"
            "📱 **Bot commands အတွက်** `/start` သုံးပါ\n\n"
            "👋 ကျေးဇူးတင်ပါတယ်! AI နဲ့ စကားပြောပေးတဲ့အတွက်! 😊",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "ℹ️ **AI Assistant မစတင်ထားပါ**\n\n"
            "🔄 AI စတင်ရန် `/aistart` သုံးပါ",
            parse_mode="Markdown"
        )

async def approve_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    # Check if user is admin
    if int(user_id) != ADMIN_ID:
        await update.message.reply_text("❌ သင်သည် admin မဟုတ်ပါ!")
        return

    args = context.args
    if len(args) != 2:
        await update.message.reply_text(
            "❌ အမှားရှိပါတယ်!\n\n"
            "**မှန်ကန်တဲ့ format**: `/approve user_id amount`\n"
            "**ဥပမာ**: `/approve 123456789 50000`"
        )
        return

    try:
        target_user_id = args[0]
        amount = int(args[1])
    except ValueError:
        await update.message.reply_text("❌ ငွေပမာဏမှားနေပါတယ်!")
        return

    data = load_data()

    if target_user_id not in data["users"]:
        await update.message.reply_text("❌ User မတွေ့ရှိပါ!")
        return

    # Add balance to user
    data["users"][target_user_id]["balance"] += amount

    # Update topup status
    topups = data["users"][target_user_id]["topups"]
    for topup in reversed(topups):
        if topup["status"] == "pending" and topup["amount"] == amount:
            topup["status"] = "approved"
            topup["approved_at"] = datetime.now().isoformat()
            break

    save_data(data)

    # Clear user restriction state after approval
    if target_user_id in user_states:
        del user_states[target_user_id]

    # Notify user
    try:
        user_msg = (
            f"✅ **ငွေဖြည့်မှု အတည်ပြုပါပြီ!** 🎉\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💰 **ပမာဏ:** `{amount:,} MMK`\n"
            f"💳 **လက်ကျန်ငွေ:** `{data['users'][target_user_id]['balance']:,} MMK`\n"
            f"⏰ **အချိန်:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎉 **ယခုအခါ diamonds များ ဝယ်ယူနိုင်ပါပြီ!** 💎\n\n"
            "⚡ အမြန်ဆုံး diamonds များကို `/mmb` command နဲ့ မှာယူပါ ⚡\n\n"
            "🔓 **Bot လုပ်ဆောင်ချက်များ ပြန်လည် အသုံးပြုနိုင်ပါပြီ!**"
        )
        await context.bot.send_message(chat_id=int(target_user_id), text=user_msg, parse_mode="Markdown")
    except:
        pass

    # Confirm to admin
    await update.message.reply_text(
        f"✅ **Approve အောင်မြင်ပါပြီ!**\n\n"
        f"👤 User ID: `{target_user_id}`\n"
        f"💰 Amount: `{amount:,} MMK`\n"
        f"💳 User's new balance: `{data['users'][target_user_id]['balance']:,} MMK`\n"
        f"🔓 User restrictions cleared!",
        parse_mode="Markdown"
    )

async def deduct_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    # Check if user is admin
    if int(user_id) != ADMIN_ID:
        await update.message.reply_text("❌ သင်သည် admin မဟုတ်ပါ!")
        return

    args = context.args
    if len(args) != 2:
        await update.message.reply_text(
            "❌ အမှားရှိပါတယ်!\n\n"
            "**မှန်ကန်တဲ့ format**: `/deduct user_id amount`\n"
            "**ဥပမာ**: `/deduct 123456789 10000`"
        )
        return

    try:
        target_user_id = args[0]
        amount = int(args[1])
        if amount <= 0:
            await update.message.reply_text("❌ ငွေပမာဏသည် သုညထက် ကြီးရမည်!")
            return
    except ValueError:
        await update.message.reply_text("❌ ငွေပမာဏမှားနေပါတယ်!")
        return

    data = load_data()

    if target_user_id not in data["users"]:
        await update.message.reply_text("❌ User မတွေ့ရှိပါ!")
        return

    current_balance = data["users"][target_user_id]["balance"]

    if current_balance < amount:
        await update.message.reply_text(
            f"❌ **နှုတ်လို့မရပါ!**\n\n"
            f"👤 User ID: `{target_user_id}`\n"
            f"💰 နှုတ်ချင်တဲ့ပမာဏ: `{amount:,} MMK`\n"
            f"💳 User လက်ကျန်ငွေ: `{current_balance:,} MMK`\n"
            f"❗ လိုအပ်သေးတာ: `{amount - current_balance:,} MMK`",
            parse_mode="Markdown"
        )
        return

    # Deduct balance from user
    data["users"][target_user_id]["balance"] -= amount
    save_data(data)

    # Notify user
    try:
        user_msg = (
            f"⚠️ **လက်ကျန်ငွေ နှုတ်ခံရမှု**\n\n"
            f"💰 နှုတ်ခံရတဲ့ပမာဏ: `{amount:,} MMK`\n"
            f"💳 လက်ကျန်ငွေ: `{data['users'][target_user_id]['balance']:,} MMK`\n"
            f"⏰ အချိန်: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            "📞 မေးခွန်းရှိရင် admin ကို ဆက်သွယ်ပါ။"
        )
        await context.bot.send_message(chat_id=int(target_user_id), text=user_msg, parse_mode="Markdown")
    except:
        pass

    # Confirm to admin
    await update.message.reply_text(
        f"✅ **Balance နှုတ်ခြင်း အောင်မြင်ပါပြီ!**\n\n"
        f"👤 User ID: `{target_user_id}`\n"
        f"💰 နှုတ်ခဲ့တဲ့ပမာဏ: `{amount:,} MMK`\n"
        f"💳 User လက်ကျန်ငွေ: `{data['users'][target_user_id]['balance']:,} MMK`",
        parse_mode="Markdown"
    )

async def done_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    # Check if user is admin
    if int(user_id) != ADMIN_ID:
        await update.message.reply_text("❌ သင်သည် admin မဟုတ်ပါ!")
        return
        
    args = context.args
    if len(args) != 1 or not args[0].isdigit():
        await update.message.reply_text("❌ မှန်ကန်တဲ့အတိုင်း: /done <user_id>")
        return

    target_user_id = int(args[0])
    try:
        await context.bot.send_message(
            chat_id=target_user_id,
            text="🙏 ဝယ်ယူအားပေးမှုအတွက် ကျေးဇူးအများကြီးတင်ပါတယ်။\n\n✅ Order Done! 🎉"
        )
        await update.message.reply_text("✅ User ထံ message ပေးပြီးပါပြီ။")
    except:
        await update.message.reply_text("❌ User ID မှားနေပါတယ်။ Message မပို့နိုင်ပါ။")

async def reply_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    # Check if user is admin
    if int(user_id) != ADMIN_ID:
        await update.message.reply_text("❌ သင်သည် admin မဟုတ်ပါ!")
        return
        
    args = context.args
    if len(args) < 2 or not args[0].isdigit():
        await update.message.reply_text("❌ မှန်ကန်တဲ့အတိုင်း: /reply <user_id> <message>")
        return

    target_user_id = int(args[0])
    message = " ".join(args[1:])
    try:
        await context.bot.send_message(
            chat_id=target_user_id,
            text=message
        )
        await update.message.reply_text("✅ Message ပေးပြီးပါပြီ။")
    except:
        await update.message.reply_text("❌ Message မပို့နိုင်ပါ။")

async def authorize_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    # Check if user is admin
    if int(user_id) != ADMIN_ID:
        await update.message.reply_text("❌ သင်သည် admin မဟုတ်ပါ!")
        return
        
    args = context.args
    if len(args) != 1 or not args[0].isdigit():
        await update.message.reply_text("❌ မှန်ကန်တဲ့အတိုင်း: /authorize <user_id>")
        return

    target_user_id = args[0]
    load_authorized_users()
    
    if target_user_id in AUTHORIZED_USERS:
        await update.message.reply_text("ℹ️ User ကို အရင်က authorize လုပ်ထားပြီးပါပြီ။")
        return
    
    AUTHORIZED_USERS.add(target_user_id)
    save_authorized_users()
    
    # Clear any restrictions when authorizing
    if target_user_id in user_states:
        del user_states[target_user_id]
    
    # Notify user
    try:
        await context.bot.send_message(
            chat_id=int(target_user_id),
            text="🎉 **Bot အသုံးပြုခွင့် ရရှိပါပြီ!**\n\n"
                 "✅ Owner က သင့်ကို bot အသုံးပြုခွင့် ပေးပါပြီ။\n\n"
                 "🚀 ယခုအခါ `/start` နှိပ်ပြီး bot ကို အသုံးပြုနိုင်ပါပြီ!"
        )
    except:
        pass
    
    await update.message.reply_text(
        f"✅ **User Authorize အောင်မြင်ပါပြီ!**\n\n"
        f"👤 User ID: `{target_user_id}`\n"
        f"🎯 Status: Authorized\n"
        f"📝 Total authorized users: {len(AUTHORIZED_USERS)}",
        parse_mode="Markdown"
    )

async def unauthorize_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    # Check if user is admin
    if int(user_id) != ADMIN_ID:
        await update.message.reply_text("❌ သင်သည် admin မဟုတ်ပါ!")
        return
        
    args = context.args
    if len(args) != 1 or not args[0].isdigit():
        await update.message.reply_text("❌ မှန်ကန်တဲ့အတိုင်း: /unauthorize <user_id>")
        return

    target_user_id = args[0]
    load_authorized_users()
    
    if target_user_id not in AUTHORIZED_USERS:
        await update.message.reply_text("ℹ️ User သည် authorize မလုပ်ထားပါ။")
        return
    
    AUTHORIZED_USERS.remove(target_user_id)
    save_authorized_users()
    
    # Notify user
    try:
        await context.bot.send_message(
            chat_id=int(target_user_id),
            text="⚠️ **Bot အသုံးပြုခွင့် ရုပ်သိမ်းခံရမှု**\n\n"
                 "❌ Owner က သင့်ရဲ့ bot အသုံးပြုခွင့်ကို ရုပ်သိမ်းလိုက်ပါပြီ။\n\n"
                 "📞 ပြန်လည် အသုံးပြုရန် Owner ကို ဆက်သွယ်ပါ။"
        )
    except:
        pass
    
    await update.message.reply_text(
        f"✅ **User Unauthorize အောင်မြင်ပါပြီ!**\n\n"
        f"👤 User ID: `{target_user_id}`\n"
        f"🎯 Status: Unauthorized\n"
        f"📝 Total authorized users: {len(AUTHORIZED_USERS)}",
        parse_mode="Markdown"
    )

async def maintenance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    # Check if user is admin
    if int(user_id) != ADMIN_ID:
        await update.message.reply_text("❌ သင်သည် admin မဟုတ်ပါ!")
        return
        
    args = context.args
    if len(args) != 2:
        await update.message.reply_text(
            "❌ မှန်ကန်တဲ့အတိုင်း: `/maintenance <feature> <on/off>`\n\n"
            "**Features:**\n"
            "• `orders` - အော်ဒါလုပ်ဆောင်ချက်\n"
            "• `topups` - ငွေဖြည့်လုပ်ဆောင်ချက်\n"
            "• `general` - ယေဘူယျ လုပ်ဆောင်ချက်\n\n"
            "**ဥပမာ:**\n"
            "• `/maintenance orders off`\n"
            "• `/maintenance topups on`"
        )
        return
        
    feature = args[0].lower()
    status = args[1].lower()
    
    if feature not in ["orders", "topups", "general"]:
        await update.message.reply_text("❌ Feature မှားနေပါတယ်! orders, topups, general ထဲမှ ရွေးပါ")
        return
        
    if status not in ["on", "off"]:
        await update.message.reply_text("❌ Status မှားနေပါတယ်! on သို့မဟုတ် off ရွေးပါ")
        return
        
    bot_maintenance[feature] = (status == "on")
    
    status_text = "🟢 ဖွင့်ထား" if status == "on" else "🔴 ပိတ်ထား"
    feature_text = {
        "orders": "အော်ဒါလုပ်ဆောင်ချက်",
        "topups": "ငွေဖြည့်လုပ်ဆောင်ချက်", 
        "general": "ယေဘူယျလုပ်ဆောင်ချက်"
    }
    
    await update.message.reply_text(
        f"✅ **Maintenance Mode ပြောင်းလဲပါပြီ!**\n\n"
        f"🔧 Feature: {feature_text[feature]}\n"
        f"📊 Status: {status_text}\n\n"
        f"**လက်ရှိ Maintenance Status:**\n"
        f"• အော်ဒါများ: {'🟢 ဖွင့်ထား' if bot_maintenance['orders'] else '🔴 ပိတ်ထား'}\n"
        f"• ငွေဖြည့်များ: {'🟢 ဖွင့်ထား' if bot_maintenance['topups'] else '🔴 ပိတ်ထား'}\n"
        f"• ယေဘူယျ: {'🟢 ဖွင့်ထား' if bot_maintenance['general'] else '🔴 ပိတ်ထား'}",
        parse_mode="Markdown"
    )

async def setprice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    # Check if user is admin
    if int(user_id) != ADMIN_ID:
        await update.message.reply_text("❌ သင်သည် admin မဟုတ်ပါ!")
        return
        
    args = context.args
    if len(args) != 2:
        await update.message.reply_text(
            "❌ မှန်ကန်တဲ့အတိုင်း: `/setprice <item> <price>`\n\n"
            "**ဥပမာ:**\n"
            "• `/setprice wp1 7000`\n"
            "• `/setprice 86 5500`\n"
            "• `/setprice 12976 750000`"
        )
        return
        
    item = args[0]
    try:
        price = int(args[1])
        if price < 0:
            await update.message.reply_text("❌ ဈေးနှုန်း သုညထက် ကြီးရမည်!")
            return
    except ValueError:
        await update.message.reply_text("❌ ဈေးနှုန်း ကိန်းဂဏန်းဖြင့် ထည့်ပါ!")
        return
        
    custom_prices = load_prices()
    custom_prices[item] = price
    save_prices(custom_prices)
    
    await update.message.reply_text(
        f"✅ **ဈေးနှုန်း ပြောင်းလဲပါပြီ!**\n\n"
        f"💎 Item: `{item}`\n"
        f"💰 New Price: `{price:,} MMK`\n\n"
        f"📝 Users တွေ `/price` နဲ့ အသစ်တွေ့မယ်။",
        parse_mode="Markdown"
    )

async def removeprice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    # Check if user is admin
    if int(user_id) != ADMIN_ID:
        await update.message.reply_text("❌ သင်သည် admin မဟုတ်ပါ!")
        return
        
    args = context.args
    if len(args) != 1:
        await update.message.reply_text(
            "❌ မှန်ကန်တဲ့အတိုင်း: `/removeprice <item>`\n\n"
            "**ဥပမာ:** `/removeprice wp1`"
        )
        return
        
    item = args[0]
    custom_prices = load_prices()
    
    if item not in custom_prices:
        await update.message.reply_text(f"❌ `{item}` မှာ custom price မရှိပါ!")
        return
        
    del custom_prices[item]
    save_prices(custom_prices)
    
    await update.message.reply_text(
        f"✅ **Custom Price ဖျက်ပါပြီ!**\n\n"
        f"💎 Item: `{item}`\n"
        f"🔄 Default price ကို ပြန်သုံးပါမယ်။",
        parse_mode="Markdown"
    )

async def adminhelp_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    # Check if user is admin
    if int(user_id) != ADMIN_ID:
        await update.message.reply_text("❌ သင်သည် admin မဟုတ်ပါ!")
        return
        
    help_msg = (
        "🔧 **Admin Commands List** 🔧\n\n"
        "👥 **User Management:**\n"
        "• `/authorize <user_id>` - User အသုံးပြုခွင့်ပေး\n"
        "• `/unauthorize <user_id>` - User အသုံးပြုခွင့်ရုပ်သိမ်း\n\n"
        "💰 **Balance Management:**\n"
        "• `/approve <user_id> <amount>` - Topup approve လုပ်\n"
        "• `/deduct <user_id> <amount>` - Balance နှုတ်ခြင်း\n\n"
        "💬 **Communication:**\n"
        "• `/reply <user_id> <message>` - User ကို message ပို့\n"
        "• `/done <user_id>` - Order complete message ပို့\n"
        "• `/sendgroup <message>` - Admin group ကို message ပို့\n\n"
        "🔧 **Bot Maintenance:**\n"
        "• `/maintenance <orders/topups/general> <on/off>` - Features ဖွင့်ပိတ်\n\n"
        "💎 **Price Management:**\n"
        "• `/setprice <item> <price>` - Custom price ထည့်\n"
        "• `/removeprice <item>` - Custom price ဖျက်\n\n"
        "📊 **Current Status:**\n"
        f"• Orders: {'🟢 Enabled' if bot_maintenance['orders'] else '🔴 Disabled'}\n"
        f"• Topups: {'🟢 Enabled' if bot_maintenance['topups'] else '🔴 Disabled'}\n"
        f"• General: {'🟢 Enabled' if bot_maintenance['general'] else '🔴 Disabled'}\n"
        f"• Authorized Users: {len(AUTHORIZED_USERS)}\n"
        f"• AI Users: {len(ai_users)}"
    )
    
    await update.message.reply_text(help_msg, parse_mode="Markdown")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    # Check if user is authorized
    load_authorized_users()
    if not is_user_authorized(user_id):
        return

    # Validate if it's a payment screenshot
    if not is_payment_screenshot(update):
        await update.message.reply_text(
            "❌ **သင့်ပုံ လက်မခံပါ!**\n\n"
            "🔍 Payment screenshot သာ လက်ခံပါတယ်။\n"
            "💳 KPay, Wave လွှဲမှု screenshot များသာ တင်ပေးပါ။\n\n"
            "📷 Payment app ရဲ့ transfer confirmation screenshot ကို တင်ပေးပါ။",
            parse_mode="Markdown"
        )
        return

    if user_id not in pending_topups:
        await update.message.reply_text(
            "❌ **Topup process မရှိပါ!**\n\n"
            "🔄 အရင်ဆုံး `/topup amount` command ကို သုံးပါ။\n"
            "💡 ဥပမာ: `/topup 50000`",
            parse_mode="Markdown"
        )
        return

    pending = pending_topups[user_id]
    amount = pending["amount"]

    # Set user state to restricted
    user_states[user_id] = "waiting_approval"

    # Notify admin about topup request
    admin_msg = (
        f"💳 **ငွေဖြည့်တောင်းဆိုမှု**\n\n"
        f"👤 User: {update.effective_user.first_name}\n"
        f"🆔 User ID: `{user_id}`\n"
        f"💰 Amount: `{amount:,} MMK`\n"
        f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"Screenshot ပါ ပါပါတယ်။ Approve လုပ်ရန်:\n"
        f"`/approve {user_id} {amount}`"
    )

    try:
        await context.bot.forward_message(
            chat_id=ADMIN_ID,
            from_chat_id=update.effective_chat.id,
            message_id=update.message.message_id
        )
        await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode="Markdown")
    except:
        pass

    # Save topup request first
    data = load_data()
    if user_id not in data["users"]:
        data["users"][user_id] = {"name": "", "username": "", "balance": 0, "orders": [], "topups": []}

    topup_request = {
        "amount": amount,
        "status": "pending",
        "timestamp": datetime.now().isoformat()
    }
    data["users"][user_id]["topups"].append(topup_request)
    save_data(data)

    # Notify admin group
    await notify_group_topup(topup_request, update.effective_user.first_name or "Unknown", user_id)

    del pending_topups[user_id]

    await update.message.reply_text(
        f"✅ **Screenshot လက်ခံပါပြီ!**\n\n"
        f"💰 ပမာဏ: `{amount:,} MMK`\n"
        f"⏰ အချိန်: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        "🔒 **အသုံးပြုမှု ယာယီ ကန့်သတ်ပါ**\n"
        "❌ Admin က လက်ခံပြီးကြောင်း အတည်ပြုတဲ့အထိ commands တွေ အသုံးပြုလို့ မရပါ။\n\n"
        "🔍 Admin မှ စစ်ဆေးပြီး 24 နာရီအတွင်း confirm လုပ်ပါမယ်။\n"
        "✅ Approve ရပြီးမှ ပြန်လည် အသုံးပြုနိုင်ပါမယ်။\n"
        "📞 ပြဿနာရှိရင် admin ကို ဆက်သွယ်ပါ။",
        parse_mode="Markdown"
    )

async def send_to_group_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    # Check if user is admin
    if int(user_id) != ADMIN_ID:
        await update.message.reply_text("❌ သင်သည် admin မဟုတ်ပါ!")
        return
        
    args = context.args
    if len(args) < 1:
        await update.message.reply_text(
            "❌ မှန်ကန်တဲ့အတိုင်း: /sendgroup <message>\n"
            "**ဥပမာ**: `/sendgroup Bot test လုပ်နေပါတယ်`"
        )
        return

    message = " ".join(args)
    
    try:
        await context.bot.send_message(
            chat_id=ADMIN_GROUP_ID,
            text=f"📢 **Admin Message**\n\n{message}",
            parse_mode="Markdown"
        )
        await update.message.reply_text("✅ Group ထဲကို message ပေးပြီးပါပြီ။")
    except Exception as e:
        await update.message.reply_text(f"❌ Group ထဲကို message မပို့နိုင်ပါ။\nError: {str(e)}")

async def notify_group_order(order_data, user_name):
    """Notify admin group about new order"""
    try:
        bot = Bot(token=BOT_TOKEN)
        message = (
            f"🛒 **အော်ဒါအသစ် ရောက်ပါပြီ!**\n\n"
            f"📝 Order ID: `{order_data['order_id']}`\n"
            f"👤 User: {user_name}\n"
            f"🎮 Game ID: `{order_data['game_id']}`\n"
            f"🌐 Server ID: `{order_data['server_id']}`\n"
            f"💎 Amount: {order_data['amount']}\n"
            f"💰 Price: {order_data['price']:,} MMK\n"
            f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"#NewOrder #MLBB"
        )
        await bot.send_message(chat_id=ADMIN_GROUP_ID, text=message, parse_mode="Markdown")
    except Exception as e:
        print(f"Group notification error: {e}")

async def notify_group_topup(topup_data, user_name, user_id):
    """Notify admin group about new topup request"""
    try:
        bot = Bot(token=BOT_TOKEN)
        message = (
            f"💳 **ငွေဖြည့်တောင်းဆိုမှု**\n\n"
            f"👤 User: {user_name}\n"
            f"🆔 User ID: `{user_id}`\n"
            f"💰 Amount: `{topup_data['amount']:,} MMK`\n"
            f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"Approve လုပ်ရန်: `/approve {user_id} {topup_data['amount']}`\n\n"
            f"#TopupRequest #Payment"
        )
        await bot.send_message(chat_id=ADMIN_GROUP_ID, text=message, parse_mode="Markdown")
    except Exception as e:
        print(f"Group topup notification error: {e}")

async def handle_restricted_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all non-command messages for restricted users"""
    user_id = str(update.effective_user.id)
    
    # Check if user is authorized first
    load_authorized_users()
    if not is_user_authorized(user_id):
        # For unauthorized users, give AI reply
        if update.message.text:
            reply = ai_reply(update.message.text)
            await update.message.reply_text(reply, parse_mode="Markdown")
        return

    # Check if user is restricted after sending screenshot
    if user_id in user_states and user_states[user_id] == "waiting_approval":
        # Block everything except photos for restricted users
        if update.message.photo:
            await handle_photo(update, context)
            return
        
        # Block all other content types
        await update.message.reply_text(
            "❌ **အသုံးပြုမှု ကန့်သတ်ထားပါ!**\n\n"
            "🔒 Screenshot ပို့ပြီးပါပြီ။ Admin က လက်ခံပြီးကြောင်း အတည်ပြုတဲ့အထိ:\n\n"
            "❌ Commands အသုံးပြုလို့ မရပါ\n"
            "❌ စာသား ပို့လို့ မရပါ\n"
            "❌ Voice, Sticker, GIF, Video ပို့လို့ မရပါ\n"
            "❌ Emoji ပို့လို့ မရပါ\n\n"
            "⏰ Admin က approve လုပ်ပြီးမှ ပြန်လည် အသုံးပြုနိုင်ပါမယ်။\n"
            "📞 အရေးပေါ်ဆိုရင် admin ကို ဆက်သွယ်ပါ။",
            parse_mode="Markdown"
        )
        return

    # For authorized users with AI enabled
    if user_id in ai_users and update.message.text:
        reply = ai_reply(update.message.text)
        await update.message.reply_text(reply, parse_mode="Markdown")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = str(query.from_user.id)
    
    # Check if user is restricted
    if user_id in user_states and user_states[user_id] == "waiting_approval":
        await query.answer("❌ Screenshot ပို့ပြီးပါပြီ! Admin approve စောင့်ပါ။", show_alert=True)
        return
    
    if query.data == "copy_kpay":
        await query.answer("📱 KPay Number copied! 09678786528", show_alert=True)
        await query.message.reply_text(
            "📱 **KBZ Pay Number**\n\n"
            "`09678786528`\n\n"
            "👤 Name: **Ma May Phoo Wai**\n"
            "📋 Number ကို အပေါ်မှ copy လုပ်ပါ",
            parse_mode="Markdown"
        )
        
    elif query.data == "copy_wave":
        await query.answer("📱 Wave Number copied! 09673585480", show_alert=True)
        await query.message.reply_text(
            "📱 **Wave Money Number**\n\n"
            "`09673585480`\n\n"
            "👤 Name: **Nine Nine**\n"
            "📋 Number ကို အပေါ်မှ copy လုပ်ပါ",
            parse_mode="Markdown"
        )
        
    elif query.data == "topup_button":
        try:
            keyboard = [
                [InlineKeyboardButton("📱 Copy KPay Number", callback_data="copy_kpay")],
                [InlineKeyboardButton("📱 Copy Wave Number", callback_data="copy_wave")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text="💳 **ငွေဖြည့်လုပ်ငန်းစဉ်**\n\n"
                     "**အဆင့် 1**: ငွေပမာဏ ရေးပါ\n"
                     "`/topup amount` ဥပမာ: `/topup 50000`\n\n"
                     "**အဆင့် 2**: ငွေလွှဲပါ\n"
                     "📱 KBZ Pay: `09678786528` (Ma May Phoo Wai)\n"
                     "📱 Wave Money: `09673585480` (Nine Nine)\n\n"
                     "**အဆင့် 3**: Screenshot တင်ပါ\n"
                     "ငွေလွှဲပြီးရင် screenshot ကို ဒီမှာ တင်ပေးပါ။\n\n"
                     "⏰ 24 နာရီအတွင်း confirm လုပ်ပါမယ်။",
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        except Exception as e:
            # If edit fails, send new message
            keyboard = [
                [InlineKeyboardButton("📱 Copy KPay Number", callback_data="copy_kpay")],
                [InlineKeyboardButton("📱 Copy Wave Number", callback_data="copy_wave")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.reply_text(
                text="💳 **ငွေဖြည့်လုပ်ငန်းစဉ်**\n\n"
                     "**အဆင့် 1**: ငွေပမာဏ ရေးပါ\n"
                     "`/topup amount` ဥပမာ: `/topup 50000`\n\n"
                     "**အဆင့် 2**: ငွေလွှဲပါ\n"
                     "📱 KBZ Pay: `09678786528` (Ma May Phoo Wai)\n"
                     "📱 Wave Money: `09673585480` (Nine Nine)\n\n"
                     "**အဆင့် 3**: Screenshot တင်ပါ\n"
                     "ငွေလွှဲပြီးရင် screenshot ကို ဒီမှာ တင်ပေးပါ။\n\n"
                     "⏰ 24 နာရီအတွင်း confirm လုပ်ပါမယ်။",
                parse_mode="Markdown",
                reply_markup=reply_markup
            )

def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN environment variable မရှိပါ!")
        return

    application = Application.builder().token(BOT_TOKEN).build()

    # Load authorized users on startup
    load_authorized_users()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("mmb", mmb_command))
    application.add_handler(CommandHandler("balance", balance_command))
    application.add_handler(CommandHandler("topup", topup_command))
    application.add_handler(CommandHandler("price", price_command))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CommandHandler("aistart", aistart_command))
    application.add_handler(CommandHandler("stopai", stopai_command))
    
    # Admin commands
    application.add_handler(CommandHandler("approve", approve_command))
    application.add_handler(CommandHandler("deduct", deduct_command))
    application.add_handler(CommandHandler("done", done_command))
    application.add_handler(CommandHandler("reply", reply_command))
    application.add_handler(CommandHandler("authorize", authorize_command))
    application.add_handler(CommandHandler("unauthorize", unauthorize_command))
    application.add_handler(CommandHandler("sendgroup", send_to_group_command))
    application.add_handler(CommandHandler("maintenance", maintenance_command))
    application.add_handler(CommandHandler("setprice", setprice_command))
    application.add_handler(CommandHandler("removeprice", removeprice_command))
    application.add_handler(CommandHandler("adminhelp", adminhelp_command))
    
    # Callback query handler
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Photo handler (for payment screenshots)
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    # Handle all other message types (text, voice, sticker, video, etc.)
    application.add_handler(MessageHandler(
        (filters.TEXT | filters.VOICE | filters.Sticker.ALL | filters.VIDEO | 
         filters.ANIMATION | filters.AUDIO | filters.Document.ALL) & ~filters.COMMAND, 
        handle_restricted_content
    ))

    print("🤖 Bot စတင်နေပါသည် - 24/7 Running Mode")
    print("✅ Orders, Topups နဲ့ AI စလုံးအဆင်သင့်ပါ")
    print("🔧 Admin commands များ အသုံးပြုနိုင်ပါပြီ")
    application.run_polling()

if __name__ == "__main__":
    main()
