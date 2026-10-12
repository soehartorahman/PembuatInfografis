import os
import io
import urllib.request
import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import LinearSegmentedColormap
from PIL import Image, ImageDraw, ImageFont
import requests

# Ambil Token & Chat ID dari GitHub Secrets
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8874117089:AAF3nRjb4_aU1D04TJADhsX7v8Jn7_y7R28")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "-1004416837944")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BG_FILE = os.path.join(BASE_DIR, "background10th.png")
FOLDER_ICON = os.path.join(BASE_DIR, "icons_cuaca")
FOLDER_FONT = os.path.join(BASE_DIR, "fonts")

def get_font(file_name, size):
    base_name, _ = os.path.splitext(file_name)
    alternatif_nama = []
    for ext in ['.ttf', '.otf', '.TTF', '.OTF']:
        for name_variant in [base_name, base_name.lower(), base_name.replace("-", " "), base_name.replace("-", "_")]:
            alternatif_nama.append(f"{name_variant}{ext}")
    
    alternatif_nama = list(dict.fromkeys(alternatif_nama))
    for nama in alternatif_nama:
        if os.path.exists(nama):
            try: return ImageFont.truetype(nama, size)
            except Exception: pass
    for nama in alternatif_nama:
        path_fonts_folder = os.path.join(FOLDER_FONT, nama)
        if os.path.exists(path_fonts_folder):
            try: return ImageFont.truetype(path_fonts_folder, size)
            except Exception: pass
    return ImageFont.load_default()

def fetch_data_from_gdrive():
    doc_id = "16XVJ6C8LMg8PTzCoHSCfVu5lfqyis63P"
    csv_url = f"https://docs.google.com/spreadsheets/d/{doc_id}/export?format=csv"
    req = urllib.request.Request(csv_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        return pd.read_csv(io.StringIO(response.read().decode('utf-8')))

def dapatkan_warna_indikator(val, limits, colors):
    if not limits or not colors: return "black"
    try: val = float(val)
    except (ValueError, TypeError): return "black"
    for i in range(len(limits) - 1):
        if limits[i] <= val <= limits[i+1]: return colors[i]
    if val > limits[-1]: return colors[-1]
    return colors[0]

def hitung_kategori_pm25(nilai):
    try: nilai = float(nilai)
    except: return "Data Belum Terisi"
    if nilai <= 15.5: return "Baik"
    elif nilai <= 55.4: return "Sedang"
    elif nilai <= 150.4: return "Tidak Sehat"
    elif nilai <= 250.4: return "Sangat Tidak Sehat"
    else: return "Berbahaya"

def hitung_kategori_pm10(nilai):
    try: nilai = float(nilai)
    except: return "Data Belum Terisi"
    if nilai <= 50: return "Baik"
    elif nilai <= 150: return "Sedang"
    elif nilai <= 350: return "Tidak Sehat"
    elif nilai <= 420: return "Sangat Tidak Sehat"
    else: return "Berbahaya"

def format_jam_otomatis(jam_str):
    try:
        jam_bersih = str(jam_str).strip().replace('.', ':')
        if "-" in jam_bersih: jam_bersih = jam_bersih.split("-")[0].strip()
        waktu_awal = datetime.datetime.strptime(jam_bersih, "%H:%M")
        waktu_akhir = waktu_awal + datetime.timedelta(minutes=10)
        return f"{waktu_awal.strftime('%H:%M')} - {waktu_akhir.strftime('%H:%M')} WITA"
    except Exception: return f"{jam_str} WITA"

def buat_grafik_conditional(df, col_name, batas_nilai, warna_list, output_name):
    df_clean = df.dropna(subset=[col_name, 'Tanggal']).copy()
    df_clean = df_clean[pd.to_numeric(df_clean[col_name], errors='coerce').notnull()]
    df_7 = df_clean.tail(7).copy().reset_index(drop=True)
    
    x = np.arange(len(df_7))
    y = df_7[col_name].astype(float).values
    
    bulan_id = {'januari': 1, 'februari': 2, 'maret': 3, 'april': 4, 'mei': 5, 'juni': 6, 'juli': 7, 'agustus': 8, 'september': 9, 'oktober': 10, 'november': 11, 'desember': 12}
    bulan_singkat = {1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'Mei', 6: 'Jun', 7: 'Jul', 8: 'Agu', 9: 'Sep', 10: 'Okt', 11: 'Nov', 12: 'Des'}

    parsed_dates = []
    for tgl_str in df_7['Tanggal']:
        tgl_clean = str(tgl_str).strip()
        parts = tgl_clean.split()
        if len(parts) >= 2:
            day = parts[0]
            month_str = parts[1].lower()
            month_num = bulan_id.get(month_str, None)
            parsed_dates.append({'day': day, 'month_num': month_num, 'raw': tgl_clean})
        else:
            parsed_dates.append({'day': tgl_clean, 'month_num': None, 'raw': tgl_clean})

    months_in_7 = set(p['month_num'] for p in parsed_dates if p['month_num'] is not None)
    
    formatted_dates = []
    for p in parsed_dates:
        if len(months_in_7) > 1 and p['month_num'] is not None:
            formatted_dates.append(f"{p['day']} {bulan_singkat.get(p['month_num'], '')}")
        else:
            formatted_dates.append(p['day'])

    fig, ax = plt.subplots(figsize=(7, 2.775), dpi=300)
    fig.patch.set_alpha(0.0)
    ax.patch.set_alpha(0.0)

    if batas_nilai and warna_list:
        for i in range(len(df_7) - 1):
            y_start, y_end = y[i], y[i+1]
            c_start = dapatkan_warna_indikator(y_start, batas_nilai, warna_list)
            c_end = dapatkan_warna_indikator(y_end, batas_nilai, warna_list)
            
            cmap_lokal = LinearSegmentedColormap.from_list("lokal", [c_start, c_end])
            x_seg = np.linspace(x[i], x[i+1], 30)
            y_seg = np.linspace(y_start, y_end, 30)
            
            points = np.array([x_seg, y_seg]).T.reshape(-1, 1, 2)
            segments = np.concatenate([points[:-1], points[1:]], axis=1)
            
            lc = LineCollection(segments, cmap=cmap_lokal, norm=plt.Normalize(vmin=0.0, vmax=1.0), linewidth=4, zorder=2)
            lc.set_array(np.linspace(0.0, 1.0, len(segments)))
            ax.add_collection(lc)
    else:
        ax.plot(x, y, color="#e67e22", linewidth=4, zorder=2)

    max_y_val = max(y) if len(y) > 0 and max(y) > 0 else 50
    for idx in range(len(df_7)):
        val = y[idx]
        pt_color = dapatkan_warna_indikator(val, batas_nilai, warna_list) if batas_nilai else "#e67e22"
        ax.scatter(x[idx], val, color=pt_color, edgecolor='black', s=90, zorder=3)
        ax.text(x[idx], val + (max_y_val * 0.05), f"{int(val)}", ha='center', va='bottom', fontsize=11, weight='bold', color='black')

    ax.set_xticks(x)
    ax.set_xticklabels(formatted_dates, fontsize=7)
    ax.set_xlabel("Tanggal Pengukuran", fontsize=11, weight='bold', labelpad=5)
    ax.set_ylabel("Hasil Pengukuran (µg/m3)", fontsize=9, weight='bold', labelpad=5)
    ax.set_ylim(0, max_y_val + (max_y_val * 0.25))
    ax.grid(axis='y', linestyle='--', alpha=0.5)
    for spine in ['top', 'right']: ax.spines[spine].set_visible(False)
    plt.tight_layout()
    plt.savefig(output_name, transparent=True, bbox_inches='tight')
    plt.close()

def main():
    df = fetch_data_from_gdrive()
    df.columns = df.columns.str.strip()
    
    df_valid = df.dropna(subset=['PM10', 'PM2.5', 'PM1']).copy()
    df_valid = df_valid[pd.to_numeric(df_valid['PM10'], errors='coerce').notnull()]
    df_valid = df_valid[pd.to_numeric(df_valid['PM2.5'], errors='coerce').notnull()]
    df_valid = df_valid[pd.to_numeric(df_valid['PM1'], errors='coerce').notnull()]
    
    hari_h = df_valid.iloc[-1]
    tgl_terakhir = str(hari_h['Tanggal']).strip()

    # Cek apakah tanggal ini sudah pernah terkirim
    log_file = os.path.join(BASE_DIR, "last_sent.txt")
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            if f.read().strip() == tgl_terakhir:
                print(f"✅ Data tanggal '{tgl_terakhir}' sudah pernah dikirim sebelumnya. Skip.")
                return

    print(f"🚀 Data baru terdeteksi tanggal '{tgl_terakhir}'. Memproses infografis...")

    colors_standard = ["#27ae60", "#2980b9", "#f1c40f", "#e74c3c", "#8e44ad"]
    lim_pm10 = [0, 50, 150, 350, 420, 500]
    lim_pm25 = [0, 15.5, 55.4, 150.4, 250.4, 500]

    chart_pm10_path = os.path.join(BASE_DIR, 'chart_pm10.png')
    chart_pm25_path = os.path.join(BASE_DIR, 'chart_pm25.png')
    chart_pm1_path  = os.path.join(BASE_DIR, 'chart_pm1.png')

    buat_grafik_conditional(df, 'PM10', lim_pm10, colors_standard, chart_pm10_path)
    buat_grafik_conditional(df, 'PM2.5', lim_pm25, colors_standard, chart_pm25_path)
    buat_grafik_conditional(df, 'PM1', None, None, chart_pm1_path)

    base_img = Image.open(BG_FILE).convert("RGBA").resize((1080, 1920))
    draw = ImageDraw.Draw(base_img)

    font_poppins       = get_font("Poppins-Bold.ttf", 20)
    font_cuaca_besar   = get_font("Aileron-Regular.otf", 18)  
    font_public_sans   = get_font("PublicSans-Bold.ttf", 18)
    font_public_sans_s = get_font("PublicSans-Bold.ttf", 15)  
    font_spartan_giant = get_font("LeagueSpartan-Bold.ttf", 110) 

    txt_tgl = str(hari_h['Tanggal'])
    bbox_tgl = draw.textbbox((0, 0), txt_tgl, font=font_poppins)
    tgl_w = bbox_tgl[2] - bbox_tgl[0] + 24
    draw.rectangle([335.5, 194.1, 335.5 + tgl_w, 194.1 + 36], fill="#247571")
    draw.text((335.5 + 12, 194.1 + 4), txt_tgl, font=font_poppins, fill="white")

    status_cuaca = str(hari_h['Cuaca']).strip()
    base_y_bar = 416
    icon_path = os.path.join(FOLDER_ICON, f"{status_cuaca}.png")
    if os.path.exists(icon_path):
        w_icon = Image.open(icon_path).convert("RGBA").resize((36, 54))
        base_img.paste(w_icon, (210, int(base_y_bar - 18)), w_icon)
        text_x_start = 255
    else:
        text_x_start = 215

    draw.text((text_x_start, int(base_y_bar - 1)), status_cuaca, font=font_cuaca_besar, fill="white")

    for g_path, pos in [(chart_pm10_path, (8, 512)), (chart_pm25_path, (22, 870)), (chart_pm1_path, (31, 1227))]:
        g_img = Image.open(g_path)
        g_img_hd = g_img.resize((int(g_img.size[0] * 0.3333), int(g_img.size[1] * 0.3333)), Image.Resampling.LANCZOS)
        base_img.paste(g_img_hd, pos, g_img_hd)

    parameters = [
        {"name": "PM10", "y_box": 516, "y_time": 566, "val": hari_h['PM10'], "time": hari_h['Jam_PM10'], "lim": lim_pm10, "colors": colors_standard, "is_pm1": False},
        {"name": "PM2.5", "y_box": 863, "y_time": 913, "val": hari_h['PM2.5'], "time": hari_h['Jam_PM2.5'], "lim": lim_pm25, "colors": colors_standard, "is_pm1": False},
        {"name": "PM1", "y_box": 1210, "y_time": 1260, "val": hari_h['PM1'], "time": hari_h['Jam_PM1'], "lim": None, "colors": None, "is_pm1": True}
    ]

    for p in parameters:
        x1, y1, x2, y2 = 740, p["y_box"], 980, p["y_box"] + 250
        for offset in range(0, x2-x1, 16):
            draw.line([(x1+offset, y1), (min(x1+offset+10, x2), y1)], fill="black", width=4)
            draw.line([(x1+offset, y2), (min(x1+offset+10, x2), y2)], fill="black", width=4)
        for offset in range(0, y2-y1, 16):
            draw.line([(x1, y1+offset), (x1, min(y1+offset+10, y2))], fill="black", width=4)
            draw.line([(x2, y1+offset), (x2, min(y1+offset+10, y2))], fill="black", width=4)

        p_name_w = draw.textbbox((0, 0), p["name"], font=font_public_sans)[2] - draw.textbbox((0, 0), p["name"], font=font_public_sans)[0] + 20
        draw.rectangle([760, p["y_box"] + 10, 760 + p_name_w, p["y_box"] + 40], fill="#247571")
        draw.text((770, p["y_box"] + 12), p["name"], font=font_public_sans, fill="white")
        draw.text((760, p["y_time"]), format_jam_otomatis(p["time"]), font=font_public_sans_s, fill="#247571")

        num_str = str(int(p["val"]))
        bbox_num = draw.textbbox((0, 0), num_str, font=font_spartan_giant)
        num_w, num_h = bbox_num[2] - bbox_num[0], bbox_num[3] - bbox_num[1]
        center_x, center_y = x1 + (x2 - x1) / 2, y1 + (y2 - y1) / 2
        num_x, num_y = center_x - (num_w / 2), center_y - (num_h / 2) + 10

        c_formatting = "white" if p["is_pm1"] else dapatkan_warna_indikator(p["val"], p["lim"], p["colors"])
        for sx in [-3, 0, 3]:
            for sy in [-3, 0, 3]:
                draw.text((num_x+sx, num_y+sy), num_str, font=font_spartan_giant, fill="black")
        draw.text((num_x, num_y), num_str, font=font_spartan_giant, fill=c_formatting)

        txt_unit = "µg/m³"
        font_unit = get_font("PublicSans-Bold.ttf", 22)
        bbox_unit = draw.textbbox((0, 0), txt_unit, font=font_unit)
        unit_w, unit_h = bbox_unit[2] - bbox_unit[0], bbox_unit[3] - bbox_unit[1]
        unit_x, unit_y = center_x - (unit_w / 2), y2 - unit_h - 20

        if p["is_pm1"]:
            draw.text((unit_x, unit_y), txt_unit, font=font_unit, fill="black")
        else:
            draw.rectangle([unit_x - 10, unit_y - 4, unit_x + unit_w + 10, unit_y + unit_h + 6], fill=c_formatting)
            draw.text((unit_x, unit_y), txt_unit, font=font_unit, fill="white")

    # Render Gambar ke Bytes
    final_img = base_img.convert("RGB")
    img_byte_arr = io.BytesIO()
    final_img.save(img_byte_arr, format='PNG')
    img_bytes = img_byte_arr.getvalue()

    # Hapus file temporary
    for f_temp in [chart_pm10_path, chart_pm25_path, chart_pm1_path]:
        if os.path.exists(f_temp): os.remove(f_temp)

    # Buat Pesan Telegram
    nama_hari = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    nama_bulan = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
    waktu_sekarang = datetime.datetime.now()
    tgl_info = f"{nama_hari[waktu_sekarang.weekday()]}, {waktu_sekarang.day:02d} {nama_bulan[waktu_sekarang.month]} {waktu_sekarang.year}"

    pm1_val, pm25_val, pm10_val = int(hari_h['PM1']), int(hari_h['PM2.5']), int(hari_h['PM10'])
    kat_pm25, kat_pm10 = hitung_kategori_pm25(pm25_val), hitung_kategori_pm10(pm10_val)

    teks_msg = f"""*Informasi Kualitas Udara Kota Palu Harian*

🗓️ {tgl_info}
🕑 PM1: {format_jam_otomatis(hari_h['Jam_PM1'])}
   PM2.5: {format_jam_otomatis(hari_h['Jam_PM2.5'])}
   PM10: {format_jam_otomatis(hari_h['Jam_PM10'])}
🏠 Jl. Sapta Marga, Kel. Birobuli Utara, Kec. Palu Selatan

Hasil pemantauan kualitas udara partikulat:
PM1 = {pm1_val} µgram/m3 
PM2.5 = {pm25_val} µgram/m3 (*{kat_pm25}*)
PM10  = {pm10_val} µgram/m3 (*{kat_pm10}*)
Kondisi Cuaca = *{hari_h['Cuaca']}*

Salam,
*Stasiun Pemantau Atmosfer Global Lore Lindu Bariri*"""

    # Send to Telegram
    url_photo = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    files = {'photo': ('infografis.png', img_bytes, 'image/png')}
    data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': teks_msg, 'parse_mode': 'Markdown'}
    
    res = requests.post(url_photo, data=data, files=files).json()
    if res.get("ok"):
        print("🎉 Berhasil dikirim ke Channel Telegram!")
        with open(log_file, "w") as f:
            f.write(tgl_terakhir)
    else:
        print(f"⚠️ Gagal kirim ke Telegram: {res.get('description')}")

if __name__ == "__main__":
    main()
