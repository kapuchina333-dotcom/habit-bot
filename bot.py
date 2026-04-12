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
        'help_text': "🤖 Помощь\n\n📋 Сегодня – отметить привычки\n📊 Статистика – графики и время\n➕ Добавить – новая привычка\n🗑 Удалить – убрать привычку\n🏆 Лидеры – таблица рейтинга\n📆 Календарь – отметить любой день\n📁 Экспорт CSV – выгрузить данные\n✏️ Редактировать – изменить привычку или добавить напоминание\n👤 Профиль – ваш уровень и опыт\n/skip – пропустить день (не сбрасывает серию, 1 раз в 7 дней)",
        'use_buttons': "Используйте кнопки меню.",
        'select_habit_to_edit': "✏️ Выберите привычку для редактирования:",
        'what_to_edit': "Что хотите изменить?",
        'edit_name': "✏️ Название",
        'edit_days': "📅 Дни выполнения",
        'edit_reminder': "⏰ Напоминание",
        'edit_name_prompt': "Введите новое название:",
        'edit_name_saved': "Название изменено!",
        'edit_days_prompt': "Выберите новые дни:",
        'edit_days_saved': "Дни изменены!",
        'edit_reminder_prompt': "Введите время напоминания (ЧЧ:ММ) или 'нет' чтобы удалить:",
        'edit_reminder_saved': "Напоминание обновлено!",
        'skip_used': "Вы уже использовали пропуск на этой неделе. Серия будет прервана.",
        'skip_ok': "✅ Пропуск засчитан. Серия не сброшена, но привычка сегодня не выполнена.",
        'level_up': "🎉 Поздравляем! Вы достигли уровня {}!",
        'achievement_unlock': "🏆 Новое достижение: {}",
        'streak7_achievement': "7 дней подряд! 🔥",
        'streak30_achievement': "30 дней подряд! ⭐",
        'perfect_month_achievement': "Идеальный месяц! 🌟",
        'ask_time_after': "⏱ Сколько времени потратили?",
        'add_time': "⏱ Добавить время",
        'skip_time': "✅ Пропустить",
        'enter_time': "Введите время в минутах (только число):",
        'time_saved': "✅ {} минут добавлено!",
        'no_reminder': "⏰ Нет напоминания",
        'set_reminder': "⏰ Установить напоминание",
        'delete_reminder': "❌ Удалить напоминание",
        'reminder_set': "✅ Напоминание установлено на {}",
        'reminder_deleted': "✅ Напоминание удалено",
        'stats_time_today': "⏱ Сегодня: {} мин",
        'stats_time_week': "⏱ За неделю: {} мин",
        'stats_time_month': "⏱ За месяц: {} мин",
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
        'help_text': "🤖 Help\n\n📋 Today – mark habits\n📊 Stats – graphs and time\n➕ Add – new habit\n🗑 Delete – remove habit\n🏆 Leaderboard – ranking\n📆 Calendar – mark any day\n📁 Export CSV – download data\n✏️ Edit – modify habit or add reminder\n👤 Profile – your level and XP\n/skip – skip a day (doesn't break streak, once per 7 days)",
        'use_buttons': "Use menu buttons.",
        'select_habit_to_edit': "✏️ Select habit to edit:",
        'what_to_edit': "What would you like to change?",
        'edit_name': "✏️ Name",
        'edit_days': "📅 Days",
        'edit_reminder': "⏰ Reminder",
        'edit_name_prompt': "Enter new name:",
        'edit_name_saved': "Name changed!",
        'edit_days_prompt': "Select new days:",
        'edit_days_saved': "Days changed!",
        'edit_reminder_prompt': "Enter reminder time (HH:MM) or 'no' to remove:",
        'edit_reminder_saved': "Reminder updated!",
        'skip_used': "You already used skip this week. Streak will break.",
        'skip_ok': "✅ Skip counted. Streak preserved, but habit not completed today.",
        'level_up': "🎉 Congratulations! You reached level {}!",
        'achievement_unlock': "🏆 New achievement: {}",
        'streak7_achievement': "7 days in a row! 🔥",
        'streak30_achievement': "30 days in a row! ⭐",
        'perfect_month_achievement': "Perfect month! 🌟",
        'ask_time_after': "⏱ How many minutes did you spend?",
        'add_time': "⏱ Add time",
        'skip_time': "✅ Skip",
        'enter_time': "Enter time in minutes (number only):",
        'time_saved': "✅ {} minutes added!",
        'no_reminder': "⏰ No reminder",
        'set_reminder': "⏰ Set reminder",
        'delete_reminder': "❌ Delete reminder",
        'reminder_set': "✅ Reminder set for {}",
        'reminder_deleted': "✅ Reminder deleted",
        'stats_time_today': "⏱ Today: {} min",
        'stats_time_week': "⏱ This week: {} min",
        'stats_time_month': "⏱ This month: {} min",
    }
}

MOTIVATION_RU = [
    "🔥 Отлично! +10 XP",
    "💪 Ты крут! Продолжай в том же духе!",
    "🌟 Ещё один день – ещё одна победа!",
    "🎉 Маленькие шаги ведут к большим целям!",
]
MOTIVATION_EN = [
    "🔥 Great! +10 XP",
    "💪 You're awesome! Keep going!",
    "🌟 Another day, another victory!",
    "🎉 Small steps lead to big goals!",
]

# Состояния диалогов
(TYPING_HABIT_NAME, CHOOSING_HABIT_DAYS, CONFIRM_DELETE,
 EDIT_SELECT, EDIT_NAME, EDIT_DAYS, EDIT_REMINDER_TIME) = range(7)

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
        start_date = today.strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")
    elif period == 'week':
        start_date = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")
    elif period == 'month':
        start_date = today.replace(day=1).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")
    else:
        return 0
    result = db_query(
        "SELECT SUM(minutes) FROM habit_logs WHERE habit_id = ? AND completed_date >= ? AND completed_date <= ? AND minutes >= 0",
        (habit_id, start_date, end_date), fetch_one=True
    )
    return result[0] if result[0] else 0

def check_achievements(user_id, habit_id):
    streak = get_streak(user_id, habit_id)
    percent = get_percentage(user_id, habit_id, 30)
    lang = get_user_lang(user_id)
    earned = []
    if streak >= 7:
        if not db_query("SELECT 1 FROM achievements WHERE user_id=? AND type='streak7'", (user_id,), fetch_one=True):
            db_query("INSERT INTO achievements(user_id, type, achieved_at) VALUES(?,?,?)", (user_id, 'streak7', datetime.now(TIMEZONE).isoformat()))
            earned.append(TEXTS[lang].get('streak7_achievement', "7 days streak! 🔥"))
    if streak >= 30:
        if not db_query("SELECT 1 FROM achievements WHERE user_id=? AND type='streak30'", (user_id,), fetch_one=True):
            db_query("INSERT INTO achievements(user_id, type, achieved_at) VALUES(?,?,?)", (user_id, 'streak30', datetime.now(TIMEZONE).isoformat()))
            earned.append(TEXTS[lang].get('streak30_achievement', "30 days streak! ⭐"))
    if percent >= 99.9:
        if not db_query("SELECT 1 FROM achievements WHERE user_id=? AND type='perfect_month'", (user_id,), fetch_one=True):
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

# ========== ОБРАБОТЧИКИ ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = update.effective_user.language_code if update.effective_user.language_code in ('ru','en') else 'ru'
    db_query("INSERT OR IGNORE INTO users (id, username, first_name, last_name, lang) VALUES (?,?,?,?,?)",
             (user.id, user.username, user.first_name, user.last_name, lang))
    keyboard = ReplyKeyboardMarkup([
        [get_text(user.id, 'today'), get_text(user.id, 'stats')],
        [get_text(user.id, 'add'), get_text(user.id, 'delete')],
        [get_text(user.id, 'leaderboard'), get_text(user.id, 'calendar'), get_text(user.id, 'export')],
        [get_text(user.id, 'edit'), get_text(user.id, 'profile'), get_text(user.id, 'help')]
    ], resize_keyboard=True)
    await update.message.reply_text(get_text(user.id, 'welcome'), reply_markup=keyboard)

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    row = db_query("SELECT xp, level FROM users WHERE id=?", (user_id,), fetch_one=True)
    if not row:
        await update.message.reply_text("Ошибка: пользователь не найден")
        return
    xp, level = row
    next_xp = level * 100 - xp
    text = f"👤 *Ваш профиль*\nУровень: {level}\nОпыт: {xp} / {level*100}\nДо следующего уровня: {next_xp} XP\n"
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

# ---------- ДОБАВЛЕНИЕ ПРИВЫЧКИ (без напоминания) ----------
async def add_habit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(get_text(user_id, 'add_name'))
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
        habit_name = context.user_data['habit_name']
        db_query("INSERT INTO habits (user_id, name, days, reminder_time) VALUES (?,?,?,?)",
                 (user_id, habit_name, days_str, None))
        await query.edit_message_text(get_text(user_id, 'habit_added').format(habit_name))
        return ConversationHandler.END
    day = int(query.data.split('_')[1])
    if day in context.user_data['habit_days']:
        context.user_data['habit_days'].remove(day)
    else:
        context.user_data['habit_days'].add(day)
    days_names = ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]
    row = [InlineKeyboardButton(f"{'✅ ' if i in context.user_data['habit_days'] else '⬜ '}{days_names[i]}", callback_data=f"day_{i}") for i in range(7)]
    keyboard = [row, [InlineKeyboardButton("✅ Готово", callback_data="days_done")]]
    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))

# ---------- ОТМЕТКА ВЫПОЛНЕНИЯ С ВРЕМЕНЕМ ----------
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
            mins = completed[1]
            text = f"✅ {name}" + (f" ({mins} мин)" if mins > 0 else "")
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
    existing = db_query("SELECT id, minutes FROM habit_logs WHERE habit_id=? AND completed_date=?", (habit_id, date_str), fetch_one=True)
    if existing and existing[1] >= 0:
        await query.edit_message_text(get_text(user_id, 'already_done'))
        return
    if existing:
        db_query("DELETE FROM habit_logs WHERE id=?", (existing[0],))
    db_query("INSERT INTO habit_logs (habit_id, completed_date, minutes) VALUES (?,?,0)", (habit_id, date_str))
    xp, new_level, level_up = add_xp(user_id, 10)
    mot = random.choice(MOTIVATION_RU if get_user_lang(user_id)=='ru' else MOTIVATION_EN)
    reply = f"{mot}\n+10 XP"
    if level_up:
        reply += "\n" + get_text(user_id, 'level_up').format(new_level)
    earned = check_achievements(user_id, habit_id)
    for ach in earned:
        reply += f"\n{get_text(user_id, 'achievement_unlock').format(ach)}"
    context.user_data['pending_habit_id'] = habit_id
    context.user_data['pending_date'] = date_str
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(get_text(user_id, 'add_time'), callback_data="add_time_prompt")],
        [InlineKeyboardButton(get_text(user_id, 'skip_time'), callback_data="skip_time")]
    ])
    await query.edit_message_text(reply + "\n\n" + get_text(user_id, 'ask_time_after'), reply_markup=keyboard)

async def add_time_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    await query.edit_message_text(get_text(user_id, 'enter_time'))
    context.user_data['awaiting_time'] = True

async def skip_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    await query.edit_message_text("✅ Время не добавлено.")
    context.user_data.pop('pending_habit_id', None)
    context.user_data.pop('pending_date', None)
    await show_today(update, context)

async def save_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_time'):
        return
    try:
        minutes = int(update.message.text)
        habit_id = context.user_data.get('pending_habit_id')
        date_str = context.user_data.get('pending_date')
        if habit_id is None or date_str is None:
            await update.message.reply_text("Ошибка. Попробуйте отметить привычку заново.")
            context.user_data.pop('awaiting_time', None)
            return
        db_query("UPDATE habit_logs SET minutes = ? WHERE habit_id = ? AND completed_date = ?", (minutes, habit_id, date_str))
        await update.message.reply_text(get_text(update.effective_user.id, 'time_saved').format(minutes))
        context.user_data.pop('awaiting_time', None)
        context.user_data.pop('pending_habit_id', None)
        context.user_data.pop('pending_date', None)
        await show_today(update, context)
    except ValueError:
        await update.message.reply_text("Введите число (минуты).")

# ---------- СТАТИСТИКА С ВРЕМЕНЕМ ----------
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
        mins_today = get_total_minutes(user_id, hid, 'today')
        mins_week = get_total_minutes(user_id, hid, 'week')
        mins_month = get_total_minutes(user_id, hid, 'month')
        text += f"*{name}*\n"
        text += f"🔥 Серия: {streak} дн.\n"
        text += f"📈 30 дней: {percent:.1f}%\n{bar}\n"
        text += f"⏱ Сегодня: {mins_today} мин | За неделю: {mins_week} мин | За месяц: {mins_month} мин\n\n"
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

# ---------- РЕДАКТИРОВАНИЕ (включая напоминание) ----------
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
    habit_id = context.user_data['edit_id']
    row = db_query("SELECT days FROM habits WHERE id=?", (habit_id,), fetch_one=True)
    current_days = set(map(int, row[0])) if row else set()
    context.user_data['edit_days_temp'] = current_days
    days_names = ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]
    row_btns = [InlineKeyboardButton(f"{'✅ ' if i in current_days else '⬜ '}{days_names[i]}", callback_data=f"editday_{i}") for i in range(7)]
    keyboard = [row_btns, [InlineKeyboardButton("✅ Сохранить", callback_data="editdays_save")]]
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
    user_id = query.from_user.id
    habit_id = context.user_data['edit_id']
    row = db_query("SELECT reminder_time FROM habits WHERE id=?", (habit_id,), fetch_one=True)
    current = row[0] if row else None
    text = get_text(user_id, 'edit_reminder_prompt')
    if current:
        text += f"\nТекущее: {current}"
    await query.edit_message_text(text)
    return EDIT_REMINDER_TIME

async def edit_reminder_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reminder = update.message.text.strip()
    user_id = update.effective_user.id
    habit_id = context.user_data['edit_id']
    if reminder.lower() == 'нет':
        reminder = None
    else:
        try:
            datetime.strptime(reminder, "%H:%M")
        except:
            await update.message.reply_text("Неверный формат. Введите ЧЧ:ММ или 'нет'")
            return EDIT_REMINDER_TIME
    db_query("UPDATE habits SET reminder_time=? WHERE id=?", (reminder, habit_id))
    if reminder:
        # Обновляем job в queue (упрощённо: при перезапуске бота подхватится)
        pass
    await update.message.reply_text(get_text(user_id, 'edit_reminder_saved'))
    return ConversationHandler.END

async def edit_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Редактирование отменено.")
    return ConversationHandler.END

# ---------- КАЛЕНДАРЬ ----------
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

# ---------- ЛИДЕРЫ ----------
async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = db_query("SELECT id, first_name, username, level, xp FROM users", fetch_all=True)
    data = []
    for uid, fname, uname, level, xp in users:
        name = fname or uname or f"User_{uid}"
        data.append((name, level, xp))
    data.sort(key=lambda x: (-x[1], -x[2]))
    text = "🏆 *Таблица лидеров (уровень/опыт)*\n\n"
    for i, (name, level, xp) in enumerate(data[:10], 1):
        medal = "🥇 " if i==1 else "🥈 " if i==2 else "🥉 " if i==3 else ""
        text += f"{medal}{i}. {name} — уровень {level} ({xp} XP)\n"
    await update.message.reply_text(text, parse_mode="Markdown")

# ---------- ЭКСПОРТ ----------
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

# ---------- ПОМОЩЬ ----------
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(get_text(user_id, 'help_text'))

# ---------- ОБРАБОТЧИКИ ----------
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
    elif data == "edit_reminder":
        await edit_reminder_prompt(update, context)
    elif data == "edit_cancel":
        await edit_cancel(update, context)
    elif data.startswith("editday_"):
        await edit_days_callback(update, context)
    elif data == "editdays_save":
        await edit_days_save(update, context)
    elif data == "add_time_prompt":
        await add_time_prompt(update, context)
    elif data == "skip_time":
        await skip_time(update, context)
    else:
        await query.answer()

# ========== ЗАПУСК ==========
def main():
    init_db()
    app = Application.builder().token(TOKEN).build()

    add_conv = ConversationHandler(
        entry_points=[CommandHandler("add", add_habit_start), MessageHandler(filters.Regex("➕ Добавить привычку"), add_habit_start)],
        states={
            TYPING_HABIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_habit_name)],
            CHOOSING_HABIT_DAYS: [CallbackQueryHandler(days_callback, pattern="^day_|days_done$")],
        },
        fallbacks=[CommandHandler("cancel", lambda u,c: ConversationHandler.END)],
        allow_reentry=True
    )
    del_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("🗑 Удалить привычку"), delete_habit_start)],
        states={CONFIRM_DELETE: [CallbackQueryHandler(confirm_delete, pattern="^del_|cancel_del$")]},
        fallbacks=[CommandHandler("cancel", lambda u,c: ConversationHandler.END)],
        allow_reentry=True
    )
    edit_conv = ConversationHandler(
        entry_points=[CommandHandler("edit", edit_habit_start), MessageHandler(filters.Regex("✏️ Редактировать"), edit_habit_start)],
        states={
            EDIT_SELECT: [CallbackQueryHandler(edit_select, pattern="^edith_|edit_name|edit_days|edit_reminder|edit_cancel$")],
            EDIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_name_save)],
            EDIT_DAYS: [CallbackQueryHandler(edit_days_callback, pattern="^editday_|editdays_save$")],
            EDIT_REMINDER_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_reminder_save)],
        },
        fallbacks=[CommandHandler("cancel", lambda u,c: ConversationHandler.END)],
        allow_reentry=True
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("export", export_csv))
    app.add_handler(add_conv)
    app.add_handler(del_conv)
    app.add_handler(edit_conv)
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    print("✅ Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
