import logging
import sqlite3
import os
import random
import csv
import io
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo
import matplotlib.pyplot as plt
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# ========== НАСТРОЙКИ ==========
TOKEN = os.environ.get("BOT_TOKEN", "")
if not TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set")
DB_NAME = "habits.db"
TIMEZONE = ZoneInfo("Europe/Moscow")

# ========== ЯЗЫКИ ==========
TEXTS = {
    'ru': {
        'welcome': "👋 Привет! Я трекер привычек.",
        'today': "📋 Сегодня",
        'stats': "📊 Статистика",
        'add': "➕ Добавить привычку",
        'delete': "🗑 Удалить привычку",
        'leaderboard': "🏆 Лидеры",
        'help': "❓ Помощь",
        'calendar': "📆 Календарь",
        'export': "📁 Экспорт CSV",
        'edit': "✏️ Редактировать",
        'profile': "👤 Профиль",
        'reminder': "⏰ Напоминание",
        'add_name': "✏️ Введите название привычки:",
        'choose_days': "📅 Выберите дни выполнения (можно несколько):",
        'habit_added': "✅ Привычка '{}' добавлена!",
        'no_habits_today': "На сегодня нет запланированных привычек.",
        'today_header': "📋 Привычки на {}:",
        'already_done': "Уже отмечено!",
        'no_habits': "У вас пока нет привычек. Добавьте через меню.",
        'choose_to_delete': "🗑 Выберите привычку для удаления:",
        'deleted': "✅ Привычка удалена.",
        'cancel': "Отменено.",
        'help_text': "🤖 Помощь\n\n📋 Сегодня – отметить привычки\n📊 Статистика – графики и время\n➕ Добавить – новая привычка\n🗑 Удалить – убрать привычку\n🏆 Лидеры – таблица рейтинга\n📆 Календарь – посмотреть отметки по дням\n📁 Экспорт CSV – выгрузить данные\n✏️ Редактировать – изменить привычку\n👤 Профиль – уровень и достижения\n⏰ Напоминание – установить/изменить напоминание",
        'use_buttons': "Используйте кнопки меню.",
        'select_habit': "Выберите привычку:",
        'edit_name': "✏️ Название",
        'edit_days': "📅 Дни выполнения",
        'edit_name_prompt': "Введите новое название:",
        'edit_name_saved': "Название изменено!",
        'edit_days_prompt': "Выберите новые дни:",
        'edit_days_saved': "Дни изменены!",
        'skip_ok': "✅ Пропуск засчитан.",
        'level_up': "🎉 Поздравляем! Вы достигли уровня {}!",
        'achievement_unlock': "🏆 Новое достижение: {}",
        'streak7_achievement': "7 дней подряд! 🔥",
        'streak30_achievement': "30 дней подряд! ⭐",
        'perfect_month_achievement': "Идеальный месяц! 🌟",
        'ask_time': "⏱ Сколько минут потратили?",
        'add_time_btn': "⏱ Добавить время",
        'skip_time_btn': "✅ Пропустить",
        'enter_time': "Введите число (минуты):",
        'time_saved': "✅ {} минут добавлено!",
        'stats_time_today': "⏱ Сегодня: {} мин",
        'stats_time_week': "⏱ За неделю: {} мин",
        'stats_time_month': "⏱ За месяц: {} мин",
        'no_reminder': "⏰ Нет напоминания",
        'reminder_set': "✅ Напоминание установлено на {}",
        'reminder_deleted': "✅ Напоминание удалено",
        'reminder_prompt': "Введите время (ЧЧ:ММ) или 'нет' чтобы удалить:",
        'select_habit_for_reminder': "Выберите привычку для настройки напоминания:",
    },
    'en': {
        'welcome': "👋 Hi! I'm a habit tracker.",
        'today': "📋 Today",
        'stats': "📊 Stats",
        'add': "➕ Add habit",
        'delete': "🗑 Delete habit",
        'leaderboard': "🏆 Leaderboard",
        'help': "❓ Help",
        'calendar': "📆 Calendar",
        'export': "📁 Export CSV",
        'edit': "✏️ Edit",
        'profile': "👤 Profile",
        'reminder': "⏰ Reminder",
        'add_name': "✏️ Enter habit name:",
        'choose_days': "📅 Select days (multiple allowed):",
        'habit_added': "✅ Habit '{}' added!",
        'no_habits_today': "No habits scheduled for today.",
        'today_header': "📋 Habits for {}:",
        'already_done': "Already marked!",
        'no_habits': "You have no habits yet. Add via menu.",
        'choose_to_delete': "🗑 Choose habit to delete:",
        'deleted': "✅ Habit deleted.",
        'cancel': "Canceled.",
        'help_text': "🤖 Help\n\n📋 Today – mark habits\n📊 Stats – graphs and time\n➕ Add – new habit\n🗑 Delete – remove habit\n🏆 Leaderboard – ranking\n📆 Calendar – view marks by day\n📁 Export CSV – download data\n✏️ Edit – modify habit\n👤 Profile – level and achievements\n⏰ Reminder – set/change reminder",
        'use_buttons': "Use menu buttons.",
        'select_habit': "Select habit:",
        'edit_name': "✏️ Name",
        'edit_days': "📅 Days",
        'edit_name_prompt': "Enter new name:",
        'edit_name_saved': "Name changed!",
        'edit_days_prompt': "Select new days:",
        'edit_days_saved': "Days changed!",
        'skip_ok': "✅ Skip counted.",
        'level_up': "🎉 Congratulations! You reached level {}!",
        'achievement_unlock': "🏆 New achievement: {}",
        'streak7_achievement': "7 days in a row! 🔥",
        'streak30_achievement': "30 days in a row! ⭐",
        'perfect_month_achievement': "Perfect month! 🌟",
        'ask_time': "⏱ How many minutes did you spend?",
        'add_time_btn': "⏱ Add time",
        'skip_time_btn': "✅ Skip",
        'enter_time': "Enter number (minutes):",
        'time_saved': "✅ {} minutes added!",
        'stats_time_today': "⏱ Today: {} min",
        'stats_time_week': "⏱ This week: {} min",
        'stats_time_month': "⏱ This month: {} min",
        'no_reminder': "⏰ No reminder",
        'reminder_set': "✅ Reminder set for {}",
        'reminder_deleted': "✅ Reminder deleted",
        'reminder_prompt': "Enter time (HH:MM) or 'no' to remove:",
        'select_habit_for_reminder': "Select habit to set reminder:",
    }
}

MOTIVATION_RU = ["🔥 Отлично! +10 XP", "💪 Ты крут!", "🌟 Ещё одна победа!", "🎉 Маленькие шаги = большие цели!"]
MOTIVATION_EN = ["🔥 Great! +10 XP", "💪 You're awesome!", "🌟 Another victory!", "🎉 Small steps = big goals!"]

# Состояния
(TYPING_HABIT_NAME, CHOOSING_HABIT_DAYS, CONFIRM_DELETE,
 EDIT_SELECT, EDIT_NAME, EDIT_DAYS, REMINDER_SELECT, REMINDER_TIME) = range(8)

# ========== БАЗА ДАННЫХ ==========
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        lang TEXT DEFAULT 'ru',
        xp INTEGER DEFAULT 0,
        level INTEGER DEFAULT 1
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS habits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT,
        days TEXT DEFAULT '0123456',
        reminder_time TEXT,
        is_active INTEGER DEFAULT 1,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS habit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        habit_id INTEGER,
        completed_date TEXT,
        minutes INTEGER DEFAULT 0,
        UNIQUE(habit_id, completed_date)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS achievements (
        user_id INTEGER,
        type TEXT,
        achieved_at TIMESTAMP,
        PRIMARY KEY (user_id, type)
    )''')
    conn.commit()
    conn.close()

def db_query(query, params=(), fetch_one=False, fetch_all=False):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(query, params)
    result = None
    if fetch_one:
        result = c.fetchone()
    elif fetch_all:
        result = c.fetchall()
    else:
        result = c.lastrowid
    conn.commit()
    conn.close()
    return result

def get_user_lang(user_id):
    row = db_query("SELECT lang FROM users WHERE id = ?", (user_id,), fetch_one=True)
    return row[0] if row and row[0] in ('ru','en') else 'ru'

def get_text(user_id, key):
    lang = get_user_lang(user_id)
    return TEXTS[lang].get(key, TEXTS['ru'][key])

def add_xp(user_id, amount):
    row = db_query("SELECT xp, level FROM users WHERE id = ?", (user_id,), fetch_one=True)
    if not row:
        return None, None, False
    xp, level = row
    xp += amount
    new_level = level
    level_up = False
    while xp >= new_level * 100:
        xp -= new_level * 100
        new_level += 1
        level_up = True
    db_query("UPDATE users SET xp = ?, level = ? WHERE id = ?", (xp, new_level, user_id))
    return xp, new_level, level_up

def get_streak(user_id, habit_id):
    logs = db_query("SELECT completed_date FROM habit_logs WHERE habit_id = ? AND minutes >= 0 ORDER BY completed_date DESC", (habit_id,), fetch_all=True)
    if not logs:
        return 0
    habit_days = db_query("SELECT days FROM habits WHERE id = ? AND user_id = ?", (habit_id, user_id), fetch_one=True)
    if not habit_days:
        return 0
    allowed_days = set(map(int, habit_days[0]))
    today = datetime.now(TIMEZONE).date()
    streak = 0
    current_date = today
    log_dates = {log[0] for log in logs}
    while True:
        if current_date.weekday() in allowed_days:
            if current_date.strftime("%Y-%m-%d") in log_dates:
                streak += 1
            else:
                break
        current_date -= timedelta(days=1)
    return streak

def get_percentage(user_id, habit_id, days=30):
    habit_days = db_query("SELECT days FROM habits WHERE id = ? AND user_id = ?", (habit_id, user_id), fetch_one=True)
    if not habit_days:
        return 0
    allowed_days = set(map(int, habit_days[0]))
    today = datetime.now(TIMEZONE).date()
    required = []
    for i in range(days):
        d = today - timedelta(days=i)
        if d.weekday() in allowed_days:
            required.append(d.strftime("%Y-%m-%d"))
    if not required:
        return 100
    placeholders = ','.join(['?']*len(required))
    completed = db_query(f"SELECT COUNT(DISTINCT completed_date) FROM habit_logs WHERE habit_id = ? AND completed_date IN ({placeholders}) AND minutes >= 0", (habit_id, *required), fetch_one=True)
    return (completed[0] / len(required)) * 100

def get_total_minutes(user_id, habit_id, period='today'):
    today = datetime.now(TIMEZONE).date()
    if period == 'today':
        start = today.strftime("%Y-%m-%d")
        end = today.strftime("%Y-%m-%d")
    elif period == 'week':
        start = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
        end = today.strftime("%Y-%m-%d")
    elif period == 'month':
        start = today.replace(day=1).strftime("%Y-%m-%d")
        end = today.strftime("%Y-%m-%d")
    else:
        return 0
    res = db_query("SELECT SUM(minutes) FROM habit_logs WHERE habit_id = ? AND completed_date >= ? AND completed_date <= ? AND minutes >= 0", (habit_id, start, end), fetch_one=True)
    return res[0] if res[0] else 0

def check_achievements(user_id, habit_id):
    streak = get_streak(user_id, habit_id)
    percent = get_percentage(user_id, habit_id, 30)
    lang = get_user_lang(user_id)
    earned = []
    if streak >= 7 and not db_query("SELECT 1 FROM achievements WHERE user_id=? AND type='streak7'", (user_id,), fetch_one=True):
        db_query("INSERT INTO achievements(user_id, type, achieved_at) VALUES(?,?,?)", (user_id, 'streak7', datetime.now(TIMEZONE).isoformat()))
        earned.append(TEXTS[lang].get('streak7_achievement', "7 days streak! 🔥"))
    if streak >= 30 and not db_query("SELECT 1 FROM achievements WHERE user_id=? AND type='streak30'", (user_id,), fetch_one=True):
        db_query("INSERT INTO achievements(user_id, type, achieved_at) VALUES(?,?,?)", (user_id, 'streak30', datetime.now(TIMEZONE).isoformat()))
        earned.append(TEXTS[lang].get('streak30_achievement', "30 days streak! ⭐"))
    if percent >= 99.9 and not db_query("SELECT 1 FROM achievements WHERE user_id=? AND type='perfect_month'", (user_id,), fetch_one=True):
        db_query("INSERT INTO achievements(user_id, type, achieved_at) VALUES(?,?,?)", (user_id, 'perfect_month', datetime.now(TIMEZONE).isoformat()))
        earned.append(TEXTS[lang].get('perfect_month_achievement', "Perfect month! 🌟"))
    return earned

def get_month_calendar(user_id, year, month):
    first_day = datetime(year, month, 1, tzinfo=TIMEZONE)
    last_day = (first_day.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    start_weekday = first_day.weekday()
    weeks = []
    week = ['   '] * start_weekday
    for day in range(1, last_day.day + 1):
        date_str = datetime(year, month, day, tzinfo=TIMEZONE).strftime("%Y-%m-%d")
        habits = db_query("SELECT id FROM habits WHERE user_id=? AND is_active=1", (user_id,), fetch_all=True)
        if not habits:
            mark = '⬜'
        else:
            total = len(habits)
            done = db_query("SELECT COUNT(DISTINCT habit_id) FROM habit_logs WHERE habit_id IN ({}) AND completed_date=? AND minutes>=0".format(','.join(['?']*total)), [h[0] for h in habits] + [date_str], fetch_one=True)[0]
            mark = '✅' if done == total else '⚠️' if done > 0 else '❌'
        week.append(f"{mark}{day:2d}")
        if len(week) == 7:
            weeks.append(' '.join(week))
            week = []
    if week:
        weeks.append(' '.join(week))
    return '\n'.join(weeks)

# ========== ОСНОВНЫЕ ОБРАБОТЧИКИ ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = user.language_code if user.language_code in ('ru','en') else 'ru'
    # Регистрация пользователя
    db_query("INSERT OR IGNORE INTO users (id, username, first_name, last_name, lang) VALUES (?,?,?,?,?)",
             (user.id, user.username, user.first_name, user.last_name, lang))
    keyboard = ReplyKeyboardMarkup([
        [get_text(user.id, 'today'), get_text(user.id, 'stats')],
        [get_text(user.id, 'add'), get_text(user.id, 'delete')],
        [get_text(user.id, 'leaderboard'), get_text(user.id, 'calendar'), get_text(user.id, 'export')],
        [get_text(user.id, 'edit'), get_text(user.id, 'profile'), get_text(user.id, 'reminder'), get_text(user.id, 'help')]
    ], resize_keyboard=True)
    await update.message.reply_text(get_text(user.id, 'welcome'), reply_markup=keyboard)

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    row = db_query("SELECT xp, level FROM users WHERE id=?", (user_id,), fetch_one=True)
    if not row:
        await update.message.reply_text("Ошибка: пользователь не найден. Используйте /start")
        return
    xp, level = row
    next_xp = level * 100 - xp
    text = f"👤 *Профиль*\nУровень: {level}\nОпыт: {xp} / {level*100}\nДо следующего уровня: {next_xp} XP\n"
    ach = db_query("SELECT type FROM achievements WHERE user_id=?", (user_id,), fetch_all=True)
    if ach:
        text += "\n🏆 *Достижения:*\n"
        for (t,) in ach:
            text += "🔥 7 дней\n" if t == 'streak7' else "⭐ 30 дней\n" if t == 'streak30' else "🌟 Идеальный месяц\n"
    await update.message.reply_text(text, parse_mode="Markdown")

# ---------- ДОБАВЛЕНИЕ ПРИВЫЧКИ ----------
async def add_habit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(get_text(update.effective_user.id, 'add_name'))
    return TYPING_HABIT_NAME

async def add_habit_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['habit_name'] = update.message.text
    user_id = update.effective_user.id
    keyboard = [[InlineKeyboardButton(day, callback_data=f"day_{i}") for i, day in enumerate(["Пн","Вт","Ср","Чт","Пт","Сб","Вс"])],
                [InlineKeyboardButton("✅ Готово", callback_data="days_done")]]
    await update.message.reply_text(get_text(user_id, 'choose_days'), reply_markup=InlineKeyboardMarkup(keyboard))
    return CHOOSING_HABIT_DAYS

async def days_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if 'habit_days' not in context.user_data:
        context.user_data['habit_days'] = set()
    if query.data == "days_done":
        if not context.user_data['habit_days']:
            await query.edit_message_text("Выберите хотя бы один день!")
            return
        days_str = ''.join(map(str, sorted(context.user_data['habit_days'])))
        user_id = query.from_user.id
        name = context.user_data['habit_name']
        db_query("INSERT INTO habits (user_id, name, days, reminder_time) VALUES (?,?,?,?)", (user_id, name, days_str, None))
        await query.edit_message_text(get_text(user_id, 'habit_added').format(name))
        return ConversationHandler.END
    day = int(query.data.split('_')[1])
    if day in context.user_data['habit_days']:
        context.user_data['habit_days'].remove(day)
    else:
        context.user_data['habit_days'].add(day)
    days_names = ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]
    row = [InlineKeyboardButton(f"{'✅ ' if i in context.user_data['habit_days'] else '⬜ '}{days_names[i]}", callback_data=f"day_{i}") for i in range(7)]
    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([row, [InlineKeyboardButton("✅ Готово", callback_data="days_done")]]))

# ---------- СЕГОДНЯ И ВРЕМЯ ----------
async def show_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    today = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    weekday = datetime.now(TIMEZONE).weekday()
    habits = db_query("SELECT id, name FROM habits WHERE user_id=? AND is_active=1 AND days LIKE ?", (user_id, f'%{weekday}%'), fetch_all=True)
    if not habits:
        await update.message.reply_text(get_text(user_id, 'no_habits_today'))
        return
    keyboard = []
    for hid, name in habits:
        done = db_query("SELECT minutes FROM habit_logs WHERE habit_id=? AND completed_date=?", (hid, today), fetch_one=True)
        if done and done[0] >= 0:
            text = f"✅ {name}" + (f" ({done[0]} мин)" if done[0] > 0 else "")
        else:
            text = f"⬜ {name}"
        keyboard.append([InlineKeyboardButton(text, callback_data=f"complete_{hid}_{today}")])
    await update.message.reply_text(get_text(user_id, 'today_header').format(datetime.now(TIMEZONE).strftime("%d.%m.%Y")), reply_markup=InlineKeyboardMarkup(keyboard))

async def complete_habit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, hid, date_str = query.data.split('_')
    habit_id = int(hid)
    user_id = query.from_user.id
    existing = db_query("SELECT id, minutes FROM habit_logs WHERE habit_id=? AND completed_date=?", (habit_id, date_str), fetch_one=True)
    if existing and existing[1] >= 0:
        await query.edit_message_text(get_text(user_id, 'already_done'))
        return
    if existing:
        db_query("DELETE FROM habit_logs WHERE id=?", (existing[0],))
    db_query("INSERT INTO habit_logs (habit_id, completed_date, minutes) VALUES (?,?,0)", (habit_id, date_str))
    xp, new_level, level_up = add_xp(user_id, 10)
    reply = f"{random.choice(MOTIVATION_RU if get_user_lang(user_id)=='ru' else MOTIVATION_EN)}\n+10 XP"
    if level_up:
        reply += "\n" + get_text(user_id, 'level_up').format(new_level)
    for ach in check_achievements(user_id, habit_id):
        reply += f"\n{get_text(user_id, 'achievement_unlock').format(ach)}"
    context.user_data['pending_habit'] = (habit_id, date_str)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(get_text(user_id, 'add_time_btn'), callback_data="add_time")],
        [InlineKeyboardButton(get_text(user_id, 'skip_time_btn'), callback_data="skip_time")]
    ])
    await query.edit_message_text(reply + "\n\n" + get_text(user_id, 'ask_time'), reply_markup=keyboard)

async def add_time_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(get_text(query.from_user.id, 'enter_time'))
    context.user_data['awaiting_time'] = True

async def skip_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.pop('pending_habit', None)
    await query.edit_message_text("✅ Время не добавлено")
    await show_today(update, context)

async def save_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_time'):
        return
    try:
        minutes = int(update.message.text)
        habit_id, date_str = context.user_data.get('pending_habit', (None, None))
        if habit_id is None:
            await update.message.reply_text("Ошибка, попробуйте ещё раз")
            context.user_data.pop('awaiting_time', None)
            return
        db_query("UPDATE habit_logs SET minutes = ? WHERE habit_id = ? AND completed_date = ?", (minutes, habit_id, date_str))
        await update.message.reply_text(get_text(update.effective_user.id, 'time_saved').format(minutes))
        context.user_data.pop('awaiting_time', None)
        context.user_data.pop('pending_habit', None)
        await show_today(update, context)
    except ValueError:
        await update.message.reply_text("Введите число (минуты)")

# ---------- СТАТИСТИКА ----------
async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    habits = db_query("SELECT id, name FROM habits WHERE user_id=? AND is_active=1", (user_id,), fetch_all=True)
    if not habits:
        await update.message.reply_text(get_text(user_id, 'no_habits'))
        return
    text = "📊 *Статистика*\n\n"
    for hid, name in habits:
        streak = get_streak(user_id, hid)
        percent = get_percentage(user_id, hid, 30)
        bar = "█" * int(percent//10) + "░" * (10 - int(percent//10))
        mins_today = get_total_minutes(user_id, hid, 'today')
        mins_week = get_total_minutes(user_id, hid, 'week')
        mins_month = get_total_minutes(user_id, hid, 'month')
        text += f"*{name}*\n🔥 {streak} дн. | 📈 {percent:.0f}%\n{bar}\n"
        text += f"⏱ Сегодня: {mins_today} мин | Неделя: {mins_week} мин | Месяц: {mins_month} мин\n\n"
    await update.message.reply_text(text, parse_mode="Markdown")
    keyboard = [[InlineKeyboardButton("📈 График", callback_data="plot_stats")]]
    await update.message.reply_text("Построить график?", reply_markup=InlineKeyboardMarkup(keyboard))

async def plot_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    habits = db_query("SELECT id, name FROM habits WHERE user_id=? AND is_active=1", (user_id,), fetch_all=True)
    if not habits:
        await query.edit_message_text("Нет привычек")
        return
    plt.figure(figsize=(10,6))
    today = datetime.now(TIMEZONE).date()
    for hid, name in habits:
        dates, completions = [], []
        for i in range(30, -1, -1):
            d = today - timedelta(days=i)
            dates.append(d.strftime("%d.%m"))
            done = db_query("SELECT id FROM habit_logs WHERE habit_id=? AND completed_date=? AND minutes>=0", (hid, d.strftime("%Y-%m-%d")), fetch_one=True)
            completions.append(1 if done else 0)
        plt.plot(dates, completions, marker='o', label=name, linewidth=2)
    plt.title("Прогресс за 30 дней")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    await query.edit_message_text("Вот ваш график:")
    await query.message.reply_photo(photo=buf)

# ---------- УДАЛЕНИЕ ----------
async def delete_habit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    habits = db_query("SELECT id, name FROM habits WHERE user_id=? AND is_active=1", (user_id,), fetch_all=True)
    if not habits:
        await update.message.reply_text(get_text(user_id, 'no_habits'))
        return ConversationHandler.END
    keyboard = [[InlineKeyboardButton(f"❌ {name}", callback_data=f"del_{hid}")] for hid, name in habits]
    keyboard.append([InlineKeyboardButton("🚫 Отмена", callback_data="cancel_del")])
    await update.message.reply_text(get_text(user_id, 'choose_to_delete'), reply_markup=InlineKeyboardMarkup(keyboard))
    return CONFIRM_DELETE

async def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "cancel_del":
        await query.edit_message_text(get_text(query.from_user.id, 'cancel'))
        return ConversationHandler.END
    hid = int(query.data.split('_')[1])
    db_query("UPDATE habits SET is_active=0 WHERE id=?", (hid,))
    await query.edit_message_text(get_text(query.from_user.id, 'deleted'))
    return ConversationHandler.END

# ---------- РЕДАКТИРОВАНИЕ ----------
async def edit_habit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    habits = db_query("SELECT id, name FROM habits WHERE user_id=? AND is_active=1", (user_id,), fetch_all=True)
    if not habits:
        await update.message.reply_text(get_text(user_id, 'no_habits'))
        return ConversationHandler.END
    keyboard = [[InlineKeyboardButton(name, callback_data=f"edith_{hid}")] for hid, name in habits]
    await update.message.reply_text(get_text(user_id, 'select_habit'), reply_markup=InlineKeyboardMarkup(keyboard))
    return EDIT_SELECT

async def edit_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['edit_id'] = int(query.data.split('_')[1])
    user_id = query.from_user.id
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(get_text(user_id, 'edit_name'), callback_data="edit_name")],
        [InlineKeyboardButton(get_text(user_id, 'edit_days'), callback_data="edit_days")],
        [InlineKeyboardButton("🔙 Назад", callback_data="edit_cancel")]
    ])
    await query.edit_message_text("Что меняем?", reply_markup=keyboard)

async def edit_name_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(get_text(query.from_user.id, 'edit_name_prompt'))
    return EDIT_NAME

async def edit_name_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_name = update.message.text
    db_query("UPDATE habits SET name=? WHERE id=?", (new_name, context.user_data['edit_id']))
    await update.message.reply_text(get_text(update.effective_user.id, 'edit_name_saved'))
    return ConversationHandler.END

async def edit_days_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    habit_id = context.user_data['edit_id']
    row = db_query("SELECT days FROM habits WHERE id=?", (habit_id,), fetch_one=True)
    current = set(map(int, row[0])) if row else set()
    context.user_data['edit_days_temp'] = current
    days_names = ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]
    row_btns = [InlineKeyboardButton(f"{'✅ ' if i in current else '⬜ '}{days_names[i]}", callback_data=f"editday_{i}") for i in range(7)]
    keyboard = [row_btns, [InlineKeyboardButton("✅ Сохранить", callback_data="editdays_save")]]
    await query.edit_message_text(get_text(query.from_user.id, 'edit_days_prompt'), reply_markup=InlineKeyboardMarkup(keyboard))
    return EDIT_DAYS

async def edit_days_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    day = int(query.data.split('_')[1])
    if 'edit_days_temp' not in context.user_data:
        context.user_data['edit_days_temp'] = set()
    if day in context.user_data['edit_days_temp']:
        context.user_data['edit_days_temp'].remove(day)
    else:
        context.user_data['edit_days_temp'].add(day)
    days_names = ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]
    row = [InlineKeyboardButton(f"{'✅ ' if i in context.user_data['edit_days_temp'] else '⬜ '}{days_names[i]}", callback_data=f"editday_{i}") for i in range(7)]
    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([row, [InlineKeyboardButton("✅ Сохранить", callback_data="editdays_save")]]))

async def edit_days_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    days_set = context.user_data.get('edit_days_temp', set())
    if not days_set:
        await query.edit_message_text("Выберите хотя бы один день!")
        return
    days_str = ''.join(map(str, sorted(days_set)))
    db_query("UPDATE habits SET days=? WHERE id=?", (days_str, context.user_data['edit_id']))
    await query.edit_message_text(get_text(query.from_user.id, 'edit_days_saved'))
    return ConversationHandler.END

async def edit_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Отменено")
    return ConversationHandler.END

# ---------- НАПОМИНАНИЕ (ОТДЕЛЬНАЯ КНОПКА) ----------
async def reminder_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    habits = db_query("SELECT id, name FROM habits WHERE user_id=? AND is_active=1", (user_id,), fetch_all=True)
    if not habits:
        await update.message.reply_text(get_text(user_id, 'no_habits'))
        return
    keyboard = [[InlineKeyboardButton(name, callback_data=f"rem_{hid}")] for hid, name in habits]
    await update.message.reply_text(get_text(user_id, 'select_habit_for_reminder'), reply_markup=InlineKeyboardMarkup(keyboard))

async def reminder_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    habit_id = int(query.data.split('_')[1])
    context.user_data['reminder_habit_id'] = habit_id
    row = db_query("SELECT reminder_time FROM habits WHERE id=?", (habit_id,), fetch_one=True)
    current = row[0] if row else None
    user_id = query.from_user.id
    text = get_text(user_id, 'reminder_prompt')
    if current:
        text += f"\nТекущее: {current}"
    await query.edit_message_text(text)
    return REMINDER_TIME

async def reminder_time_set(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reminder = update.message.text.strip()
    user_id = update.effective_user.id
    habit_id = context.user_data.get('reminder_habit_id')
    if reminder.lower() == 'нет':
        db_query("UPDATE habits SET reminder_time=? WHERE id=?", (None, habit_id))
        await update.message.reply_text(get_text(user_id, 'reminder_deleted'))
    else:
        try:
            datetime.strptime(reminder, "%H:%M")
            db_query("UPDATE habits SET reminder_time=? WHERE id=?", (reminder, habit_id))
            await update.message.reply_text(get_text(user_id, 'reminder_set').format(reminder))
        except:
            await update.message.reply_text("Неверный формат. Введите ЧЧ:ММ или 'нет'")
            return REMINDER_TIME
    context.user_data.pop('reminder_habit_id', None)
    return ConversationHandler.END

# ---------- КАЛЕНДАРЬ ДЛЯ ПРОСМОТРА ОТМЕТОК ----------
async def calendar_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    now = datetime.now(TIMEZONE)
    cal = get_month_calendar(user_id, now.year, now.month)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️", callback_data=f"cal_{now.year}_{now.month-1 if now.month>1 else 12}_{now.year if now.month>1 else now.year-1}"),
         InlineKeyboardButton(f"{now.month:02d}.{now.year}", callback_data="ignore"),
         InlineKeyboardButton("▶️", callback_data=f"cal_{now.year}_{now.month+1 if now.month<12 else 1}_{now.year if now.month<12 else now.year+1}")],
        [InlineKeyboardButton(get_text(user_id, 'today'), callback_data="cal_today")]
    ])
    await update.message.reply_text(f"📅 *{now.year}-{now.month:02d}*\n{cal}", parse_mode="Markdown", reply_markup=keyboard)

async def calendar_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "cal_today":
        await calendar_menu(update, context)
        return
    if data.startswith("cal_"):
        _, y, m, _ = data.split('_')
        year, month = int(y), int(m)
        user_id = query.from_user.id
        cal = get_month_calendar(user_id, year, month)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️", callback_data=f"cal_{year}_{month-1 if month>1 else 12}_{year if month>1 else year-1}"),
             InlineKeyboardButton(f"{month:02d}.{year}", callback_data="ignore"),
             InlineKeyboardButton("▶️", callback_data=f"cal_{year}_{month+1 if month<12 else 1}_{year if month<12 else year+1}")],
            [InlineKeyboardButton(get_text(user_id, 'today'), callback_data="cal_today")]
        ])
        await query.edit_message_text(f"📅 *{year}-{month:02d}*\n{cal}", parse_mode="Markdown", reply_markup=keyboard)

# ---------- ЛИДЕРЫ, ЭКСПОРТ, ПОМОЩЬ ----------
async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = db_query("SELECT id, first_name, username, level, xp FROM users", fetch_all=True)
    data = [(fname or uname or f"User_{uid}", level, xp) for uid, fname, uname, level, xp in users]
    data.sort(key=lambda x: (-x[1], -x[2]))
    text = "🏆 *Лидеры*\n\n"
    for i, (name, level, xp) in enumerate(data[:10], 1):
        medal = "🥇 " if i==1 else "🥈 " if i==2 else "🥉 " if i==3 else ""
        text += f"{medal}{i}. {name} — уровень {level} ({xp} XP)\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def export_csv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = db_query("""
        SELECT h.name, hl.completed_date, hl.minutes
        FROM habit_logs hl JOIN habits h ON hl.habit_id = h.id
        WHERE h.user_id=? AND hl.minutes >= 0
        ORDER BY hl.completed_date DESC
    """, (user_id,), fetch_all=True)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Habit", "Date", "Minutes"])
    writer.writerows(data)
    output.seek(0)
    await update.message.reply_document(document=output.getvalue().encode(), filename="habits.csv")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(get_text(update.effective_user.id, 'help_text'))

# ---------- ОБЩИЙ ОБРАБОТЧИК ----------
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if context.user_data.get('awaiting_time'):
        await save_time(update, context)
        return
    text = update.message.text
    t = get_text(user_id, 'today')
    s = get_text(user_id, 'stats')
    a = get_text(user_id, 'add')
    d = get_text(user_id, 'delete')
    l = get_text(user_id, 'leaderboard')
    c = get_text(user_id, 'calendar')
    e = get_text(user_id, 'export')
    ed = get_text(user_id, 'edit')
    p = get_text(user_id, 'profile')
    r = get_text(user_id, 'reminder')
    h = get_text(user_id, 'help')
    if text == t:
        await show_today(update, context)
    elif text == s:
        await show_stats(update, context)
    elif text == a:
        await add_habit_start(update, context)
    elif text == d:
        await delete_habit_start(update, context)
    elif text == l:
        await leaderboard(update, context)
    elif text == c:
        await calendar_menu(update, context)
    elif text == e:
        await export_csv(update, context)
    elif text == ed:
        await edit_habit_start(update, context)
    elif text == p:
        await profile(update, context)
    elif text == r:
        await reminder_menu(update, context)
    elif text == h:
        await help_command(update, context)
    else:
        await update.message.reply_text(get_text(user_id, 'use_buttons'))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    if data.startswith("complete_"):
        await complete_habit(update, context)
    elif data == "plot_stats":
        await plot_stats(update, context)
    elif data.startswith("cal_"):
        await calendar_callback(update, context)
    elif data.startswith("edith_"):
        await edit_select(update, context)
    elif data == "edit_name":
        await edit_name_prompt(update, context)
    elif data == "edit_days":
        await edit_days_prompt(update, context)
    elif data == "edit_cancel":
        await edit_cancel(update, context)
    elif data.startswith("editday_"):
        await edit_days_callback(update, context)
    elif data == "editdays_save":
        await edit_days_save(update, context)
    elif data == "add_time":
        await add_time_prompt(update, context)
    elif data == "skip_time":
        await skip_time(update, context)
    elif data.startswith("rem_"):
        await reminder_select(update, context)
    else:
        await query.answer()

# ========== ЗАПУСК ==========
def main():
    init_db()
    app = Application.builder().token(TOKEN).build()

    add_conv = ConversationHandler(
        entry_points=[CommandHandler("add", add_habit_start), MessageHandler(filters.Regex("➕ Добавить привычку"), add_habit_start)],
        states={TYPING_HABIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_habit_name)], CHOOSING_HABIT_DAYS: [CallbackQueryHandler(days_callback, pattern="^day_|days_done$")]},
        fallbacks=[CommandHandler("cancel", lambda u,c: ConversationHandler.END)], allow_reentry=True
    )
    del_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("🗑 Удалить привычку"), delete_habit_start)],
        states={CONFIRM_DELETE: [CallbackQueryHandler(confirm_delete, pattern="^del_|cancel_del$")]},
        fallbacks=[CommandHandler("cancel", lambda u,c: ConversationHandler.END)], allow_reentry=True
    )
    edit_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("✏️ Редактировать"), edit_habit_start)],
        states={EDIT_SELECT: [CallbackQueryHandler(edit_select, pattern="^edith_|edit_name|edit_days|edit_cancel$")], EDIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_name_save)], EDIT_DAYS: [CallbackQueryHandler(edit_days_callback, pattern="^editday_|editdays_save$")]},
        fallbacks=[CommandHandler("cancel", lambda u,c: ConversationHandler.END)], allow_reentry=True
    )
    reminder_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("⏰ Напоминание"), reminder_menu)],
        states={REMINDER_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, reminder_time_set)]},
        fallbacks=[CommandHandler("cancel", lambda u,c: ConversationHandler.END)], allow_reentry=True
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(add_conv)
    app.add_handler(del_conv)
    app.add_handler(edit_conv)
    app.add_handler(reminder_conv)
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    print("✅ Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
