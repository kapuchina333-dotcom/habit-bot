import logging, sqlite3, os
from datetime import datetime, timedelta
from telegram import *
from telegram.ext import *

T = os.environ.get("BOT_TOKEN", "")
DB = "h.db"

def r(s, p=(), o=0):
    c = sqlite3.connect(DB)
    e = c.cursor()
    e.execute(s, p)
    if o == 1:
        x = e.fetchone()
    elif o == 2:
        x = e.fetchall()
    else:
        x = e.lastrowid
    c.commit()
    c.close()
    return x

def setup():
    r("CREATE TABLE IF NOT EXISTS u(id INTEGER PRIMARY KEY,n TEXT,rh INT DEFAULT -1)")
    r("CREATE TABLE IF NOT EXISTS h(id INTEGER PRIMARY KEY AUTOINCREMENT,u INT,n TEXT,a INT DEFAULT 1)")
    r("CREATE TABLE IF NOT EXISTS c(id INTEGER PRIMARY KEY AUTOINCREMENT,u INT,h INT,d TEXT,m INT DEFAULT 0,UNIQUE(h,d))")

MN = ReplyKeyboardMarkup([["📋 Сегодня","📊 Стат"],["➕ Добав","🗑 Удал"],["❓ Помощь"]],resize_keyboard=True)

async def start(up, ctx):
    u = up.effective_user.id
    r("INSERT OR IGNORE INTO u(id,n) VALUES(?,?)", (u, up.effective_user.username or ""))
    await up.message.reply_text("👋 Жми 📋 Сегодня", reply_markup=MN)

async def today(msg, u, ed=False):
    d = datetime.now().strftime("%Y-%m-%d")
    rows = r("SELECT h.id,h.n,CASE WHEN c.id IS NOT NULL THEN 1 ELSE 0 END,COALESCE(c.m,0) FROM h LEFT JOIN c ON h.id=c.h AND c.d=? WHERE h.u=? AND h.a=1", (d, u), 2)
    if not rows:
        t = "Нет привычек! Жми ➕ Добав"
        if ed:
            try: await msg.edit_text(t)
            except: pass
        else:
            await msg.reply_text(t, reply_markup=MN)
        return
    t = "📋 Сегодня:\n\n"
    kb = []
    dn = 0
    for hid, hn, ok, mn in rows:
        if ok:
            t += f"✅ {hn}"
            if mn > 0:
                t += f" ({mn} мин)"
            t += "\n"
            dn += 1
            kb.append([InlineKeyboardButton("✅", callback_data=f"t_{hid}"), InlineKeyboardButton("⏱", callback_data=f"m_{hid}")])
        else:
            t += f"⬜ {hn}\n"
            kb.append([InlineKeyboardButton(f"⬜ {hn}", callback_data=f"t_{hid}")])
    tot = len(rows)
    pct = round(dn/tot*100) if tot else 0
    t += f"\n{'🟩'*(pct//10)}{'⬜'*(10-pct//10)} {pct}%"
    if dn == tot and tot > 0:
        t += "\n🎉 Всё сделано!"
    mk = InlineKeyboardMarkup(kb)
    if ed:
        try: await msg.edit_text(t, reply_markup=mk)
        except: pass
    else:
        await msg.reply_text(t, reply_markup=mk)

async def cb(up, ctx):
    q = up.callback_query
    await q.answer()
    u = q.from_user.id
    d = q.data
    if d.startswith("t_"):
        hid = int(d[2:])
        dd = datetime.now().strftime("%Y-%m-%d")
        x = r("SELECT id FROM c WHERE h=? AND d=?", (hid, dd), 1)
        if x:
            r("DELETE FROM c WHERE id=?", (x[0],))
        else:
            r("INSERT INTO c(u,h,d,m) VALUES(?,?,?,0)", (u, hid, dd))
        await today(q.message, u, True)
    elif d.startswith("m_"):
        hid = int(d[2:])
        h = str(hid)
        kb = [
            [InlineKeyboardButton("15м", callback_data=f"s_{h}_15"),
             InlineKeyboardButton("30м", callback_data=f"s_{h}_30"),
             InlineKeyboardButton("45м", callback_data=f"s_{h}_45")],
            [InlineKeyboardButton("1ч", callback_data=f"s_{h}_60"),
             InlineKeyboardButton("2ч", callback_data=f"s_{h}_120"),
             InlineKeyboardButton("3ч", callback_data=f"s_{h}_180")],
            [InlineKeyboardButton("⬅️", callback_data="back")]
        ]
        try: await q.message.edit_text("⏱ Выбери:", reply_markup=InlineKeyboardMarkup(kb))
        except: pass
    elif d.startswith("s_"):
        p = d[2:].split("_")
        hid = int(p[0])
        mn = int(p[1])
        dd = datetime.now().strftime("%Y-%m-%d")
        x = r("SELECT id FROM c WHERE h=? AND d=?", (hid, dd), 1)
        if x:
            r("UPDATE c SET m=? WHERE id=?", (mn, x[0]))
        else:
            r("INSERT INTO c(u,h,d,m) VALUES(?,?,?,?)", (u, hid, dd, mn))
        try: await q.message.edit_text(f"✅ {mn} мин")
        except: pass
        await today(q.message, u, False)
    elif d == "back":
        await today(q.message, u, True)
    elif d.startswith("del_"):
        hid = int(d[4:])
        r("UPDATE h SET a=0 WHERE id=?", (hid,))
        try: await q.message.edit_text("✅ Удалено!")
        except: pass

async def txt(up, ctx):
    u = up.effective_user.id
    t = up.message.text
    if ctx.user_data.get("add"):
        r("INSERT INTO h(u,n) VALUES(?,?)", (u, t))
        ctx.user_data.pop("add", None)
        await up.message.reply_text(f"✅ {t} добавлена!", reply_markup=MN)
        return
    if "Сегодня" in t:
        await today(up.message, u)
    elif "Добав" in t:
        ctx.user_data["add"] = True
        await up.message.reply_text("✍️ Напиши название:")
    elif "Удал" in t:
        hb = r("SELECT id,n FROM h WHERE u=? AND a=1", (u,), 2)
        if not hb:
            await up.message.reply_text("Нет!", reply_markup=MN)
            return
        kb = [[InlineKeyboardButton(f"🗑 {n}", callback_data=f"del_{i}")] for i, n in hb]
        await up.message.reply_text("🗑 Какую?", reply_markup=InlineKeyboardMarkup(kb))
    elif "Стат" in t:
        hb = r("SELECT id,n FROM h WHERE u=? AND a=1", (u,), 2)
        if not hb:
            await up.message.reply_text("Нет!", reply_markup=MN)
            return
        tx = "📊 Привычки:\n\n"
        for hid, hn in hb:
            tx += f"{hn}\n"
        await up.message.reply_text(tx, reply_markup=MN)
    elif "Помощь" in t:
        await up.message.reply_text("📋=сегодня\n➕=добавить\n🗑=удалить\n⏱=время", reply_markup=MN)
    else:
        await up.message.reply_text("👇", reply_markup=MN)

def main():
    setup()
    app = Application.builder().token(T).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(cb))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, txt))
    print("OK")
    app.run_polling()

if __name__ == "__main__":
    main()
