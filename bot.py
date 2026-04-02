import logging, sqlite3, time as ttime, os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_PLT = True
except:
    HAS_PLT = False

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
MENU_KB = ReplyKeyboardMarkup(
    [["📋 Сегодня", "📊 Статистика"],
     ["🔔 Напоминание", "📆 Календарь"],
     ["➕ Добавить", "🗑 Удалить"],
     ["🏆 Достижения", "⚙️ Настройки"],
     ["❓ Помощь"]], resize_keyboard=True)
DEFAULT_HABITS = ["💧 Пить воду", "🏃 Зарядка", "📖 Чтение", "🧘 Медитация",
                  "😴 Сон до 23:00", "🥗 Здоровое питание", "📵 Без телефона 1ч",
                  "✍️ Дневник", "🚶 Прогулка", "💊 Витамины"]
DAYS_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
logging.basicConfig(level=logging.INFO)
timers = {}


def init_db():
    c = sqlite3.connect("habits.db")
    e = c.cursor()
    e.execute("CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY,username TEXT,reminder_hour INTEGER DEFAULT -1,reminder_min INTEGER DEFAULT 0)")
    e.execute("CREATE TABLE IF NOT EXISTS habits(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,name TEXT,active INTEGER DEFAULT 1,days TEXT DEFAULT '0123456')")
    e.execute("CREATE TABLE IF NOT EXISTS completions(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,habit_id INTEGER,date TEXT,minutes INTEGER DEFAULT 0,UNIQUE(habit_id,date))")
    e.execute("CREATE TABLE IF NOT EXISTS achievements(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,ach_id TEXT,date TEXT,UNIQUE(user_id,ach_id))")
    try:
        e.execute("ALTER TABLE habits ADD COLUMN days TEXT DEFAULT '0123456'")
    except:
        pass
    c.commit()
    c.close()


def db(q, p=(), f=False, f1=False):
    c = sqlite3.connect("habits.db")
    e = c.cursor()
    e.execute(q, p)
    if f1:
        r = e.fetchone()
    elif f:
        r = e.fetchall()
    else:
        r = e.lastrowid
    c.commit()
    c.close()
    return r


def get_habits(u):
    return db("SELECT id,name FROM habits WHERE user_id=? AND active=1", (u,), f=True)


def get_habits_full(u):
    return db("SELECT id,name,days FROM habits WHERE user_id=? AND active=1", (u,), f=True)


def get_today(u):
    d = datetime.now().strftime("%Y-%m-%d")
    dow = str(datetime.now().weekday())
    return db(
        "SELECT h.id,h.name,CASE WHEN c.id IS NOT NULL THEN 1 ELSE 0 END,COALESCE(c.minutes,0) "
        "FROM habits h LEFT JOIN completions c ON h.id=c.habit_id AND c.date=? "
        "WHERE h.user_id=? AND h.active=1 AND h.days LIKE '%'||?||'%'",
        (d, u, dow), f=True)


def do_toggle(u, h):
    d = datetime.now().strftime("%Y-%m-%d")
    x = db("SELECT id FROM completions WHERE habit_id=? AND date=?", (h, d), f1=True)
    if x:
        db("DELETE FROM completions WHERE id=?", (x[0],))
        return False
    db("INSERT INTO completions(user_id,habit_id,date,minutes)VALUES(?,?,?,0)", (u, h, d))
    return True


def set_time(u, h, m):
    d = datetime.now().strftime("%Y-%m-%d")
    x = db("SELECT id FROM completions WHERE habit_id=? AND date=?", (h, d), f1=True)
    if x:
        db("UPDATE completions SET minutes=? WHERE id=?", (m, x[0]))
    else:
        db("INSERT INTO completions(user_id,habit_id,date,minutes)VALUES(?,?,?,?)", (u, h, d, m))


def get_streak(u, h):
    s = 0
    d = datetime.now()
    days_col = db("SELECT days FROM habits WHERE id=?", (h,), f1=True)
    habit_days = days_col[0] if days_col and days_col[0] else "0123456"
    while True:
        if str(d.weekday()) in habit_days:
            r = db("SELECT id FROM completions WHERE habit_id=? AND date=?", (h, d.strftime("%Y-%m-%d")), f1=True)
            if r:
                s += 1
            else:
                break
        d -= timedelta(days=1)
        if s > 365:
            break
    return s


def get_max_streak(u):
    mx = 0
    for h, n in get_habits(u):
        s = get_streak(u, h)
        if s > mx:
            mx = s
    return mx


def get_total(u):
    r = db("SELECT COUNT(*) FROM completions WHERE user_id=?", (u,), f1=True)
    return r[0] if r else 0


def get_perfect(u):
    rows = db("SELECT date FROM completions WHERE user_id=? GROUP BY date", (u,), f=True)
    perfect = 0
    for (date_str,) in rows:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        dow = str(dt.weekday())
        total = db("SELECT COUNT(*) FROM habits WHERE user_id=? AND active=1 AND days LIKE '%'||?||'%'", (u, dow), f1=True)
        done = db("SELECT COUNT(*) FROM completions WHERE user_id=? AND date=?", (u, date_str), f1=True)
        if total and done and total[0] > 0 and done[0] >= total[0]:
            perfect += 1
    return perfect


def get_monthly_time(u, hid):
    now = datetime.now()
    start = now.replace(day=1).strftime("%Y-%m-%d")
    end = now.strftime("%Y-%m-%d")
    r = db("SELECT SUM(minutes) FROM completions WHERE user_id=? AND habit_id=? AND date BETWEEN ? AND ?",
           (u, hid, start, end), f1=True)
    return r[0] if r and r[0] else 0


def fmt_min(m):
    if m < 60:
        return str(m) + " мин"
    h = m // 60
    mm = m % 60
    if mm == 0:
        return str(h) + " ч"
    return str(h) + " ч " + str(mm) + " мин"


def days_text(days_str):
    if not days_str or days_str == "0123456" or len(days_str) >= 7:
        return "каждый день"
    return ", ".join(DAYS_RU[int(d)] for d in sorted(days_str) if d.isdigit() and int(d) < 7)


def build_pick_kb(u):
    ex = [h[1] for h in get_habits(u)]
    kb = []
    for idx, h in enumerate(DEFAULT_HABITS):
        if h in ex:
            kb.append([InlineKeyboardButton("✅ " + h, callback_data="up_" + str(idx))])
        else:
            kb.append([InlineKeyboardButton("⬜ " + h, callback_data="pk_" + str(idx))])
    kb.append([InlineKeyboardButton("✅ Готово", callback_data="done_pick")])
    return kb


def build_days_kb(hid, current_days="0123456"):
    kb = []
    row = []
    for i, name in enumerate(DAYS_RU):
        if str(i) in current_days:
            label = "✅ " + name
        else:
            label = "⬜ " + name
        row.append(InlineKeyboardButton(label, callback_data="sd_" + str(hid) + "_" + str(i)))
        if len(row) == 4:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    kb.append([InlineKeyboardButton("Каждый день", callback_data="sd_" + str(hid) + "_all")])
    kb.append([InlineKeyboardButton("✅ Готово", callback_data="sd_" + str(hid) + "_done")])
    return kb


def clear_state(context):
    for key in ["ct", "rem_custom", "adding", "manual_time"]:
        context.user_data.pop(key, None)


async def send_reminder(context):
    now = datetime.now()
    users = db("SELECT user_id,reminder_hour,reminder_min FROM users WHERE reminder_hour>=0", (), f=True)
    for uid, rh, rm in users:
        if now.hour == rh and now.minute == rm:
            habits = get_today(uid)
            if not habits:
                continue
            done = sum(1 for _, _, c, _ in habits if c)
            total = len(habits)
            if done >= total:
                continue
            try:
                await context.bot.send_message(chat_id=uid, text="🔔 Напоминание!\nОсталось: " + str(total - done) + "/" + str(total), reply_markup=MENU_KB)
            except:
                pass


async def post_init(app):
    await app.bot.set_my_commands([BotCommand("start", "Начать"), BotCommand("today", "Сегодня"), BotCommand("stats", "Статистика"), BotCommand("calendar", "Календарь"), BotCommand("help", "Помощь")])
    app.job_queue.run_repeating(send_reminder, interval=60, first=10)


async def cmd_start(update, context):
    u = update.effective_user.id
    clear_state(context)
    db("INSERT OR IGNORE INTO users(user_id,username)VALUES(?,?)", (u, update.effective_user.username or ""))
    await update.message.reply_text("👋 Привет! Выбери привычки:", reply_markup=InlineKeyboardMarkup(build_pick_kb(u)))


async def show_today(msg, u, edit=False):
    st = get_today(u)
    if not st:
        txt = "📋 " + DAYS_RU[datetime.now().weekday()] + " — нет привычек на сегодня!\nДобавь через ➕ или настрой расписание в ⚙️"
        if edit:
            try:
                await msg.edit_text(txt)
            except:
                pass
        else:
            await msg.reply_text(txt, reply_markup=MENU_KB)
        return
    t = "📋 Сегодня (" + DAYS_RU[datetime.now().weekday()] + ", " + datetime.now().strftime("%d.%m") + "):\n\n"
    kb = []
    done = 0
    for hid, hn, comp, mins in st:
        timer_key = str(u) + "_" + str(hid)
        timer_running = timer_key in timers
        if comp:
            s = get_streak(u, hid)
            line = "✅ " + hn
            if s > 1:
                line += " 🔥" + str(s)
            if timer_running:
                elapsed = int((ttime.time() - timers[timer_key]) / 60)
                line += " ⏱ " + fmt_min(elapsed) + "..."
            elif mins > 0:
                line += " (" + fmt_min(mins) + ")"
            done += 1
        else:
            line = "⬜ " + hn
        t += line + "\n"
        row = [InlineKeyboardButton("✅" if comp else "⬜", callback_data="t_" + str(hid))]
        if comp:
            if timer_running:
                elapsed = int((ttime.time() - timers[timer_key]) / 60)
                row.append(InlineKeyboardButton("🕐 " + fmt_min(elapsed), callback_data="tcheck_" + str(hid)))
                row.append(InlineKeyboardButton("⏹", callback_data="tstop_" + str(hid)))
            else:
                row.append(InlineKeyboardButton("▶️", callback_data="tstart_" + str(hid)))
                row.append(InlineKeyboardButton("✍️", callback_data="manual_" + str(hid)))
        kb.append(row)
    tot = len(st)
    pct = round((done / tot) * 100) if tot else 0
    bar = "🟩" * (pct // 10) + "⬜" * (10 - pct // 10)
    t += "\n" + bar + " " + str(pct) + "% (" + str(done) + "/" + str(tot) + ")"
    if done == tot and tot > 0:
        t += "\n\n🎉 ИДЕАЛЬНЫЙ ДЕНЬ!"
    if edit:
        try:
            await msg.edit_text(t, reply_markup=InlineKeyboardMarkup(kb))
        except:
            pass
    else:
        await msg.reply_text(t, reply_markup=InlineKeyboardMarkup(kb))


async def cmd_today(update, context):
    clear_state(context)
    await show_today(update.message, update.effective_user.id)


async def show_calendar(msg, u, week_offset=0, edit=False):
    today = datetime.now()
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    habits = get_habits_full(u)
    t = "📆 Неделя " + monday.strftime("%d.%m") + " — " + (monday + timedelta(days=6)).strftime("%d.%m") + ":\n\n"
    for i in range(7):
        day = monday + timedelta(days=i)
        dow = str(day.weekday())
        ds = day.strftime("%Y-%m-%d")
        is_today = " ← СЕГОДНЯ" if ds == today.strftime("%Y-%m-%d") else ""
        day_habits = [h for h in habits if dow in (h[2] or "0123456")]
        done_count = 0
        for hid, hn, days in day_habits:
            r = db("SELECT id FROM completions WHERE habit_id=? AND date=?", (hid, ds), f1=True)
            if r:
                done_count += 1
        total = len(day_habits)
        if total == 0:
            status = "— выходной"
        elif day.date() <= today.date():
            if done_count == total:
                status = "✅ " + str(done_count) + "/" + str(total)
            elif done_count > 0:
                status = "⚠️ " + str(done_count) + "/" + str(total)
            else:
                status = "❌ 0/" + str(total)
        else:
            status = "📌 " + str(total) + " привычек"
        icons = " ".join(hn.split()[0] for _, hn, _ in day_habits[:5]) if day_habits else ""
        t += DAYS_RU[day.weekday()] + " " + day.strftime("%d.%m") + ": " + status + is_today + "\n"
        if icons:
            t += "   " + icons + "\n"
    kb = [[InlineKeyboardButton("⬅️", callback_data="cal_" + str(week_offset - 1)), InlineKeyboardButton("Сегодня", callback_data="cal_0"), InlineKeyboardButton("➡️", callback_data="cal_" + str(week_offset + 1))]]
    if edit:
        try:
            await msg.edit_text(t, reply_markup=InlineKeyboardMarkup(kb))
        except:
            pass
    else:
        await msg.reply_text(t, reply_markup=InlineKeyboardMarkup(kb))


async def cmd_calendar(update, context):
    clear_state(context)
    await show_calendar(update.message, update.effective_user.id)


async def cmd_stats(update, context):
    clear_state(context)
    kb = [[InlineKeyboardButton("📅 7 дн", callback_data="stats_7"), InlineKeyboardButton("📅 30 дн", callback_data="stats_30")], [InlineKeyboardButton("⏱ Время за месяц", callback_data="stats_time")], [InlineKeyboardButton("📊 График", callback_data="chart")]]
    await update.message.reply_text("📊 Статистика:", reply_markup=InlineKeyboardMarkup(kb))


async def cmd_remind(update, context):
    clear_state(context)
    u = update.effective_user.id
    r = db("SELECT reminder_hour,reminder_min FROM users WHERE user_id=?", (u,), f1=True)
    cur_h = r[0] if r and r[0] >= 0 else None
    kb = []
    row = []
    for h in range(6, 24):
        label = ("✅ " + str(h) + ":00") if cur_h == h else str(h) + ":00"
        row.append(InlineKeyboardButton(label, callback_data="rem_" + str(h)))
        if len(row) == 4:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    kb.append([InlineKeyboardButton("✍️ Точное время", callback_data="rem_custom")])
    kb.append([InlineKeyboardButton("🔕 Выключить", callback_data="rem_off")])
    status = "🔔 " + str(cur_h) + ":00" if cur_h is not None else "🔕 Выключено"
    await update.message.reply_text("🔔 Напоминание\n\n" + status, reply_markup=InlineKeyboardMarkup(kb))


async def cmd_settings(update, context):
    clear_state(context)
    kb = [[InlineKeyboardButton("🔄 Выбрать привычки", callback_data="reselect")], [InlineKeyboardButton("📅 Расписание по дням", callback_data="schedule")], [InlineKeyboardButton("💣 Сбросить всё", callback_data="reset_ask")]]
    await update.message.reply_text("⚙️ Настройки:", reply_markup=InlineKeyboardMarkup(kb))


async def cmd_ach(update, context):
    clear_state(context)
    u = update.effective_user.id
    ms = get_max_streak(u)
    tc = get_total(u)
    pf = get_perfect(u)
    t = "🏆 Достижения:\n\n"
    achs = [("🌱", "Росток", "streak", 3), ("⚡", "Разгон", "streak", 7), ("🔥", "В огне", "streak", 14), ("⭐", "Звезда", "streak", 21), ("💎", "Бриллиант", "streak", 30), ("1️⃣", "Первый шаг", "total", 1), ("🔟", "Десятка", "total", 10), ("💯", "Сотня", "total", 100), ("💪", "Идеальный день", "perfect", 1)]
    cnt = 0
    for i, n, tp, v in achs:
        val = ms if tp == "streak" else tc if tp == "total" else pf
        if val >= v:
            t += "✅ " + i + " " + n + "\n"
            cnt += 1
        else:
            t += "🔒 " + i + " " + n + " (ещё " + str(v - val) + ")\n"
    t += "\n" + str(cnt) + "/" + str(len(achs))
    await update.message.reply_text(t, reply_markup=MENU_KB)


async def cmd_help(update, context):
    clear_state(context)
    await update.message.reply_text("📖 Как пользоваться:\n\n📋 Сегодня — привычки на сегодня\n✅ — отметить\n▶️ — таймер\n🕐 — сколько прошло\n⏹ — стоп\n✍️ — записать время вручную\n📆 Календарь — неделя\n📊 Статистика — прогресс\n🏆 Достижения\n🔔 Напоминание\n➕ Добавить\n🗑 Удалить\n⚙️ Расписание по дням", reply_markup=MENU_KB)


async def make_chart(u):
    if not HAS_PLT:
        return None
    h = get_habits(u)
    if not h:
        return None
    end = datetime.now()
    start = end - timedelta(days=29)
    dates = []
    pcts = []
    for i in range(30):
        d = start + timedelta(days=i)
        ds = d.strftime("%Y-%m-%d")
        dow = str(d.weekday())
        total = db("SELECT COUNT(*) FROM habits WHERE user_id=? AND active=1 AND days LIKE '%'||?||'%'", (u, dow), f1=True)
        tot = total[0] if total else 0
        if tot == 0:
            pcts.append(0)
            dates.append(d)
            continue
        r = db("SELECT COUNT(*) FROM completions WHERE user_id=? AND date=?", (u, ds), f1=True)
        done = r[0] if r else 0
        pcts.append(min(round((done / tot) * 100), 100))
        dates.append(d)
    fig, ax = plt.subplots(figsize=(10, 5))
    colors = ["#2ecc71" if p >= 80 else "#f39c12" if p >= 50 else "#e74c3c" if p > 0 else "#bdc3c7" for p in pcts]
    ax.bar(dates, pcts, color=colors, width=0.8)
    ax.set_ylim(0, 110)
    ax.set_title("30 days")
    fig.autofmt_xdate()
    plt.tight_layout()
    p = "/tmp/chart.png"
    plt.savefig(p, dpi=150)
    plt.close()
    return p


async def handle_cb(update, context):
    q = update.callback_query
    await q.answer()
    u = q.from_user.id
    d = q.data

    if d.startswith("pk_"):
        idx = int(d[3:])
        if idx < len(DEFAULT_HABITS):
            db("INSERT INTO habits(user_id,name,days)VALUES(?,?,?)", (u, DEFAULT_HABITS[idx], "0123456"))
        try:
            await q.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(build_pick_kb(u)))
        except:
            pass

    elif d.startswith("up_"):
        idx = int(d[3:])
        if idx < len(DEFAULT_HABITS):
            name = DEFAULT_HABITS[idx]
            for hid, hn in get_habits(u):
                if hn == name:
                    db("UPDATE habits SET active=0 WHERE id=?", (hid,))
                    break
        try:
            await q.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(build_pick_kb(u)))
        except:
            pass

    elif d == "done_pick":
        h = get_habits(u)
        try:
            await q.message.edit_text("✅ Выбрано: " + str(len(h)) + " привычек!")
        except:
            pass
        await q.message.reply_text("🎉 Готово!", reply_markup=MENU_KB)

    elif d.startswith("t_"):
        hid = int(d[2:])
        do_toggle(u, hid)
        await show_today(q.message, u, edit=True)

    elif d.startswith("tstart_"):
        hid = int(d[7:])
        timer_key = str(u) + "_" + str(hid)
        timers[timer_key] = ttime.time()
        hn = db("SELECT name FROM habits WHERE id=?", (hid,), f1=True)
        name = hn[0] if hn else "?"
        start_time = datetime.now().strftime("%H:%M:%S")
        await q.message.reply_text("⏱ ТАЙМЕР ЗАПУЩЕН!\n\n" + name + "\n🕐 Старт: " + start_time + "\n\nНажми 🕐 — проверить время\nНажми ⏹ — остановить", reply_markup=MENU_KB)

    elif d.startswith("tcheck_"):
        hid = int(d[7:])
        timer_key = str(u) + "_" + str(hid)
        if timer_key in timers:
            elapsed = ttime.time() - timers[timer_key]
            mins = int(elapsed / 60)
            secs = int(elapsed % 60)
            hn = db("SELECT name FROM habits WHERE id=?", (hid,), f1=True)
            name = hn[0] if hn else "?"
            await q.answer(text="⏱ " + name + ": " + str(mins) + " мин " + str(secs) + " сек", show_alert=True)
        else:
            await q.answer(text="Таймер не запущен", show_alert=True)

    elif d.startswith("tstop_"):
        hid = int(d[6:])
        timer_key = str(u) + "_" + str(hid)
        if timer_key in timers:
            elapsed = ttime.time() - timers[timer_key]
            mins = max(int(elapsed / 60), 1)
            del timers[timer_key]
            set_time(u, hid, mins)
            hn = db("SELECT name FROM habits WHERE id=?", (hid,), f1=True)
            name = hn[0] if hn else "?"
            monthly = get_monthly_time(u, hid)
            await q.message.reply_text("⏹ ТАЙМЕР ОСТАНОВЛЕН!\n\n" + name + "\n⏱ Записано: " + fmt_min(mins) + "\n📅 За месяц: " + fmt_min(monthly), reply_markup=MENU_KB)
        await show_today(q.message, u, edit=False)

    elif d.startswith("manual_"):
        hid = int(d[7:])
        context.user_data["manual_time"] = hid
        hn = db("SELECT name FROM habits WHERE id=?", (hid,), f1=True)
        name = hn[0] if hn else "?"
        monthly = get_monthly_time(u, hid)
        kb = [
            [InlineKeyboardButton("15м", callback_data="setm_" + str(hid) + "_15"), InlineKeyboardButton("30м", callback_data="setm_" + str(hid) + "_30"), InlineKeyboardButton("45м", callback_data="setm_" + str(hid) + "_45")],
            [InlineKeyboardButton("1ч", callback_data="setm_" + str(hid) + "_60"), InlineKeyboardButton("1ч 20м", callback_data="setm_" + str(hid) + "_80"), InlineKeyboardButton("1ч 30м", callback_data="setm_" + str(hid) + "_90")],
            [InlineKeyboardButton("2ч", callback_data="setm_" + str(hid) + "_120"), InlineKeyboardButton("2ч 30м", callback_data="setm_" + str(hid) + "_150"), InlineKeyboardButton("3ч", callback_data="setm_" + str(hid) + "_180")],
            [InlineKeyboardButton("✍️ Ввести своё", callback_data="ct_" + str(hid))],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
        ]
        try:
            await q.message.edit_text("✍️ " + name + "\n📅 За месяц: " + fmt_min(monthly) + "\n\nВыбери или напиши время:", reply_markup=InlineKeyboardMarkup(kb))
        except:
            pass

    elif d.startswith("setm_"):
        parts = d[5:].split("_")
        hid = int(parts[0])
        mins = int(parts[1])
        set_time(u, hid, mins)
        hn = db("SELECT name FROM habits WHERE id=?", (hid,), f1=True)
        name = hn[0] if hn else "?"
        monthly = get_monthly_time(u, hid)
        try:
            await q.message.edit_text("✅ " + name + "\nЗаписано: " + fmt_min(mins) + "\n📅 За месяц: " + fmt_min(monthly))
        
