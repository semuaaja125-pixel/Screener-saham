import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

st.set_page_config(page_title="Screener Saham IDX", layout="wide")
st.title("📈 Screener Saham Indonesia — Otomatis Update")
st.markdown(f"**Update:** {datetime.now().strftime('%d %B %Y %H:%M')} WIB")

# Fungsi skoring
@st.cache_data(ttl=3600)
def get_all_saham():
    TICKERS = [
        "BBCA.JK","BBRI.JK","BMRI.JK","BBNI.JK","BRIS.JK",
        "TLKM.JK","ASII.JK","ADRO.JK","PTBA.JK","PGAS.JK",
        "UNVR.JK","ICBP.JK","KLBF.JK","SIDO.JK","INDF.JK",
        "HMSP.JK","GGRM.JK","ARTO.JK","BRMS.JK","MDKA.JK",
        "ANTM.JK","MEDC.JK","EXCL.JK","ISAT.JK","FREN.JK",
        "MTEL.JK","TOWR.JK","JSMR.JK","WSKT.JK","WIKA.JK",
        "PTPP.JK","ADHI.JK","TINS.JK","BRPT.JK","INTP.JK",
        "SMGR.JK","CTRA.JK","PWON.JK","BSDE.JK","LPKR.JK",
        "SMRA.JK","MAPI.JK","ERAA.JK","ACES.JK","JPFA.JK",
        "CPIN.JK","AALI.JK","LSIP.JK","SSMS.JK","ULTJ.JK",
        "ROTI.JK","MYOR.JK","KAEF.JK","TSPC.JK","DVLA.JK",
        "WIIM.JK","SCMA.JK","MNCN.JK","BBTN.JK","BUMI.JK",
        "BYAN.JK","ITMG.JK","HRUM.JK","INDY.JK"
    ]
    
    data_list = []
    progress_bar = st.progress(0)
    
    for i, t in enumerate(TICKERS):
        try:
            s = yf.Ticker(t)
            info = s.info
            hist = s.history(period="6mo")
            
            if hist.empty or len(hist) < 20:
                continue
                
            harga = info.get("currentPrice") or info.get("regularMarketPrice")
            per = info.get("trailingPE")
            pbv = info.get("priceToBook")
            roe = info.get("returnOnEquity")
            mc = info.get("marketCap")
            nama = info.get("longName", t)[:40]
            
            # RSI
            delta = hist["Close"].diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = round(rs.iloc[-1], 1) if not rs.isna().iloc[-1] else None
            
            # Volume 20 hari
            vol_avg = int(hist["Volume"].tail(20).mean())
            
            # MA50
            ma50 = hist["Close"].rolling(50).mean().iloc[-1]
            di_atas_ma50 = "✅" if harga and ma50 and harga > ma50 else "❌"
            
            # Skor
            s_per = 10 if per and per < 10 else (8 if per and per < 15 else (5 if per and per < 20 else 2))
            s_roe = 10 if roe and roe > 0.25 else (8 if roe and roe > 0.20 else (6 if roe and roe > 0.15 else 3))
            s_pbv = 10 if pbv and pbv < 1 else (8 if pbv and pbv < 1.5 else (6 if pbv and pbv < 3 else 3))
            s_rsi = 10 if rsi and rsi < 30 else (8 if rsi and rsi < 40 else (5 if rsi and rsi < 60 else 3))
            total = round(s_per*0.25 + s_roe*0.30 + s_pbv*0.15 + s_rsi*0.30, 1)
            
            data_list.append({
                "Kode": t.replace(".JK",""),
                "Nama": nama,
                "Harga": harga or 0,
                "PER": round(per,1) if per else 0,
                "ROE%": round(roe*100,1) if roe else 0,
                "PBV": round(pbv,1) if pbv else 0,
                "RSI": rsi or 50,
                "MA50": di_atas_ma50,
                "Volume": vol_avg,
                "Skor": total
            })
        except:
            pass
        progress_bar.progress((i+1)/len(TICKERS))
    
    df = pd.DataFrame(data_list)
    df = df.sort_values("Skor", ascending=False).reset_index(drop=True)
    return df

with st.spinner("📡 Mengambil data dari bursa..."):
    df = get_all_saham()

# TABS
tab1, tab2, tab3 = st.tabs(["🏆 Ranking Semua", "🔍 Cari Manual", "📊 Detail Saham"])

with tab1:
    col1, col2 = st.columns([3, 1])
    with col1:
        min_score = st.slider("Minimal Skor", 0, 10, 6)
    with col2:
        st.metric("Total Saham Diproses", len(df))
    
    df_display = df[df["Skor"] >= min_score][["Kode", "Harga", "PER", "ROE%", "PBV", "RSI", "MA50", "Volume", "Skor"]]
    st.dataframe(df_display, use_container_width=True, height=600)
    
    st.info("💡 **Cara baca:** Skor 8+ = kandidat beli kuat, 6-8 = pantau, di bawah 6 = tunggu koreksi")

with tab2:
    cari = st.text_input("Cari kode saham (cth: BBCA, BBRI, TLKM)")
    if cari:
        hasil = df[df["Kode"].str.contains(cari.upper())]
        if not hasil.empty:
            st.dataframe(hasil, use_container_width=True)
        else:
            st.warning("Saham tidak ditemukan di database")

with tab3:
    kode = st.selectbox("Pilih saham untuk detail", df["Kode"].tolist())
    if kode:
        detail = df[df["Kode"] == kode].iloc[0]
        cols = st.columns(5)
        cols[0].metric("Harga", f"Rp{detail['Harga']:,.0f}")
        cols[1].metric("PER", detail["PER"])
        cols[2].metric("ROE", f"{detail['ROE%']}%")
        cols[3].metric("PBV", detail["PBV"])
        cols[4].metric("Skor", detail["Skor"])
        
        # Rekomendasi
        skor = detail["Skor"]
        if skor >= 8:
            st.success("🟢 **REKOMENDASI: BELI** — Fundamental kuat, valuasi murah, teknikal mendukung")
        elif skor >= 6:
            st.warning("🟡 **REKOMENDASI: PANTAU** — Fundamental ok, tunggu harga lebih murah atau katalis")
        else:
            st.error("🔴 **REKOMENDASI: LEWATI** — Fundamental kurang menarik atau terlalu mahal")

st.markdown("---")
st.caption("**Disclaimer:** Ini alat screening otomatis, bukan saran beli. Selalu lakukan riset sendiri sebelum transaksi.")
