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
    r("CREATE TABLE IF NOT EXISTS u(id INTEGER PRIMARY KEY,n TEXT,rh INT DEFAULT -1,rm INT DEFAULT 0)")
    r("CREATE TABLE IF NOT EXISTS h(id INTEGER PRIMARY KEY AUTOINCREMENT,u INT,n TEXT,a INT DEFAULT 1)")
    r("CREATE TABLE IF NOT EXISTS c(id INTEGER PRIMARY KEY AUTOINCREMENT,u INT,h INT,d TEXT,m INT DEFAULT 0,UNIQUE(h,d))")

MN = ReplyKeyboardMarkup([
    ["📋 Сегодня", "📊 Стат"],
    ["📆 Календарь", "❓ Помощь"],
    ["➕ Добав", "🗑 Удал"]
], resize_keyboard=True)

async def start(up, ctx):
    u = up.effective_user.id
    r("INSERT OR IGNORE INTO u(id,n) VALUES(?,?)",
      (u, up.effective_user.username or ""))
    await up.message.reply_text(
        "👋 Жми 📋 Сегодня", reply_markup=MN)

async def today(msg, u, ed=False):
    d = datetime.now().strftime("%Y-%m-%d")
    rows = r(
        "SELECT h.id,h.n,"
        "CASE WHEN c.id IS NOT NULL THEN 1 ELSE 0 END,"
        "COALESCE(c.m,0) "
        "FROM h LEFT JOIN c ON h.id=c.h AND c.d=? "
        "WHERE h.u=? AND h.a=1", (d, u), 2)
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
                hrs = mn // 60
                mins = mn % 60
                if hrs > 0 and mins > 0:
                    t += f" ({hrs}ч {mins}м)"
                elif hrs > 0:
                    t += f" ({hrs}ч)"
                else:
                    t += f" ({mins}м)"
            t += "\n"
            dn += 1
            kb.append([
                InlineKeyboardButton("✅", callback_data=f"t_{hid}"),
                InlineKeyboardButton("⏱", callback_data=f"m_{hid}")
            ])
        else:
            t += f"⬜ {hn}\n"
            kb.append([
                InlineKeyboardButton(f"⬜ {hn}", callback_data=f"t_{hid}")
            ])
    tot = len(rows)
    pct = round(dn / tot * 100) if tot else 0
    bar = "🟩" * (pct // 10) + "⬜" * (10 - pct // 10)
    t += f"\n{bar} {pct}%"
    if dn == tot and tot > 0:
        t += "\n🎉 Всё сделано!"
    mk = InlineKeyboardMarkup(kb)
    if ed:
        try: await msg.edit_text(t, reply_markup=mk)
        except: pass
    else:
        await msg.reply_text(t, reply_markup=mk)

async def calendar(msg, u, wo=0, ed=False):
    now = datetime.now()
    mon = now - timedelta(days=now.weekday()) + timedelta(weeks=wo)
    dn = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    d1 = mon.strftime("%d.%m")
    d2 = (mon + timedelta(days=6)).strftime("%d.%m")
    t = f"📆 {d1} — {d2}:\n\n"
    for i in range(7):
        day = mon + timedelta(days=i)
        ds = day.strftime("%Y-%m-%d")
        mark = " ← СЕГОДНЯ" if ds == now.strftime("%Y-%m-%d") else ""
        total = r("SELECT COUNT(*) FROM h WHERE u=? AND a=1", (u,), 1)
        done = r("SELECT COUNT(*) FROM c WHERE u=? AND d=?", (u, ds), 1)
        tl = total[0] if total else 0
        dc = done[0] if done else 0
        if tl == 0:
            sv = "—"
        elif day.date() <= now.date():
            if dc == tl:
                sv = f"✅{dc}/{tl}"
            elif dc > 0:
                sv = f"⚠️{dc}/{tl}"
            else:
                sv = f"❌0/{tl}"
        else:
            sv = f"📌{tl}"
        name = dn[day.weekday()]
        dd = day.strftime("%d.%m")
        t += f"{name} {dd}: {sv}{mark}\n"
    kb = [[
        InlineKeyboardButton("⬅️", callback_data=f"cal_{wo-1}"),
        InlineKeyboardButton("Сегодня", callback_data="cal_0"),
        InlineKeyboardButton("➡️", callback_data=f"cal_{wo+1}")
    ]]
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
        ctx.user_data["time_hid"] = hid
        try: await q.message.edit_text("⏱ Напиши время.\nПримеры: 30 или 1ч30м или 7ч")
        except: pass
    elif d == "back":
        await today(q.message, u, True)
    elif d.startswith("cal_"):
        wo = int(d[4:])
        await calendar(q.message, u, wo, True)
    elif d.startswith("del_"):
        hid = int(d[4:])
        r("UPDATE h SET a=0 WHERE id=?", (hid,))
        try: await q.message.edit_text("✅ Удалено!")
        except: pass

def parse_time(t):
    t = t.strip().lower().replace(" ", "")
    if t.isdigit():
        return int(t)
    total = 0
    if "ч" in t:
        parts = t.split("ч")
        h = parts[0]
        if h.isdigit():
            total += int(h) * 60
        rest = parts[1] if len(parts) > 1 else ""
    else:
        rest = t
    rest = rest.replace("м", "").replace("m", "")
    if rest.isdigit():
        total += int(rest)
    return total if total > 0 else None

async def txt(up, ctx):
    u = up.effective_user.id
    t = up.message.text
    if ctx.user_data.get("time_hid"):
        hid = ctx.user_data.pop("time_hid")
        mn = parse_time(t)
        if mn is None:
            await up.message.reply_text("❌ Не понял. Напиши число: 30 или 1ч30м")
            ctx.user_data["time_hid"] = hid
            return
        dd = datetime.now().strftime("%Y-%m-%d")
        x = r("SELECT id FROM c WHERE h=? AND d=?", (hid, dd), 1)
        if x:
            r("UPDATE c SET m=? WHERE id=?", (mn, x[0]))
        else:
            r("INSERT INTO c(u,h,d,m) VALUES(?,?,?,?)", (u, hid, dd, mn))
        hrs = mn // 60
        mins = mn % 60
        if hrs > 0 and mins > 0:
            ft = f"{hrs}ч {mins}м"
        elif hrs > 0:
            ft = f"{hrs}ч"
        else:
            ft = f"{mins}м"
        await up.message.reply_text(f"✅ Записано: {ft}", reply_markup=MN)
        return
    if ctx.user_data.get("add"):
        r("INSERT INTO h(u,n) VALUES(?,?)", (u, t))
        ctx.user_data.pop("add", None)
        await up.message.reply_text(f"✅ {t} добавлена!", reply_markup=MN)
        return
    if "Сегодня" in t:
        await today(up.message, u)
    elif "Календарь" in t:
        await calendar(up.message, u)
    elif "Добав" in t:
        ctx.user_data["add"] = True
        await up.message.reply_text("✍️ Напиши название:")
    elif "Удал" in t:
        hb = r("SELECT id,n FROM h WHERE u=? AND a=1", (u,), 2)
        if not hb:
            await up.message.reply_text("Нет!", reply_markup=MN)
            return
        kb = []
        for i, n in hb:
            kb.append([InlineKeyboardButton(f"🗑 {n}", callback_data=f"del_{i}")])
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
        await up.message.reply_text(
            "📋=сегодня\n📆=календарь\n➕=добавить\n🗑=удалить\n⏱=время",
            reply_markup=MN)
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
