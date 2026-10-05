import os, threading, requests, time
import numpy as np
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.environ.get("TOKEN")
app_flask = Flask(__name__)
@app_flask.route('/')
def home(): return "ONDO BOTTOM SIGNAL LIVE"

# --- TÍNH CHỈ BÁO ---
def get_candles(bar="4H", limit=100):
    url=f"https://www.okx.com/api/v5/market/candles?instId=ONDO-USDT&bar={bar}&limit={limit}"
    r=requests.get(url, timeout=10).json()
    data=r['data'][::-1] # cũ -> mới
    closes=np.array([float(x[4]) for x in data])
    highs=np.array([float(x[2]) for x in data])
    lows=np.array([float(x[3]) for x in data])
    vols=np.array([float(x[5]) for x in data])
    return closes, highs, lows, vols

def calc_stoch(closes, highs, lows, k=14, d=3):
    lowest_l = np.array([lows[i-k+1:i+1].min() if i>=k-1 else lows[:i+1].min() for i in range(len(lows))])
    highest_h = np.array([highs[i-k+1:i+1].max() if i>=k-1 else highs[:i+1].max() for i in range(len(highs))])
    k_per = 100 * (closes - lowest_l) / (highest_h - lowest_l + 1e-9)
    d_per = np.convolve(k_per, np.ones(d)/d, mode='same')
    return k_per[-1], d_per[-1]

def calc_mfi(closes, highs, lows, vols, period=14):
    tp = (highs + lows + closes)/3
    rmf = tp * vols
    pmf = np.zeros(len(tp)); nmf = np.zeros(len(tp))
    for i in range(1,len(tp)):
        if tp[i] > tp[i-1]: pmf[i]=rmf[i]
        else: nmf[i]=rmf[i]
    pmf_sum = np.convolve(pmf, np.ones(period), mode='valid')
    nmf_sum = np.convolve(nmf, np.ones(period), mode='valid')
    mfr = pmf_sum / (nmf_sum + 1e-9)
    mfi = 100 - (100/(1+mfr))
    return mfi[-1] if len(mfi)>0 else 50

def calc_cci(closes, highs, lows, period=20):
    tp = (highs + lows + closes)/3
    sma = np.convolve(tp, np.ones(period)/period, mode='valid')
    # mean deviation
    md = []
    for i in range(period-1, len(tp)):
        md.append(np.mean(np.abs(tp[i-period+1:i+1] - sma[i-period+1])))
    md=np.array(md)
    cci = (tp[period-1:] - sma) / (0.015 * md + 1e-9)
    return cci[-1] if len(cci)>0 else 0

def check_signal(bar="4H"):
    closes, highs, lows, vols = get_candles(bar, 100)
    price = closes[-1]
    stoch_k, stoch_d = calc_stoch(closes, highs, lows)
    mfi = calc_mfi(closes, highs, lows, vols)
    cci = calc_cci(closes, highs, lows)
    avg_vol = np.mean(vols[-21:-1])
    cur_vol = vols[-1]
    vol_x = cur_vol / (avg_vol + 1e-9)

    is_bottom = (stoch_k < 20 and mfi < 25 and cci < -100)
    is_vol_spike = vol_x >= 1.8

    msg = f"📊 ONDO {bar} - ${price:.4f}\n"
    msg += f"STOCH K:{stoch_k:.1f} D:{stoch_d:.1f} {'🟢 ĐÁY' if stoch_k<20 else '⚪'}\n"
    msg += f"MFI: {mfi:.1f} {'🟢 CẠN BÁN' if mfi<20 else '⚪'}\n"
    msg += f"CCI: {cci:.1f} {'🟢 ĐÁY SÂU' if cci<-100 else '⚪'}\n"
    msg += f"VOL: {cur_vol:,.0f} / TB {avg_vol:,.0f} x{vol_x:.1f} {'🔥 ĐỘT BIẾN' if is_vol_spike else ''}\n\n"

    if is_bottom and is_vol_spike:
        msg += "🚨🚨 SIÊU TÍN HIỆU ĐÁY + VOL NỔ 🟢🟢\n👉 Gom mạnh, cá mập vào tiền!"
    elif is_bottom:
        msg += "🟢 TÍN HIỆU ĐÁY - Đang cạn cung\n👉 Canh gom, đợi vol nổ"
    elif is_vol_spike:
        msg += "🔥 VOL ĐỘT BIẾN - Có biến động lớn sắp tới"
    else:
        msg += "⚪ Chưa có tín hiệu đáy"

    return msg, is_bottom and is_vol_spike

async def start_cmd(u,c):
    await u.message.reply_text("🤖 ONDO BOTTOM HUNTER\n\n/signal - Check 4H\n/signal1D - Check 1D\n/scan - Quét cả 4H & 1D\n/auto_bottom - Auto báo khi về đáy + vol nổ")

async def signal_cmd(u,c):
    bar = "1D" if "1d" in u.message.text.lower() else "4H"
    await u.message.reply_text(f"⏳ Đang quét {bar}...")
    msg, _ = check_signal(bar)
    await u.message.reply_text(msg)

async def scan_cmd(u,c):
    await u.message.reply_text("⏳ Đang quét 4H và 1D...")
    msg4h, strong4h = check_signal("4H")
    msg1d, strong1d = check_signal("1D")
    await u.message.reply_text(msg4h + "\n\n" + "="*20 + "\n\n" + msg1d)

async def auto_bottom_job(ctx):
    try:
        for bar in ["4H","1D"]:
            msg, is_strong = check_signal(bar)
            if is_strong:
                await ctx.bot.send_message(chat_id=ctx.job.chat_id, text=f"🚨 AUTO BÁO ĐÁY {bar}\n\n{msg}")
    except Exception as e:
        print(e)

async def auto_toggle(u,c):
    cid=u.effective_chat.id
    jobs=c.job_queue.get_jobs_by_name(f"bottom_{cid}")
    if jobs:
        for j in jobs: j.schedule_removal()
        await u.message.reply_text("Đã TẮT auto đáy"); return
    c.job_queue.run_repeating(auto_bottom_job, interval=900, first=10, chat_id=cid, name=f"bottom_{cid}")
    await u.message.reply_text("✅ Đã BẬT auto đáy 15p - Khi STOCH/MFI/CCI về đáy + VOL nổ sẽ báo!")

def run_flask(): app_flask.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    app=Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("signal", signal_cmd))
    app.add_handler(CommandHandler("signal1d", signal_cmd))
    app.add_handler(CommandHandler("scan", scan_cmd))
    app.add_handler(CommandHandler("auto_bottom", auto_toggle))
    print("ONDO BOTTOM starting...")
    app.run_polling(stop_signals=None, close_loop=False)
