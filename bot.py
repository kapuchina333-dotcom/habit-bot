import logging
import sqlite3
import os
from datetime import datetime,timedelta
from telegram import Update
from telegram import InlineKeyboardButton as B
from telegram import InlineKeyboardMarkup as M
from telegram import ReplyKeyboardMarkup as R
from telegram import BotCommand
from telegram.ext import Application
from telegram.ext import CommandHandler
from telegram.ext import CallbackQueryHandler
from telegram.ext import MessageHandler
from telegram.ext import filters

BOT_TOKEN=os.environ.get("BOT_TOKEN","")
logging.basicConfig(level=logging.INFO)

MN=R([
 ["📋 Сегодня","📊 Статистика"],
 ["🔔 Напоминание","📆 Календарь"],
 ["➕ Добавить","🗑 Удалить"],
 ["🏆 Достижения","⚙️ Настройки"],
 ["❓ Помощь"]
],resize_keyboard=True)

DH=[
 "💧 Пить воду",
 "🏃 Зарядка",
 "📖 Чтение",
 "🧘 Медитация",
 "😴 Сон до 23:00",
 "🥗 Здоровое питание",
 "📵 Без телефона 1ч",
 "✍️ Дневник",
 "🚶 Прогулка",
 "💊 Витамины"
]

DR=["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]

def init_db():
 c=sqlite3.connect("h.db")
 e=c.cursor()
 e.execute(
  "CREATE TABLE IF NOT EXISTS u("
  "uid INTEGER PRIMARY KEY,"
  "un TEXT,"
  "rh INTEGER DEFAULT -1,"
  "rm INTEGER DEFAULT 0)"
 )
 e.execute(
  "CREATE TABLE IF NOT EXISTS h("
  "id INTEGER PRIMARY KEY AUTOINCREMENT,"
  "uid INTEGER,"
  "name TEXT,"
  "act INTEGER DEFAULT 1,"
  "days TEXT DEFAULT '0123456')"
 )
 e.execute(
  "CREATE TABLE IF NOT EXISTS c("
  "id INTEGER PRIMARY KEY AUTOINCREMENT,"
  "uid INTEGER,"
  "hid INTEGER,"
  "date TEXT,"
  "mins INTEGER DEFAULT 0,"
  "UNIQUE(hid,date))"
 )
 try:
  e.execute(
   "ALTER TABLE h ADD COLUMN "
   "days TEXT DEFAULT '0123456'"
  )
 except:
  pass
 c.commit()
 c.close()

def q(s,p=(),f=False,f1=False):
 c=sqlite3.connect("h.db")
 e=c.cursor()
 e.execute(s,p)
 if f1:
  r=e.fetchone()
 elif f:
  r=e.fetchall()
 else:
  r=e.lastrowid
 c.commit()
 c.close()
 return r

def gh(u):
 return q(
  "SELECT id,name FROM h "
  "WHERE uid=? AND act=1",
  (u,),f=True
 )

def ghf(u):
 return q(
  "SELECT id,name,days FROM h "
  "WHERE uid=? AND act=1",
  (u,),f=True
 )

def gt(u):
 d=datetime.now().strftime("%Y-%m-%d")
 w=str(datetime.now().weekday())
 return q(
  "SELECT h.id,h.name,"
  "CASE WHEN c.id IS NOT NULL "
  "THEN 1 ELSE 0 END,"
  "COALESCE(c.mins,0) "
  "FROM h LEFT JOIN c "
  "ON h.id=c.hid AND c.date=? "
  "WHERE h.uid=? AND h.act=1 "
  "AND h.days LIKE '%'||?||'%'",
  (d,u,w),f=True
 )

def tog(u,hid):
 d=datetime.now().strftime("%Y-%m-%d")
 x=q(
  "SELECT id FROM c "
  "WHERE hid=? AND date=?",
  (hid,d),f1=True
 )
 if x:
  q("DELETE FROM c WHERE id=?",(x[0],))
  return False
 q(
  "INSERT INTO c(uid,hid,date,mins)"
  "VALUES(?,?,?,0)",
  (u,hid,d)
 )
 return True

def stm(u,hid,m):
 d=datetime.now().strftime("%Y-%m-%d")
 x=q(
  "SELECT id FROM c "
  "WHERE hid=? AND date=?",
  (hid,d),f1=True
 )
 if x:
  q("UPDATE c SET mins=? WHERE id=?",
   (m,x[0]))
 else:
  q(
   "INSERT INTO c(uid,hid,date,mins)"
   "VALUES(?,?,?,?)",
   (u,hid,d,m)
  )

def stk(u,hid):
 s=0
 d=datetime.now()
 dc=q(
  "SELECT days FROM h WHERE id=?",
  (hid,),f1=True
 )
 hd=dc[0] if dc and dc[0] else "0123456"
 while True:
  if str(d.weekday()) in hd:
   r=q(
    "SELECT id FROM c "
    "WHERE hid=? AND date=?",
    (hid,d.strftime("%Y-%m-%d")),
    f1=True
   )
   if r:
    s+=1
   else:
    break
  d-=timedelta(days=1)
  if s>365:
   break
 return s

def mxs(u):
 mx=0
 for hid,n in gh(u):
  s=stk(u,hid)
  if s>mx:
   mx=s
 return mx

def ttl(u):
 r=q(
  "SELECT COUNT(*) FROM c WHERE uid=?",
  (u,),f1=True
 )
 return r[0] if r else 0

def prf(u):
 rows=q(
  "SELECT date FROM c "
  "WHERE uid=? GROUP BY date",
  (u,),f=True
 )
 p=0
 for(ds,)in rows:
  w=str(datetime.strptime(
   ds,"%Y-%m-%d"
  ).weekday())
  t=q(
   "SELECT COUNT(*) FROM h "
   "WHERE uid=? AND act=1 "
   "AND days LIKE '%'||?||'%'",
   (u,w),f1=True
  )
  d=q(
   "SELECT COUNT(*) FROM c "
   "WHERE uid=? AND date=?",
   (u,ds),f1=True
  )
  if t and d and t[0]>0 and d[0]>=t[0]:
   p+=1
 return p

def gmt(u,hid):
 s=datetime.now().replace(
  day=1
 ).strftime("%Y-%m-%d")
 e=datetime.now().strftime("%Y-%m-%d")
 r=q(
  "SELECT SUM(mins) FROM c "
  "WHERE uid=? AND hid=? "
  "AND date BETWEEN ? AND ?",
  (u,hid,s,e),f1=True
 )
 return r[0] if r and r[0] else 0

def fm(m):
 if m<60:
  return str(m)+" мин"
 h=m//60
 mm=m%60
 if mm==0:
  return str(h)+" ч"
 return str(h)+" ч "+str(mm)+" мин"

def bpk(u):
 ex=[x[1] for x in gh(u)]
 kb=[]
 for i,h in enumerate(DH):
  if h in ex:
   kb.append([B(
    "✅ "+h,
    callback_data="up_"+str(i)
   )])
  else:
   kb.append([B(
    "⬜ "+h,
    callback_data="pk_"+str(i)
   )])
 kb.append([B(
  "✅ Готово",
  callback_data="dp"
 )])
 return kb

def cs(ctx):
 for k in["ct","rc","adding"]:
  ctx.user_data.pop(k,None)

async def srem(context):
 now=datetime.now()
 rows=q(
  "SELECT uid,rh,rm FROM u "
  "WHERE rh>=0",
  (),f=True
 )
 for uid,rh,rm in rows:
  if now.hour==rh and now.minute==rm:
   habits=gt(uid)
   if not habits:
    continue
   dn=sum(1 for _,_,cc,_ in habits if cc)
   tl=len(habits)
   if dn>=tl:
    continue
   try:
    txt="🔔 Осталось: "
    txt+=str(tl-dn)+"/"+str(tl)
    await context.bot.send_message(
     chat_id=uid,
     text=txt,
     reply_markup=MN
    )
   except:
    pass

async def post_init(app):
 cmds=[
  BotCommand("start","Начать"),
  BotCommand("today","Сегодня"),
  BotCommand("stats","Статистика"),
  BotCommand("calendar","Календарь"),
  BotCommand("help","Помощь")
 ]
 await app.bot.set_my_commands(cmds)
 app.job_queue.run_repeating(
  srem,interval=60,first=10
 )

async def cmd_start(up,ctx):
 u=up.effective_user.id
 cs(ctx)
 q(
  "INSERT OR IGNORE INTO u(uid,un)"
  "VALUES(?,?)",
  (u,up.effective_user.username or "")
 )
 await up.message.reply_text(
  "👋 Выбери привычки:",
  reply_markup=M(bpk(u))
 )

async def show_today(msg,u,edit=False):
 st=gt(u)
 if not st:
  tx="📋 Нет привычек!\nНажми ➕"
  if edit:
   try:
    await msg.edit_text(tx)
   except:
    pass
  else:
   await msg.reply_text(tx,reply_markup=MN)
  return
 wd=DR[datetime.now().weekday()]
 dd=datetime.now().strftime("%d.%m")
 t="📋 "+wd+" "+dd+":\n\n"
 kb=[]
 dn=0
 for hid,hn,comp,mins in st:
  if comp:
   s=stk(u,hid)
   line="✅ "+hn
   if s>1:
    line+=" 🔥"+str(s)
   if mins>0:
    line+=" ("+fm(mins)+")"
   dn+=1
  else:
   line="⬜ "+hn
  t+=line+"\n"
  if comp:
   kb.append([B(
    "✅",
    callback_data="t_"+str(hid)
   )])
   kb.append([B(
    "⏱ "+hn+" — записать время",
    callback_data="mn_"+str(hid)
   )])
  else:
   kb.append([B(
    "⬜ "+hn,
    callback_data="t_"+str(hid)
   )])
 tot=len(st)
 pct=round((dn/tot)*100) if tot else 0
 bar="🟩"*(pct//10)+"⬜"*(10-pct//10)
 t+="\n"+bar+" "+str(pct)+"%"
 t+=" ("+str(dn)+"/"+str(tot)+")"
 if dn==tot and tot>0:
  t+="\n\n🎉 ИДЕАЛЬНЫЙ ДЕНЬ!"
 if edit:
  try:
   await msg.edit_text(t,reply_markup=M(kb))
  except:
   pass
 else:
  await msg.reply_text(
   t,reply_markup=M(kb)
  )

async def cmd_today(up,ctx):
 cs(ctx)
 await show_today(
  up.message,
  up.effective_user.id
 )

async def show_cal(msg,u,wo=0,edit=False):
 today=datetime.now()
 mon=today-timedelta(
  days=today.weekday()
 )+timedelta(weeks=wo)
 habits=ghf(u)
 d1=mon.strftime("%d.%m")
 d2=(mon+timedelta(days=6)).strftime("%d.%m")
 t="📆 "+d1+" — "+d2+":\n\n"
 for i in range(7):
  day=mon+timedelta(days=i)
  w=str(day.weekday())
  ds=day.strftime("%Y-%m-%d")
  td=today.strftime("%Y-%m-%d")
  it=""
  if ds==td:
   it=" ← СЕГОДНЯ"
  dh=[x for x in habits
   if w in(x[2] or "0123456")]
  dc=0
  for hid,_,_ in dh:
   r=q(
    "SELECT id FROM c "
    "WHERE hid=? AND date=?",
    (hid,ds),f1=True
   )
   if r:
    dc+=1
  tl=len(dh)
  if tl==0:
   sv="—"
  elif day.date()<=today.date():
   if dc==tl:
    sv="✅"+str(dc)+"/"+str(tl)
   elif dc>0:
    sv="⚠️"+str(dc)+"/"+str(tl)
   else:
    sv="❌0/"+str(tl)
  else:
   sv="📌"+str(tl)
  dn=DR[day.weekday()]
  dd=day.strftime("%d.%m")
  t+=dn+" "+dd+": "+sv+it+"\n"
 prev="cl_"+str(wo-1)
 nxt="cl_"+str(wo+1)
 kb=[[
  B("⬅️",callback_data=prev),
  B("Сегодня",callback_data="cl_0"),
  B("➡️",callback_data=nxt)
 ]]
 if edit:
  try:
   await msg.edit_text(
    t,reply_markup=M(kb)
   )
  except:
   pass
 else:
  await msg.reply_text(
   t,reply_markup=M(kb)
  )

async def cmd_cal(up,ctx):
 cs(ctx)
 await show_cal(
  up.message,
  up.effective_user.id
 )

async def cmd_stats(up,ctx):
 cs(ctx)
 kb=[
  [B("7 дней",callback_data="s7"),
   B("30 дней",callback_data="s30")],
  [B("⏱ Время",callback_data="st")]
 ]
 await up.message.reply_text(
  "📊 Выбери:",
  reply_markup=M(kb)
 )

async def cmd_rem(up,ctx):
 cs(ctx)
 u=up.effective_user.id
 r=q(
  "SELECT rh FROM u WHERE uid=?",
  (u,),f1=True
 )
 cur=r[0] if r and r[0]>=0 else None
 kb=[]
 row=[]
 for h in range(6,24):
  lbl=str(h)+":00"
  if cur==h:
   lbl="✅"+lbl
  row.append(B(
   lbl,
   callback_data="rm_"+str(h)
  ))
  if len(row)==4:
   kb.append(row)
   row=[]
 if row:
  kb.append(row)
 kb.append([B(
  "✍️ Точное",
  callback_data="rc"
 )])
 kb.append([B(
  "🔕 Выкл",
  callback_data="ro"
 )])
 cur_txt="выкл"
 if cur is not None:
  cur_txt=str(cur)+":00"
 await up.message.reply_text(
  "🔔 Сейчас: "+cur_txt,
  reply_markup=M(kb)
 )

async def cmd_set(up,ctx):
 cs(ctx)
 kb=[
  [B("🔄 Привычки",callback_data="rs")],
  [B("💣 Сброс",callback_data="ra")]
 ]
 await up.message.reply_text(
  "⚙️ Настройки:",
  reply_markup=M(kb)
 )

async def cmd_ach(up,ctx):
 cs(ctx)
 u=up.effective_user.id
 ms=mxs(u)
 tc=ttl(u)
 pf=prf(u)
 t="🏆 Достижения:\n\n"
 achs=[
  ("🌱","Росток","s",3),
  ("⚡","Разгон","s",7),
  ("🔥","В огне","s",14),
  ("⭐","Звезда","s",21),
  ("💎","Бриллиант","s",30),
  ("1️⃣","Первый шаг","t",1),
  ("🔟","Десятка","t",10),
  ("💯","Сотня","t",100),
  ("💪","Идеальный день","p",1)
 ]
 cnt=0
 for i,n,tp,v in achs:
  if tp=="s":
   val=ms
  elif tp=="t":
   val=tc
  else:
   val=pf
  if val>=v:
   t+="✅ "+i+" "+n+"\n"
   cnt+=1
  else:
   left=str(v-val)
   t+="🔒 "+i+" "+n
   t+=" (ещё "+left+")\n"
 t+="\n"+str(cnt)+"/"+str(len(achs))
 await up.message.reply_text(
  t,reply_markup=MN
 )

async def cmd_help(up,ctx):
 cs(ctx)
 t="✅ — отметить\n"
 t+="⏱ — записать время\n"
 t+="📆 Календарь\n"
 t+="📊 Статистика\n"
 t+="🔔 Напоминание\n"
 t+="➕ Добавить / 🗑 Удалить\n"
 t+="🏆 Достижения"
 await up.message.reply_text(
  t,reply_markup=MN
 )

async def handle_cb(up,ctx):
 cq=up.callback_query
 await cq.answer()
 u=cq.from_user.id
 d=cq.data
 if d.startswith("pk_"):
  i=int(d[3:])
  if i<len(DH):
   q(
    "INSERT INTO h(uid,name,days)"
    "VALUES(?,?,?)",
    (u,DH[i],"0123456")
   )
  try:
   await cq.message.edit_reply_markup(
    reply_markup=M(bpk(u))
   )
  except:
   pass
 elif d.startswith("up_"):
  i=int(d[3:])
  if i<len(DH):
   for hid,hn in gh(u):
    if hn==DH[i]:
     q(
      "UPDATE h SET act=0 "
      "WHERE id=?",
      (hid,)
     )
     break
  try:
   await cq.message.edit_reply_markup(
    reply_markup=M(bpk(u))
   )
  except:
   pass
 elif d=="dp":
  cnt=str(len(gh(u)))
  try:
   await cq.message.edit_text(
    "✅ Выбрано: "+cnt
   )
  except:
   pass
  await cq.message.reply_text(
   "🎉 Жми 📋 Сегодня",
   reply_markup=MN
  )
 elif d.startswith("t_"):
  hid=int(d[2:])
  tog(u,hid)
  await show_today(cq.message,u,edit=True)
 elif d.startswith("mn_"):
  hid=int(d[3:])
  hn=q(
   "SELECT name FROM h WHERE id=?",
   (hid,),f1=True
  )
  cur=gmt(u,hid)
  tx="⏱ "+(hn[0] if hn else "?")
  tx+="\n📅 Месяц: "+fm(cur)
  tx+="\n\nВыбери:"
  h=str(hid)
  kb=[
   [B("15м",callback_data="sm_"+h+"_15"),
    B("30м",callback_data="sm_"+h+"_30"),
    B("45м",callback_data="sm_"+h+"_45")],
   [B("1ч",callback_data="sm_"+h+"_60"),
    B("1.5ч",callback_data="sm_"+h+"_90"),
    B("2ч",callback_data="sm_"+h+"_120")],
   [B("3ч",callback_data="sm_"+h+"_180"),
    B("4ч",callback_data="sm_"+h+"_240"),
    B("5ч",callback_data="sm_"+h+"_300")],
   [B("✍️ Своё",
    callback_data="ct_"+h)],
   [B("⬅️ Назад",
    callback_data="bk")]
  ]
  try:
   await cq.message.edit_text(
    tx,reply_markup=M(kb)
   )
  except:
   pass
 elif d.startswith("sm_"):
  p=d[3:].split("_")
  hid=int(p[0])
  mins=int(p[1])
  stm(u,hid,mins)
  hn=q(
   "SELECT name FROM h WHERE id=?",
   (hid,),f1=True
  )
  nm=hn[0] if hn else "?"
  tx="✅ "+nm+": "+fm(mins)
  tx+="\n📅 Месяц: "+fm(gmt(u,hid))
  try:
   await cq.message.edit_text(tx)
  except:
   pass
  await show_today(
   cq.message,u,edit=False
  )
 elif d.startswith("ct_"):
  ctx.user_data["ct"]=int(d[3:])
  try:
   await cq.message.edit_text(
    "✍️ Напиши минуты:\n"
    "90 = полтора часа\n"
    "1:30 = 1 час 30 мин"
   )
  except:
   pass
 elif d=="bk":
  cs(ctx)
  await show_today(
   cq.message,u,edit=True
  )
 elif d.startswith("cl_"):
  wo=int(d[3:])
  await show_cal(
   cq.message,u,wo,edit=True
  )
 elif d=="s7" or d=="s30":
  days=7 if d=="s7" else 30
  hb=gh(u)
  if not hb:
   try:
    await cq.message.edit_text("Нет!")
   except:
    pass
   return
  tp=0
  td=0
  end=datetime.now()
  start=end-timedelta(days=days-1)
  for i in range(days):
   day=start+timedelta(days=i)
   ds=day.strftime("%Y-%m-%d")
   w=str(day.weekday())
   cn=q(
    "SELECT COUNT(*) FROM h "
    "WHERE uid=? AND act=1 "
    "AND days LIKE '%'||?||'%'",
    (u,w),f1=True
   )
   tp+=cn[0] if cn else 0
   r=q(
    "SELECT COUNT(*) FROM c "
    "WHERE uid=? AND date=?",
    (u,ds),f1=True
   )
   td+=r[0] if r else 0
  pct=round((td/tp)*100) if tp else 0
  bar="🟩"*(pct//10)+"⬜"*(10-pct//10)
  tx="📊 "+str(days)+" дн:\n"
  tx+=bar+" "+str(pct)+"%\n"
  for hid,hn in hb:
   tx+="\n"+hn+" 🔥"+str(stk(u,hid))
  try:
   await cq.message.edit_text(tx)
  except:
   pass
 elif d=="st":
  hb=gh(u)
  if not hb:
   try:
    await cq.message.edit_text("Нет!")
   except:
    pass
   return
  tx="⏱ Месяц:\n\n"
  ta=0
  for hid,hn in hb:
   m=gmt(u,hid)
   ta+=m
   if m>0:
    tx+=hn+": "+fm(m)+"\n"
  tx+="\nВсего: "+fm(ta)
  try:
   await cq.message.edit_text(tx)
  except:
   pass
 elif d=="ro":
  q(
   "UPDATE u SET rh=-1 WHERE uid=?",
   (u,)
  )
  try:
   await cq.message.edit_text("🔕")
  except:
   pass
 elif d=="rc":
  ctx.user_data["rc"]=True
  try:
   await cq.message.edit_text(
    "✍️ Напиши время (20:30)"
   )
  except:
   pass
 elif d.startswith("rm_"):
  h=int(d[3:])
  q(
   "UPDATE u SET rh=?,rm=0 "
   "WHERE uid=?",
   (h,u)
  )
  try:
   await cq.message.edit_text(
    "🔔 "+str(h)+":00 ✅"
   )
  except:
   pass
 elif d=="rs":
  try:
   await cq.message.edit_text(
    "📋 Выбери:",
    reply_markup=M(bpk(u))
   )
  except:
   pass
 elif d=="ra":
  kb=[[
   B("✅ Да",callback_data="ry"),
   B("❌ Нет",callback_data="rn")
  ]]
  try:
   await cq.message.edit_text(
    "💣 Точно?",
    reply_markup=M(kb)
   )
  except:
   pass
 elif d=="ry":
  for tb in["c","h","u"]:
   q(
    "DELETE FROM "+tb+" WHERE uid=?",
    (u,)
   )
  try:
   await cq.message.edit_text(
    "🗑 Удалено! /start"
   )
  except:
   pass
 elif d=="rn":
  try:
   await cq.message.edit_text("👍")
  except:
   pass
 elif d.startswith("dh_"):
  hid=int(d[3:])
  r=q(
   "SELECT name FROM h WHERE id=?",
   (hid,),f1=True
  )
  q(
   "UPDATE h SET act=0 WHERE id=?",
   (hid,)
  )
  nm=r[0] if r else "?"
  try:
   await cq.message.edit_text(
    "✅ "+nm+" удалена!"
   )
  except:
   pass

async def handle_txt(up,ctx):
 u=up.effective_user.id
 t=up.message.text
 if ctx.user_data.get("ct"):
  try:
   tx=t.replace(" ","")
   tx=tx.replace("ч",":")
   tx=tx.replace("м","")
   if ":" in tx:
    pp=tx.split(":")
    m=int(pp[0])*60+int(pp[1])
   else:
    m=int(tx)
   hid=ctx.user_data["ct"]
   stm(u,hid,m)
   cs(ctx)
   await up.message.reply_text(
    "✅ "+fm(m),
    reply_markup=MN
   )
  except:
   await up.message.reply_text(
    "❌ Число! 90 или 1:30"
   )
  return
 if ctx.user_data.get("rc"):
  try:
   p=t.replace(".",":").split(":")
   h=int(p[0])
   m=int(p[1]) if len(
