import logging,sqlite3,time as ttime
from datetime import datetime,timedelta
from telegram import Update,InlineKeyboardButton,InlineKeyboardMarkup,ReplyKeyboardMarkup,BotCommand
from telegram.ext import Application,CommandHandler,CallbackQueryHandler,MessageHandler,filters
try:
    import matplotlib;matplotlib.use("Agg");import matplotlib.pyplot as plt;HAS_PLT=True
except:HAS_PLT=False
BOT_TOKEN="8717114083:AAEgNViVX7h0ea6pHc4Awp76h0gF0eJbcQg"
MENU_KB=ReplyKeyboardMarkup([["📋 Сегодня","📊 Статистика"],["🔔 Напоминание","⚙️ Настройки"],["➕ Добавить","🗑 Удалить"],["🏆 Достижения","❓ Помощь"]],resize_keyboard=True)
DEFAULT_HABITS=["💧 Пить воду","🏃 Зарядка","📖 Чтение","🧘 Медитация","😴 Сон до 23:00","🥗 Здоровое питание","📵 Без телефона 1ч","✍️ Дневник","🚶 Прогулка","💊 Витамины"]
logging.basicConfig(level=logging.INFO)
timers={}
def init_db():
    c=sqlite3.connect("habits.db");e=c.cursor()
    e.execute("CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY,username TEXT,reminder_hour INTEGER DEFAULT -1,reminder_min INTEGER DEFAULT 0)")
    e.execute("CREATE TABLE IF NOT EXISTS habits(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,name TEXT,active INTEGER DEFAULT 1)")
    e.execute("CREATE TABLE IF NOT EXISTS completions(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,habit_id INTEGER,date TEXT,minutes INTEGER DEFAULT 0,UNIQUE(habit_id,date))")
    e.execute("CREATE TABLE IF NOT EXISTS achievements(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,ach_id TEXT,date TEXT,UNIQUE(user_id,ach_id))")
    c.commit();c.close()
def db(q,p=(),f=False,f1=False):
    c=sqlite3.connect("habits.db");e=c.cursor();e.execute(q,p)
    if f1:r=e.fetchone()
    elif f:r=e.fetchall()
    else:r=e.lastrowid
    c.commit();c.close();return r
def get_habits(u):return db("SELECT id,name FROM habits WHERE user_id=? AND active=1",(u,),f=True)
def get_today(u):
    d=datetime.now().strftime("%Y-%m-%d")
    return db("SELECT h.id,h.name,CASE WHEN c.id IS NOT NULL THEN 1 ELSE 0 END,COALESCE(c.minutes,0) FROM habits h LEFT JOIN completions c ON h.id=c.habit_id AND c.date=? WHERE h.user_id=? AND h.active=1",(d,u),f=True)
def do_toggle(u,h):
    d=datetime.now().strftime("%Y-%m-%d")
    x=db("SELECT id FROM completions WHERE habit_id=? AND date=?",(h,d),f1=True)
    if x:db("DELETE FROM completions WHERE id=?",(x[0],));return False
    db("INSERT INTO completions(user_id,habit_id,date,minutes)VALUES(?,?,?,0)",(u,h,d));return True
def set_time(u,h,m):
    d=datetime.now().strftime("%Y-%m-%d")
    x=db("SELECT id FROM completions WHERE habit_id=? AND date=?",(h,d),f1=True)
    if x:db("UPDATE completions SET minutes=? WHERE id=?",(m,x[0]))
    else:db("INSERT INTO completions(user_id,habit_id,date,minutes)VALUES(?,?,?,?)",(u,h,d,m))
def get_streak(u,h):
    s=0;d=datetime.now()
    while True:
        r=db("SELECT id FROM completions WHERE habit_id=? AND date=?",(h,d.strftime("%Y-%m-%d")),f1=True)
        if r:s+=1;d-=timedelta(days=1)
        else:break
    return s
def get_max_streak(u):
    mx=0
    for h,n in get_habits(u):
        s=get_streak(u,h)
        if s>mx:mx=s
    return mx
def get_total(u):
    r=db("SELECT COUNT(*) FROM completions WHERE user_id=?",(u,),f1=True);return r[0] if r else 0
def get_perfect(u):
    h=get_habits(u)
    if not h:return 0
    n=len(h);rows=db("SELECT date,COUNT(*) FROM completions WHERE user_id=? GROUP BY date",(u,),f=True)
    return sum(1 for d,c in rows if c>=n)
def fmt_min(m):
    if m<60:return str(m)+" мин"
    h=m//60;mm=m%60
    if mm==0:return str(h)+" ч"
    return str(h)+" ч "+str(mm)+" мин"
def build_pick_kb(u):
    ex=[h[1] for h in get_habits(u)];kb=[]
    for idx,h in enumerate(DEFAULT_HABITS):
        if h in ex:kb.append([InlineKeyboardButton("✅ "+h,callback_data="up_"+str(idx))])
        else:kb.append([InlineKeyboardButton("⬜ "+h,callback_data="pk_"+str(idx))])
    kb.append([InlineKeyboardButton("✅ Готово",callback_data="done_pick")]);return kb
def clear_state(context):
    for key in ["ct","rem_custom","adding","deleting"]:
        context.user_data.pop(key,None)
async def send_reminder(context):
    now=datetime.now()
    users=db("SELECT user_id,reminder_hour,reminder_min FROM users WHERE reminder_hour>=0",(),f=True)
    for uid,rh,rm in users:
        if now.hour==rh and now.minute==rm:
            habits=get_today(uid)
            if not habits:continue
            done=sum(1 for _,_,c,_ in habits if c);total=len(habits)
            if done>=total:continue
            try:await context.bot.send_message(chat_id=uid,text="🔔 Напоминание!\nОсталось: "+str(total-done)+"/"+str(total)+"\nНажми 📋 Сегодня!",reply_markup=MENU_KB)
            except:pass
async def post_init(app):
    await app.bot.set_my_commands([BotCommand("start","Начать"),BotCommand("today","Сегодня"),BotCommand("stats","Статистика"),BotCommand("help","Помощь")])
    app.job_queue.run_repeating(send_reminder,interval=60,first=10)
async def cmd_start(update,context):
    u=update.effective_user.id;clear_state(context)
    db("INSERT OR IGNORE INTO users(user_id,username)VALUES(?,?)",(u,update.effective_user.username or ""))
    await update.message.reply_text("👋 Выбери привычки:",reply_markup=InlineKeyboardMarkup(build_pick_kb(u)))
async def show_today(msg,u,edit=False,timers_dict=None):
    st=get_today(u)
    if not st:
        if edit:
            try:await msg.edit_message_text("Нет привычек! /start")
            except:pass
        else:await msg.reply_text("Нет привычек! /start",reply_markup=MENU_KB)
        return
    t="📋 Сегодня:\n\n";kb=[];done=0
    for hid,hn,comp,mins in st:
        timer_key=str(u)+"_"+str(hid)
        timer_running=timer_key in timers
        if comp:
            s=get_streak(u,hid);line="✅ "+hn
            if s>1:line+=" 🔥"+str(s)
            if mins>0:line+=" ("+fmt_min(mins)+")"
            if timer_running:line+=" ⏱️▶️"
            done+=1
        else:line="⬜ "+hn
        t+=line+"\n"
        mark="✅" if comp else "⬜"
        row=[InlineKeyboardButton(mark+" "+hn,callback_data="t_"+str(hid))]
        if comp:
            if timer_running:
                row.append(InlineKeyboardButton("⏹ Стоп",callback_data="tstop_"+str(hid)))
            else:
                row.append(InlineKeyboardButton("▶️ Таймер",callback_data="tstart_"+str(hid)))
        kb.append(row)
    tot=len(st);pct=round((done/tot)*100) if tot else 0
    bar="🟩"*(pct//10)+"⬜"*(10-pct//10)
    t+="\n"+bar+" "+str(pct)+"%\n"+str(done)+"/"+str(tot)
    if done==tot and tot>0:t+="\n\n🎉 ИДЕАЛЬНЫЙ ДЕНЬ!"
    if edit:
        try:await msg.edit_message_text(t,reply_markup=InlineKeyboardMarkup(kb))
        except:pass
    else:await msg.reply_text(t,reply_markup=InlineKeyboardMarkup(kb))
async def cmd_today(update,context):
    clear_state(context);await show_today(update.message,update.effective_user.id)
async def cmd_stats(update,context):
    clear_state(context)
    kb=[[InlineKeyboardButton("📅 7 дн",callback_data="stats_7"),InlineKeyboardButton("📅 30 дн",callback_data="stats_30")],[InlineKeyboardButton("📊 График",callback_data="chart")]]
    await update.message.reply_text("📊 Статистика:",reply_markup=InlineKeyboardMarkup(kb))
async def cmd_remind(update,context):
    clear_state(context);u=update.effective_user.id
    r=db("SELECT reminder_hour,reminder_min FROM users WHERE user_id=?",(u,),f1=True)
    cur_h=r[0] if r and r[0]>=0 else None;cur_m=r[1] if r and r[0]>=0 else 0
    kb=[];row=[]
    for h in range(6,24):
        label=("✅"+str(h)+":00") if cur_h==h else str(h)+":00"
        row.append(InlineKeyboardButton(label,callback_data="rem_"+str(h)))
        if len(row)==4:kb.append(row);row=[]
    if row:kb.append(row)
    kb.append([InlineKeyboardButton("✍️ Точное время",callback_data="rem_custom")])
    kb.append([InlineKeyboardButton("🔕 Выключить",callback_data="rem_off")])
    status="🔔 "+str(cur_h)+":"+str(cur_m).zfill(2) if cur_h is not None else "🔕 Выключено"
    await update.message.reply_text("🔔 Напоминание\n\n"+status+"\n\nВыбери час или нажми Точное время:",reply_markup=InlineKeyboardMarkup(kb))
async def cmd_settings(update,context):
    clear_state(context)
    kb=[[InlineKeyboardButton("🔄 Выбрать привычки",callback_data="reselect")],[InlineKeyboardButton("💣 Сбросить всё",callback_data="reset_ask")]]
    await update.message.reply_text("⚙️ Настройки:",reply_markup=InlineKeyboardMarkup(kb))
async def cmd_ach(update,context):
    clear_state(context);u=update.effective_user.id
    ms=get_max_streak(u);tc=get_total(u);pf=get_perfect(u)
    t="🏆 Достижения:\n\n"
    achs=[("🌱","Росток","3 дня подряд","streak",3),("⚡","Разгон","7 дней подряд","streak",7),("🔥","В огне","14 дней","streak",14),("⭐","Звезда","21 день","streak",21),("💎","Бриллиант","30 дней","streak",30),("1️⃣","Первый шаг","1 выполнение","total",1),("🔟","Десятка","10 выполнений","total",10),("💯","Сотня","100 выполнений","total",100),("💪","Идеальный день","Все за день","perfect",1)]
    cnt=0
    for i,n,d,tp,v in achs:
        if tp=="streak":val=ms
        elif tp=="total":val=tc
        else:val=pf
        if val>=v:t+="✅ "+i+" "+n+"\n";cnt+=1
        else:t+="🔒 "+i+" "+n+" (ещё "+str(v-val)+")\n"
    t+="\n"+str(cnt)+"/"+str(len(achs))
    await update.message.reply_text(t,reply_markup=MENU_KB)
async def cmd_help(update,context):
    clear_state(context)
    await update.message.reply_text("📖 Как пользоваться:\n\n📋 Сегодня — отмечай привычки\n▶️ Таймер — засекает время\n⏹ Стоп — останавливает таймер\n📊 Статистика — прогресс\n🏆 Достижения — награды\n🔔 Напоминание — в любое время\n➕ Добавить — новая привычка\n🗑 Удалить — убрать привычку\n⚙️ Настройки",reply_markup=MENU_KB)
async def make_chart(u):
    if not HAS_PLT:return None
    h=get_habits(u)
    if not h:return None
    end=datetime.now();start=end-timedelta(days=29);dates=[];pcts=[]
    for i in range(30):
        d=start+timedelta(days=i);ds=d.strftime("%Y-%m-%d")
        r=db("SELECT COUNT(*) FROM completions WHERE user_id=? AND date=?",(u,ds),f1=True)
        done=r[0] if r else 0;pct=round((done/len(h))*100);dates.append(d);pcts.append(pct)
    fig,ax=plt.subplots(figsize=(10,5))
    colors=["#2ecc71" if p>=80 else "#f39c12" if p>=50 else "#e74c3c" if p>0 else "#bdc3c7" for p in pcts]
    ax.bar(dates,pcts,color=colors,width=0.8);ax.set_ylim(0,110);ax.set_ylabel("%")
    ax.set_title("30 дней");fig.autofmt_xdate();plt.tight_layout()
    p="/tmp/chart.png";plt.savefig(p,dpi=150);plt.close();return p
async def handle_cb(update,context):
    q=update.callback_query;await q.answer();u=q.from_user.id;d=q.data
    if d.startswith("pk_"):
        idx=int(d[3:])
        if idx<len(DEFAULT_HABITS):db("INSERT INTO habits(user_id,name)VALUES(?,?)",(u,DEFAULT_HABITS[idx]))
        try:await q.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(build_pick_kb(u)))
        except:pass
    elif d.startswith("up_"):
        idx=int(d[3:])
        if idx<len(DEFAULT_HABITS):
            name=DEFAULT_HABITS[idx]
            for hid,hn in get_habits(u):
                if hn==name:db("UPDATE habits SET active=0 WHERE id=?",(hid,));break
        try:await q.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(build_pick_kb(u)))
        except:pass
    elif d=="done_pick":
        h=get_habits(u)
        try:await q.message.edit_message_text("✅ Выбрано: "+str(len(h))+" привычек!\n\nНажми 📋 Сегодня чтобы начать!")
        except:pass
        await q.message.reply_text("🎉 Готово! Используй меню внизу:",reply_markup=MENU_KB)
    elif d.startswith("t_"):
        hid=int(d[2:]);do_toggle(u,hid);await show_today(q.message,u,edit=True)
    elif d.startswith("tstart_"):
        hid=int(d[7:]);timer_key=str(u)+"_"+str(hid)
        timers[timer_key]=ttime.time()
        await show_today(q.message,u,edit=True)
    elif d.startswith("tstop_"):
        hid=int(d[6:]);timer_key=str(u)+"_"+str(hid)
        if timer_key in timers:
            elapsed=int((ttime.time()-timers[timer_key])/60)
            if elapsed<1:elapsed=1
            del timers[timer_key]
            set_time(u,hid,elapsed)
        await show_today(q.message,u,edit=True)
    elif d.startswith("tm_"):
        hid=int(d[3:]);kb=[];row=[]
        for m in [5,10,15,20,30,45,60,90,120]:
            lb=str(m)+" мин" if m<60 else str(m//60)+" ч"
            row.append(InlineKeyboardButton(lb,callback_data="sm_"+str(hid)+"_"+str(m)))
            if len(row)==3:kb.append(row);row=[]
        if row:kb.append(row)
        kb.append([InlineKeyboardButton("✍️ Своё",callback_data="ct_"+str(hid))])
        kb.append([InlineKeyboardButton("⬅️",callback_data="back")])
        try:await q.message.edit_message_text("⏱ Сколько?",reply_markup=InlineKeyboardMarkup(kb))
        except:pass
    elif d.startswith("sm_"):
        parts=d[3:].split("_");hid=int(parts[0]);mins=int(parts[1])
        set_time(u,hid,mins);await show_today(q.message,u,edit=True)
    elif d.startswith("ct_"):
        context.user_data["ct"]=int(d[3:])
        try:await q.message.edit_message_text("✍️ Напиши минуты числом:")
        except:pass
    elif d=="back":await show_today(q.message,u,edit=True)
    elif d.startswith("stats_"):
        days=int(d[6:]);hb=get_habits(u)
        if not hb:
            try:await q.message.edit_message_text("Нет привычек!")
            except:pass
            return
        end=datetime.now();start=end-timedelta(days=days-1)
        r=db("SELECT COUNT(*) FROM completions WHERE user_id=? AND date BETWEEN ? AND ?",(u,start.strftime("%Y-%m-%d"),end.strftime("%Y-%m-%d")),f1=True)
        comp=r[0] if r else 0;pos=len(hb)*days;pct=round((comp/pos)*100) if pos else 0
        bar="🟩"*(pct//10)+"⬜"*(10-pct//10)
        t="📊 "+str(days)+" дней:\n\n"+bar+" "+str(pct)+"%\n"+str(comp)+"/"+str(pos)+"\n"
        for hid,hn in hb:t+="\n"+hn+" 🔥"+str(get_streak(u,hid))
        try:await q.message.edit_message_text(t)
        except:pass
    elif d=="chart":
        try:await q.message.edit_message_text("📊 Рисую...")
        except:pass
        p=await make_chart(u)
        if p:await q.message.reply_photo(photo=open(p,"rb"),reply_markup=MENU_KB)
        else:await q.message.reply_text("Нет данных!",reply_markup=MENU_KB)
    elif d.startswith("rem_"):
        if d=="rem_off":
            db("UPDATE users SET reminder_hour=-1,reminder_min=0 WHERE user_id=?",(u,))
            try:await q.message.edit_message_text("🔕 Напоминания выключены!")
            except:pass
        elif d=="rem_custom":
            context.user_data["rem_custom"]=True
            try:await q.message.edit_message_text("✍️ Напиши время напоминания в формате ЧЧ:ММ\n\nНапример: 20:30 или 7:15 или 21:45\n\nПросто напиши время сообщением:")
            except:pass
        else:
            h=int(d[4:]);db("UPDATE users SET reminder_hour=?,reminder_min=0 WHERE user_id=?",(h,u))
            try:await q.message.edit_message_text("🔔 Напоминание установлено на "+str(h)+":00 ✅\n\nБот напомнит тебе каждый день!")
            except:pass
    elif d=="reselect":
        try:await q.message.edit_message_text("📋 Выбери:",reply_markup=InlineKeyboardMarkup(build_pick_kb(u)))
        except:pass
    elif d=="reset_ask":
        kb=[[InlineKeyboardButton("✅ Да удалить",callback_data="reset_yes"),InlineKeyboardButton("❌ Нет",callback_data="reset_no")]]
        try:await q.message.edit_message_text("💣 Удалить ВСЕ данные?",reply_markup=InlineKeyboardMarkup(kb))
        except:pass
    elif d=="reset_yes":
        for tbl in ["completions","habits","achievements","users"]:db("DELETE FROM "+tbl+" WHERE user_id=?",(u,))
        try:await q.message.edit_message_text("🗑 Всё удалено! Нажми /start")
        except:pass
    elif d=="reset_no":
        try:await q.message.edit_message_text("👍 Отменено!")
        except:pass
        await q.message.reply_text("📱",reply_markup=MENU_KB)
    elif d.startswith("dh_"):
        hid=int(d[3:]);h=db("SELECT name FROM habits WHERE id=?",(hid,),f1=True);nm=h[0] if h else "?"
        db("UPDATE habits SET active=0 WHERE id=?",(hid,));db("DELETE FROM completions WHERE habit_id=?",(hid,))
        try:await q.message.edit_message_text("✅ Привычка '"+nm+"' удалена!")
        except:pass
        await q.message.reply_text("📱",reply_markup=MENU_KB)
async def handle_txt(update,context):
    u=update.effective_user.id;t=update.message.text
    if context.user_data.get("ct"):
        try:
            m=int(t);set_time(u,context.user_data["ct"],m);clear_state(context)
            await update.message.reply_text("✅ Записано: "+fmt_min(m),reply_markup=MENU_KB)
        except:await update.message.reply_text("❌ Напиши число!")
        return
    if context.user_data.get("rem_custom"):
        try:
            parts=t.replace(".",":").replace(" ",":").split(":")
            h=int(parts[0]);m=int(parts[1]) if len(parts)>1 else 0
            if 0<=h<=23 and 0<=m<=59:
                db("UPDATE users SET reminder_hour=?,reminder_min=? WHERE user_id=?",(h,m,u))
                clear_state(context)
                await update.message.reply_text("🔔 Напоминание установлено на "+str(h)+":"+str(m).zfill(2)+" ✅\n\nБот напомнит тебе каждый день в это время!",reply_markup=MENU_KB)
            else:await update.message.reply_text("❌ Неверное время! Напиши от 0:00 до 23:59")
        except:await update.message.reply_text("❌ Напиши время как 20:30")
        return
    if context.user_data.get("adding"):
        db("INSERT INTO habits(user_id,name)VALUES(?,?)",(u,t));clear_state(context)
        await update.message.reply_text("✅ Привычка '"+t+"' добавлена!\n\nНажми 📋 Сегодня чтобы увидеть.",reply_markup=MENU_KB);return
    if context.user_data.get("deleting"):
        clear_state(context)
        await update.message.reply_text("Выбери привычку из списка выше!",reply_markup=MENU_KB);return
    if "Сегодня" in t:clear_state(context);await show_today(update.message,u)
    elif "Статистика" in t:clear_state(context);await cmd_stats(update,context)
    elif "Напоминание" in t:clear_state(context);await cmd_remind(update,context)
    elif "Настройки" in t:clear_state(context);await cmd_settings(update,context)
    elif "Добавить" in t:clear_state(context);context.user_data["adding"]=True;await update.message.reply_text("✍️ Напиши название новой привычки:")
    elif "Удалить" in t:
        clear_state(context);hb=get_habits(u)
        if not hb:await update.message.reply_text("Нет привычек для удаления!",reply_markup=MENU_KB);return
        kb=[[InlineKeyboardButton("🗑 "+hn,callback_data="dh_"+str(hid))] for hid,hn in hb]
        await update.message.reply_text("🗑 Какую привычку удалить?",reply_markup=InlineKeyboardMarkup(kb))
    elif "Достижения" in t:clear_state(context);await cmd_ach(update,context)
    elif "Помощь" in t:clear_state(context);await cmd_help(update,context)
    else:clear_state(context);await update.message.reply_text("Используй кнопки меню 👇",reply_markup=MENU_KB)
def main():
    init_db();print("🚀 Бот запущен!")
    app=Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start",cmd_start))
    app.add_handler(CommandHandler("today",cmd_today))
    app.add_handler(CommandHandler("stats",cmd_stats))
    app.add_handler(CommandHandler("reminder",cmd_remind))
    app.add_handler(CommandHandler("settings",cmd_settings))
    app.add_handler(CommandHandler("achievements",cmd_ach))
    app.add_handler(CommandHandler("help",cmd_help))
    app.add_handler(CallbackQueryHandler(handle_cb))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,handle_txt))
    app.run_polling()
if __name__=="__main__":main()
