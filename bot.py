import logging,sqlite3,os,time as tt
from datetime import datetime,timedelta
from telegram import Update,InlineKeyboardButton as B,InlineKeyboardMarkup as M,ReplyKeyboardMarkup as R,BotCommand
from telegram.ext import Application,CommandHandler,CallbackQueryHandler,MessageHandler,filters
BOT_TOKEN=os.environ.get("BOT_TOKEN","")
MN=R([["📋 Сегодня","📊 Статистика"],["🔔 Напоминание","📆 Календарь"],["➕ Добавить","🗑 Удалить"],["🏆 Достижения","⚙️ Настройки"],["❓ Помощь"]],resize_keyboard=True)
DH=["💧 Пить воду","🏃 Зарядка","📖 Чтение","🧘 Медитация","😴 Сон до 23:00","🥗 Здоровое питание","📵 Без телефона 1ч","✍️ Дневник","🚶 Прогулка","💊 Витамины"]
DR=["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]
logging.basicConfig(level=logging.INFO)
def init_db():
 c=sqlite3.connect("h.db");e=c.cursor()
 e.execute("CREATE TABLE IF NOT EXISTS u(uid INTEGER PRIMARY KEY,un TEXT,rh INTEGER DEFAULT -1,rm INTEGER DEFAULT 0)")
 e.execute("CREATE TABLE IF NOT EXISTS h(id INTEGER PRIMARY KEY AUTOINCREMENT,uid INTEGER,name TEXT,act INTEGER DEFAULT 1,days TEXT DEFAULT '0123456')")
 e.execute("CREATE TABLE IF NOT EXISTS c(id INTEGER PRIMARY KEY AUTOINCREMENT,uid INTEGER,hid INTEGER,date TEXT,mins INTEGER DEFAULT 0,UNIQUE(hid,date))")
 try:e.execute("ALTER TABLE h ADD COLUMN days TEXT DEFAULT '0123456'")
 except:pass
 c.commit();c.close()
def q(s,p=(),f=False,f1=False):
 c=sqlite3.connect("h.db");e=c.cursor();e.execute(s,p)
 if f1:r=e.fetchone()
 elif f:r=e.fetchall()
 else:r=e.lastrowid
 c.commit();c.close();return r
def gh(u):return q("SELECT id,name FROM h WHERE uid=? AND act=1",(u,),f=True)
def ghf(u):return q("SELECT id,name,days FROM h WHERE uid=? AND act=1",(u,),f=True)
def gt(u):
 d=datetime.now().strftime("%Y-%m-%d");w=str(datetime.now().weekday())
 return q("SELECT h.id,h.name,CASE WHEN c.id IS NOT NULL THEN 1 ELSE 0 END,COALESCE(c.mins,0) FROM h LEFT JOIN c ON h.id=c.hid AND c.date=? WHERE h.uid=? AND h.act=1 AND h.days LIKE '%'||?||'%'",(d,u,w),f=True)
def tog(u,hid):
 d=datetime.now().strftime("%Y-%m-%d");x=q("SELECT id FROM c WHERE hid=? AND date=?",(hid,d),f1=True)
 if x:q("DELETE FROM c WHERE id=?",(x[0],));return False
 q("INSERT INTO c(uid,hid,date,mins)VALUES(?,?,?,0)",(u,hid,d));return True
def stm(u,hid,m):
 d=datetime.now().strftime("%Y-%m-%d");x=q("SELECT id FROM c WHERE hid=? AND date=?",(hid,d),f1=True)
 if x:q("UPDATE c SET mins=? WHERE id=?",(m,x[0]))
 else:q("INSERT INTO c(uid,hid,date,mins)VALUES(?,?,?,?)",(u,hid,d,m))
def stk(u,hid):
 s=0;d=datetime.now();dc=q("SELECT days FROM h WHERE id=?",(hid,),f1=True);hd=dc[0] if dc and dc[0] else "0123456"
 while True:
  if str(d.weekday()) in hd:
   r=q("SELECT id FROM c WHERE hid=? AND date=?",(hid,d.strftime("%Y-%m-%d")),f1=True)
   if r:s+=1
   else:break
  d-=timedelta(days=1)
  if s>365:break
 return s
def mxs(u):
 mx=0
 for hid,n in gh(u):
  s=stk(u,hid)
  if s>mx:mx=s
 return mx
def ttl(u):r=q("SELECT COUNT(*) FROM c WHERE uid=?",(u,),f1=True);return r[0] if r else 0
def prf(u):
 rows=q("SELECT date FROM c WHERE uid=? GROUP BY date",(u,),f=True);p=0
 for(ds,)in rows:
  w=str(datetime.strptime(ds,"%Y-%m-%d").weekday())
  t=q("SELECT COUNT(*) FROM h WHERE uid=? AND act=1 AND days LIKE '%'||?||'%'",(u,w),f1=True)
  d=q("SELECT COUNT(*) FROM c WHERE uid=? AND date=?",(u,ds),f1=True)
  if t and d and t[0]>0 and d[0]>=t[0]:p+=1
 return p
def gmt(u,hid):
 s=datetime.now().replace(day=1).strftime("%Y-%m-%d");e=datetime.now().strftime("%Y-%m-%d")
 r=q("SELECT SUM(mins) FROM c WHERE uid=? AND hid=? AND date BETWEEN ? AND ?",(u,hid,s,e),f1=True)
 return r[0] if r and r[0] else 0
def fm(m):
 if m<60:return str(m)+" мин"
 h=m//60;mm=m%60
 return str(h)+" ч" if mm==0 else str(h)+" ч "+str(mm)+" мин"
def dtx(ds):
 if not ds or ds=="0123456" or len(ds)>=7:return "ежедневно"
 return ",".join(DR[int(d)] for d in sorted(ds) if d.isdigit() and int(d)<7)
def bpk(u):
 ex=[x[1] for x in gh(u)];kb=[]
 for i,h in enumerate(DH):
  if h in ex:kb.append([B("✅ "+h,callback_data="up_"+str(i))])
  else:kb.append([B("⬜ "+h,callback_data="pk_"+str(i))])
 kb.append([B("✅ Готово",callback_data="dp")]);return kb
def cs(ctx):
 for k in["ct","rc","adding"]:ctx.user_data.pop(k,None)
async def srem(context):
 now=datetime.now()
 for uid,rh,rm in q("SELECT uid,rh,rm FROM u WHERE rh>=0",(),f=True):
  if now.hour==rh and now.minute==rm:
   habits=gt(uid)
   if not habits:continue
   dn=sum(1 for _,_,cc,_ in habits if cc);tl=len(habits)
   if dn>=tl:continue
   try:await context.bot.send_message(chat_id=uid,text="🔔 Осталось: "+str(tl-dn)+"/"+str(tl),reply_markup=MN)
   except:pass
async def post_init(app):
 await app.bot.set_my_commands([BotCommand("start","Начать"),BotCommand("today","Сегодня"),BotCommand("stats","Статистика"),BotCommand("calendar","Календарь"),BotCommand("help","Помощь")])
 app.job_queue.run_repeating(srem,interval=60,first=10)
async def cmd_start(up,ctx):
 u=up.effective_user.id;cs(ctx);q("INSERT OR IGNORE INTO u(uid,un)VALUES(?,?)",(u,up.effective_user.username or ""))
 await up.message.reply_text("👋 Привет! Выбери привычки:",reply_markup=M(bpk(u)))
async def show_today(msg,u,edit=False):
 st=gt(u)
 if not st:
  tx="📋 Нет привычек на сегодня!\nНажми ➕ Добавить"
  if edit:
   try:await msg.edit_text(tx)
   except:pass
  else:await msg.reply_text(tx,reply_markup=MN)
  return
 t="📋⚙️ Настройки:",reply_markup=M(kb))
async def cmd_ach(up,ctx):
 cs(ctx);u=up.effective_user.id;ms=mxs(u);tc=ttl(u);pf=prf(u)
 t="🏆 Достижения:\n\n";achs=[("🌱","Росток","s",3),("⚡","Разгон","s",7),("🔥","В огне","s",14),("⭐","Звезда","s",21),("💎","Бриллиант","s",30),("1️⃣","Первый шаг","t",1),("🔟","Десятка","t",10),("💯","Сотня","t",100),("💪","Идеальный день","p",1)];cnt=0
 for i,n,tp,v in achs:
  val=ms if tp=="s" else tc if tp=="t" else pf
  if val>=v:t+="✅ "+i+" "+n+"\n";cnt+=1
  else:t+="🔒 "+i+" "+n+" (ещё "+str(v-val)+")\n"
 t+="\n"+str(cnt)+"/"+str(len(achs));await up.message.reply_text(t,reply_markup=MN)
async def cmd_help(up,ctx):
 cs(ctx);await up.message.reply_text("📋 Сегодня — список привычек\n✅ — отметить выполнение\n⏱ Записать время — сколько делал\n📆 Календарь — неделя\n📊 Статистика — прогресс\n🔔 Напоминание — настроить\n➕ Добавить / 🗑 Удалить\n🏆 Достижения — награды",reply_markup=MN)
async def handle_cb(up,ctx):
 cq=up.callback_query;await cq.answer();u=cq.from_user.id;d=cq.data
 if d.startswith("pk_"):
  i=int(d[3:])
  if i<len(DH):q("INSERT INTO h(uid,name,days)VALUES(?,?,?)",(u,DH[i],"0123456"))
  try:await cq.message.edit_reply_markup(reply_markup=M(bpk(u)))
  except:pass
 elif d.startswith("up_"):
  i=int(d[3:])
  if i<len(DH):
   for hid,hn in gh(u):
    if hn==DH[i]:q("UPDATE h SET act=0 WHERE id=?",(hid,));break
  try:await cq.message.edit_reply_markup(reply_markup=M(bpk(u)))
  except:pass
 elif d=="dp":
  try:await cq.message.edit_text("✅ Выбрано: "+str(len(gh(u)))+" привычек!")
  except:pass
  await cq.message.reply_text("🎉 Готово! Жми 📋 Сегодня",reply_markup=MN)
 elif d.startswith("t_"):tog(u,int(d[2:]));await show_today(cq.message,u,edit=True)
 elif d.startswith("mn_"):
  hid=int(d[3:]);hn=q("SELECT name FROM h WHERE id=?",(hid,),f1=True)
  cur=gmt(u,hid);tx="⏱ "+(hn[0] if hn else "?")+"\n📅 За месяц: "+fm(cur)+"\n\nВыбери время:"
  kb=[[B("15 мин",callback_data="sm_"+str(hid)+"_15"),B("30 мин",callback_data="sm_"+str(hid)+"_30"),B("45 мин",callback_data="sm_"+str(hid)+"_45")],[B("1 ч",callback_data="sm_"+str(hid)+"_60"),B("1.5 ч",callback_data="sm_"+str(hid)+"_90"),B("2 ч",callback_data="sm_"+str(hid)+"_120")],[B("3 ч",callback_data="sm_"+str(hid)+"_180"),B("4 ч",callback_data="sm_"+str(hid)+"_240"),B("5 ч",callback_data="sm_"+str(hid)+"_300")],[B("✍️ Ввести своё",callback_data="ct_"+str(hid))],[B("⬅️ Назад",callback_data="bk")]]
  try:await cq.message.edit_text(tx,reply_markup=M(kb))
  except:pass
 elif d.startswith("sm_"):
  p=d[3:].split("_");hid=int(p[0]);mins=int(p[1]);stm(u,hid,mins)
  hn=q("SELECT name FROM h WHERE id=?",(hid,),f1=True)
  try:await cq.message.edit_text("✅ "+(hn[0] if hn else "?")+": "+fm(mins)+"\n📅 За месяц: "+fm(gmt(u,hid)))
  except:pass
  await show_today(cq.message,u,edit=False)
 elif d.startswith("ct_"):
  ctx.user_data["ct"]=int(d[3:])
  try:await cq.message.edit_text("✍️ Напиши время:\n90 = 90 минут\n1:30 = 1 час 30 мин")
  except:pass
 elif d=="bk":cs(ctx);await show_today(cq.message,u,edit=True)
 elif d.startswith("cl_"):await show_cal(cq.message,u,int(d[3:]),edit=True)
 elif d=="s7" or d=="s30":
  days=7 if d=="s7" else 30;hb=gh(u)
  if not hb:
   try:await cq.message.edit_text("Нет привычек!")
   except:pass
   return
  tp=0;td=0;end=datetime.now();start=end-timedelta(days=days-1)
  for i in range(days):
   day=start+timedelta(days=i);ds=day.strftime("%Y-%m-%d");w=str(day.weekday())
   cn=q("SELECT COUNT(*) FROM h WHERE uid=? AND act=1 AND days LIKE '%'||?||'%'",(u,w),f1=True);tp+=cn[0] if cn else 0
   r=q("SELECT COUNT(*) FROM c WHERE uid=? AND date=?",(u,ds),f1=True);td+=r[0] if r else 0
  pct=round((td/tp)*100) if tp else 0;tx="📊 "+str(days)+" дней:\n"+"🟩"*(pct//10)+"⬜"*(10-pct//10)+" "+str(pct)+"%\n"
  for hid,hn in hb:tx+="\n"+hn+" 🔥"+str(stk(u,hid))
  try:await cq.message.edit_text(tx)
  except:pass
 elif d=="st":
  hb=gh(u)
  if not hb:
   try:await cq.message.edit_text("Нет привычек!")
   except:pass
   return
  tx="⏱ Время за месяц:\n\n";ta=0
  for hid,hn in hb:
   m=gmt(u,hid);ta+=m
   if m>0:tx+=hn+": "+fm(m)+"\n"
  tx+="\n📊 Всего: "+fm(ta)
  try:await cq.message.edit_text(tx)
  except:pass
 elif d=="ro":q("UPDATE u SET rh=-1 WHERE uid=?",(u,));await cq.message.edit_text("🔕 Выключено!")
 elif d=="rc":
  ctx.user_data["rc"]=True
  try:await cq.message.edit_text("✍️ Напиши время (например 20:30)")
  except:pass
 elif d.startswith("rm_"):
  h=int(d[3:]);q("UPDATE u SET rh=?,rm=0 WHERE uid=?",(h,u))
  try:await cq.message.edit_text("🔔 "+str(h)+":00 ✅")
  except:pass
 elif d=="rs":
  try:await cq.message.edit_text("📋 Выбери привычки:",reply_markup=M(bpk(u)))
  except:pass
 elif d=="ra":
  try:await cq.message.edit_text("💣 Точно удалить ВСЁ?",reply_markup=M([[B("✅ Да",callback_data="ry"),B("❌ Нет",callback_data="rn")]]))
  except:pass
 elif d=="ry":
  for t in["c","h","u"]:q("DELETE FROM "+t+" WHERE uid=?",(u,))
  try:await cq.message.edit_text("🗑 Удалено! Нажми /start")
  except:pass
 elif d=="rn":
  try:await cq.message.edit_text("👍 Отменено!")
  except:pass
  await cq.message.reply_text("📱",reply_markup=MN)
 elif d.startswith("dh_"):
  hid=int(d[3:]);r=q("SELECT name FROM h WHERE id=?",(hid,),f1=True);q("UPDATE h SET act=0 WHERE id=?",(hid,))
  try:await cq.message.edit_text("✅ "+(r[0] if r else "?")+" удалена!")
  except:pass
  await cq.message.reply_text("📱",reply_markup=MN)
async def handle_txt(up,ctx):
 u=up.effective_user.id;t=up.message.text
 if ctx.user_data.get("ct"):
  try:
   tx=t.replace(" ","").replace("ч",":").replace("м","")
   m=int(tx.split(":")[0])*60+int(tx.split(":")[1]) if ":" in tx else int(tx)
   hid=ctx.user_data["ct"];stm(u,hid,m);cs(ctx)
   await up.message.reply_text("✅ "+fm(m)+"\n📅 За месяц: "+fm(gmt(u,hid)),reply_markup=MN)
  except:await up.message.reply_text("❌ Напиши число! 90 или 1:30")
  return
 if ctx.user_data.get("rc"):
  try:
   p=t.replace(".",":").split(":");h=int(p[0]);m=int(p[1]) if len(p)>1 else 0
   if 0<=h<=23 and 0<=m<=59:q("UPDATE u SET rh=?,rm=? WHERE uid=?",(h,m,u));cs(ctx);await up.message.reply_text("🔔 "+str(h)+":"+str(m).zfill(2)+" ✅",reply_markup=MN)
   else:await up.message.reply_text("❌ От 0:00 до 23:59")
  except:await up.message.reply_text("❌ Напиши 20:30")
  return
 if ctx.user_data.get("adding"):
  q("INSERT INTO h(uid,name,days)VALUES(?,?,?)",(u,t,"0123456"));cs(ctx)
  await up.message.reply_text("✅ "+t+" добавлена!",reply_markup=MN);return
 if "Сегодня" in t:cs(ctx);await show_today(up.message,u)
 elif "Статистика" in t:await cmd_stats(up,ctx)
 elif "Напоминание" in t:await cmd_rem(up,ctx)
 elif "Календарь" in t:await show_cal(up.message,u)
 elif "Настройки" in t:await cmd_set(up,ctx)
 elif "Добавить" in t:cs(ctx);ctx.user_data["adding"]=True;await up.message.reply_text("✍️ Напиши название привычки:")
 elif "Удалить" in t:
  hb=gh(u)
  if not hb:await up.message.reply_text("Нет привычек!",reply_markup=MN);return
  await up.message.reply_text("🗑 Какую удалить?",reply_markup=M([[B("🗑 "+hn,callback_data="dh_"+str(hid))] for hid,hn in hb]))
 elif "Достижения" in t:await cmd_ach(up,ctx)
 elif "Помощь" in t:await cmd_help(up,ctx)
 else:await up.message.reply_text("Выбери из меню 👇",reply_markup=MN)
def main():
 init_db();print("🚀 Бот запущен!")
 app=Application.builder().token(BOT_TOKEN).post_init(post_init).build()
 for c,f in[("start",cmd_start),("today",cmd_today),("stats",cmd_stats),("reminder",cmd_rem),("settings",cmd_set),("achievements",cmd_ach),("calendar",cmd_cal),("help",cmd_help)]:app.add_handler(CommandHandler(c,f))
 app.add_handler(CallbackQueryHandler(handle_cb));app.add_handler(MessageHandler(filters.TEXT&~filters.COMMAND,handle_txt))
 app.run_polling()
if __name__=="__main__":main()
