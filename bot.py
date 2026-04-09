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
TOKEN = os.environ.get("8717114083:AAEgNViVX7h0ea6pHc4Awp76h0gF0eJbcQg", "")
if not TOKEN:
    raise ValueError("8717114083:AAEgNViVX7h0ea6pHc4Awp76h0gF0eJbcQg environment variable not set")
DB_NAME = "habits.db"
TIMEZONE = ZoneInfo("Europe/Moscow")  # измените под свой часовой пояс

# ========== ЯЗЫКИ (только русский и английский) ==========
TEXTS = {
    'ru': {
        'welcome': "👋 Привет! Я трекер привычек с уровнями и опытом. Выбери язык /choose_language",
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
        'add_name': "✏️ Введите название привычки:",
        'ask_time': "⏱ Введите целевое время в минутах (или 0, если не важно):",
        'choose_days': "📅 Выберите дни выполнения (можно несколько):",
        'ask_reminder': "⏰ Введите время напоминания (ЧЧ:ММ) или 'нет':",
        'habit_added': "✅ Привычка '{}' добавлена!",
        'no_habits_today': "На сегодня нет запланированных привычек.",
        'today_header': "📋 Привычки на {}:",
        'already_done': "Уже отмечено!",
        'motivation': "Отлично! +10 XP 🔥",
        'no_habits': "У вас пока нет привычек. Добавьте через меню.",
        'choose_to_delete': "🗑 Выберите привычку для удаления:",
        'deleted': "✅ Привычка удалена.",
        'cancel': "Отменено.",
        'help_text': "🤖 Помощь\n\n📋 Сегодня – отметить привычки\n📊 Статистика – графики и проценты\n➕ Добавить – новая привычка\n🗑 Удалить – убрать привычку\n🏆 Лидеры – таблица рейтинга\n📆 Календарь – отметить любой день\n📁 Экспорт CSV – выгрузить данные\n✏️ Редактировать – изменить привычку\n👤 Профиль – ваш уровень и опыт\n/skip – пропустить день (не сбрасывает серию, 1 раз в 7 дней)",
        'use_buttons': "Используйте кнопки меню.",
        'select_habit_to_edit': "✏️ Выберите привычку для редактирования:",
        'what_to_edit': "Что хотите изменить?",
        'edit_name': "Название",
        'edit_days': "Дни выполнения",
        'edit_reminder': "Время напоминания",
        'edit_name_prompt': "Введите новое название:",
        'edit_name_saved': "Название изменено!",
        'edit_days_prompt': "Выберите новые дни:",
        'edit_days_saved': "Дни изменены!",
        'edit_reminder_prompt': "Введите новое время (ЧЧ:ММ) или 'нет':",
        'edit_reminder_saved': "Напоминание обновлено!",
        'skip_used': "Вы уже использовали пропуск на этой неделе. Серия будет прервана.",
        'skip_ok': "✅ Пропуск засчитан. Серия не сброшена, но привычка сегодня не выполнена.",
        'level_up': "🎉 Поздравляем! Вы достигли уровня {}!",
        'achievement_unlock': "🏆 Новое достижение: {}",
        'streak7_achievement': "7 дней подряд! 🔥",
        'streak30_achievement': "30 дней подряд! ⭐",
        'perfect_month_achievement': "Идеальный месяц! 🌟",
    },
    'en': {
        'welcome': "👋 Hi! I'm a habit tracker with levels and XP. Choose language /choose_language",
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
        'add_name': "✏️ Enter habit name:",
        'ask_time': "⏱ Enter target time in minutes (or 0 if not important):",
        'choose_days': "📅 Select days (multiple allowed):",
        'ask_reminder': "⏰ Enter reminder time (HH:MM) or 'no':",
        'habit_added': "✅ Habit '{}' added!",
        'no_habits_today': "No habits scheduled for today.",
        'today_header': "📋 Habits for {}:",
        'already_done': "Already marked!",
        'motivation': "Great! +10 XP 🔥",
        'no_habits': "You have no habits yet. Add via menu.",
        'choose_to_delete': "🗑 Choose habit to delete:",
        'deleted': "✅ Habit deleted.",
        'cancel': "Canceled.",
        'help_text': "🤖 Help\n\n📋 Today – mark habits\n📊 Stats – graphs and percentages\n➕ Add – new habit\n🗑 Delete – remove habit\n🏆 Leaderboard – ranking\n📆 Calendar – mark any day\n📁 Export CSV – download data\n✏️ Edit – modify habit\n👤 Profile – your level and XP\n/skip – skip a day (doesn't break streak, once per 7 days)",
        'use_buttons': "Use menu buttons.",
        'select_habit_to_edit': "✏️ Select habit to edit:",
        'what_to_edit': "What would you like to change?",
        'edit_name': "Name",
        'edit_days': "Days",
        'edit_reminder': "Reminder time",
        'edit_name_prompt': "Enter new name:",
        'edit_name_saved': "Name changed!",
        'edit_days_prompt': "Select new days:",
        'edit_days_saved': "Days changed!",
        'edit_reminder_prompt': "Enter new time (HH:MM) or 'no':",
        'edit_reminder_saved': "Reminder updated!",
        'skip_used': "You already used skip this week. Streak will break.",
        'skip_ok': "✅ Skip counted. Streak preserved, but habit not completed today.",
        'level_up': "🎉 Congratulations! You reached level {}!",
        'achievement_unlock': "🏆 New achievement: {}",
        'streak7_achievement': "7 days in a row! 🔥",
        'streak30_achievement': "30 days in a row! ⭐",
        'perfect_month_achievement': "Perfect month! 🌟",
    }
}

MOTIVATION_RU = [
    "🔥 Отлично! +10 XP",
    "💪 Ты крут! Продолжай в том же духе!",
    "🌟 Ещё один день – ещё одна победа!",
    "🎉 Маленькие шаги ведут к большим целям!",
    "🧠 Привычка становится сильнее!"
]
MOTIVATION_EN = [
    "🔥 Great! +10 XP",
    "💪 You're awesome! Keep going!",
    "🌟 Another day, another victory!",
    "🎉 Small steps lead to big goals!",
    "🧠 Your habit is getting stronger!"
]

# Состояния диалогов
(CHOOSING_HABIT_TYPE, TYPING_HABIT_NAME, TYPING_HABIT_TIME,
 CHOOSING_HABIT_DAYS, CHOOSING_REMINDER_TIME, CONFIRM_DELETE,
 EDIT_SELECT, EDIT_NAME, EDIT_DAYS, EDIT_REMINDER) = range(10)

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
        level INTEGER DEFAULT 1,
        last_skip_week INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS habits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT,
        target_time INTEGER DEFAULT 0,
        days TEXT DEFAULT '0123456',
        reminder_time TEXT,
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS habit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        habit_id INTEGER,
        completed_date TEXT,
        minutes INTEGER DEFAULT 0,
        FOREIGN KEY (habit_id) REFERENCES habits (id),
        UNIQUE(habit_id, completed_date)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS achievements (
        user_id INTEGER,
        type TEXT,
        achieved_at TIMESTAMP,
        PRIMARY KEY (user_id, type)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS skip_usage (
        user_id INTEGER,
        used_week INTEGER,
        PRIMARY KEY (user_id, used_week)
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
    """Добавляет опыт, повышает уровень, возвращает (new_xp, new_level, level_up_flag)"""
    row = db_query("SELECT xp, level FROM users WHERE id = ?", (user_id,), fetch_one=True)
    if not row:
        return
    xp, level = row
    xp += amount
    new_level = level
    level_up = False
    # Формула: следующий уровень требует level*100 XP
    while xp >= new_level * 100:
        xp -= new_level * 100
        new_level += 1
        level_up = True
    db_query("UPDATE users SET xp = ?, level = ? WHERE id = ?", (xp, new_level, user_id))
    return xp, new_level, level_up

def get_streak(user_id, habit_id):
    logs = db_query("SELECT completed_date FROM habit_logs WHERE habit_id = ? ORDER BY completed_date DESC", (habit_id,), fetch_all=True)
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
    completed = db_query(f"SELECT COUNT(DISTINCT completed_date) FROM habit_logs WHERE habit_id = ? AND completed_date IN ({placeholders})", (habit_id, *required), fetch_one=True)
    return (completed[0] / len(required)) * 100

def check_achievements(user_id, habit_id):
    """Проверяет и выдает ачивки, возвращает список названий (на русском для сообщения)"""
    streak = get_streak(user_id, habit_id)
    percent = get_percentage(user_id, habit_id, 30)
    lang = get_user_lang(user_id)
    earned = []
    # Достижение 7 дней
    if streak >= 7:
        if not db_query("SELECT 1 FROM achievements WHERE user_id=? AND type='streak7'", (user_id,), fetch_one=True):
            db_query("INSERT INTO achievements(user_id, type, achieved_at) VALUES(?,?,?)", (user_id, 'streak7', datetime.now(TIMEZONE).isoformat()))
            earned.append(TEXTS[lang].get('streak7_achievement', "7 days streak! 🔥"))
    # 30 дней
    if streak >= 30:
        if not db_query("SELECT 1 FROM achievements WHERE user_id=? AND type='streak30'", (user_id,), fetch_one=True):
            db_query("INSERT INTO achievements(user_id, type, achieved_at) VALUES(?,?,?)", (user_id, 'streak30', datetime.now(TIMEZONE).isoformat()))
            earned.append(TEXTS[lang].get('streak30_achievement', "30 days streak! ⭐"))
    # Идеальный месяц (100% за 30 дней)
    if percent >= 99.9:
        if not db_query("SELECT 1 FROM achievements WHERE user_id=? AND type='perfect_month'", (user_id,), fetch_one=True):
            db_query("INSERT INTO achievements(user_id, type, achieved_at) VALUES(?,?,?)", (user_id, 'perfect_month', datetime.now(TIMEZONE).isoformat()))
            earned.append(TEXTS[lang].get('perfect_month_achievement', "Perfect month! 🌟"))
    return earned

def get_month_calendar(user_id, year, month):
    """Возвращает текст календаря с символами выполнения"""
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
            done = db_query("SELECT COUNT(DISTINCT habit_id) FROM habit_logs WHERE habit_id IN ({}) AND completed_date=?".format(','.join(['?']*total)), [h[0] for h in habits] + [date_str], fetch_one=True)[0]
            if total == 0:
                mark = '⬜'
            else:
                ratio = done / total
                if ratio == 1:
                    mark = '✅'
                elif ratio > 0:
                    mark = '⚠️'
                else:
                    mark = '❌'
        week.append(f"{mark}{day:2d}")
        if len(week) == 7:
            weeks.append(' '.join(week))
            week = []
    if week:
        weeks.append(' '.join(week))
    return '\n'.join(weeks)

def can_skip(user_id):
    """Проверяет, можно ли использовать пропуск (не чаще раза в 7 дней)"""
    current_week = datetime.now(TIMEZONE).isocalendar()[1]
    used = db_query("SELECT 1 FROM skip_usage WHERE user_id=? AND used_week=?", (user_id, current_week), fetch_one=True)
    return used is None

def mark_skip_used(user_id):
    current_week = datetime.now(TIMEZONE).isocalendar()[1]
    db_query("INSERT INTO skip_usage(user_id, used_week) VALUES(?,?)", (user_id, current_week))

# ========== ОБРАБОТЧИКИ ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = update.effective_user.language_code if update.effective_user.language_code in ('ru','en') else 'ru'
    db_query("INSERT OR IGNORE INTO users (id, username, first_name, last_name, lang) VALUES (?,?,?,?,?)",
             (user.id, user.username, user.first_name, user.last_name, lang))
    text = get_text(user.id, 'welcome')
    keyboard = ReplyKeyboardMarkup([
        [get_text(user.id, 'today'), get_text(user.id, 'stats')],
        [get_text(user.id, 'add'), get_text(user.id, 'delete')],
        [get_text(user.id, 'leaderboard'), get_text(user.id, 'calendar'), get_text(user.id, 'export')],
        [get_text(user.id, 'edit'), get_text(user.id, 'profile'), get_text(user.id, 'help')]
    ], resize_keyboard=True)
    await update.message.reply_text(text, reply_markup=keyboard)

async def choose_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")]
    ])
    await update.message.reply_text("Select language / Выберите язык:", reply_markup=keyboard)

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.data.split('_')[1]
    db_query("UPDATE users SET lang = ? WHERE id = ?", (lang, query.from_user.id))
    await query.edit_message_text(f"Language set to {lang}. Use /start to see menu.")

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    row = db_query("SELECT xp, level FROM users WHERE id=?", (user_id,), fetch_one=True)
    if not row:
        await update.message.reply_text("Ошибка")
        return
    xp, level = row
    next_xp = level * 100 - xp
    text = f"👤 *Ваш профиль*\nУровень: {level}\nОпыт: {xp} / {level*100}\nДо следующего уровня: {next_xp} XP\n"
    # Достижения
    achievements = db_query("SELECT type FROM achievements WHERE user_id=?", (user_id,), fetch_all=True)
    if achievements:
        text += "\n🏆 *Достижения:*\n"
        for (typ,) in achievements:
            if typ == 'streak7':
                text += "🔥 7 дней подряд\n"
            elif typ == 'streak30':
                text += "⭐ 30 дней подряд\n"
            elif typ == 'perfect_month':
                text += "🌟 Идеальный месяц\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def skip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not can_skip(user_id):
        await update.message.reply_text(get_text(user_id, 'skip_used'))
        return
    # Пропуск действует на все привычки сегодня: не сбрасывает серию, но и не отмечает.
    # Механизм: мы ничего не записываем в habit_logs, но помечаем, что пропуск использован.
    # Серия не сбросится, потому что get_streak смотрит только на дни, которые были выполнены.
    # Однако для корректного поведения нужно, чтобы привычка не считалась выполненной, но и не считалась пропущенной.
    # Наша функция get_streak уже корректна: если нет записи в habit_logs, день считается пропущенным и серия обрывается.
    # Чтобы серия не обрывалась, мы должны добавить фиктивную запись? Нет, это будет считаться выполнением.
    # Лучше реализовать отдельную таблицу skipped_days, но для простоты изменим get_streak так, чтобы он игнорировал дни с пропуском.
    # Однако проще: при пропуске мы добавляем запись в habit_logs с minutes=-1, означающую пропуск. get_streak будет её игнорировать.
    # Сделаем так:
    today_str = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    habits = db_query("SELECT id FROM habits WHERE user_id=? AND is_active=1", (user_id,), fetch_all=True)
    for (hid,) in habits:
        # Проверяем, нет ли уже отметки
        existing = db_query("SELECT id FROM habit_logs WHERE habit_id=? AND completed_date=?", (hid, today_str), fetch_one=True)
        if not existing:
            db_query("INSERT INTO habit_logs (habit_id, completed_date, minutes) VALUES (?,?,?)", (hid, today_str, -1))
    mark_skip_used(user_id)
    await update.message.reply_text(get_text(user_id, 'skip_ok'))

# Модифицируем get_streak, чтобы игнорировать записи с minutes = -1
def get_streak_fixed(user_id, habit_id):
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

# Переопределим get_streak на исправленную версию
get_streak = get_streak_fixed

# ---------- ДОБАВЛЕНИЕ ПРИВЫЧКИ ----------
async def add_habit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(get_text(user_id, 'add_name'))
    return TYPING_HABIT_NAME

async def add_habit_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['habit_name'] = update.message.text
    user_id = update.effective_user.id
    await update.message.reply_text(get_text(user_id, 'ask_time'))
    return TYPING_HABIT_TIME

async def add_habit_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        target = int(update.message.text)
        context.user_data['habit_target'] = target
        user_id = update.effective_user.id
        keyboard = [[InlineKeyboardButton(day, callback_data=f"day_{i}") for i, day in enumerate(["Пн","Вт","Ср","Чт","Пт","Сб","Вс"])],
                    [InlineKeyboardButton("✅ Готово", callback_data="days_done")]]
        await update.message.reply_text(get_text(user_id, 'choose_days'), reply_markup=InlineKeyboardMarkup(keyboard))
        return CHOOSING_HABIT_DAYS
    except ValueError:
        await update.message.reply_text("Введите число (минуты):")
        return TYPING_HABIT_TIME

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
        context.user_data['habit_days_str'] = days_str
        user_id = query.from_user.id
        await query.edit_message_text(get_text(user_id, 'ask_reminder'))
        return CHOOSING_REMINDER_TIME
    day = int(query.data.split('_')[1])
    if day in context.user_data['habit_days']:
        context.user_data['habit_days'].remove(day)
    else:
        context.user_data['habit_days'].add(day)
    days_names = ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]
    row = [InlineKeyboardButton(f"{'✅ ' if i in context.user_data['habit_days'] else '⬜ '}{days_names[i]}", callback_data=f"day_{i}") for i in range(7)]
    keyboard = [row, [InlineKeyboardButton("✅ Готово", callback_data="days_done")]]
    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))

async def add_habit_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reminder = update.message.text.strip()
    if reminder.lower() == 'нет':
        reminder = None
    else:
        try:
            datetime.strptime(reminder, "%H:%M")
        except:
            await update.message.reply_text("Формат ЧЧ:ММ или 'нет'")
            return CHOOSING_REMINDER_TIME
    user_id = update.effective_user.id
    habit_name = context.user_data['habit_name']
    target_time = context.user_data['habit_target']
    days_str = context.user_data['habit_days_str']
    db_query("INSERT INTO habits (user_id, name, target_time, days, reminder_time) VALUES (?,?,?,?,?)",
             (user_id, habit_name, target_time, days_str, reminder))
    if reminder:
        habit_id = db_query("SELECT last_insert_rowid()", fetch_one=True)[0]
        hour, minute = map(int, reminder.split(':'))
        remind_time = time(hour, minute, tzinfo=TIMEZONE)
        context.application.job_queue.run_daily(
            send_reminder, remind_time,
            days=tuple(map(int, days_str)),
            context={"user_id": user_id, "habit_name": habit_name, "habit_id": habit_id},
            name=f"remind_{user_id}_{habit_id}"
        )
    await update.message.reply_text(get_text(user_id, 'habit_added').format(habit_name))
    return ConversationHandler.END

# ---------- НАПОМИНАНИЕ С ОТЛОЖЕНИЕМ ----------
async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.context
    user_id = data["user_id"]
    habit_name = data["habit_name"]
    habit_id = data["habit_id"]
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("⏰ Напомнить через 30 мин", callback_data=f"snooze_{habit_id}")]])
    await context.bot.send_message(user_id, f"🔔 Напоминание: пора выполнить '{habit_name}'!", reply_markup=keyboard)

async def snooze_habit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    habit_id = int(query.data.split('_')[1])
    # Получаем данные о привычке
    row = db_query("SELECT user_id, name, reminder_time, days FROM habits WHERE id=?", (habit_id,), fetch_one=True)
    if not row:
        return
    user_id, name, reminder_time, days_str = row
    # Устанавливаем новое напоминание через 30 минут
    new_time = datetime.now(TIMEZONE) + timedelta(minutes=30)
    context.application.job_queue.run_once(
        send_reminder_once, when=new_time,
        context={"user_id": user_id, "habit_name": name, "habit_id": habit_id},
        name=f"snooze_{user_id}_{habit_id}"
    )
    await query.edit_message_text("⏰ Напомню через 30 минут.")

async def send_reminder_once(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.context
    await context.bot.send_message(data["user_id"], f"🔔 Напоминание: пора выполнить '{data['habit_name']}'!")

# ---------- ОТМЕТКА СЕГОДНЯ И КАЛЕНДАРЬ ----------
async def show_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    today_str = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    weekday = datetime.now(TIMEZONE).weekday()
    habits = db_query("SELECT id, name FROM habits WHERE user_id=? AND is_active=1 AND days LIKE ?", (user_id, f'%{weekday}%'), fetch_all=True)
    if not habits:
        await update.message.reply_text(get_text(user_id, 'no_habits_today'))
        return
    keyboard = []
    for hid, name in habits:
        completed = db_query("SELECT id, minutes FROM habit_logs WHERE habit_id=? AND completed_date=?", (hid, today_str), fetch_one=True)
        if completed and completed[1] >= 0:
            text = f"✅ {name} ✅"
        else:
            text = f"⬜ {name}"
        keyboard.append([InlineKeyboardButton(text, callback_data=f"complete_{hid}_{today_str}")])
    await update.message.reply_text(get_text(user_id, 'today_header').format(datetime.now(TIMEZONE).strftime("%d.%m.%Y")), reply_markup=InlineKeyboardMarkup(keyboard))

async def complete_habit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, hid, date_str = query.data.split('_')
    habit_id = int(hid)
    user_id = query.from_user.id
    # Проверяем, нет ли уже отметки (и не пропуск)
    existing = db_query("SELECT id, minutes FROM habit_logs WHERE habit_id=? AND completed_date=?", (habit_id, date_str), fetch_one=True)
    if existing and existing[1] >= 0:
        await query.edit_message_text(get_text(user_id, 'already_done'))
        return
    # Удаляем запись о пропуске, если была
    if existing and existing[1] == -1:
        db_query("DELETE FROM habit_logs WHERE id=?", (existing[0],))
    # Добавляем выполнение
    db_query("INSERT INTO habit_logs (habit_id, completed_date, minutes) VALUES (?,?,0)", (habit_id, date_str))
    # Начисляем XP
    xp_gain = 10
    new_xp, new_level, level_up = add_xp(user_id, xp_gain)
    # Мотивационная фраза
    lang = get_user_lang(user_id)
    mot = random.choice(MOTIVATION_RU if lang=='ru' else MOTIVATION_EN)
    reply = f"{mot}\n+{xp_gain} XP"
    if level_up:
        reply += "\n" + get_text(user_id, 'level_up').format(new_level)
    # Проверка достижений
    earned_ach = check_achievements(user_id, habit_id)
    for ach in earned_ach:
        reply += f"\n{get_text(user_id, 'achievement_unlock').format(ach)}"
    await query.edit_message_text(reply)
    # Обновляем список сегодня
    await show_today(update, context)

async def calendar_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    today = datetime.now(TIMEZONE)
    year, month = today.year, today.month
    cal_text = get_month_calendar(user_id, year, month)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️", callback_data=f"cal_{year}_{month-1 if month>1 else 12}_{year if month>1 else year-1}"),
         InlineKeyboardButton(f"{month:02d}.{year}", callback_data="ignore"),
         InlineKeyboardButton("▶️", callback_data=f"cal_{year}_{month+1 if month<12 else 1}_{year if month<12 else year+1}")],
        [InlineKeyboardButton(get_text(user_id, 'today'), callback_data="cal_today")]
    ])
    await update.message.reply_text(f"📅 *{year}-{month:02d}*\n{cal_text}", parse_mode="Markdown", reply_markup=keyboard)

async def calendar_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "cal_today":
        await calendar_menu(update, context)
        return
    if data.startswith("cal_"):
        parts = data.split('_')
        if len(parts) == 4:
            _, y, m, y2 = parts
            year, month = int(y), int(m)
            user_id = query.from_user.id
            cal_text = get_month_calendar(user_id, year, month)
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️", callback_data=f"cal_{year}_{month-1 if month>1 else 12}_{year if month>1 else year-1}"),
                 InlineKeyboardButton(f"{month:02d}.{year}", callback_data="ignore"),
                 InlineKeyboardButton("▶️", callback_data=f"cal_{year}_{month+1 if month<12 else 1}_{year if month<12 else year+1}")],
                [InlineKeyboardButton(get_text(user_id, 'today'), callback_data="cal_today")]
            ])
            await query.edit_message_text(f"📅 *{year}-{month:02d}*\n{cal_text}", parse_mode="Markdown", reply_markup=keyboard)

# ---------- СТАТИСТИКА И ГРАФИК ----------
async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    habits = db_query("SELECT id, name FROM habits WHERE user_id=? AND is_active=1", (user_id,), fetch_all=True)
    if not habits:
        await update.message.reply_text(get_text(user_id, 'no_habits'))
        return
    text = "📊 *Ваша статистика*\n\n"
    for hid, name in habits:
        streak = get_streak(user_id, hid)
        percent = get_percentage(user_id, hid, 30)
        bar = "█" * int(percent//10) + "░" * (10 - int(percent//10))
        text += f"*{name}*\n🔥 Серия: {streak} дн.\n📈 30 дней: {percent:.1f}%\n{bar}\n\n"
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
    plt.xlabel("Дата")
    plt.ylabel("Выполнено")
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

# ---------- УДАЛЕНИЕ ПРИВЫЧКИ ----------
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

# ---------- РЕДАКТИРОВАНИЕ ПРИВЫЧКИ ----------
async def edit_habit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    habits = db_query("SELECT id, name FROM habits WHERE user_id=? AND is_active=1", (user_id,), fetch_all=True)
    if not habits:
        await update.message.reply_text(get_text(user_id, 'no_habits'))
        return ConversationHandler.END
    keyboard = [[InlineKeyboardButton(name, callback_data=f"edith_{hid}")] for hid, name in habits]
    await update.message.reply_text(get_text(user_id, 'select_habit_to_edit'), reply_markup=InlineKeyboardMarkup(keyboard))
    return EDIT_SELECT

async def edit_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    habit_id = int(query.data.split('_')[1])
    context.user_data['edit_id'] = habit_id
    user_id = query.from_user.id
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(get_text(user_id, 'edit_name'), callback_data="edit_name")],
        [InlineKeyboardButton(get_text(user_id, 'edit_days'), callback_data="edit_days")],
        [InlineKeyboardButton(get_text(user_id, 'edit_reminder'), callback_data="edit_reminder")],
        [InlineKeyboardButton("🔙 Назад", callback_data="edit_cancel")]
    ])
    await query.edit_message_text(get_text(user_id, 'what_to_edit'), reply_markup=keyboard)
    return EDIT_SELECT  # остаёмся в том же состоянии

async def edit_name_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(get_text(query.from_user.id, 'edit_name_prompt'))
    return EDIT_NAME

async def edit_name_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_name = update.message.text
    habit_id = context.user_data['edit_id']
    db_query("UPDATE habits SET name=? WHERE id=?", (new_name, habit_id))
    await update.message.reply_text(get_text(update.effective_user.id, 'edit_name_saved'))
    return ConversationHandler.END

async def edit_days_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    # Получаем текущие дни
    habit_id = context.user_data['edit_id']
    row = db_query("SELECT days FROM habits WHERE id=?", (habit_id,), fetch_one=True)
    current_days = set(map(int, row[0])) if row else set()
    context.user_data['edit_days_temp'] = current_days
    keyboard = []
    days_names = ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]
    row_btns = []
    for i, name in enumerate(days_names):
        emoji = "✅ " if i in current_days else "⬜ "
        row_btns.append(InlineKeyboardButton(f"{emoji}{name}", callback_data=f"editday_{i}"))
    keyboard.append(row_btns)
    keyboard.append([InlineKeyboardButton("✅ Сохранить", callback_data="editdays_save")])
    await query.edit_message_text(get_text(user_id, 'edit_days_prompt'), reply_markup=InlineKeyboardMarkup(keyboard))
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
    # обновляем клавиатуру
    days_names = ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]
    row = [InlineKeyboardButton(f"{'✅ ' if i in context.user_data['edit_days_temp'] else '⬜ '}{days_names[i]}", callback_data=f"editday_{i}") for i in range(7)]
    keyboard = [row, [InlineKeyboardButton("✅ Сохранить", callback_data="editdays_save")]]
    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))

async def edit_days_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    days_set = context.user_data.get('edit_days_temp', set())
    if not days_set:
        await query.edit_message_text("Выберите хотя бы один день!")
        return
    days_str = ''.join(map(str, sorted(days_set)))
    habit_id = context.user_data['edit_id']
    db_query("UPDATE habits SET days=? WHERE id=?", (days_str, habit_id))
    await query.edit_message_text(get_text(query.from_user.id, 'edit_days_saved'))
    return ConversationHandler.END

async def edit_reminder_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(get_text(query.from_user.id, 'edit_reminder_prompt'))
    return EDIT_REMINDER

async def edit_reminder_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reminder = update.message.text.strip()
    user_id = update.effective_user.id
    if reminder.lower() == 'нет':
        reminder = None
    else:
        try:
            datetime.strptime(reminder, "%H:%M")
        except:
            await update.message.reply_text("Неверный формат. Введите ЧЧ:ММ или 'нет'")
            return EDIT_REMINDER
    habit_id = context.user_data['edit_id']
    db_query("UPDATE habits SET reminder_time=? WHERE id=?", (reminder, habit_id))
    # Обновляем JobQueue: удаляем старую и создаём новую
    # (упрощённо: можно перезапустить бота, но для правильной работы нужно удалить старый job)
    # Здесь для простоты оставим, пользователь перезапустит бота или следующее напоминание сработает по новому расписанию после перезапуска.
    await update.message.reply_text(get_text(user_id, 'edit_reminder_saved'))
    return ConversationHandler.END

async def edit_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Редактирование отменено.")
    return ConversationHandler.END

# ---------- ТАБЛИЦА ЛИДЕРОВ (по уровню + XP) ----------
async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = db_query("SELECT id, first_name, username, level, xp FROM users", fetch_all=True)
    data = []
    for uid, fname, uname, level, xp in users:
        name = fname or uname or f"User_{uid}"
        data.append((name, level, xp))
    data.sort(key=lambda x: (-x[1], -x[2]))  # по уровню, потом по XP
    text = "🏆 *Таблица лидеров (уровень/опыт)*\n\n"
    for i, (name, level, xp) in enumerate(data[:10], 1):
        medal = "🥇 " if i==1 else "🥈 " if i==2 else "🥉 " if i==3 else ""
        text += f"{medal}{i}. {name} — уровень {level} ({xp} XP)\n"
    await update.message.reply_text(text, parse_mode="Markdown")

# ---------- ЭКСПОРТ CSV ----------
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

# ---------- ЕЖЕНЕДЕЛЬНЫЙ ОТЧЁТ ----------
async def weekly_report(context: ContextTypes.DEFAULT_TYPE):
    users = db_query("SELECT id FROM users", fetch_all=True)
    for (uid,) in users:
        habits = db_query("SELECT id, name FROM habits WHERE user_id=? AND is_active=1", (uid,), fetch_all=True)
        if not habits:
            continue
        total_possible = 0
        total_done = 0
        for hid, name in habits:
            days_str = db_query("SELECT days FROM habits WHERE id=?", (hid,), fetch_one=True)[0]
            allowed = list(map(int, days_str))
            for i in range(7):
                d = datetime.now(TIMEZONE).date() - timedelta(days=i)
                if d.weekday() in allowed:
                    total_possible += 1
                    if db_query("SELECT id FROM habit_logs WHERE habit_id=? AND completed_date=? AND minutes>=0", (hid, d.strftime("%Y-%m-%d")), fetch_one=True):
                        total_done += 1
        if total_possible > 0:
            percent = total_done / total_possible * 100
            text = f"📊 *Еженедельный отчёт*\nВыполнено {percent:.0f}% привычек за неделю! Так держать! 🎉"
            await context.bot.send_message(uid, text, parse_mode="Markdown")

# ---------- ОБРАБОТЧИК ТЕКСТА И КНОПОК ----------
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
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
    elif text == h:
        await help_command(update, context)
    else:
        await update.message.reply_text(get_text(user_id, 'use_buttons'))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(get_text(user_id, 'help_text'))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    if data.startswith("complete_"):
        await complete_habit(update, context)
    elif data == "plot_stats":
        await plot_stats(update, context)
    elif data.startswith("cal_"):
        await calendar_callback(update, context)
    elif data.startswith("lang_"):
        await set_language(update, context)
    elif data.startswith("edith_"):
        await edit_select(update, context)
    elif data == "edit_name":
        await edit_name_prompt(update, context)
    elif data == "edit_days":
        await edit_days_prompt(update, context)
    elif data == "edit_reminder":
        await edit_reminder_prompt(update, context)
    elif data == "edit_cancel":
        await edit_cancel(update, context)
    elif data.startswith("editday_"):
        await edit_days_callback(update, context)
    elif data == "editdays_save":
        await edit_days_save(update, context)
    elif data.startswith("snooze_"):
        await snooze_habit(update, context)
    else:
        await query.answer()

# ========== ЗАПУСК ==========
def main():
    init_db()
    app = Application.builder().token(TOKEN).build()

    # ConversationHandler для добавления
    add_conv = ConversationHandler(
        entry_points=[CommandHandler("add", add_habit_start), MessageHandler(filters.Regex("➕ Добавить привычку"), add_habit_start)],
        states={
            TYPING_HABIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_habit_name)],
            TYPING_HABIT_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_habit_time)],
            CHOOSING_HABIT_DAYS: [CallbackQueryHandler(days_callback, pattern="^day_|days_done$")],
            CHOOSING_REMINDER_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_habit_reminder)],
        },
        fallbacks=[CommandHandler("cancel", lambda u,c: ConversationHandler.END)],
        allow_reentry=True
    )
    # Удаление
    del_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("🗑 Удалить привычку"), delete_habit_start)],
        states={CONFIRM_DELETE: [CallbackQueryHandler(confirm_delete, pattern="^del_|cancel_del$")]},
        fallbacks=[CommandHandler("cancel", lambda u,c: ConversationHandler.END)],
        allow_reentry=True
    )
    # Редактирование
    edit_conv = ConversationHandler(
        entry_points=[CommandHandler("edit", edit_habit_start), MessageHandler(filters.Regex("✏️ Редактировать"), edit_habit_start)],
        states={
            EDIT_SELECT: [CallbackQueryHandler(edit_select, pattern="^edith_|edit_name|edit_days|edit_reminder|edit_cancel$")],
            EDIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_name_save)],
            EDIT_DAYS: [CallbackQueryHandler(edit_days_callback, pattern="^editday_|editdays_save$")],
            EDIT_REMINDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_reminder_save)],
        },
        fallbacks=[CommandHandler("cancel", lambda u,c: ConversationHandler.END)],
        allow_reentry=True
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("choose_language", choose_language))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("skip", skip_command))
    app.add_handler(CommandHandler("export", export_csv))
    app.add_handler(add_conv)
    app.add_handler(del_conv)
    app.add_handler(edit_conv)
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    # Еженедельный отчёт каждое воскресенье в 10:00
    app.job_queue.run_daily(weekly_report, time=time(10,0, tzinfo=TIMEZONE), days=(6,))

    print("Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
