import logging,sqlite3,time as ttime,os
from datetime import datetime,timedelta
from telegram import Update,InlineKeyboardButton as IKB,InlineKeyboardMarkup as IKM,ReplyKeyboardMarkup as RKM,BotCommand
from telegram.ext import Application,CommandHandler,CallbackQueryHandler,MessageHandler,filters
try:
 import matplotlib;matplotlib.use("Agg");import matplotlib.pyplot as plt;HAS_PLT=True
except:HAS_PLT=False
BOT_TOKEN=os.environ.get("BOT_TOKEN","")
MENU=RKM([["📋 Сегодня","📊 Статистика"],["🔔 Напоминание","📆 Календарь"],["➕ Добавить","🗑 Удалить"],["🏆 Достижения","⚙️ Настройки"],["❓ Помощь"]],resize_keyboard=True)
DH=["💧 Пить воду","🏃 Зарядка","📖 Чтение","🧘 Медитация","😴 Сон до 23:00","🥗 Здоровое питание","📵 Без телефона 1ч","✍️ Дневник","🚶 Прогулка","💊 Витамины"]
DR=["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]
logging.basicConfig(level=logging.INFO)
TM={}
def init_db():
 c=sqlite3.connect("h.db");e=c.cursor()
 e.execute("CREATE TABLE IF NOT EXISTS u(uid INTEGER PRIMARY KEY,un TEXT,rh INTEGER DEFAULT -1,rm INTEGER DEFAULT 0)")
 e.execute("CREATE TABLE IF NOT EXISTS h(id INTEGER PRIMARY KEY AUTOINCREMENT,uid INTEGER,name TEXT,act INTEGER DEFAULT 1,days TEXT DEFAULT '0123456')")
 e.execute("CREATE TABLE IF NOT EXISTS c(id INTEGER PRIMARY KEY AUTOINCREMENT,uid INTEGER,hid INTEGER,date TEXT,mins INTEGER DEFAULT 0,UNIQUE(hid,date))")
 try:e.execute("ALTER TABLE h ADD COLUMN days TEXT DEFAULT '0123456'")
 except:pass
 c.commit();c.close()
def q(sql,p=(),f=False,f1=False):
 c=sqlite3.connect("h.db");e=c.cursor();e.execute(sql,p)
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
 if m<60:return str(m)+"м"
 h=m//60;mm=m%60
 return str(h)+"ч" if mm==0 else str(h)+"ч"+str(mm)+"м"
def dtx(ds):
 if not ds or ds=="0123456" or len(ds)>=7:return "ежедневно"
 return ",".join(DR[int(d)] for d in sorted(ds) if d.isdigit() and int(d)<7)
def bpk(u):
 ex=[x[1] for x in gh(u)];kb=[]
 for i,h in enumerate(DH):
  if h in ex:kb.append([IKB("✅ "+h,callback_data="up_"+str(i))])
  else:kb.append([IKB("⬜ "+h,callback_data="pk_"+str(i))])
 kb.append([IKB("✅ Готово",callback_data="dp")]);return kb
def bdk(hid,cur="0123456"):
 kb=[];row=[]
 for i,nm in enumerate(DR):
  row.append(IKB(("✅" if str(i) in cur else "⬜")+nm,callback_data="sd_"+str(hid)+"_"+str(i)))
  if len(row)==4:kb.append(row);row=[]
 if row:kb.append(row)
 kb.append([IKB("Каждый день",callback_data="sd_"+str(hid)+"_all")]);kb.append([IKB("✅Готово",callback_data="sd_"+str(hid)+"_done")]);return kb
def cs(ctx):
 for k in["ct","rc","adding","mt"]:ctx.user_data.pop(k,None)
async def srem(context):
 now=datetime.now()
 for uid,rh,rm in q("SELECT uid,rh,rm FROM u WHERE rh>=0",(),f=True):
  if now.hour==rh and now.minute==rm:
   habits=gt(uid)
   if not habits:continue
   dn=sum(1 for _,_,cc,_ in habits if cc);tl=len(habits)
   if dn>=tl:continue
   try:await context.bot.send_message(chat_id=uid,text="🔔 Осталось: "+str(tl-dn)+"/"+str(tl),reply_markup=MENU)
   except:pass
async def post_init(app):
 await app.bot.set_my_commands([BotCommand("start","Начать"),BotCommand("today","Сегодня"),BotCommand("stats","Статистика"),BotCommand("calendar","Календарь"),BotCommand("help","Помощь")])
 app.job_queue.run_repeating(srem,interval=60,first=10)
async def cmd_start(up,ctx):
 u=up.effective_user.id;cs(ctx);q("INSERT OR IGNORE INTO u(uid,un)VALUES(?,?)",(u,up.effective_user.username or ""))
 await up.message.reply_text("👋 Выбери привычки:",reply_markup=IKM(bpk(u)))
async def show_today(msg,u,edit=False):
 st=gt(u)
 if not st:
  txt="📋 Нет привычек на сегодня! Добавь ➕"
  if edit:
   try:await msg.edit_text(txt)
   except:pass
  else:await msg.reply_text(txt,reply_markup=MENU)
  return
 t="📋 "+DR[datetime.now().weekday()]+" "+datetime.now().strftime("%d.%m")+":\n\n";kb=[];dn=0
 for hid,hn,comp,mins in st:
  tk=str(u)+"_"+str(hid);tr=tk in TM
  if comp:
   s=stk(u,hid);line="✅ "+hn
   if s>1:line+=" 🔥"+str(s)
   if tr:line+=" ⏱"+fm(int((ttime.time()-TM[tk])/60))
   elif mins>0:line+=" ("+fm(mins)+")"
   dn+=1
  else:line="⬜ "+hn
  t+=line+"\n";row=[IKB("✅" if comp else "⬜",callback_data="t_"+str(hid))]
  if comp:
   if tr:row.append(IKB("🕐",callback_data="tc_"+str(hid)));row.append(IKB("⏹",callback_data="ts_"+str(hid)))
   else:row.append(IKB("▶️",callback_data="go_"+str(hid)));row.append(IKB("✍️",callback_data="mn_"+str(hid)))
  kb.append(row)
 tot=len(st);pct=round((dn/tot)*100) if tot else 0
 t+="\n"+"🟩"*(pct//10)+"⬜"*(10-pct//10)+" "+str(pct)+"% ("+str(dn)+"/"+str(tot)+")"
 if dn==tot and tot>0:t+="\n\n🎉 ИДЕАЛЬНЫЙ ДЕНЬ!"
 if edit:
  try:await msg.edit_text(t,reply_markup=IKM(kb))
  except:pass
 else:await msg.reply_text(t,reply_markup=IKM(kb))
async def cmd_today(up,ctx):cs(ctx);await show_today(up.message,up.effective_user.id)
async def show_cal(msg,u,wo=0,edit=False):
 today=datetime.now();mon=today-timedelta(days=today.weekday())+timedelta(weeks=wo);habits=ghf(u)
 t="📆 "+mon.strftime("%d.%m")+"—"+(mon+timedelta(days=6)).strftime("%d.%m")+":\n\n"
 for i in range(7):
  day=mon+timedelta(days=i);w=str(day.weekday());ds=day.strftime("%Y-%m-%d")
  it=" ←СЕГОДНЯ" if ds==today.strftime("%Y-%m-%d") else ""
  dh=[x for x in habits if w in(x[2] or "0123456")]
  dc=sum(1 for hid,_,_ in dh if q("SELECT id FROM c WHERE hid=? AND date=?",(hid,ds),f1=True));tl=len(dh)
  if tl==0:s="выходной"
  elif day.date()<=today.date():s="✅"+str(dc)+"/"+str(tl) if dc==tl else "⚠️"+str(dc)+"/"+str(tl) if dc>0 else "❌0/"+str(tl)
  else:s="📌"+str(tl)
  t+=DR[day.weekday()]+" "+day.strftime("%d.%m")+": "+s+it+"\n"
 kb=[[IKB("⬅️",callback_data="cl_"+str(wo-1)),IKB("Сегодня",callback_data="cl_0"),IKB("➡️",callback_data="cl_"+str(wo+1))]]
 if edit:
  try:await msg.edit_text(t,reply_markup=IKM(kb))
  except:pass
 else:await msg.reply_text(t,reply_markup=IKM(kb))
async def cmd_cal(up,ctx):cs(ctx);await show_cal(up.message,up.effective_user.id)
async def cmd_stats(up,ctx):
 cs(ctx);kb=[[IKB("7д",callback_data="s7"),IKB("30д",callback_data="s30")],[IKB("⏱Время",callback_data="st")],[IKB("📊График",callback_data="ch")]]
 await up.message.reply_text("📊 Статистика:",reply_markup=IKM(kb))
async def cmd_rem(up,ctx):
 cs(ctx);u=up.effective_user.id;r=q("SELECT rh FROM u WHERE uid=?",(u,),f1=True);cur=r[0] if r and r[0]>=0 else None
 kb=[];row=[]
 for h in range(6,24):
  row.append(IKB(("✅" if cur==h else "")+str(h)+":00",callback_data="rm_"+str(h)))
  if len(row)==4:kb.append(row);row=[]
 if row:kb.append(row)
 kb.append([IKB("✍️Точное",callback_data="rc")]);kb.append([IKB("🔕Выкл",callback_data="ro")])
 await up.message.reply_text("🔔 "+(str(cur)+":00" if cur else "Выкл"),reply_markup=IKM(kb))
async def cmd_set(up,ctx):
 cs(ctx);kb=[[IKB("🔄Привычки",callback_data="rs")],[IKB("📅Расписание",callback_data="sc")],[IKB("💣Сброс",callback_data="ra")]]
 await up.message.reply_text("⚙️",reply_markup=IKM(kb))
async def cmd_ach(up,ctx):
 cs(ctx);u=up.effective_user.id;ms=mxs(u);tc=ttl(u);pf=prf(u)
 t="🏆 Достижения:\n\n";achs=[("🌱","Росток","streak",3),("⚡","Разгон","streak",7),("🔥","В огне","streak",14),("⭐","Звезда","streak",21),("💎","Бриллиант","streak",30),("1️⃣","Первый шаг","total",1),("🔟","Десятка","total",10),("💯","Сотня","total",100),("💪","Идеальный день","perfect",1)];cnt=0
 for i,n,tp,v in achs:
  val=ms if tp=="streak" else tc if tp=="total" else pf
  if val>=v:t+="✅"+i+n+"\n";cnt+=1
  else:t+="🔒"+i+n+"("+str(v-val)+")\n"
 t+="\n"+str(cnt)+"/"+str(len(achs));await up.message.reply_text(t,reply_markup=MENU)
async def cmd_help(up,ctx):cs(ctx);await up.message.reply_text("📋Сегодня ✅отметить ▶️таймер 🕐время ⏹стоп ✍️вручную\n📆Календарь 📊Статистика 🏆Достижения\n🔔Напоминание ➕Добавить 🗑Удалить ⚙️Расписание",reply_markup=MENU)
async def handle_cb(up,ctx):
 cq=up.callback_query;await cq.answer();u=cq.from_user.id;d=cq.data
 if d.startswith("pk_"):
  i=int(d[3:])
  if i<len(DH):q("INSERT INTO h(uid,name,days)VALUES(?,?,?)",(u,DH[i],"0123456"))
  try:await cq.message.edit_reply_markup(reply_markup=IKM(bpk(u)))
  except:pass
 elif d.startswith("up_"):
  i=int(d[3:])
  if i<len(DH):
   for hid,hn in gh(u):
    if hn==DH[i]:q("UPDATE h SET act=0 WHERE id=?",(hid,));break
  try:await cq.message.edit_reply_markup(reply_markup=IKM(bpk(u)))
  except:pass
 elif d=="dp":
  try:await cq.message.edit_text("✅ Выбрано: "+str(len(gh(u))))
  except:pass
  await cq.message.reply_text("🎉",reply_markup=MENU)
 elif d.startswith("t_"):tog(u,int(d[2:]));await show_today(cq.message,u,edit=True)
 elif d.startswith("go_"):
  hid=int(d[3:]);TM[str(u)+"_"+str(hid)]=ttime.time()
  hn=q("SELECT name FROM h WHERE id=?",(hid,),f1=True)
  await cq.message.reply_text("⏱ ТАЙМЕР: "+(hn[0] if hn else "?")+"\n🕐 "+datetime.now().strftime("%H:%M:%S")+"\n\n🕐=проверить ⏹=стоп",reply_markup=MENU)
 elif d.startswith("tc_"):
  hid=int(d[3:]);tk=str(u)+"_"+str(hid)
  if tk in TM:
   el=ttime.time()-TM[tk];await cq.answer(text="⏱ "+str(int(el/60))+"м "+str(int(el%60))+"с",show_alert=True)
  else:await cq.answer(text="Не запущен",show_alert=True)
 elif d.startswith("ts_"):
  hid=int(d[3:]);tk=str(u)+"_"+str(hid)
  if tk in TM:
   mins=max(int((ttime.time()-TM[tk])/60),1);del TM[tk];stm(u,hid,mins)
   hn=q("SELECT name FROM h WHERE id=?",(hid,),f1=True)
   await cq.message.reply_text("⏹ "+(hn[0] if hn else "?")+"\n⏱ "+fm(mins)+"\n📅Месяц: "+fm(gmt(u,hid)),reply_markup=MENU)
  await show_today(cq.message,u,edit=False)
 elif d.startswith("mn_"):
  hid=int(d[3:]);ctx.user_data["mt"]=hid;hn=q("SELECT name FROM h WHERE id=?",(hid,),f1=True)
  kb=[[IKB("15м",callback_data="sm("+dtx(days)+")",callback_data="sh_"+str(hid))] for hid,hn,days in hb];kb.append([IKB("⬅️",callback_data="bs")])
  try:await cq.message.edit_text("📅 Расписание:",reply_markup=IKM(kb))
  except:pass
 elif d.startswith("sh_"):
  hid=int(d[3:]);r=q("SELECT name,days FROM h WHERE id=?",(hid,),f1=True)
  if r:
   try:await cq.message.edit_text("📅 "+r[0],reply_markup=IKM(bdk(hid,r[1] or "0123456")))
   except:pass
 elif d.startswith("sd_"):
  p=d[3:].split("_");hid=int(p[0]);act=p[1]
  if act=="done":
   r=q("SELECT name,days FROM h WHERE id=?",(hid,),f1=True)
   try:await cq.message.edit_text("✅ "+r[0]+" — "+dtx(r[1]))
   except:pass
   await cq.message.reply_text("📱",reply_markup=MENU)
  elif act=="all":
   q("UPDATE h SET days=? WHERE id=?",("0123456",hid));nm=q("SELECT name FROM h WHERE id=?",(hid,),f1=True)
   try:await cq.message.edit_text("📅 "+nm[0],reply_markup=IKM(bdk(hid,"0123456")))
   except:pass
  else:
   r=q("SELECT days FROM h WHERE id=?",(hid,),f1=True);days=r[0] if r and r[0] else "0123456"
   days=days.replace(act,"") if act in days else days+act
   if not days:days="0123456"
   days="".join(sorted(days));q("UPDATE h SET days=? WHERE id=?",(days,hid));nm=q("SELECT name FROM h WHERE id=?",(hid,),f1=True)
   try:await cq.message.edit_text("📅 "+nm[0],reply_markup=IKM(bdk(hid,days)))
   except:pass
 elif d=="rs":
  try:await cq.message.edit_text("📋",reply_markup=IKM(bpk(u)))
  except:pass
 elif d=="bs":
  kb=[[IKB("🔄Привычки",callback_data="rs")],[IKB("📅Расписание",callback_data="sc")],[IKB("💣Сброс",callback_data="ra")]]
  try:await cq.message.edit_text("⚙️",reply_markup=IKM(kb))
  except:pass
 elif d=="ra":
  try:await cq.message.edit_text("💣 Удалить ВСЕ?",reply_markup=IKM([[IKB("✅Да",callback_data="ry"),IKB("❌Нет",callback_data="rn")]]))
  except:pass
 elif d=="ry":
  for t in["c","h","u"]:q("DELETE FROM "+t+" WHERE uid=?",(u,))
  try:await cq.message.edit_text("🗑 /start")
  except:pass
 elif d=="rn":
  try:await cq.message.edit_text("👍")
  except:pass
  await cq.message.reply_text("📱",reply_markup=MENU)
 elif d.startswith("dh_"):
  hid=int(d[3:]);r=q("SELECT name FROM h WHERE id=?",(hid,),f1=True);q("UPDATE h SET act=0 WHERE id=?",(hid,))
  try:await cq.message.edit_text("✅ "+(r[0] if r else "?")+" удалена!")
  except:pass
  await cq.message.reply_text("📱",reply_markup=MENU)
async def handle_txt(up,ctx):
 u=up.effective_user.id;t=up.message.text
 if ctx.user_data.get("ct"):
  try:
   txt=t.replace(" ","").replace("ч",":").replace("м","")
   m=int(txt.split(":")[0])*60+int(txt.split(":")[1]) if ":" in txt else int(txt)
   hid=ctx.user_data["ct"];stm(u,hid,m);cs(ctx)
   await up.message.reply_text("✅ "+fm(m)+"\n📅"+fm(gmt(u,hid)),reply_markup=MENU)
  except:await up.message.reply_text("❌ Число! 90 или 1:30")
  return
 if ctx.user_data.get("mt"):
  try:
   txt=t.replace(" ","").replace("ч",":").replace("м","")
   m=int(txt.split(":")[0])*60+int(txt.split(":")[1]) if ":" in txt else int(txt)
   hid=ctx.user_data["mt"];stm(u,hid,m);cs(ctx)
   await up.message.reply_text("✅ "+fm(m)+"\n📅"+fm(gmt(u,hid)),reply_markup=MENU)
  except:await up.message.reply_text("❌ Число! 90 или 1:30")
  return
 if ctx.user_data.get("rc"):
  try:
   p=t.replace(".",":").split(":");h=int(p[0]);m=int(p[1]) if len(p)>1 else 0
   if 0<=h<=23 and 0<=m<=59:q("UPDATE u SET rh=?,rm=? WHERE uid=?",(h,m,u));cs(ctx);await up.message.reply_text("🔔 "+str(h)+":"+str(m).zfill(2)+" ✅",reply_markup=MENU)
   else:await up.message.reply_text("❌ 0:00-23:59")
  except:await up.message.reply_text("❌ 20:30")
  return
 if ctx.user_data.get("adding"):
  q("INSERT INTO h(uid,name,days)VALUES(?,?,?)",(u,t,"0123456"));cs(ctx)
  await up.message.reply_text("✅ "+t+" добавлена!",reply_markup=MENU);return
 if "Сегодня" in t:cs(ctx);await show_today(up.message,u)
 elif "Статистика" in t:await cmd_stats(up,ctx)
 elif "Напоминание" in t:await cmd_rem(up,ctx)
 elif "Календарь" in t:await show_cal(up.message,u)
 elif "Настройки" in t:await cmd_set(up,ctx)
 elif "Добавить" in t:cs(ctx);ctx.user_data["adding"]=True;await up.message.reply_text("✍️ Название:")
 elif "Удалить" in t:
  hb=gh(u)
  if not hb:await up.message.reply_text("Нет!",reply_markup=MENU);return
  await up.message.reply_text("🗑",reply_markup=IKM([[IKB("🗑"+hn,callback_data="dh_"+str(hid))] for hid,hn in hb]))
 elif "Достижения" in t:await cmd_ach(up,ctx)
 elif "Помощь" in t:await cmd_help(up,ctx)
 else:await up.message.reply_text("Меню👇",reply_markup=MENU)
def main():
 init_db();print("🚀 Запущен!")
 app=Application.builder().token(BOT_TOKEN).post_init(post_init).build()
 for c,f in[("start",cmd_start),("today",cmd_today),("stats",cmd_stats),("reminder",cmd_rem),("settings",cmd_set),("achievements",cmd_ach),("calendar",cmd_cal),("help",cmd_help)]:app.add_handler(CommandHandler(c,f))
 app.add_handler(CallbackQueryHandler(handle_cb));app.add_handler(MessageHandler(filters.TEXT&~filters.COMMAND,handle_txt))
 app.run_polling()
if __name__=="__main__":main()
