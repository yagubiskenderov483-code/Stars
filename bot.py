import logging, json, os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN    = "8636524725:AAHohfHayrAE2MXswcFMHHiC4kLoI7fd5XE"
ADMIN_ID     = 174415647
BOT_USERNAME = "GiftDealsRobot"
MANAGER_USERNAME = "@GiftDealsManager"
CRYPTO_ADDRESS = "UQDGN5pfjPxorFyjN2xha84bapuADDtPcRofNDJ4dK2YXxZd"
CRYPTO_BOT   = "https://t.me/send?start=IVbfPL7Tk4XA"
CARD_NUMBER  = "+79041751408"
CARD_NAME    = "Александр Ф."
CARD_BANK    = "ВТБ"
DB_FILE      = "db.json"

def ce(eid, fb): return f"<tg-emoji emoji-id='{eid}'>{fb}</tg-emoji>"

E = {
    "user":      ce("5199552030615558774","👤"),
    "star":      ce("5267500801240092311","⭐"),
    "shield":    ce("5197434882321567830","⭐"),
    "premium":   ce("5377620962390857342","🪙"),
    "pencil":    ce("5197371802136892976","⛏"),
    "cross":     ce("5443127283898405358","📥"),
    "sticker":   ce("5294167145079395967","🛍"),
    "fire":      ce("5303138782004924588","💬"),
    "bell":      ce("5312361253610475399","🛒"),
    "deal":      ce("5445221832074483553","💼"),
    "check":     ce("5274055917766202507","🗓"),
    "money":     ce("5278467510604160626","💰"),
    "diamond":   ce("5264713049637409446","🪙"),
    "nft":       ce("5193177581888755275","💻"),
    "gem":       ce("5258203794772085854","⚡️"),
    "clock":     ce("5429651785352501917","↗️"),
    "spark":     ce("5902449142575141204","🔎"),
    "pin":       ce("5893297890117292323","📞"),
    "wallet":    ce("5893382531037794941","👛"),
    "num1":      ce("5794164805065514131","1️⃣"),
    "num2":      ce("5794085322400733645","2️⃣"),
    "num3":      ce("5794280000383358988","3️⃣"),
    "num4":      ce("5794241397217304511","4️⃣"),
    "link":      ce("5902449142575141204","🔗"),
    "tonkeeper": ce("5397829221605191505","💎"),
    "top_medal": ce("5188344996356448758","🏆"),
    "stars_deal":ce("5321485469249198987","⭐️"),
    "joined":    ce("5902335789798265487","🤝"),
    "security_e":ce("5197288647275071607","🛡"),
    "deal_link": ce("5972261808747057065","🔗"),
    "warning":   ce("5447644880824181073","⚠️"),
    "stats":     ce("5028746137645876535","📊"),
    "requisites":ce("5242631901214171852","💳"),
    "cryptobot": ce("5242606681166220600","🤖"),
    "welcome":   ce("5251340119205501791","👋"),
    "balance_e": ce("5424976816530014958","💰"),
    "star_prem": ce("5361541546057189236","⭐"),
}
CM = ce("5278467510604160626","💰")

TNAMES_RU = {
    "nft":              f"{E['nft']} NFT подарок",
    "username":         f"{E['user']} NFT Username",
    "stars":            f"{E['stars_deal']} Звёзды Telegram",
    "crypto":           f"{E['tonkeeper']} Крипта (TON/USDT)",
    "premium":          f"{E['premium']} Telegram Premium",
    "premium_stickers": f"{E['sticker']} Премиум стикеры",
}
TNAMES_EN = {
    "nft":              f"{E['nft']} NFT Gift",
    "username":         f"{E['user']} NFT Username",
    "stars":            f"{E['stars_deal']} Telegram Stars",
    "crypto":           f"{E['tonkeeper']} Crypto (TON/USDT)",
    "premium":          f"{E['premium']} Telegram Premium",
    "premium_stickers": f"{E['sticker']} Premium Stickers",
}
TNAMES = TNAMES_RU

def tname(dtype, lang="ru"):
    return TNAMES_EN.get(dtype,dtype) if lang=="en" else TNAMES_RU.get(dtype,dtype)

# Currency names without flag (for deal cards)
CUR_PLAIN = {
    "TON":"💎 TON","USDT":"💵 USDT","Stars":"⭐️ Stars",
    "RUB":"Рубли","KZT":"Теңге","AZN":"Manat","KGS":"Сом",
    "UZS":"So'm","TJS":"Сомонӣ","BYN":"Рублі","UAH":"Гривня","GEL":"ლარი",
}
# Currency names with flag (for buttons)
CUR_BTN = {
    "TON":"💎 TON","USDT":"💵 USDT","Stars":"⭐️ Stars / Звёзды",
    "RUB":"🇷🇺 Рубли","KZT":"🇰🇿 Теңге","AZN":"🇦🇿 Manat","KGS":"🇰🇬 Сом",
    "UZS":"🇺🇿 So'm","TJS":"🇹🇯 Сомонӣ","BYN":"🇧🇾 Рублі","UAH":"🇺🇦 Гривня","GEL":"🇬🇪 ლარი",
}
CURMAP = {"cur_ton":"TON","cur_usdt":"USDT","cur_rub":"RUB","cur_stars":"Stars",
          "cur_kzt":"KZT","cur_azn":"AZN","cur_kgs":"KGS","cur_uzs":"UZS",
          "cur_tjs":"TJS","cur_byn":"BYN","cur_uah":"UAH","cur_gel":"GEL"}

def cur_plain(code): return CUR_PLAIN.get(code, code)
def lbl(ru, a, b): return a if ru else b

BANNER_SECTIONS = {
    "main":"🏠 Главное меню","deal":"🎁 Создать сделку","balance":"💸 Пополнить/Вывод",
    "profile":"👤 Профиль","top":"🏆 Топ сделок","my_deals":"🗂 Мои сделки",
    "deal_card":"💼 Карточка сделки","ref":"👥 Рефералы",
}

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE,"r",encoding="utf-8") as f: return json.load(f)
    return {"users":{},"deals":{},"banner":None,"banner_photo":None,"banner_video":None,
            "banner_gif":None,"menu_description":None,"deal_counter":1,"banners":{},
            "logs":[],"log_chat_id":None}

def save_db(db):
    with open(DB_FILE,"w",encoding="utf-8") as f: json.dump(db,f,ensure_ascii=False,indent=2)

def add_log(db,event,deal_id=None,uid=None,username=None,extra="",item_link=""):
    if "logs" not in db: db["logs"]=[]
    db["logs"].append({"time":datetime.now().strftime("%d.%m.%Y %H:%M"),"event":event,
        "deal_id":deal_id or "","uid":str(uid) if uid else "","username":username or "",
        "extra":extra,"item_link":item_link})
    if len(db["logs"])>500: db["logs"]=db["logs"][-500:]

async def send_log(context, db, entry, hidden=False):
    chat_id=db.get("log_chat_id")
    if not chat_id: return
    try:
        u=entry.get("username",""); us=entry.get("uid","")
        deal=f" #{entry['deal_id']}" if entry.get("deal_id") else ""
        extra=f"\n{entry['extra']}" if entry.get("extra") else ""
        ilink=f"\n{entry['item_link']}" if entry.get("item_link") else ""
        ud=mask(f"@{u}") if hidden and u else (f"@{u}" if u else "")
        uid_d=mask(us) if hidden and us else (f"<code>{us}</code>" if us else "")
        await context.bot.send_message(chat_id=int(chat_id),
            text=f"<b>{entry['time']}</b> {entry['event']}{deal}\n{ud} {uid_d}{extra}{ilink}",
            parse_mode="HTML")
    except Exception as e: logger.error(f"send_log: {e}")

def mask(t):
    if not t: return "—"
    if t.startswith("@"):
        s=t[1:]; return "@***" if len(s)<=3 else f"@{s[:2]}***{s[-2:]}"
    if t.isdigit(): return t[:3]+"***"+t[-2:]
    return t[:2]+"***"

def get_user(db, uid):
    k=str(uid)
    if k not in db["users"]:
        db["users"][k]={"username":"","balance":0,"total_deals":0,"success_deals":0,
            "turnover":0,"reputation":0,"reviews":[],"status":"","lang":"ru",
            "requisites":{},"ref_by":None,"ref_count":0,"ref_earned":0,"hidden":False}
    u=db["users"][k]
    for f,v in [("requisites",{}),("ref_by",None),("ref_count",0),("ref_earned",0),("hidden",False)]:
        if f not in u: u[f]=v
    return u

def get_lang(uid):
    try: return get_user(load_db(),uid).get("lang","ru")
    except: return "ru"

def gen_deal_id(db):
    n=db.get("deal_counter",1); db["deal_counter"]=n+1; save_db(db); return f"GD{n:05d}"

LANGS={"ru":"🇷🇺 Русский","en":"🇬🇧 English"}

def get_welcome(lang):
    if lang=="en":
        pts=["Automatic NFT & gift deals","Full protection for both parties",
             "Funds frozen until confirmation","Transfer via manager: @GiftDealsManager"]
        intro="Gift Deals — the safest platform for deals in Telegram"
        footer="Choose an action below"; stats="1000+ deals · $6,350 turnover"
    else:
        pts=["Автоматические сделки с НФТ и подарками","Полная защита обеих сторон",
             "Средства заморожены до подтверждения","Передача через менеджера: @GiftDealsManager"]
        intro="Gift Deals — самая безопасная площадка для сделок в Telegram"
        footer="Выберите действие ниже"; stats="1000+ сделок · оборот $6,350"
    nums=[E['num1'],E['num2'],E['num3'],E['num4']]
    lines="\n".join(f"<blockquote><b>{nums[i]} {pts[i]}.</b></blockquote>" for i in range(4))
    return f"{E['welcome']} <b>{intro}</b>\n\n{lines}\n\n<blockquote><b>{E['stats']} {stats}</b></blockquote>\n\n{E['spark']} <b>{footer}</b>"

def cur_kb(lang):
    def n(c): return CUR_BTN.get(c,c)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(n("TON"),callback_data="cur_ton"),InlineKeyboardButton(n("USDT"),callback_data="cur_usdt")],
        [InlineKeyboardButton(n("RUB"),callback_data="cur_rub"),InlineKeyboardButton(n("Stars"),callback_data="cur_stars")],
        [InlineKeyboardButton(n("KZT"),callback_data="cur_kzt"),InlineKeyboardButton(n("AZN"),callback_data="cur_azn")],
        [InlineKeyboardButton(n("KGS"),callback_data="cur_kgs"),InlineKeyboardButton(n("UZS"),callback_data="cur_uzs")],
        [InlineKeyboardButton(n("TJS"),callback_data="cur_tjs"),InlineKeyboardButton(n("BYN"),callback_data="cur_byn")],
        [InlineKeyboardButton(n("UAH"),callback_data="cur_uah"),InlineKeyboardButton(n("GEL"),callback_data="cur_gel")],
    ])

def get_banner(db, section="main"):
    b=db.get("banners",{}).get(section)
    if b and (b.get("photo") or b.get("video") or b.get("gif") or b.get("text")): return b
    if section=="main":
        lg={"photo":db.get("banner_photo"),"video":db.get("banner_video"),
            "gif":db.get("banner_gif"),"text":db.get("banner") or ""}
        if any(v for v in lg.values()): return lg
    return None

async def send_with_banner(update, text, kb=None, section="main"):
    try:
        db=load_db(); b=get_banner(db,section)
        bv=b.get("video") if b else None; bg=b.get("gif") if b else None; bp=b.get("photo") if b else None
        bt=b.get("text","") if b else ""
        full=text+(f"\n\n<b>{bt}</b>" if bt else "")
        has_media=bool(bv or bg or bp)
        old=None; old_media=False
        try:
            if update.callback_query:
                old=update.callback_query.message
                if old: old_media=bool(old.photo or old.video or old.animation)
        except: pass
        if not has_media and not old_media and old:
            try: await old.edit_text(full,parse_mode="HTML",reply_markup=kb); return
            except: pass
        elif has_media and old_media and old:
            try: await old.edit_caption(caption=full,parse_mode="HTML",reply_markup=kb); return
            except:
                try: await old.delete()
                except: pass
        elif old:
            try: await old.delete()
            except: pass
        if bv: await update.effective_chat.send_video(video=bv,caption=full,parse_mode="HTML",reply_markup=kb)
        elif bg: await update.effective_chat.send_animation(animation=bg,caption=full,parse_mode="HTML",reply_markup=kb)
        elif bp: await update.effective_chat.send_photo(photo=bp,caption=full,parse_mode="HTML",reply_markup=kb)
        else: await update.effective_chat.send_message(full,parse_mode="HTML",reply_markup=kb)
    except Exception as e:
        logger.error(f"send_with_banner: {e}")
        try: await update.effective_message.reply_text(text,parse_mode="HTML",reply_markup=kb)
        except: pass

async def eos(update, text, kb=None, section="main"):
    await send_with_banner(update,text,kb,section=section)

def main_kb(lang):
    ru=lang=="ru"
    sup=lbl(ru,"🆘 Тех. поддержка","🆘 Tech Support")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 "+lbl(ru,"Создать сделку","Create Deal"),callback_data="menu_deal"),
         InlineKeyboardButton("⭐ "+lbl(ru,"Профиль","Profile"),callback_data="menu_profile")],
        [InlineKeyboardButton("💸 "+lbl(ru,"Пополнить/Вывод","Top Up/Withdraw"),callback_data="menu_balance"),
         InlineKeyboardButton("🪪 "+lbl(ru,"Мои сделки","My Deals"),callback_data="menu_my_deals")],
        [InlineKeyboardButton("🌍 "+lbl(ru,"Язык / Lang","Language"),callback_data="menu_lang"),
         InlineKeyboardButton("🏆 "+lbl(ru,"Топ сделок","Top Deals"),callback_data="menu_top")],
        [InlineKeyboardButton("👥 "+lbl(ru,"Рефералы","Referrals"),callback_data="menu_ref"),
         InlineKeyboardButton("📋 "+lbl(ru,"Реквизиты","Requisites"),callback_data="menu_req")],
        [InlineKeyboardButton(sup,url="https://t.me/GiftDealsSupport")],
    ])

async def show_main(update, context, edit=False):
    try:
        db=load_db(); uid=update.effective_user.id; u=get_user(db,uid)
        lang=u.get("lang","ru")
        desc=db.get("menu_description") or get_welcome(lang)
        await send_with_banner(update,desc,main_kb(lang),section="main")
    except Exception as e: logger.error(f"show_main: {e}")

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        db=load_db(); uid=update.effective_user.id; u=get_user(db,uid)
        u["username"]=update.effective_user.username or ""
        args=context.args
        if args and args[0].startswith("ref_") and not u.get("ref_by"):
            ref_uid=args[0][4:]; ref_user=db.get("users",{}).get(ref_uid)
            if ref_uid!=str(uid) and ref_user:
                u["ref_by"]=ref_uid
                db["users"][ref_uid]["ref_count"]=db["users"][ref_uid].get("ref_count",0)+1
                add_log(db,"👥 Новый реферал",uid=uid,username=u["username"],extra=f"@{ref_user.get('username','?')}")
                tag=f"@{u['username']}" if u.get("username") else f"#{uid}"
                try:
                    rr=ref_user.get("lang","ru")=="ru"
                    await context.bot.send_message(chat_id=int(ref_uid),
                        text=f"👥 <b>{lbl(rr,'Новый реферал!','New referral!')}</b>\n\n<blockquote>{tag}</blockquote>",
                        parse_mode="HTML")
                except: pass
                if db.get("logs"): await send_log(context,db,db["logs"][-1],hidden=db.get("log_hidden",False))
        save_db(db); context.user_data.clear()
        if args and args[0].startswith("deal_"):
            deal_id=args[0][5:].upper(); d=db.get("deals",{}).get(deal_id)
            if d:
                seller_uid=d.get("user_id"); lang=u.get("lang","ru"); ru=lang=="ru"
                if seller_uid and seller_uid==str(uid):
                    await update.effective_message.reply_text("⚠️ "+lbl(ru,"Нельзя быть покупателем своей сделки.","Can't be the buyer of your own deal."))
                    await show_main(update,context); return
                buyer_reqs=u.get("requisites",{})
                if not any(buyer_reqs.get(f) for f in ("card","ton","stars")):
                    msg=(f"{ce('5420323339723881652','⚠️')} <b>{lbl(ru,'Добавьте реквизиты для участия в сделке.','Add requisites to join the deal.')}</b>\n\n"
                         f"<blockquote>{lbl(ru,'Выберите что добавить:','Choose what to add:')}</blockquote>")
                    kb=InlineKeyboardMarkup([
                        [InlineKeyboardButton("💳 "+lbl(ru,"Карта / СБП","Card / SBP"),callback_data=f"req_deal_card_{deal_id}")],
                        [InlineKeyboardButton("💎 TON / USDT",callback_data=f"req_deal_ton_{deal_id}")],
                        [InlineKeyboardButton("⭐️ "+lbl(ru,"Звёзды","Stars"),callback_data=f"req_deal_stars_{deal_id}")],
                    ])
                    await update.effective_message.reply_text(msg,parse_mode="HTML",reply_markup=kb)
                    context.user_data["pending_deal"]=deal_id; return
                buyer_tag=f"@{update.effective_user.username}" if update.effective_user.username else f"#{uid}"
                add_log(db,"🔗 Покупатель открыл сделку",deal_id=deal_id,uid=uid,username=u["username"])
                db["deals"][deal_id]["buyer_uid"]=str(uid); save_db(db)
                if db.get("logs"): await send_log(context,db,db["logs"][-1],hidden=db.get("log_hidden",False))
                if seller_uid:
                    try:
                        sl=get_lang(int(seller_uid)); rs=sl=="ru"
                        await context.bot.send_message(chat_id=int(seller_uid),
                            text=f"{E['joined']} <b>{lbl(rs,'Покупатель присоединился!','Buyer joined!')}</b>\n\n<blockquote>{lbl(rs,'Сделка','Deal')}: #{deal_id}\n{buyer_tag}</blockquote>",
                            parse_mode="HTML")
                    except Exception as e: logger.error(f"joined notify: {e}")
                await send_deal_card(update,context,deal_id,d,buyer=True); return
        await show_main(update,context)
    except Exception as e: logger.error(f"cmd_start: {e}")

def deal_types_kb(lang="ru"):
    ru=lang=="ru"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 NFT",callback_data="dt_nft"),
         InlineKeyboardButton("🎴 NFT Username",callback_data="dt_usr")],
        [InlineKeyboardButton("⭐️ "+lbl(ru,"Звёзды","Stars"),callback_data="dt_str"),
         InlineKeyboardButton("💎 "+lbl(ru,"Крипта","Crypto"),callback_data="dt_cry")],
        [InlineKeyboardButton("✈️ Telegram Premium",callback_data="dt_prm")],
        [InlineKeyboardButton("🔙 "+lbl(ru,"Назад","Back"),callback_data="main_menu")],
    ])

def role_kb(lang):
    ru=lang=="ru"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 "+lbl(ru,"Я покупатель","I am the Buyer"),callback_data="role_buyer")],
        [InlineKeyboardButton("🏷 "+lbl(ru,"Я продавец","I am the Seller"),callback_data="role_seller")],
        [InlineKeyboardButton("🔙 "+lbl(ru,"Назад","Back"),callback_data="main_menu")],
    ])

def validate_username(text):
    # Only ASCII letters, digits, underscore; must start with @; min 5 chars total
    if not text.startswith("@"): return None,"no_at"
    u=text[1:]
    if len(u)<4: return None,"short"
    if not all(c.isascii() and (c.isalnum() or c=="_") for c in u): return None,"chars"
    return text,None

def validate_card(t):
    c=t.replace(" ","").replace("-","").replace("+","")
    if t.startswith("+") or (c.isdigit() and 10<=len(c)<=12):
        if c.isdigit() and 10<=len(c)<=12: return t
    if c.isdigit() and len(c) in (14,16): return c
    return None

def validate_nft_link(t,dtype):
    c=t.replace("https://","").replace("http://","")
    if not c.startswith("t.me/"): return False,"no_tme"
    if dtype=="nft" and not c[5:].startswith("nft/"): return False,"wrong_nft"
    return True,None

async def on_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        q=update.callback_query; await q.answer(); d=q.data
        ud=context.user_data; uid=update.effective_user.id
        lang=get_lang(uid); ru=lang=="ru"

        if d=="menu_ref": await show_ref(update,context); return
        if d=="menu_req": await show_req(update,context); return

        if d=="req_del_menu":
            db=load_db(); u=get_user(db,uid); reqs=u.get("requisites",{})
            rows=[]
            if reqs.get("card"): rows.append([InlineKeyboardButton("💳 "+lbl(ru,"Удалить карту","Delete card"),callback_data="req_del_card")])
            if reqs.get("ton"):  rows.append([InlineKeyboardButton("💎 "+lbl(ru,"Удалить TON","Delete TON"),callback_data="req_del_ton")])
            if reqs.get("stars"):rows.append([InlineKeyboardButton("⭐️ "+lbl(ru,"Удалить @username","Delete @username"),callback_data="req_del_stars")])
            rows.append([InlineKeyboardButton("🔙 "+lbl(ru,"Назад","Back"),callback_data="menu_req")])
            await eos(update,f"🗑 <b>{lbl(ru,'Что удалить?','What to delete?')}</b>",InlineKeyboardMarkup(rows),section="profile"); return

        if d.startswith("req_del_"):
            field=d[8:]; db=load_db(); u=get_user(db,uid)
            u.setdefault("requisites",{}).pop(field,None); save_db(db)
            await show_req(update,context); return

        if d.startswith("req_edit_"):
            field=d[9:]
            prompts={
                "card": f"💳 <b>{lbl(ru,'Карта / СБП','Card / SBP')}</b>\n\n<blockquote><b>{lbl(ru,'Введите номер телефона (СБП) или карты (14 или 16 цифр).','Enter phone (SBP) or card number (14/16 digits).')}\n\n{lbl(ru,'Примеры','Examples')}:\n<code>+79041751408</code>\n<code>4276123456781234</code></b></blockquote>",
                "ton":  f"💎 <b>TON / USDT</b>\n\n<blockquote><b>{lbl(ru,'Введите TON адрес (UQ или EQ).','Enter TON address (UQ or EQ).')}\n\n{lbl(ru,'Пример','Example')}:\n<code>UQDxxx...xxx</code></b></blockquote>",
                "stars":f"{E['star_prem']} <b>{lbl(ru,'Звёзды','Stars')}</b>\n\n<blockquote><b>{lbl(ru,'Введите @юзернейм (только латинские буквы, цифры, _).','Enter @username (only English letters, digits, _).')}\n\n{lbl(ru,'Пример','Example')}: <code>@username</code></b></blockquote>",
            }
            ud["req_step"]=field
            await eos(update,prompts.get(field,"?"),
                InlineKeyboardMarkup([[InlineKeyboardButton("🔙 "+lbl(ru,"Назад","Back"),callback_data="menu_req")]]),section="profile"); return

        if d.startswith("add_req_"):
            deal_id=d[8:]; ud["req_for_deal"]=deal_id
            text=(f"{ce('5420323339723881652','⚠️')} <b>{lbl(ru,'Добавьте реквизиты','Add requisites')}</b>\n\n"
                  f"<blockquote>{lbl(ru,'Выберите тип:','Choose type:')}</blockquote>")
            kb=InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 "+lbl(ru,"Карта / СБП","Card / SBP"),callback_data=f"req_deal_card_{deal_id}")],
                [InlineKeyboardButton("💎 TON / USDT",callback_data=f"req_deal_ton_{deal_id}")],
                [InlineKeyboardButton("⭐️ "+lbl(ru,"Звёзды","Stars"),callback_data=f"req_deal_stars_{deal_id}")],
                [InlineKeyboardButton("🔙 "+lbl(ru,"Назад","Back"),callback_data="main_menu")],
            ])
            await eos(update,text,kb,section="deal_card"); return

        if d.startswith("req_deal_"):
            parts=d[9:].split("_",1); field=parts[0]; deal_id=parts[1] if len(parts)>1 else ""
            ud["req_step"]=field; ud["req_for_deal"]=deal_id
            prompts={
                "card": f"💳 <b>{lbl(ru,'Карта / СБП','Card / SBP')}</b>\n\n<blockquote><b>{lbl(ru,'Телефон (СБП) или номер карты (14/16 цифр).','Phone (SBP) or card number (14/16 digits).')}\n\n{lbl(ru,'Примеры','Examples')}:\n<code>+79041751408</code> / <code>4276123456781234</code></b></blockquote>",
                "ton":  f"💎 <b>TON {lbl(ru,'адрес','address')}</b>\n\n<blockquote><b>{lbl(ru,'Адрес начинается с UQ или EQ.','Address starts with UQ or EQ.')}\n\n{lbl(ru,'Пример','Example')}: <code>UQDxxx...xxx</code></b></blockquote>",
                "stars":f"{E['star_prem']} <b>{lbl(ru,'Звёзды','Stars')}</b>\n\n<blockquote><b>{lbl(ru,'@юзернейм (только латиница, цифры, _).','@username (only English, digits, _).')}\n\n{lbl(ru,'Пример','Example')}: <code>@username</code></b></blockquote>",
            }
            await eos(update,prompts.get(field,"?"),
                InlineKeyboardMarkup([[InlineKeyboardButton("🔙 "+lbl(ru,"Назад","Back"),callback_data=f"add_req_{deal_id}")]]),section="deal_card"); return

        if d=="main_menu":
            ud.clear()
            try: await q.message.delete()
            except: pass
            await show_main(update,context); return

        if d=="menu_deal":
            ud.clear()
            try: await q.message.delete()
            except: pass
            await update.effective_message.reply_text(
                f"{E['pencil']} <b>{lbl(ru,'Создать сделку','Create Deal')}\n\n{lbl(ru,'Кто вы в этой сделке?','What is your role in this deal?')}</b>",
                parse_mode="HTML",reply_markup=role_kb(lang)); return

        if d in ("role_buyer","role_seller"):
            ud["creator_role"]="buyer" if d=="role_buyer" else "seller"
            try: await q.message.delete()
            except: pass
            await update.effective_message.reply_text(
                f"{E['pencil']} <b>{lbl(ru,'Создать сделку','Create Deal')}\n\n{lbl(ru,'Выберите тип','Choose type')}:</b>",
                parse_mode="HTML",reply_markup=deal_types_kb(lang)); return

        if d=="menu_balance":
            try: await q.message.delete()
            except: pass
            await show_balance(update,context); return

        if d=="balance_topup":
            await eos(update,f"{E['money']} <b>{lbl(ru,'Выберите способ пополнения:','Choose top-up method:')}</b>",
                InlineKeyboardMarkup([
                    [InlineKeyboardButton("⭐️ "+lbl(ru,"Звёзды","Stars"),callback_data="balance_stars")],
                    [InlineKeyboardButton("💰 "+lbl(ru,"Рубли","Rubles"),callback_data="balance_rub")],
                    [InlineKeyboardButton("💎 TON / USDT",callback_data="balance_crypto")],
                    [InlineKeyboardButton("🔙 "+lbl(ru,"Назад","Back"),callback_data="menu_balance")],
                ]),section="balance"); return

        if d=="menu_lang":
            try: await q.message.delete()
            except: pass
            await show_lang(update,context); return

        if d=="menu_profile":
            try: await q.message.delete()
            except: pass
            await show_profile(update,context); return

        if d=="menu_top":
            try: await q.message.delete()
            except: pass
            await show_top(update,context); return

        if d=="menu_my_deals":
            try: await q.message.delete()
            except: pass
            await show_my_deals(update,context); return

        if d.startswith("lang_"): await set_lang(update,context,d[5:]); return
        if d.startswith("balance_"): await show_balance_info(update,context,d[8:]); return
        if d=="withdraw": await show_withdraw(update,context); return

        if d.startswith("withdraw_"):
            method=d[9:]
            prompts={"stars":lbl(ru,"@юзернейм для звёзд:","@username for stars:"),
                     "crypto":lbl(ru,"TON/USDT адрес:","TON/USDT address:"),
                     "card":lbl(ru,"Номер карты:","Card number:")}
            ud["withdraw_method"]=method; ud["withdraw_step"]="requisite"
            await eos(update,f"{E['wallet']} <b>{lbl(ru,'Вывод средств','Withdraw')}</b>\n\n<blockquote><b>{prompts.get(method,'?')}</b></blockquote>",
                InlineKeyboardMarkup([[InlineKeyboardButton("🔙 "+lbl(ru,"Назад","Back"),callback_data="withdraw")]]),section="balance"); return

        if d.startswith("rev_"):
            parts=d.split("_"); deal_id=parts[1]; role=parts[2]; stars=int(parts[3])
            ud["review_deal"]=deal_id; ud["review_role"]=role; ud["review_stars"]=stars; ud["review_step"]="text"
            star_e=ce("5438496463044752972","⭐️")
            await q.edit_message_text(f"{star_e*stars} {lbl(ru,'Оценка','Rating')}: {stars}/5\n\n{lbl(ru,'Напишите комментарий:','Write a comment:')}:",parse_mode="HTML"); return

        if d.startswith("adm_del_rev_"):
            parts=d[12:].split("_",1); target_uid=parts[0]; rev_idx=int(parts[1]) if len(parts)>1 else -1
            db=load_db()
            if target_uid in db["users"] and rev_idx>=0:
                revs=db["users"][target_uid].get("reviews",[])
                if 0<=rev_idx<len(revs):
                    revs.pop(rev_idx); db["users"][target_uid]["reviews"]=revs; save_db(db)
                    await q.answer("Отзыв удалён ✅")
                    u2=db["users"][target_uid]; uname2=u2.get("username","?"); revs2=u2.get("reviews",[])
                    if not revs2:
                        await q.edit_message_text(f"<b>@{uname2}: отзывов нет</b>",parse_mode="HTML",
                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад",callback_data="adm_back")]]))
                    else:
                        lines=[f"<b>📋 Отзывы @{uname2} ({len(revs2)}):</b>"]; rows2=[]
                        for i,r in enumerate(revs2):
                            lines.append(f"\n{i+1}. {r}")
                            rows2.append([InlineKeyboardButton(f"🗑 #{i+1}",callback_data=f"adm_del_rev_{target_uid}_{i}")])
                        rows2.append([InlineKeyboardButton("🔙 Назад",callback_data="adm_back")])
                        await q.edit_message_text("\n".join(lines),parse_mode="HTML",reply_markup=InlineKeyboardMarkup(rows2))
            return

        if d.startswith("paid_"): await on_paid(update,context); return

        if d.startswith("topup_sent_"):
            method=d[11:]; uname2=update.effective_user.username or str(uid)
            mmap={"stars":"Звёзды","rub":"Рубли","crypto":"TON/USDT"}
            mname=mmap.get(method,method)
            try:
                await context.bot.send_message(chat_id=ADMIN_ID,
                    text=f"{E['bell']} <b>Запрос на пополнение — {mname}</b>\n{E['user']} @{uname2} (<code>{uid}</code>)\n\nПроверьте и подтвердите:",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("✅ Пришло",callback_data=f"adm_topup_ok_{uid}_{method}"),
                        InlineKeyboardButton("❌ Не пришло",callback_data=f"adm_topup_no_{uid}"),
                    ]]))
            except Exception as e: logger.error(f"topup_sent admin: {e}")
            await q.edit_message_reply_markup(InlineKeyboardMarkup([
                [InlineKeyboardButton("⏳ "+lbl(ru,"Ожидание...","Waiting..."),callback_data="noop")],
                [InlineKeyboardButton("🏠 "+lbl(ru,"Главное меню","Main menu"),callback_data="main_menu")],
            ])); return

        if d.startswith("adm_topup_ok_"):
            if update.effective_user.id!=ADMIN_ID: return
            parts=d[13:].split("_",1); target_uid=parts[0]
            await q.edit_message_text(f"✅ <b>Пополнение подтверждено!</b>\n<code>{target_uid}</code>",parse_mode="HTML")
            try:
                tl=get_lang(int(target_uid)); tr=tl=="ru"
                await context.bot.send_message(chat_id=int(target_uid),
                    text=f"{E['check']} <b>{lbl(tr,'Баланс пополнен!','Balance topped up!')}</b>",parse_mode="HTML")
            except: pass
            return

        if d.startswith("adm_topup_no_"):
            if update.effective_user.id!=ADMIN_ID: return
            target_uid=d[13:]
            await q.edit_message_text(f"❌ <b>Не подтверждено.</b>\n<code>{target_uid}</code>",parse_mode="HTML")
            try:
                tl=get_lang(int(target_uid)); tr=tl=="ru"
                await context.bot.send_message(chat_id=int(target_uid),
                    text=f"{E['cross']} <b>{lbl(tr,'Пополнение не найдено. Свяжитесь с менеджером.','Top-up not found. Contact manager.')}</b>",parse_mode="HTML")
            except: pass
            return

        if d=="noop": return
        if d.startswith("adm_confirm_"): await adm_confirm(update,context); return
        if d.startswith("adm_decline_"): await adm_decline(update,context); return
        if d=="adm_back":
            try: await q.message.edit_text(f"{E['shield']} <b>Панель администратора</b>",parse_mode="HTML",reply_markup=adm_kb())
            except: await q.message.reply_text(f"{E['shield']} <b>Панель администратора</b>",parse_mode="HTML",reply_markup=adm_kb())
            return
        if d.startswith("adm_"): await handle_adm_cb(update,context); return

        type_map={"dt_nft":"nft","dt_usr":"username","dt_str":"stars","dt_cry":"crypto","dt_prm":"premium","dt_pst":"premium_stickers"}
        if d in type_map:
            ud["type"]=type_map[d]; ud["step"]="partner"
            creator_role=ud.get("creator_role","seller")
            pp=lbl(ru,"Введите @username продавца:","Enter seller @username:") if creator_role=="buyer" else lbl(ru,"Введите @username покупателя:","Enter buyer @username:")
            try: await q.message.delete()
            except: pass
            msg=await update.effective_chat.send_message(
                f"{pp}\n\n<b>{lbl(ru,'Пример','Example')}:</b> <code>@username</code>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 "+lbl(ru,"Назад","Back"),callback_data="menu_deal")]]))
            ud["last_bot_msg"]=msg.message_id; return

        if d=="cry_ton":
            ud["currency"]="TON"; ud["step"]="amount"
            try: await q.message.delete()
            except: pass
            msg=await update.effective_chat.send_message(f"💎 {lbl(ru,'Введите сумму','Enter amount')} (TON):",parse_mode="HTML")
            ud["last_bot_msg"]=msg.message_id; return

        if d=="cry_usd":
            ud["currency"]="USDT"; ud["step"]="amount"
            try: await q.message.delete()
            except: pass
            msg=await update.effective_chat.send_message(f"💵 {lbl(ru,'Введите сумму','Enter amount')} (USDT):",parse_mode="HTML")
            ud["last_bot_msg"]=msg.message_id; return

        if d in ("prm_3","prm_6","prm_12"):
            prru={"prm_3":"3 месяца","prm_6":"6 месяцев","prm_12":"12 месяцев"}
            pren={"prm_3":"3 months","prm_6":"6 months","prm_12":"12 months"}
            ud["premium_period"]=(prru if ru else pren)[d]; ud["step"]="currency"
            try: await q.message.delete()
            except: pass
            msg=await update.effective_chat.send_message(lbl(ru,"Выберите валюту:","Choose currency:"),reply_markup=cur_kb(lang),parse_mode="HTML")
            ud["last_bot_msg"]=msg.message_id; return

        if d in ("pst_1","pst_3","pst_5","pst_10"):
            crru={"pst_1":"1 пак","pst_3":"3 пака","pst_5":"5 паков","pst_10":"10 паков"}
            cren={"pst_1":"1 pack","pst_3":"3 packs","pst_5":"5 packs","pst_10":"10 packs"}
            ud["sticker_count"]=(crru if ru else cren)[d]; ud["step"]="currency"
            try: await q.message.delete()
            except: pass
            msg=await update.effective_chat.send_message(lbl(ru,"Выберите валюту:","Choose currency:"),reply_markup=cur_kb(lang),parse_mode="HTML")
            ud["last_bot_msg"]=msg.message_id; return

        if d.startswith("cur_"):
            ud["currency"]=CURMAP.get(d,d); ud["step"]="amount"
            try: await q.message.delete()
            except: pass
            msg=await update.effective_chat.send_message(
                f"{lbl(ru,'Введите сумму сделки','Enter deal amount')} ({CURMAP.get(d,d)}):",parse_mode="HTML")
            ud["last_bot_msg"]=msg.message_id; return

    except Exception as e: logger.error(f"on_cb: {e}")

async def on_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        ud=context.user_data; uid=update.effective_user.id; lang=get_lang(uid); ru=lang=="ru"
        text=update.message.text.strip() if update.message.text else ""
        if uid==ADMIN_ID and ud.get("adm_step"): await handle_adm_msg(update,context); return

        if ud.get("req_step") in ("card","ton","stars"):
            field=ud["req_step"]; db=load_db(); u=get_user(db,uid)
            u.setdefault("requisites",{})
            err=None
            if field=="card":
                r=validate_card(text)
                if r is None: err=lbl(ru,"Введите телефон (СБП) или карту (14/16 цифр).\n\n<code>+79041751408</code> или <code>4276123456781234</code>","Enter phone (SBP) or card (14/16 digits).\n\n<code>+79041751408</code> or <code>4276123456781234</code>")
                else: text=r
            elif field=="ton":
                if not ((text.startswith("UQ") or text.startswith("EQ")) and len(text)>=40):
                    err=lbl(ru,"Введите TON адрес (начинается с UQ или EQ).\n\n<code>UQDxxx...xxx</code>","Enter TON address (starts with UQ or EQ).\n\n<code>UQDxxx...xxx</code>")
            elif field=="stars":
                t2=text if text.startswith("@") else f"@{text}"
                cleaned,ec=validate_username(t2)
                if ec=="chars": err=lbl(ru,"Только латинские буквы, цифры и _.\n\n<b>Пример:</b> <code>@username</code>","Only English letters, digits and _.\n\n<b>Example:</b> <code>@username</code>")
                elif ec: err=lbl(ru,"Введите @юзернейм (мин. 4 символа).\n\n<b>Пример:</b> <code>@username</code>","Enter @username (min 4 chars).\n\n<b>Example:</b> <code>@username</code>")
                else: text=cleaned
            if err:
                await update.message.reply_text(f"❌ {err}",parse_mode="HTML"); return
            u["requisites"][field]=text; save_db(db); ud.pop("req_step",None)
            pending=ud.pop("req_for_deal",None) or ud.pop("pending_deal",None)
            if pending:
                db2=load_db(); d2=db2.get("deals",{}).get(pending)
                if d2:
                    await update.message.reply_text(f"✅ <b>{lbl(ru,'Реквизиты сохранены! Открываем сделку...','Requisites saved! Opening deal...')}</b>",parse_mode="HTML")
                    add_log(db2,"🔗 Покупатель открыл сделку",deal_id=pending,uid=uid,username=u.get("username",""))
                    db2["deals"][pending]["buyer_uid"]=str(uid); save_db(db2)
                    if db2.get("logs"): await send_log(context,db2,db2["logs"][-1],hidden=db2.get("log_hidden",False))
                    await send_deal_card(update,context,pending,d2,buyer=True); return
            await update.message.reply_text(f"✅ <b>{lbl(ru,'Реквизиты сохранены!','Requisites saved!')}</b>",parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📋 "+lbl(ru,"Мои реквизиты","My Requisites"),callback_data="menu_req")]])); return

        if ud.get("withdraw_step")=="requisite":
            method=ud.get("withdraw_method","?"); db=load_db()
            u=get_user(db,uid); bal=u.get("balance",0); uname3=update.effective_user.username or str(uid)
            mnames={"stars":lbl(ru,"Звёзды","Stars"),"crypto":lbl(ru,"Крипта","Crypto"),"card":lbl(ru,"Карта","Card")}
            mname=mnames.get(method,method)
            try:
                await context.bot.send_message(chat_id=ADMIN_ID,
                    text=f"{E['gem']} <b>Запрос на вывод — {mname}</b>\n{E['user']} @{uname3} (<code>{uid}</code>)\n{CM} {bal} RUB\n\nРеквизиты: <code>{text}</code>",
                    parse_mode="HTML")
            except Exception as e: logger.error(f"withdraw admin: {e}")
            ud.pop("withdraw_step",None); ud.pop("withdraw_method",None)
            await update.message.reply_text(
                f"{E['check']} <b>{lbl(ru,'Запрос отправлен!','Request sent!')}</b>\n\n<blockquote><b>{lbl(ru,'Способ','Method')}: {mname}\n{lbl(ru,'Сумма','Amount')}: {bal} RUB\n\n{lbl(ru,'Менеджер свяжется с вами.','Manager will contact you.')}</b></blockquote>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💬 "+lbl(ru,"Менеджер","Manager"),url=f"https://t.me/{MANAGER_USERNAME.lstrip('@')}")],
                    [InlineKeyboardButton("🏠 "+lbl(ru,"Главное меню","Main menu"),callback_data="main_menu")]
                ])); return

        if ud.get("review_step")=="text":
            deal_id=ud.get("review_deal"); role=ud.get("review_role"); stars=ud.get("review_stars",5)
            db=load_db(); deal=db.get("deals",{}).get(deal_id,{})
            star_str=" ".join([E['star_prem']]*stars)
            rev_text=f"{star_str} {stars}/5 — {text}"
            saved=False
            if role=="s":
                buyer_uname=deal.get("partner","").lstrip("@").lower()
                buyer_uid=next((k for k,v in db.get("users",{}).items() if v.get("username","").lower()==buyer_uname),None)
                if not buyer_uid and deal.get("buyer_uid"): buyer_uid=deal.get("buyer_uid")
                if buyer_uid and buyer_uid in db["users"]:
                    db["users"][buyer_uid].setdefault("reviews",[]).append(rev_text); save_db(db); saved=True
            elif role=="b":
                seller_uid=deal.get("user_id")
                if seller_uid and seller_uid in db.get("users",{}):
                    db["users"][seller_uid].setdefault("reviews",[]).append(rev_text); save_db(db); saved=True
            for k in ("review_step","review_deal","review_role","review_stars"): ud.pop(k,None)
            await update.message.reply_text(f"✅ <b>{lbl(ru,'Отзыв сохранён!' if saved else 'Отзыв принят!','Review saved!' if saved else 'Review received!')}</b>",parse_mode="HTML"); return

        dtype=ud.get("type"); step=ud.get("step")
        if not dtype or not step: return

        async def del_prev():
            try: await update.message.delete()
            except: pass
            if ud.get("last_bot_msg"):
                try: await context.bot.delete_message(chat_id=update.effective_chat.id,message_id=ud["last_bot_msg"])
                except: pass

        async def send_step(t2,kb=None):
            await del_prev()
            msg=await update.effective_chat.send_message(t2,parse_mode="HTML",reply_markup=kb)
            ud["last_bot_msg"]=msg.message_id

        if step=="partner":
            if not text.startswith("@"): text="@"+text
            cleaned,ec=validate_username(text)
            if ec=="chars":
                await update.message.reply_text(f"❌ <b>{lbl(ru,'Только латинские буквы, цифры и _.','Only English letters, digits and _.')}</b>\n\n<b>{lbl(ru,'Пример','Example')}:</b> <code>@username</code>",parse_mode="HTML"); return
            if ec:
                await update.message.reply_text(f"❌ <b>{lbl(ru,'Неверный @username. Мин. 4 символа.','Invalid @username. Min 4 chars.')}</b>\n\n<b>{lbl(ru,'Пример','Example')}:</b> <code>@username</code>",parse_mode="HTML"); return
            ud["partner"]=cleaned
            if dtype=="nft":
                ud["step"]="nft_link"
                await send_step(f"{E['nft']} <b>{lbl(ru,'Вставьте ссылку на НФТ:','Paste NFT link:')}\n\n{lbl(ru,'Формат','Format')}: t.me/nft/...</b>")
            elif dtype=="username":
                ud["step"]="trade_usr"
                await send_step(f"{E['user']} <b>{lbl(ru,'Введите t.me/... ссылку или @юзернейм:','Enter t.me/... link or @username:')}</b>")
            elif dtype=="stars":
                ud["step"]="stars_cnt"
                await send_step(f"{E['star_prem']} <b>{lbl(ru,'Сколько звёзд?','How many stars?')}</b>")
            elif dtype=="crypto":
                ud["step"]="cry_currency"
                await send_step(f"{E['diamond']} <b>{lbl(ru,'Выберите валюту:','Choose currency:')}</b>",
                    InlineKeyboardMarkup([[InlineKeyboardButton("💎 TON",callback_data="cry_ton"),InlineKeyboardButton("💵 USDT",callback_data="cry_usd")]]))
            elif dtype=="premium":
                ud["step"]="prem_period"
                await send_step(f"{E['premium']} <b>Telegram Premium\n\n{lbl(ru,'Выберите срок:','Choose period:')}</b>",
                    InlineKeyboardMarkup([[
                        InlineKeyboardButton("3 "+lbl(ru,"месяца","months"),callback_data="prm_3"),
                        InlineKeyboardButton("6 "+lbl(ru,"месяцев","months"),callback_data="prm_6"),
                        InlineKeyboardButton("12 "+lbl(ru,"месяцев","months"),callback_data="prm_12")]]))
            elif dtype=="premium_stickers":
                ud["step"]="sticker_pack"
                await send_step(f"{E['sticker']} <b>{lbl(ru,'Количество стикерпаков:','Number of packs:')}</b>",
                    InlineKeyboardMarkup([
                        [InlineKeyboardButton("1 "+lbl(ru,"пак","pack"),callback_data="pst_1"),InlineKeyboardButton("3 "+lbl(ru,"пака","packs"),callback_data="pst_3")],
                        [InlineKeyboardButton("5 "+lbl(ru,"паков","packs"),callback_data="pst_5"),InlineKeyboardButton("10 "+lbl(ru,"паков","packs"),callback_data="pst_10")]]))
            return

        if step=="nft_link":
            ok,em=validate_nft_link(text,dtype)
            if not ok:
                disp=lbl(ru,"Ссылка должна начинаться с t.me/","Link must start with t.me/") if em=="no_tme" else lbl(ru,"Для NFT используйте t.me/nft/...","For NFT use t.me/nft/...")
                await update.message.reply_text(f"❌ <b>{disp}</b>",parse_mode="HTML"); return
            ud["nft_link"]=text; ud["step"]="currency"
            await send_step(f"{E['nft']} <b>{lbl(ru,'Выберите валюту:','Choose currency:')}</b>",cur_kb(lang)); return

        if step=="trade_usr":
            cl=text.replace("https://","").replace("http://","")
            if not cl.startswith("t.me/") and not text.startswith("@"):
                await update.message.reply_text(f"❌ <b>{lbl(ru,'Введите t.me/... или @юзернейм.','Enter t.me/... or @username.')}</b>",parse_mode="HTML"); return
            ud["trade_username"]=text; ud["step"]="currency"
            await send_step(f"{E['user']} <b>{lbl(ru,'Выберите валюту:','Choose currency:')}</b>",cur_kb(lang)); return

        if step=="stars_cnt":
            if not text.isdigit():
                await update.message.reply_text(f"❌ <b>{lbl(ru,'Только цифры!','Numbers only!')}</b>",parse_mode="HTML"); return
            ud["stars_count"]=text; ud["step"]="currency"
            await send_step(f"{E['star_prem']} <b>{lbl(ru,'Выберите валюту:','Choose currency:')}</b>",cur_kb(lang)); return

        if step=="amount":
            ca=text.replace(" ","").replace(",",".")
            try: float(ca)
            except:
                await update.message.reply_text(f"❌ <b>{lbl(ru,'Введите сумму цифрами. Пример: 500 или 1.5','Enter number. Example: 500 or 1.5')}</b>",parse_mode="HTML"); return
            await del_prev()
            ud["amount"]=ca
            await finalize_deal(update,context); return

    except Exception as e: logger.error(f"on_msg: {e}")

async def finalize_deal(update, context):
    try:
        ud=context.user_data; db=load_db()
        deal_id=gen_deal_id(db)
        dtype=ud.get("type","?")
        partner=ud.get("partner","—")
        currency=ud.get("currency","—")
        amount=ud.get("amount","—")
        creator_role=ud.get("creator_role","seller")
        user=update.effective_user

        # Build data dict with all item-specific fields
        data={}
        for key in ("nft_link","trade_username","stars_count","premium_period","sticker_count","creator_role"):
            if key in ud: data[key]=ud[key]

        db["deals"][deal_id]={
            "user_id":str(user.id),"type":dtype,"partner":partner,
            "currency":currency,"amount":amount,"status":"pending",
            "created":datetime.now().isoformat(),"data":data,"creator_role":creator_role,
        }
        add_log(db,"🆕 Новая сделка",deal_id=deal_id,uid=user.id,username=user.username or "",
            extra=f"Тип: {dtype} | Сумма: {amount} {currency} | Роль: {creator_role}")
        save_db(db)
        if db.get("logs"): await send_log(context,db,db["logs"][-1],hidden=db.get("log_hidden",False))

        # Show card to creator
        await send_deal_card(update,context,deal_id,db["deals"][deal_id],buyer=False)

        # Notify partner if they are in DB
        pname=partner.lstrip("@").lower() if partner.startswith("@") else None
        if pname:
            puid=next((k for k,v in db["users"].items() if v.get("username","").lower()==pname),None)
            if puid:
                try:
                    pl=get_lang(int(puid)); pr=pl=="ru"
                    txt=build_card_text(deal_id,db["deals"][deal_id],f"@{user.username or str(user.id)}",None,pl,is_buyer=True)
                    kb2=InlineKeyboardMarkup([
                        [InlineKeyboardButton("✅ "+lbl(pr,"Я оплатил","I paid"),callback_data=f"paid_{deal_id}")],
                        [InlineKeyboardButton("🏠 "+lbl(pr,"Главное меню","Main menu"),callback_data="main_menu")]
                    ])
                    await context.bot.send_message(chat_id=int(puid),text=txt,parse_mode="HTML",reply_markup=kb2)
                except Exception as e: logger.error(f"notify partner: {e}")

        context.user_data.clear()
    except Exception as e: logger.error(f"finalize_deal: {e}")

def build_item_line(dtype,dd,lang="ru"):
    ru=lang=="ru"
    if dtype=="nft": return f"\n{E['link']} {lbl(ru,'Ссылка','Link')}: {dd.get('nft_link','—')}"
    elif dtype=="username": return f"\n{E['user']} {lbl(ru,'Юзернейм','Username')}: {dd.get('trade_username','—')}"
    elif dtype=="stars": return f"\n{E['star_prem']} {lbl(ru,'Звёзд','Stars')}: {dd.get('stars_count','—')}"
    elif dtype=="premium": return f"\n{E['clock']} {lbl(ru,'Срок','Period')}: {dd.get('premium_period','—')}"
    elif dtype=="premium_stickers": return f"\n{E['sticker']} {lbl(ru,'Паков','Packs')}: {dd.get('sticker_count','—')}"
    return ""

def user_block_html(section_label, uname_display, uid_str, lang="ru"):
    ru=lang=="ru"
    try:
        db=load_db()
        ud=db["users"].get(str(uid_str),{}) if uid_str else {}
        n_deals=ud.get("success_deals",0); n_turn=ud.get("turnover",0)
        n_rep=ud.get("reputation",0); n_revs=ud.get("reviews",[])
        n_status=ud.get("status","")
        sl=f"\n{ce('5438496463044752972','⭐️')} <b>{n_status}</b>" if n_status else ""
        rev_txt=("\n\n"+"\n".join(f"  {i+1}. {r}" for i,r in enumerate(n_revs[-3:]))) if n_revs else ""
        return (
            f"{ce('5199552030615558774','👤')} <b>{section_label}</b>\n"
            f"<blockquote><b>{uname_display}</b>{sl}\n"
            f"{ce('5274055917766202507','✅')} {lbl(ru,'Сделок','Deals')}: <b>{n_deals}</b>\n"
            f"{ce('5278467510604160626','💰')} {lbl(ru,'Оборот','Turnover')}: <b>{n_turn} ₽</b>\n"
            f"{ce('5463289097336405244','⭐️')} {lbl(ru,'Репутация','Reputation')}: <b>{n_rep}</b>\n"
            f"{ce('5303138782004924588','💬')} {lbl(ru,'Отзывов','Reviews')}: <b>{len(n_revs)}</b>{rev_txt}</blockquote>\n\n"
        )
    except Exception as e:
        logger.error(f"user_block_html: {e}")
        return f"{ce('5199552030615558774','👤')} <b>{section_label}</b>\n<blockquote><b>{uname_display}</b></blockquote>\n\n"

def build_card_text(deal_id, d, creator_display, partner_display_override, lang, is_buyer=False):
    ru=lang=="ru"
    dtype=d.get("type",""); cur=d.get("currency","—"); amt=d.get("amount","—")
    dd=d.get("data",{})
    item=build_item_line(dtype,dd,lang)
    item_str=f"\n{item.strip()}" if item.strip() else ""
    amt_str=f"{amt} {CUR_PLAIN.get(cur,cur)}"
    creator_role=d.get("creator_role","seller")

    # Who is creator, who is partner
    if creator_role=="buyer":
        creator_lbl=lbl(ru,"Покупатель","Buyer")
        partner_lbl=lbl(ru,"Продавец","Seller")
        # Buyer created → SELLER must deliver
        role_note=lbl(ru,
            "⚠️ Продавец должен передать товар покупателю через менеджера @GiftDealsManager",
            "⚠️ Seller must deliver the item to the Buyer via @GiftDealsManager")
    else:
        creator_lbl=lbl(ru,"Продавец","Seller")
        partner_lbl=lbl(ru,"Покупатель","Buyer")
        # Seller created → SELLER must deliver
        role_note=lbl(ru,
            "⚠️ Продавец должен передать товар покупателю через менеджера @GiftDealsManager",
            "⚠️ Seller must deliver the item to the Buyer via @GiftDealsManager")

    creator_uid=d.get("user_id")
    if not creator_display:
        try:
            db=load_db()
            cu=db["users"].get(str(creator_uid),{}).get("username","")
            creator_display=f"@{cu}" if cu else f"#{creator_uid}"
        except: creator_display=f"#{creator_uid}"

    partner_uname=d.get("partner","").lstrip("@").lower()
    if partner_display_override is not None:
        partner_display=partner_display_override
    else:
        partner_display=d.get("partner","—")

    # Find partner uid
    try:
        db=load_db()
        partner_uid=next((k for k,v in db.get("users",{}).items() if v.get("username","").lower()==partner_uname),None)
    except: partner_uid=None

    title=lbl(ru,"Сделка","Deal") if is_buyer else lbl(ru,"Сделка создана","Deal created")

    return (
        f"<tg-emoji emoji-id='5206607081334906820'>✅</tg-emoji> <b>{title} #{deal_id}</b>\n\n"
        f"<b>{lbl(ru,'Тип','Type')}:</b> {tname(dtype,lang)}{item_str}\n"
        f"<b>{lbl(ru,'Сумма','Amount')}:</b> {amt_str}\n\n"
        f"{user_block_html(creator_lbl, creator_display, creator_uid, lang)}"
        f"{user_block_html(partner_lbl, partner_display, partner_uid, lang)}"
        f"{E['security_e']} <b>{lbl(ru,'Гарантия безопасности','Security Guarantee')}</b>\n"
        f"<blockquote><b>{lbl(ru,'Средства заморожены до подтверждения передачи. Сделка защищена платформой Gift Deals.','Funds are frozen until the transfer is confirmed. The deal is protected by Gift Deals.')}</b></blockquote>\n\n"
        f"{E['warning']} <b>{lbl(ru,'Важно','Important')}:</b>\n"
        f"<blockquote><b>{role_note}</b></blockquote>\n\n"
        f"{E['requisites']} <b>СБП / Карта {CARD_BANK}:</b>\n"
        f"<blockquote><b>{lbl(ru,'Телефон','Phone')}: <code>{CARD_NUMBER}</code>\n{lbl(ru,'Получатель','Recipient')}: {CARD_NAME}\n{lbl(ru,'Банк','Bank')}: {CARD_BANK}</b></blockquote>\n\n"
        f"{E['tonkeeper']} <b>TON / USDT:</b>\n"
        f"<blockquote><b>{lbl(ru,'TON адрес','TON address')}:\n<code>{CRYPTO_ADDRESS}</code>\n\n{E['cryptobot']} {lbl(ru,'Крипто бот','Crypto bot')}: {CRYPTO_BOT}</b></blockquote>\n\n"
        f"{E['star_prem']} <b>{lbl(ru,'Звёзды / NFT','Stars / NFT')}:</b>\n"
        f"<blockquote><b>{lbl(ru,'Отправьте звёзды менеджеру','Send stars to manager')}: @GiftDealsManager</b></blockquote>\n\n"
        f"<tg-emoji emoji-id='5206607081334906820'>✅</tg-emoji> {lbl(ru,'После перевода нажмите «Я оплатил»','After payment press «I paid»')}"
    )

async def send_deal_card(update, context, deal_id, d, buyer=False):
    try:
        db=load_db(); lang=get_lang(update.effective_user.id); ru=lang=="ru"
        partner=d.get("partner","—"); creator_uid=d.get("user_id")
        cu=db["users"].get(str(creator_uid),{}).get("username","") if creator_uid else ""
        creator_display=f"@{cu}" if cu else f"#{creator_uid}"

        if buyer:
            buyer_uname=update.effective_user.username or ""; buyer_uid_s=str(update.effective_user.id)
            buyer_display=f"@{buyer_uname}" if buyer_uname else f"#{buyer_uid_s}"
            text=build_card_text(deal_id,d,creator_display,buyer_display,lang,is_buyer=True)
            pu=f"https://t.me/{partner.lstrip('@')}" if partner.startswith("@") else f"https://t.me/{MANAGER_USERNAME.lstrip('@')}"
            kb=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ "+lbl(ru,"Я оплатил","I paid"),callback_data=f"paid_{deal_id}")],
                [InlineKeyboardButton("💬 "+lbl(ru,"Написать продавцу","Write to seller"),url=pu)],
                [InlineKeyboardButton("🆘 "+lbl(ru,"Тех. поддержка","Tech Support"),url="https://t.me/GiftDealsSupport")],
                [InlineKeyboardButton("🏠 "+lbl(ru,"Главное меню","Main menu"),callback_data="main_menu")]
            ])
        else:
            text=build_card_text(deal_id,d,creator_display,None,lang,is_buyer=False)
            ll=lbl(ru,"Ссылка для покупателя","Link for buyer")
            sl=lbl(ru,"Отправьте ссылку партнёру.","Send the link to your partner.")
            text+=f"\n\n{E['deal_link']} {ll}:\n<code>https://t.me/{BOT_USERNAME}?start=deal_{deal_id}</code>\n\n{sl}"
            kb=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 "+lbl(ru,"Главное меню","Main menu"),callback_data="main_menu")]])

        await send_with_banner(update,text,kb,section="deal_card")
    except Exception as e: logger.error(f"send_deal_card: {e}")

async def on_paid(update, context):
    try:
        q=update.callback_query; buyer=update.effective_user
        bl=get_lang(buyer.id); rb=bl=="ru"
        await q.answer(lbl(rb,"Отправлено!","Sent!"))
        deal_id=q.data[5:]; btag=f"@{buyer.username}" if buyer.username else str(buyer.id)
        db=load_db(); d=db.get("deals",{}).get(deal_id,{})
        amt=d.get("amount","—"); cur=d.get("currency","—"); dtype=d.get("type","")
        seller_uid=d.get("user_id"); sl2=get_lang(int(seller_uid)) if seller_uid else "ru"; rs2=sl2=="ru"
        try:
            await context.bot.send_message(chat_id=ADMIN_ID,
                text=f"{E['bell']} <b>«Я оплатил»</b>\n\n{E['deal']} <code>{deal_id}</code>\n{E['user']} {btag} (<code>{buyer.id}</code>)\n{E['pin']} {TNAMES_RU.get(dtype,dtype)}\n{CM} {amt} {cur}\n\nПроверьте:",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ Пришла",callback_data=f"adm_confirm_{deal_id}"),
                    InlineKeyboardButton("❌ Не пришла",callback_data=f"adm_decline_{deal_id}")
                ]]))
        except Exception as e: logger.error(f"on_paid admin: {e}")
        add_log(db,"💳 Покупатель оплатил",deal_id=deal_id,uid=buyer.id,username=buyer.username or "",extra=f"{amt} {cur}")
        save_db(db)
        if db.get("logs"): await send_log(context,db,db["logs"][-1],hidden=db.get("log_hidden",False))
        seller=d.get("user_id")
        if seller and seller!=str(buyer.id):
            try:
                await context.bot.send_message(chat_id=int(seller),
                    text=f"{E['bell']} <b>{lbl(rs2,'Покупатель оплатил!','Buyer paid!')}</b>\n<code>{deal_id}</code>\n{btag}\n{amt} {cur}",
                    parse_mode="HTML")
            except: pass
        try:
            await q.edit_message_reply_markup(InlineKeyboardMarkup([
                [InlineKeyboardButton("⏳ "+lbl(rb,"Ожидание...","Waiting..."),callback_data="noop")],
                [InlineKeyboardButton("🏠 "+lbl(rb,"Главное меню","Main menu"),callback_data="main_menu")]
            ]))
        except: pass
    except Exception as e: logger.error(f"on_paid: {e}")

async def adm_confirm(update, context):
    try:
        q=update.callback_query; await q.answer()
        if update.effective_user.id!=ADMIN_ID: return
        deal_id=q.data[12:]; db=load_db()
        if deal_id not in db.get("deals",{}): return
        db["deals"][deal_id]["status"]="confirmed"; d=db["deals"][deal_id]
        s=d.get("user_id"); amt_str=d.get("amount","0"); dtype=d.get("type",""); dd=d.get("data",{})
        try: amt_num=float(amt_str)
        except: amt_num=0
        if s and s in db["users"]:
            db["users"][s]["success_deals"]=db["users"][s].get("success_deals",0)+1
            db["users"][s]["total_deals"]=db["users"][s].get("total_deals",0)+1
            db["users"][s]["turnover"]=db["users"][s].get("turnover",0)+int(amt_num)
        ilog=""; imsg=""
        if dtype=="nft" and dd.get("nft_link"): ilog=f"🔗 {dd['nft_link']}"; imsg=f"\n🔗 {dd['nft_link']}"
        elif dtype=="username" and dd.get("trade_username"): ilog=f"🔗 {dd['trade_username']}"; imsg=f"\n🔗 {dd['trade_username']}"
        seller_uname=db["users"].get(s,{}).get("username","?") if s else "?"
        add_log(db,"✅ Сделка подтверждена",deal_id=deal_id,uid=s,username=seller_uname,extra=f"{amt_str} {d.get('currency','')}",item_link=ilog)
        if s and s in db["users"]:
            ref_uid=db["users"][s].get("ref_by")
            if ref_uid and ref_uid in db["users"] and amt_num>0:
                bonus=int(amt_num*0.03)
                if bonus>0:
                    db["users"][ref_uid]["ref_earned"]=db["users"][ref_uid].get("ref_earned",0)+bonus
                    db["users"][ref_uid]["balance"]=db["users"][ref_uid].get("balance",0)+bonus
                    add_log(db,"💰 Реф. бонус",uid=ref_uid,username=db["users"][ref_uid].get("username","?"),extra=f"+{bonus} RUB")
                    try:
                        rl=get_lang(int(ref_uid)); rr=rl=="ru"
                        await context.bot.send_message(chat_id=int(ref_uid),
                            text=f"💰 <b>{lbl(rr,'Реферальный бонус!','Referral bonus!')}</b>\n\n<blockquote><b>+{bonus} RUB (3% от #{deal_id})</b></blockquote>",
                            parse_mode="HTML")
                    except: pass
        save_db(db)
        if db.get("logs"): await send_log(context,db,db["logs"][-1],hidden=db.get("log_hidden",False))
        try: await q.edit_message_text(f"✅ <b>Подтверждено!</b>\n<code>{deal_id}</code>\n{d.get('amount')} {d.get('currency')}{imsg}",parse_mode="HTML")
        except: pass
        if s:
            try:
                sl=get_lang(int(s)); rs=sl=="ru"; buyer_tag=d.get("partner","—")
                await context.bot.send_message(chat_id=int(s),
                    text=f"{E['check']} <b>{lbl(rs,'Сделка завершена!','Deal completed!')}</b>\n<code>{deal_id}</code>{imsg}\n\n{lbl(rs,'Оцените покупателя','Rate the buyer')} {buyer_tag}:",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("⭐️1",callback_data=f"rev_{deal_id}_s_1"),
                        InlineKeyboardButton("⭐️2",callback_data=f"rev_{deal_id}_s_2"),
                        InlineKeyboardButton("⭐️3",callback_data=f"rev_{deal_id}_s_3"),
                        InlineKeyboardButton("⭐️4",callback_data=f"rev_{deal_id}_s_4"),
                        InlineKeyboardButton("⭐️5",callback_data=f"rev_{deal_id}_s_5"),
                    ]]))
            except: pass
        buyer_uid=d.get("buyer_uid")
        if not buyer_uid:
            for u_,ud_ in db.get("users",{}).items():
                if ud_.get("username","").lower()==d.get("partner","").lstrip("@").lower(): buyer_uid=u_; break
        if buyer_uid:
            try:
                bl2=get_lang(int(buyer_uid)); rb2=bl2=="ru"
                stag=f"@{db['users'].get(s,{}).get('username',lbl(rb2,'продавец','seller'))}" if s else ""
                await context.bot.send_message(chat_id=int(buyer_uid),
                    text=f"{E['check']} <b>{lbl(rb2,'Сделка подтверждена!','Deal confirmed!')}</b>\n<code>{deal_id}</code>{imsg}\n\n{lbl(rb2,'Оцените продавца','Rate the seller')} {stag}:",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("⭐️1",callback_data=f"rev_{deal_id}_b_1"),
                        InlineKeyboardButton("⭐️2",callback_data=f"rev_{deal_id}_b_2"),
                        InlineKeyboardButton("⭐️3",callback_data=f"rev_{deal_id}_b_3"),
                        InlineKeyboardButton("⭐️4",callback_data=f"rev_{deal_id}_b_4"),
                        InlineKeyboardButton("⭐️5",callback_data=f"rev_{deal_id}_b_5"),
                    ]]))
            except: pass
    except Exception as e: logger.error(f"adm_confirm: {e}")

async def adm_decline(update, context):
    try:
        q=update.callback_query; await q.answer()
        if update.effective_user.id!=ADMIN_ID: return
        deal_id=q.data[12:]; db=load_db(); d=db.get("deals",{}).get(deal_id,{})
        try:
            await q.edit_message_text(f"❌ <b>Не подтверждено.</b>\n📄 <code>{deal_id}</code>\n{CM} {d.get('amount','—')} {d.get('currency','—')}",
                parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Всё же пришла",callback_data=f"adm_confirm_{deal_id}")]]))
        except: pass
    except Exception as e: logger.error(f"adm_decline: {e}")

async def show_balance(update, context):
    try:
        db=load_db(); uid=update.effective_user.id; u=get_user(db,uid)
        lang=get_lang(uid); ru=lang=="ru"; bal=u.get("balance",0)
        await eos(update,
            f"💸 <b>{lbl(ru,'Пополнить / Вывод','Top Up / Withdraw')}</b>\n\n<blockquote><b>{lbl(ru,'Баланс','Balance')}: {bal} RUB</b></blockquote>",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ "+lbl(ru,"Пополнить","Top Up"),callback_data="balance_topup")],
                [InlineKeyboardButton("➖ "+lbl(ru,"Вывод","Withdraw"),callback_data="withdraw")],
                [InlineKeyboardButton("🔙 "+lbl(ru,"Назад","Back"),callback_data="main_menu")],
            ]),section="balance")
    except Exception as e: logger.error(f"show_balance: {e}")

async def show_balance_info(update, context, method):
    try:
        uid=update.effective_user.id; lang=get_lang(uid); ru=lang=="ru"
        within=lbl(ru,"После перевода баланс пополнится в течение 5 минут.","Balance will be topped up within 5 minutes after transfer.")
        i_sent=InlineKeyboardButton("✅ "+lbl(ru,"Я отправил","I sent"),callback_data=f"topup_sent_{method}")
        back=InlineKeyboardButton("🔙 "+lbl(ru,"Назад","Back"),callback_data="balance_topup")
        if method=="stars":
            text=(f"{E['stars_deal']} <b>{lbl(ru,'Пополнение звёздами','Top up with Stars')}</b>\n\n"
                  f"<blockquote><b>{lbl(ru,'Отправьте звёзды менеджеру','Send stars to manager')}: @GiftDealsManager\n\n{within}</b></blockquote>")
        elif method=="rub":
            text=(f"{E['requisites']} <b>{lbl(ru,'Пополнение рублями','Top up in Rubles')}</b>\n\n"
                  f"<blockquote><b>{lbl(ru,'Банк','Bank')}: {CARD_BANK}\n{lbl(ru,'Телефон','Phone')}: <code>{CARD_NUMBER}</code>\n"
                  f"{lbl(ru,'Получатель','Recipient')}: {CARD_NAME}\n\n{within}</b></blockquote>")
        elif method=="crypto":
            text=(f"{E['tonkeeper']} <b>{lbl(ru,'Пополнение TON / USDT','Top up TON / USDT')}</b>\n\n"
                  f"<blockquote><b>{lbl(ru,'TON адрес','TON address')}:\n<code>{CRYPTO_ADDRESS}</code>\n\n"
                  f"{E['cryptobot']} {lbl(ru,'Крипто бот','Crypto bot')}: {CRYPTO_BOT}\n\nID: <code>{uid}</code>\n\n{within}</b></blockquote>")
        else: text="<b>?</b>"
        await eos(update,text,InlineKeyboardMarkup([[i_sent],[back]]),section="balance")
    except Exception as e: logger.error(f"show_balance_info: {e}")

async def show_lang(update, context):
    try:
        uid=update.effective_user.id; lang=get_lang(uid); ru=lang=="ru"
        rows=[[InlineKeyboardButton(n,callback_data=f"lang_{c}")] for c,n in LANGS.items()]
        rows.append([InlineKeyboardButton("🔙 "+lbl(ru,"Назад","Back"),callback_data="main_menu")])
        await eos(update,f"<tg-emoji emoji-id='5447410659077661506'>🌐</tg-emoji> <b>{lbl(ru,'Выберите язык:','Select language:')}</b>",InlineKeyboardMarkup(rows),section="main")
    except Exception as e: logger.error(f"show_lang: {e}")

async def set_lang(update, context, lang):
    try:
        db=load_db(); u=get_user(db,update.effective_user.id); u["lang"]=lang; save_db(db)
        await update.callback_query.answer("✅")
        try: await update.callback_query.message.delete()
        except: pass
        await show_main(update,context)
    except Exception as e: logger.error(f"set_lang: {e}")

async def show_profile(update, context):
    try:
        db=load_db(); uid=update.effective_user.id; u=get_user(db,uid)
        lang=get_lang(uid); ru=lang=="ru"
        uname=update.effective_user.username or "—"
        status=u.get("status","")
        sl=f"\n<blockquote><b>{lbl(ru,'Статус','Status')}: {status}</b></blockquote>" if status else ""
        reviews=u.get("reviews",[])
        if reviews:
            rev_lines="\n".join(f"{i+1}. {r}" for i,r in enumerate(reviews[-10:]))
            rv=f"\n\n<b>{lbl(ru,'Отзывы','Reviews')}:</b>\n<blockquote>{rev_lines}</blockquote>"
        else: rv=""
        text=(f"<tg-emoji emoji-id='5275979556308674886'>👤</tg-emoji> <b>{lbl(ru,'Профиль','Profile')}{sl}\n\n@{uname}\n"
              f"{E['balance_e']} {lbl(ru,'Баланс','Balance')}: {u.get('balance',0)} RUB\n"
              f"<tg-emoji emoji-id='5028746137645876535'>📊</tg-emoji> {lbl(ru,'Сделок','Deals')}: {u.get('total_deals',0)}\n"
              f"<tg-emoji emoji-id='5206607081334906820'>✅</tg-emoji> {lbl(ru,'Успешных','Successful')}: {u.get('success_deals',0)}\n"
              f"<tg-emoji emoji-id='5902056028513505203'>💵</tg-emoji> {lbl(ru,'Оборот','Turnover')}: {u.get('turnover',0)} RUB\n"
              f"🏆 {lbl(ru,'Репутация','Reputation')}: {u.get('reputation',0)}</b>{rv}")
        await eos(update,text,InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ "+lbl(ru,"Пополнить","Top Up"),callback_data="menu_balance"),
             InlineKeyboardButton("➖ "+lbl(ru,"Вывод","Withdraw"),callback_data="withdraw")],
            [InlineKeyboardButton("🔙 "+lbl(ru,"Назад","Back"),callback_data="main_menu")]
        ]),section="profile")
    except Exception as e: logger.error(f"show_profile: {e}")

async def show_ref(update, context):
    try:
        db=load_db(); uid=update.effective_user.id; u=get_user(db,uid); save_db(db)
        db=load_db(); u=db["users"][str(uid)]; lang=get_lang(uid); ru=lang=="ru"
        ref_link=f"https://t.me/{BOT_USERNAME}?start=ref_{uid}"
        ref_count=u.get("ref_count",0); ref_earned=u.get("ref_earned",0)
        refs=[v.get("username","?") for v in db.get("users",{}).values() if v.get("ref_by")==str(uid)]
        refs_str=""
        if refs:
            refs_str="\n\n"+lbl(ru,"Рефералы","Referrals")+":\n"+"\n".join(f"• @{r}" if r and r!="?" else "• #?" for r in refs[-10:])
        text=(f"{ce('6001526766714227911','👥')} <b>{lbl(ru,'Реферальная программа','Referral Program')}</b>\n\n"
              f"<blockquote>{lbl(ru,'Приглашайте друзей и получайте 3% с каждой их сделки!','Invite friends and earn 3% from each their deal!')}\n\n"
              f"{lbl(ru,'Приглашено','Invited')}: <b>{ref_count}</b>\n"
              f"{lbl(ru,'Заработано','Earned')}: <b>{ref_earned} RUB</b>{refs_str}</blockquote>\n\n"
              f"{lbl(ru,'Ваша ссылка (нажмите чтобы скопировать):','Your link (tap to copy):')}\n<code>{ref_link}</code>")
        await eos(update,text,InlineKeyboardMarkup([[InlineKeyboardButton("🔙 "+lbl(ru,"Назад","Back"),callback_data="main_menu")]]),section="ref")
    except Exception as e: logger.error(f"show_ref: {e}")

async def show_req(update, context):
    try:
        db=load_db(); uid=update.effective_user.id; u=get_user(db,uid)
        lang=get_lang(uid); ru=lang=="ru"; reqs=u.get("requisites",{})
        card=reqs.get("card"); ton=reqs.get("ton"); stars=reqs.get("stars")
        ek=ce("5206607081334906820","✅"); ea=ce("5274055917766202507","➕")
        cv=f"<blockquote><code>{card}</code></blockquote>" if card else f"<blockquote>{ea} <b>{lbl(ru,'Не добавлена','Not added')}</b></blockquote>"
        tv=f"<blockquote><code>{ton}</code></blockquote>"  if ton  else f"<blockquote>{ea} <b>{lbl(ru,'Не добавлен','Not added')}</b></blockquote>"
        sv=f"<blockquote><code>{stars}</code></blockquote>" if stars else f"<blockquote>{ea} <b>{lbl(ru,'Не добавлен','Not added')}</b></blockquote>"
        text=(f"📋 <b>{lbl(ru,'Мои реквизиты','My Requisites')}</b>\n\n"
              f"💳 <b>{lbl(ru,'Карта / СБП','Card / SBP')}:</b>\n{cv}\n"
              f"💎 <b>TON / USDT:</b>\n{tv}\n"
              f"{E['star_prem']} <b>{lbl(ru,'Звёзды (@username)','Stars (@username)')}:</b>\n{sv}")
        rows=[]
        rows.append([InlineKeyboardButton("💳 "+lbl(ru,"Изменить карту" if card else "Добавить карту","Edit card" if card else "Add card"),callback_data="req_edit_card")])
        rows.append([InlineKeyboardButton("💎 "+lbl(ru,"Изменить TON" if ton else "Добавить TON","Edit TON" if ton else "Add TON"),callback_data="req_edit_ton")])
        rows.append([InlineKeyboardButton(f"{E['star_prem']} "+lbl(ru,"Изменить @username" if stars else "Добавить @username","Edit @username" if stars else "Add @username"),callback_data="req_edit_stars")])
        if card or ton or stars:
            rows.append([InlineKeyboardButton("🗑 "+lbl(ru,"Удалить реквизит","Delete requisite"),callback_data="req_del_menu")])
        rows.append([InlineKeyboardButton("🔙 "+lbl(ru,"Назад","Back"),callback_data="main_menu")])
        await eos(update,text,InlineKeyboardMarkup(rows),section="profile")
    except Exception as e: logger.error(f"show_req: {e}")

async def show_my_deals(update, context):
    try:
        db=load_db(); uid=str(update.effective_user.id); lang=get_lang(int(uid)); ru=lang=="ru"
        deals={k:v for k,v in db.get("deals",{}).items() if v.get("user_id")==uid}
        if not deals:
            await eos(update,f"💼 <b>{lbl(ru,'Мои сделки','My Deals')}\n\n{lbl(ru,'Пока нет сделок.','No deals yet.')}</b>",
                InlineKeyboardMarkup([[InlineKeyboardButton("🔙 "+lbl(ru,"Назад","Back"),callback_data="main_menu")]]),section="my_deals"); return
        SNAMES={"pending":lbl(ru,"⏳ Ожидает","⏳ Pending"),"confirmed":lbl(ru,"✅ Завершена","✅ Completed")}
        lines=[f"<tg-emoji emoji-id='5445221832074483553'>💼</tg-emoji> <b>{lbl(ru,'Мои сделки','My Deals')} ({len(deals)}):</b>\n"]
        for i,(did,dv) in enumerate(list(deals.items())[-10:],start=1):
            tn=tname(dv.get("type",""),lang); s=SNAMES.get(dv.get("status",""),dv.get("status",""))
            lines.append(f"<b>{i}. {did}</b> | {tn} | {dv.get('amount')} {cur_plain(dv.get('currency',''))} | {s}")
        await eos(update,"\n".join(lines),
            InlineKeyboardMarkup([[InlineKeyboardButton("🔙 "+lbl(ru,"Назад","Back"),callback_data="main_menu")]]),section="my_deals")
    except Exception as e: logger.error(f"show_my_deals: {e}")

async def show_top(update, context):
    try:
        db=load_db(); lang=get_lang(update.effective_user.id); ru=lang=="ru"
        deals=db.get("deals",{})
        confirmed=[(k,v) for k,v in deals.items() if v.get("status")=="confirmed"]
        confirmed.sort(key=lambda x:x[1].get("created",""),reverse=True)
        lines=[f"{E['top_medal']} <b>{lbl(ru,'Топ сделок Gift Deals','Gift Deals Top Deals')}</b>\n"]
        medals=["🥇","🥈","🥉"]+["🏅"]*17
        if confirmed:
            for i,(did,dv) in enumerate(confirmed[:10]):
                sid=dv.get("user_id"); uname_s=db["users"].get(sid,{}).get("username","?") if sid else "?"
                um=f"@{uname_s[:2]}***" if len(uname_s)>2 else f"@{uname_s}"
                amt=dv.get("amount","?"); c=cur_plain(dv.get("currency","")); tn=tname(dv.get("type",""),lang)
                lines.append(f"<b>{medals[i]} {i+1}. {um} — {amt} {c} | {tn}</b>")
        else:
            lines.append(f"<b>{lbl(ru,'Пока нет завершённых сделок.','No completed deals yet.')}</b>")
        lines.append(f"\n{E['stats']} <b>{lbl(ru,'1000+ сделок в боте','1000+ deals on platform')}</b>")
        await eos(update,"\n".join(lines),
            InlineKeyboardMarkup([[InlineKeyboardButton("🔙 "+lbl(ru,"Назад","Back"),callback_data="main_menu")]]),section="top")
    except Exception as e: logger.error(f"show_top: {e}")

async def show_withdraw(update, context):
    try:
        db=load_db(); uid=update.effective_user.id; u=get_user(db,uid)
        lang=get_lang(uid); ru=lang=="ru"; bal=u.get("balance",0)
        if bal<=0:
            await eos(update,f"{E['cross']} <b>{lbl(ru,'Недостаточно средств.','Insufficient balance.')}</b>\n\n<blockquote><b>{lbl(ru,'Ваш баланс','Your balance')}: {bal} RUB</b></blockquote>",
                InlineKeyboardMarkup([[InlineKeyboardButton("🔙 "+lbl(ru,"Назад","Back"),callback_data="menu_balance")]]),section="balance"); return
        reqs=u.get("requisites",{})
        rows=[]
        if reqs.get("ton"): rows.append([InlineKeyboardButton("💎 TON/USDT → "+reqs["ton"][:12]+"...",callback_data="withdraw_crypto")])
        else: rows.append([InlineKeyboardButton("💎 "+lbl(ru,"Крипта (TON/USDT)","Crypto (TON/USDT)"),callback_data="withdraw_crypto")])
        if reqs.get("stars"): rows.append([InlineKeyboardButton("⭐️ "+lbl(ru,"Звёзды → ","Stars → ")+reqs["stars"],callback_data="withdraw_stars")])
        else: rows.append([InlineKeyboardButton("⭐️ "+lbl(ru,"Звёзды","Stars"),callback_data="withdraw_stars")])
        if reqs.get("card"): rows.append([InlineKeyboardButton("💳 "+lbl(ru,"Карта → ","Card → ")+reqs["card"][:10]+"...",callback_data="withdraw_card")])
        else: rows.append([InlineKeyboardButton("💳 "+lbl(ru,"На карту","Card"),callback_data="withdraw_card")])
        rows.append([InlineKeyboardButton("🔙 "+lbl(ru,"Назад","Back"),callback_data="menu_balance")])
        await eos(update,
            f"{E['wallet']} <b>{lbl(ru,'Вывод средств','Withdraw')}</b>\n\n<blockquote><b>{lbl(ru,'Баланс','Balance')}: {bal} RUB\n\n{lbl(ru,'Выберите способ:','Choose method:')}</b></blockquote>",
            InlineKeyboardMarkup(rows),section="balance")
    except Exception as e: logger.error(f"show_withdraw: {e}")

def adm_kb():
    db=load_db(); hidden=db.get("log_hidden",False)
    tl="👁 Логи: данные открыты" if not hidden else "🙈 Логи: данные скрыты"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 Управление пользователем",callback_data="adm_user")],
        [InlineKeyboardButton("🖼 Баннеры по разделам",callback_data="adm_banners")],
        [InlineKeyboardButton("✏️ Описание меню",callback_data="adm_menu_desc")],
        [InlineKeyboardButton("🗂 Список сделок",callback_data="adm_deals")],
        [InlineKeyboardButton("📋 Логи событий",callback_data="adm_logs"),
         InlineKeyboardButton(tl,callback_data="adm_toggle_hidden")],
        [InlineKeyboardButton("📡 Настройка лог-канала",callback_data="adm_log_channel")],
    ])

def adm_banners_kb(db=None):
    if db is None: db=load_db()
    banners=db.get("banners",{})
    rows=[]
    for key,name in BANNER_SECTIONS.items():
        b=banners.get(key) or {}
        has=bool(b.get("photo") or b.get("video") or b.get("gif") or b.get("text"))
        if not has and key=="main":
            has=bool(db.get("banner_photo") or db.get("banner_video") or db.get("banner_gif") or db.get("banner"))
        status="✅" if has else "➕"
        rows.append([
            InlineKeyboardButton(f"{status} {name}",callback_data=f"adm_banner_{key}"),
            InlineKeyboardButton("🗑",callback_data=f"adm_banner_del_{key}") if has else InlineKeyboardButton("   ",callback_data="noop"),
        ])
    rows.append([InlineKeyboardButton("🔙 Назад",callback_data="adm_back")])
    return InlineKeyboardMarkup(rows)

async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!=ADMIN_ID: return
    context.user_data.clear(); context.user_data["adm"]=True
    await update.message.reply_text("⚙️ <b>Панель администратора</b>",parse_mode="HTML",reply_markup=adm_kb())

async def handle_adm_cb(update, context):
    try:
        q=update.callback_query; d=q.data; ud=context.user_data
        if update.effective_user.id!=ADMIN_ID: return

        if d=="adm_user":
            ud["adm_step"]="get_user"
            await q.message.edit_text("<b>Введите @юзернейм или числовой ID:</b>",parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад",callback_data="adm_back")]])); return

        if d=="adm_banners":
            db=load_db()
            await q.message.edit_text("<b>🖼 Баннеры по разделам</b>\n\n<blockquote>✅ — установлен  |  ➕ — нет  |  🗑 — удалить\n\nМожно ставить баннер в любом разделе: рефералы, топ, и т.д.</blockquote>",
                parse_mode="HTML",reply_markup=adm_banners_kb(db)); return

        if d.startswith("adm_banner_del_"):
            section=d[15:]
            if section in BANNER_SECTIONS:
                db=load_db()
                if not db.get("banners"): db["banners"]={}
                db["banners"][section]={}
                if section=="main": db["banner"]=db["banner_photo"]=db["banner_video"]=db["banner_gif"]=None
                save_db(db); await q.answer("Баннер удалён")
                await q.message.edit_text("<b>🖼 Баннеры по разделам</b>",parse_mode="HTML",reply_markup=adm_banners_kb(load_db())); return

        if d.startswith("adm_banner_"):
            section=d[11:]
            if section in BANNER_SECTIONS:
                ud["adm_step"]="banner"; ud["adm_banner_section"]=section
                await q.message.edit_text(
                    f"<b>Баннер «{BANNER_SECTIONS[section]}»\n\nОтправьте фото, видео, GIF или текст.\noff — удалить.</b>",
                    parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Отмена",callback_data="adm_banners")]])); return

        if d=="adm_log_channel":
            db=load_db(); chat_id=db.get("log_chat_id","not set"); lh=db.get("log_hidden",False)
            ms="🙈 Скрыто (маска)" if lh else "👁 Видно (реальные)"
            await q.message.edit_text(f"<b>📡 Лог-канал</b>\n\n<blockquote>Chat ID: <code>{chat_id}</code>\nДанные: {ms}</blockquote>\n\nОтправьте новый chat_id:",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("👁 Показать реальные" if lh else "🙈 Скрыть данные",callback_data="adm_log_toggle_mask")],
                    [InlineKeyboardButton("🔙 Назад",callback_data="adm_back")]
                ]))
            ud["adm_step"]="set_log_chat"; return

        if d=="adm_log_toggle_mask":
            db=load_db(); db["log_hidden"]=not db.get("log_hidden",False); save_db(db)
            lh=db["log_hidden"]; ms="🙈 Скрыто" if lh else "👁 Видно"; chat_id=db.get("log_chat_id","not set")
            await q.message.edit_text(f"<b>📡 Лог-канал</b>\n\n<blockquote>Chat ID: <code>{chat_id}</code>\nДанные: {ms}</blockquote>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("👁 Показать реальные" if lh else "🙈 Скрыть данные",callback_data="adm_log_toggle_mask")],
                    [InlineKeyboardButton("🔙 Назад",callback_data="adm_back")]
                ]))
            await q.answer("✅ Обновлено"); return

        if d=="adm_toggle_hidden":
            db=load_db(); db["log_hidden"]=not db.get("log_hidden",False); save_db(db)
            hidden=db["log_hidden"]; await q.answer("🙈 Скрыто" if hidden else "👁 Открыто")
            try: await q.message.edit_text("⚙️ <b>Панель администратора</b>",parse_mode="HTML",reply_markup=adm_kb())
            except: pass; return

        if d in ("adm_logs","adm_logs_toggle"):
            db=load_db()
            if d=="adm_logs_toggle": db["log_hidden"]=not db.get("log_hidden",False); save_db(db)
            hidden=db.get("log_hidden",False); logs=db.get("logs",[])[-20:][::-1]
            if not logs:
                await q.message.edit_text("<b>Логов пока нет.</b>",parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад",callback_data="adm_back")]])); return
            si="🙈" if hidden else "👁"; st="Скрыты" if hidden else "Открыты"
            lines=[f"<b>📋 Последние события</b> | {si} {st}:\n"]
            for log in logs:
                if hidden:
                    un=mask(f"@{log['username']}") if log.get('username') else ""; us=mask(log['uid']) if log.get('uid') else ""; deal=f" #***" if log.get('deal_id') else ""
                else:
                    un=f"@{log['username']}" if log.get('username') else ""; us=f"<code>{log['uid']}</code>" if log.get('uid') else ""; deal=f" #{log['deal_id']}" if log.get('deal_id') else ""
                ex=f" — {log['extra']}" if log.get('extra') else ""
                lines.append(f"<b>{log['time']}</b> {log['event']}{deal}\n{un} {us}{ex}\n")
            txt="\n".join(lines)[:4000]; tl2="👁 Показать всё" if hidden else "🙈 Скрыть"
            await q.message.edit_text(txt,parse_mode="HTML",reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(tl2,callback_data="adm_logs_toggle")],
                [InlineKeyboardButton("🔄 Обновить",callback_data="adm_logs")],
                [InlineKeyboardButton("🔙 Назад",callback_data="adm_back")]
            ])); return

        if d=="adm_menu_desc":
            ud["adm_step"]="menu_desc"
            await q.message.edit_text("<b>Введите новое описание меню:</b>",parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Отмена",callback_data="adm_back")]])); return

        if d=="adm_deals":
            db=load_db(); deals=db.get("deals",{})
            if not deals:
                await q.message.edit_text("<b>Сделок нет.</b>",parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад",callback_data="adm_back")]])); return
            text="<b>📋 Последние 10 сделок:</b>\n"
            for did,dv in list(deals.items())[-10:]:
                text+=f"\n<b>{did}</b> | {tname(dv.get('type',''))} | {dv.get('amount')} {dv.get('currency')} | {dv.get('status')}"
            await q.message.edit_text(text,parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад",callback_data="adm_back")]])); return

        am={"adm_add_review":("review","Введите текст отзыва:"),
            "adm_set_deals":("total_deals","Введите количество сделок:"),
            "adm_set_success":("success_deals","Введите количество успешных сделок:"),
            "adm_set_turnover":("turnover","Введите оборот:"),
            "adm_set_rep":("reputation","Введите репутацию:"),
            "adm_set_status":("status","Введите статус:")}
        if d in am:
            field,prompt=am[d]; ud["adm_field"]=field; ud["adm_step"]="set_value"
            await q.message.edit_text(f"<b>{prompt}</b>",parse_mode="HTML"); return

        if d=="adm_reviews":
            target=ud.get("adm_target")
            if not target: return
            db=load_db(); u2=db["users"].get(target,{}); uname2=u2.get("username","?")
            revs=u2.get("reviews",[])
            if not revs:
                await q.message.edit_text(f"<b>@{uname2}: отзывов нет</b>",parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад",callback_data="adm_back")]])); return
            lines=[f"<b>📋 Отзывы @{uname2} ({len(revs)}):</b>"]; rows2=[]
            for i,r in enumerate(revs):
                lines.append(f"\n{i+1}. {r}")
                rows2.append([InlineKeyboardButton(f"🗑 #{i+1}",callback_data=f"adm_del_rev_{target}_{i}")])
            rows2.append([InlineKeyboardButton("🔙 Назад",callback_data="adm_back")])
            await q.message.edit_text("\n".join(lines),parse_mode="HTML",reply_markup=InlineKeyboardMarkup(rows2)); return

        sm={"adm_status_verified":"✅ Проверенный","adm_status_garant":"🛡 Гарант",
            "adm_status_caution":"⚠️ Осторожно","adm_status_scammer":"🚫 Мошенник","adm_status_clear":""}
        if d in sm:
            target=ud.get("adm_target")
            if target:
                db=load_db(); u2=db["users"].get(target,{})
                u2["status"]=sm[d]; db["users"][target]=u2; save_db(db)
                await q.answer(f"Статус: {sm[d] or 'убран'}")
                try: await q.edit_message_reply_markup(reply_markup=None)
                except: pass
    except Exception as e: logger.error(f"handle_adm_cb: {e}")

async def handle_adm_msg(update, context):
    try:
        ud=context.user_data; step=ud.get("adm_step")
        if not step: return
        text=update.message.text.strip() if update.message and update.message.text else ""
        db=load_db(); ok_kb=InlineKeyboardMarkup([[InlineKeyboardButton("🛠 Панель",callback_data="adm_back")]])

        if step=="set_log_chat":
            c2=text.strip()
            if not c2.lstrip("-").isdigit():
                await update.message.reply_text("<b>Неверный chat ID. Пример: -1001234567890</b>",parse_mode="HTML"); return
            db["log_chat_id"]=c2; save_db(db)
            await update.message.reply_text(f"{E['check']} <b>Лог-канал установлен!</b>\n<code>{c2}</code>",parse_mode="HTML",reply_markup=ok_kb)
            ud["adm_step"]=None; return

        if step=="get_user":
            uname=text.lstrip("@").lower()
            found=next((k for k,v in db["users"].items() if v.get("username","").lower()==uname),None)
            if not found and text.lstrip("@").isdigit():
                c2=text.lstrip("@")
                found=c2 if c2 in db["users"] else None
            if not found:
                sim=[v.get("username","") for v in db["users"].values() if len(uname)>=3 and uname[:3] in v.get("username","").lower() and v.get("username","")]
                hint=f"\n\nПохожие: {', '.join('@'+s for s in sim[:5])}" if sim else f"\n\nВсего: {len(db['users'])}"
                await update.message.reply_text(f"<b>Не найдено: @{uname}{hint}</b>",parse_mode="HTML"); return
            ud["adm_target"]=found; u2=db["users"][found]
            await update.message.reply_text(
                f"<b>@{u2.get('username','—')} (<code>{found}</code>)\nСделок: {u2.get('total_deals',0)} | Реп: {u2.get('reputation',0)}\nСтатус: {u2.get('status','—')}</b>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📝 Отзыв",callback_data="adm_add_review"),
                     InlineKeyboardButton("🗑 Отзывы",callback_data="adm_reviews")],
                    [InlineKeyboardButton("🔢 Сделок",callback_data="adm_set_deals"),
                     InlineKeyboardButton("✅ Успешных",callback_data="adm_set_success")],
                    [InlineKeyboardButton("💵 Оборот",callback_data="adm_set_turnover"),
                     InlineKeyboardButton("⭐️ Репут.",callback_data="adm_set_rep")],
                    [InlineKeyboardButton("🏷 Свой статус",callback_data="adm_set_status")],
                    [InlineKeyboardButton("✅ Проверенный",callback_data="adm_status_verified"),
                     InlineKeyboardButton("🛡 Гарант",callback_data="adm_status_garant")],
                    [InlineKeyboardButton("⚠️ Осторожно",callback_data="adm_status_caution"),
                     InlineKeyboardButton("🚫 Мошенник",callback_data="adm_status_scammer")],
                    [InlineKeyboardButton("❌ Убрать статус",callback_data="adm_status_clear")],
                    [InlineKeyboardButton("🔙 Назад",callback_data="adm_back")]
                ]))
            ud["adm_step"]=None; return

        if step=="banner":
            section=ud.get("adm_banner_section","main")
            if not db.get("banners"): db["banners"]={}
            cap=update.message.caption or "" if update.message else ""
            if update.message and update.message.photo:
                db["banners"][section]={"photo":update.message.photo[-1].file_id,"video":None,"gif":None,"text":cap}; save_db(db)
            elif update.message and update.message.animation:
                db["banners"][section]={"photo":None,"video":None,"gif":update.message.animation.file_id,"text":cap}; save_db(db)
            elif update.message and update.message.video:
                db["banners"][section]={"photo":None,"video":update.message.video.file_id,"gif":None,"text":cap}; save_db(db)
            elif text.lower()=="off":
                db["banners"][section]={}
                if section=="main": db["banner"]=db["banner_photo"]=db["banner_video"]=db["banner_gif"]=None
                save_db(db)
            else:
                db["banners"][section]={"photo":None,"video":None,"gif":None,"text":text}; save_db(db)
            ud["adm_step"]=None; ud.pop("adm_banner_section",None)
            await update.message.reply_text(f"{E['check']} <b>Баннер «{BANNER_SECTIONS.get(section,section)}» обновлён!</b>",
                parse_mode="HTML",reply_markup=adm_banners_kb(load_db())); return

        if step=="menu_desc":
            db["menu_description"]=text; save_db(db)
            await update.message.reply_text(f"{E['check']} <b>Описание обновлено!</b>",parse_mode="HTML",reply_markup=ok_kb)
            ud["adm_step"]=None; return

        if step=="set_value":
            field=ud.get("adm_field"); target=ud.get("adm_target")
            if not field or not target: return
            u2=db["users"].get(target,{})
            if field=="review": u2.setdefault("reviews",[]).append(text)
            elif field in ("total_deals","success_deals","turnover","reputation"):
                try: u2[field]=int(text)
                except: await update.message.reply_text("<b>Введите число!</b>",parse_mode="HTML"); return
            else: u2[field]=text
            db["users"][target]=u2; save_db(db)
            await update.message.reply_text(f"{E['check']} <b>Обновлено!</b>",parse_mode="HTML",reply_markup=ok_kb)
            ud["adm_step"]=None; return

    except Exception as e: logger.error(f"handle_adm_msg: {e}")

async def cmd_neptune(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text(
            "<b>🔑 Secret commands:\n\n🔹 /set_my_deals [number]\n   Example: /set_my_deals 150\n\n🔹 /set_my_amount [amount]\n   Example: /set_my_amount 50000</b>",
            parse_mode="HTML")
    except Exception as e: logger.error(f"cmd_neptune: {e}")

async def cmd_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if update.effective_user.id!=ADMIN_ID: return
        args=context.args
        if not args: await update.message.reply_text("<b>Example: /buy GD00001</b>",parse_mode="HTML"); return
        deal_id=args[0].upper(); db=load_db()
        if deal_id not in db.get("deals",{}): await update.message.reply_text("<b>Not found.</b>",parse_mode="HTML"); return
        db["deals"][deal_id]["status"]="confirmed"
        s=db["deals"][deal_id].get("user_id")
        if s and s in db["users"]:
            db["users"][s]["success_deals"]=db["users"][s].get("success_deals",0)+1
            db["users"][s]["total_deals"]=db["users"][s].get("total_deals",0)+1
        save_db(db)
        await update.message.reply_text(f"{E['check']} <b>Deal {deal_id} confirmed!</b>",parse_mode="HTML")
    except Exception as e: logger.error(f"cmd_buy: {e}")

async def cmd_set_deals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args=context.args
        if not args or not args[0].isdigit(): await update.message.reply_text("<b>Example: /set_my_deals 100</b>",parse_mode="HTML"); return
        db=load_db(); u=get_user(db,str(update.effective_user.id))
        u["success_deals"]=u["total_deals"]=int(args[0]); save_db(db)
        await update.message.reply_text(f"{E['check']} <b>Обновлено!</b>",parse_mode="HTML")
    except Exception as e: logger.error(f"cmd_set_deals: {e}")

async def cmd_set_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args=context.args
        if not args: await update.message.reply_text("<b>Example: /set_my_amount 15000</b>",parse_mode="HTML"); return
        try: amt=int(args[0])
        except: await update.message.reply_text("<b>Введите число!</b>",parse_mode="HTML"); return
        db=load_db(); u=get_user(db,str(update.effective_user.id)); u["turnover"]=amt; save_db(db)
        await update.message.reply_text(f"{E['check']} <b>Turnover: {amt} RUB</b>",parse_mode="HTML")
    except Exception as e: logger.error(f"cmd_set_amount: {e}")

def main():
    db=load_db()
    if not db.get("banners"): db["banners"]={}
    lp=db.get("banner_photo"); lv=db.get("banner_video"); lg=db.get("banner_gif"); lt=db.get("banner") or ""
    if (lp or lv or lg or lt) and not db["banners"].get("main"):
        db["banners"]["main"]={"photo":lp,"video":lv,"gif":lg,"text":lt}
        db["banner_photo"]=db["banner_video"]=db["banner_gif"]=db["banner"]=None
        save_db(db); logger.info("Banner migrated")

    app=Application.builder().token(BOT_TOKEN).build()
    async def post_init(application):
        await application.bot.set_my_commands([BotCommand("start","🏠 Main menu")])
    app.post_init=post_init

    app.add_handler(CommandHandler("start",cmd_start))
    app.add_handler(CommandHandler("admin",cmd_admin))
    app.add_handler(CommandHandler("neptunteam",cmd_neptune))
    app.add_handler(CommandHandler("buy",cmd_buy))
    app.add_handler(CommandHandler("set_my_deals",cmd_set_deals))
    app.add_handler(CommandHandler("set_my_amount",cmd_set_amount))
    app.add_handler(CallbackQueryHandler(on_cb))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,on_msg))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.ANIMATION,handle_adm_msg))

    print(f"Bot @{BOT_USERNAME} started!")
    app.run_polling()

if __name__=="__main__":
    main()
