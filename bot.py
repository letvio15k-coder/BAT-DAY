import os, threading, requests, time
import numpy as np
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.environ.get("TOKEN")
app_flask = Flask(__name__)
@app_flask.route('/')
def home(): return "BOTTOM HUNTER 70 COIN LIVE"

# 70 CON TOP + MID CAP - ĐÃ TRỪ STABLE (USDT,USDC,FDUSD,DAI,TUSD) VÀ MEME (DOGE,SHIB,PEPE,BONK,WIF,FLOKI)
COINS_70 = [
    "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT","ADAUSDT","AVAXUSDT","DOTUSDT","LINKUSDT","TRXUSDT",
    "MATICUSDT","LTCUSDT","BCHUSDT","UNIUSDT","NEARUSDT","ETCUSDT","FILUSDT","HBARUSDT","APTUSDT","ICPUSDT",
    "STXUSDT","ARBUSDT","OPUSDT","SUIUSDT","INJUSDT","RNDRUSDT","IMXUSDT","GRTUSDT","MKRUSDT","AAVEUSDT",
    "THETAUSDT","ALGOUSDT","QNTUSDT","VETUSDT","LDOUSDT","FTMUSDT","EGLDUSDT","SANDUSDT","MANAUSDT","AXSUSDT",
    "FLOWUSDT","XTZUSDT","EOSUSDT","KAVAUSDT","KLAYUSDT","CHZUSDT","NEOUSDT","IOTAUSDT","CFXUSDT","MINAUSDT",
    "ROSEUSDT","ONEUSDT","QTUMUSDT","ZILUSDT","WAVESUSDT","COMPUSDT","SNXUSDT","ENSUSDT","CRVUSDT","LRCUSDT",
    "GMXUSDT","DYDXUSDT","BLURUSDT","SEIUSDT","TIAUSDT","ARKMUSDT","AGIXUSDT","FETUSDT","OCEANUSDT","JUPUSDT","STRKUSDT"
]

def get_candles(inst, bar="4H", limit=100):
    try:
        url=f"https://www.okx.com/api/v5/market/candles?instId={inst}&bar={bar}&limit={limit}"
        r=requests.get(url, timeout=10).json()
        if 'data' not in r: return None
        data=r['data'][::-1]
        closes=np.array([float(x[4]) for x in data]); highs=np.array([float(x[2]) for x in data])
        lows=np.array([float(x[3]) for x in data]); vols=np.array([float(x[5]) for x in data])
        return closes, highs, lows, vols
    except: return None

def calc_stoch(closes, highs, lows, k=14):
    ll=np.array([lows[i-k+1:i+1].min() if i>=k-1 else lows[:i+1].min() for i in range(len(lows))])
    hh=np.array([highs[i-k+1:i+1].max() if i>=k-1 else highs[:i+1].max() for i in range(len(highs))])
    k_per=100*(closes-ll)/(hh-ll+1e-9)
    return k_per[-1]

def calc_mfi(closes, highs, lows, vols, p=14):
    tp=(highs+lows+closes)/3; rmf=tp*vols
    pmf=np.zeros(len(tp)); nmf=np.zeros(len(tp))
    for i in range(1,len(tp)):
        if tp[i]>tp[i-1]: pmf[i]=rmf[i]
        else: nmf[i]=rmf[i]
    ps=np.convolve(pmf, np.ones(p), mode='valid'); ns=np.convolve(nmf, np.ones(p), mode='valid')
    mfi=100-(100/(1+ps/(ns+1e-9)))
    return mfi[-1] if len(mfi)>0 else 50

def calc_cci(closes, highs, lows, p=20):
    tp=(highs+lows+closes)/3; sma=np.convolve(tp, np.ones(p)/p, mode='valid')
    md=[];
    for i in range(p-1,len(tp)): md.append(np.mean(np.abs(tp[i-p+1:i+1]-sma[i-p+1])))
    md=np.array(md); cci=(tp[p-1:]-sma)/(0.015*md+1e-9)
    return cci[-1] if len(cci)>0 else 0

def scan_one(symbol, bar):
    inst=symbol.replace("USDT","-USDT")
    data=get_candles(inst, bar, 100)
    if data is None: return None
    closes, highs, lows, vols = data
    price=closes[-1]
    stoch=calc_stoch(closes, highs, lows)
    mfi=calc_mfi(closes, highs, lows, vols)
    cci=calc_cci(closes, highs, lows)
    avg_vol=np.mean(vols[-21:-1]); vol_x=vols[-1]/(avg_vol+1e-9)

    is_bottom = (stoch < 22 and mfi < 28 and cci < -90)
    is_vol = vol_x >= 1.7
    if is_bottom and is_vol:
        return f"🚨 {symbol} {bar} ${price:.4f}\nSTOCH:{stoch:.0f} MFI:{mfi:.0f} CCI:{cci:.0f} VOL x{vol_x:.1f} 🔥\n👉 ĐÁY + VOL NỔ - GOM!"
    elif is_bottom:
        return f"🟡 {symbol} {bar} ${price:.4f} STOCH:{stoch:.0f} MFI:{mfi:.0f} CCI:{cci:.0f} - Sắp đáy"
    return None

async def start_cmd(u,c):
    await u.message.reply_text("🤖 HUNTER 70 COIN\n/scan4h - Quét 70 con khung 4H\n/scan1d - Quét 70 con khung 1D\n/scan - Quét cả 2\n/signal BTC - Check 1 coin\n/auto_70 - Auto báo 15p/lần")

async def scan_cmd(u,c):
    bar="4H"
    if "1d" in u.message.text.lower(): bar="1D"
    elif "4h" in u.message.text.lower(): bar="4H"
    await u.message.reply_text(f"⏳ Đang quét {len(COINS_70)} coin khung {bar}... 30s")
    found=[]
    for sym in COINS_70:
        res=scan_one(sym, bar)
        if res: found.append(res)
        time.sleep(0.15) # tránh bị ban API
    if not found:
        await u.message.reply_text(f"✅ Quét xong {bar}: Chưa có con nào về đáy + vol nổ")
    else:
        msg=f"📈 KẾT QUẢ {bar} ({len(found)} con):\n\n" + "\n\n".join(found[:20])
        await u.message.reply_text(msg)

async def scan_both_cmd(u,c):
    await u.message.reply_text("⏳ Quét 70 coin 4H + 1D... 1 phút")
    found=[]
    for bar in ["4H","1D"]:
        for sym in COINS_70:
            res=scan_one(sym, bar)
            if res and "🚨" in res: found.append(res)
            time.sleep(0.1)
    if not found: await u.message.reply_text("Chưa có siêu tín hiệu đáy nào")
    else: await u.message.reply_text("\n\n".join(found[:25]))

async def signal_one_cmd(u,c):
    try:
        sym=c.args[0].upper() if c.args else "BTCUSDT"
        if "USDT" not in sym: sym+="USDT"
        await u.message.reply_text(f"Check {sym}...")
        res4=scan_one(sym,"4H") or f"{sym} 4H chưa đáy"
        res1=scan_one(sym,"1D") or f"{sym} 1D chưa đáy"
        await u.message.reply_text(res4+"\n\n"+res1)
    except Exception as e: await u.message.reply_text(f"/signal BTC hoặc /signal ETH...")

async def auto_70_job(ctx):
    try:
        found=[]
        for bar in ["4H","1D"]:
            for sym in COINS_70[:40]: # auto chỉ quét 40 con top cho nhanh
                res=scan_one(sym, bar)
                if res and "🚨" in res: found.append(res)
                time.sleep(0.1)
                if len(found)>=5: break
            if len(found)>=5: break
        if found:
            await ctx.bot.send_message(chat_id=ctx.job.chat_id, text="🚨 AUTO 70 COIN BÁO ĐÁY:\n\n"+"\n\n".join(found))
    except Exception as e: print(e)

async def auto_toggle(u,c):
    cid=u.effective_chat.id; jobs=c.job_queue.get_jobs_by_name(f"h70_{cid}")
    if jobs:
        for j in jobs: j.schedule_removal()
        await u.message.reply_text("Đã TẮT auto 70"); return
    c.job_queue.run_repeating(auto_70_job, interval=900, first=10, chat_id=cid, name=f"h70_{cid}")
    await u.message.reply_text("✅ ĐÃ BẬT auto 70 coin - 15p quét 1 lần, có đáy + vol nổ sẽ báo!")

def run_flask(): app_flask.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    app=Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("scan4h", scan_cmd))
    app.add_handler(CommandHandler("scan1d", scan_cmd))
    app.add_handler(CommandHandler("scan", scan_both_cmd))
    app.add_handler(CommandHandler("signal", signal_one_cmd))
    app.add_handler(CommandHandler("auto_70", auto_toggle))
    print("HUNTER 70 starting...")
    app.run_polling(stop_signals=None, close_loop=False)
