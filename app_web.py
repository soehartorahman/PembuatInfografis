import os
import io
import urllib.request
import datetime
import locale
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import LinearSegmentedColormap
from PIL import Image, ImageDraw, ImageFont
import streamlit as st

# ==========================================
# 1. KONFIGURASI HALAMAN WEB STREAMLIT
# ==========================================
st.set_page_config(
    page_title="Generator Infografis GAW Bariri", 
    page_icon="⚡",
    layout="centered"
)

st.title("⚡ Automated IG Story Infographics Generator")
st.subheader("Dashboard Admin GAW Bariri BMKG")
st.markdown("---")

# Direktori Dasar Aset
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BG_FILE = os.path.join(BASE_DIR, "background.png")
FOLDER_ICON = os.path.join(BASE_DIR, "icons_cuaca")
FOLDER_FONT = os.path.join(BASE_DIR, "fonts")

# Sidebar Status Sistem
st.sidebar.header("🛠️ Status Aset Sistem")
if os.path.exists(BG_FILE):
    st.sidebar.success("✅ background.png Tersedia")
else:
    st.sidebar.error("⚠️ background.png tidak ditemukan!")

# ==========================================
# 2. PANEL INPUT ADMIN (USER INTERFACE)
# ==========================================
st.markdown("### 🎨 Pengaturan Warna Narasi Himbauan")
col1, col2 = st.columns(2)
with col1:
    warna_dasar = st.color_picker("Pilih Warna Teks Dasar", "#1C5360")
with col2:
    warna_highlight = st.color_picker("Pilih Warna Teks Highlight", "#FF0000")

st.markdown("### 📝 Narasi Himbauan Kesehatan")
default_advice = (
    "• Menggunakan masker apabila berada di area [padat lalu lintas] dan area luas yang kering untuk [terlindungi dari debu].\n"
    "• [Tidak membakar sampah] rumah tangga di halaman rumah karena asap dan baunya dapat [mencemari udara] dan mengganggu lingkungan sekitar.\n"
    "• Nilai [ISPU>100] (Status Tidak Sehat), maka masyarakat diminta [mengurangi aktivitas di luar ruangan]."
)
txt_himbauan = st.text_area(
    "Gunakan kurung siku [kata] untuk memberikan warna highlight pada kata tersebut", 
    value=default_advice, 
    height=180
)

# ==========================================
# 3. FUNGSI LOGIKA UTAMA (BACKEND GENERATOR)
# ==========================================
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
    try:
        doc_id = "16XVJ6C8LMg8PTzCoHSCfVu5lfqyis63P"
        csv_url = f"https://docs.google.com/spreadsheets/d/{doc_id}/export?format=csv"
        req = urllib.request.Request(csv_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            csv_data = response.read().decode('utf-8')
        return pd.read_csv(io.StringIO(csv_data))
    except Exception as e:
        raise Exception(f"Gagal koneksi Google Drive: {str(e)}")

def buat_grafik_conditional(df, col_name, batas_nilai, warna_list, output_name):
    df_clean = df.dropna(subset=[col_name, 'Tanggal']).copy()
    df_clean = df_clean[pd.to_numeric(df_clean[col_name], errors='coerce').notnull()]
    df_7 = df_clean.tail(7).copy().reset_index(drop=True)
    
    x = np.arange(len(df_7))
    y = df_7[col_name].astype(float).values
    dates = df_7['Tanggal'].values

    fig, ax = plt.subplots(figsize=(7, 2.775), dpi=300)
    fig.patch.set_alpha(0.0)
    ax.patch.set_alpha(0.0)

    if batas_nilai and warna_list:
        for i in range(len(df_7) - 1):
            y_start = y[i]
            y_end = y[i+1]
            
            def dapatkan_warna_murni(val):
                for b_idx in range(len(batas_nilai)-1):
                    if batas_nilai[b_idx] <= val <= batas_nilai[b_idx+1]:
                        return warna_list[b_idx]
                return warna_list[-1]
            
            c_start = dapatkan_warna_murni(y_start)
            c_end = dapatkan_warna_murni(y_end)
            
            cmap_lokal = LinearSegmentedColormap.from_list("lokal_kronologis", [c_start, c_end])
            x_seg = np.linspace(x[i], x[i+1], 30)
            y_seg = np.linspace(y_start, y_end, 30)
            
            points = np.array([x_seg, y_seg]).T.reshape(-1, 1, 2)
            segments = np.concatenate([points[:-1], points[1:]], axis=1)
            
            norm_lokal = plt.Normalize(vmin=0.0, vmax=1.0)
            array_progress = np.linspace(0.0, 1.0, len(segments))
            
            lc = LineCollection(segments, cmap=cmap_lokal, norm=norm_lokal, linewidth=4, zorder=2)
            lc.set_array(array_progress)
            ax.add_collection(lc)
    else:
        ax.plot(x, y, color="#e67e22", linewidth=4, zorder=2)

    max_y_val = max(y) if len(y) > 0 and max(y) > 0 else 50
    for idx in range(len(df_7)):
        val = y[idx]
        pt_color = "#e67e22" 
        if batas_nilai and warna_list:
            for b_idx in range(len(batas_nilai)-1):
                if batas_nilai[b_idx] <= val <= batas_nilai[b_idx+1]:
                    pt_color = warna_list[b_idx]
                    break
        ax.scatter(x[idx], val, color=pt_color, edgecolor='black', s=90, zorder=3)
        ax.text(x[idx], val + (max_y_val * 0.05), f"{int(val)}", ha='center', va='bottom', fontsize=11, weight='bold', color='black')

    ax.set_xticks(x)
    ax.set_xticklabels(dates, fontsize=9)
    ax.set_xlabel("Tanggal Pengukuran", fontsize=10, weight='bold', labelpad=5)
    ax.set_ylabel("Hasil Pengukuran (µg/m3)", fontsize=9, weight='bold', labelpad=5)
    ax.set_ylim(0, max_y_val + (max_y_val * 0.25))
    ax.grid(axis='y', linestyle='--', alpha=0.5)
    for spine in ['top', 'right']: ax.spines[spine].set_visible(False)
    plt.tight_layout()
    plt.savefig(output_name, transparent=True, bbox_inches='tight')
    plt.close()

def format_jam_otomatis(jam_str):
    try:
        jam_bersih = str(jam_str).strip().replace('.', ':')
        if "-" in jam_bersih: jam_bersih = jam_bersih.split("-")[0].strip()
        waktu_awal = datetime.datetime.strptime(jam_bersih, "%H:%M")
        waktu_akhir = waktu_awal + datetime.timedelta(minutes=10)
        return f"{waktu_awal.strftime('%H:%M')} - {waktu_akhir.strftime('%H:%M')} WITA"
    except Exception: return f"{jam_str} WITA"

def dapatkan_warna_indikator(val, limits, colors):
    if not limits: return "black"
    for i in range(len(limits)-1):
        if limits[i] <= val <= limits[i+1]: return colors[i]
    return colors[-1]

def draw_justified_himbauan_dynamic(draw, text, start_x, start_y, max_width, max_height, w_dasar, w_hl):
    target_font_size = 24  
    lines_data = []
    
    while target_font_size >= 12:
        font_regular = get_font("PublicSans-Regular.ttf", target_font_size)
        font_bold    = get_font("PublicSans-Bold.ttf", target_font_size)
        
        lines_data = []
        paragraphs = text.split('\n')
        spacing_y = 10
        
        for para in paragraphs:
            if not para.strip(): continue
            is_bullet = para.strip().startswith('•')
            clean_para = para.strip()[1:].strip() if is_bullet else para.strip()
            
            tokens = []
            inside = False
            current = ""
            for char in clean_para:
                if char == '[':
                    if current: tokens.append((current, False))
                    current = ""
                    inside = True
                elif char == ']':
                    if current: tokens.append((current, True))
                    current = ""
                    inside = False
                else:
                    current += char
            if current: tokens.append((current, inside))
            
            bullet_prefix = "• " if is_bullet else ""
            prefix_w = draw.textbbox((0, 0), bullet_prefix, font=font_bold)[2] if is_bullet else 0
            indent_w = prefix_w + 10 if is_bullet else 0
            
            current_line_tokens = []
            current_w = indent_w
            
            for token_text, is_highlight in tokens:
                words = token_text.split(' ')
                for i, word in enumerate(words):
                    if i > 0 or not token_text.startswith(' '):
                        word_to_test = " " + word if current_line_tokens else word
                    else:
                        word_to_test = word
                        
                    f_active = font_bold if is_highlight else font_regular
                    word_w = draw.textbbox((0, 0), word_to_test, font=f_active)[2]
                    
                    if current_w + word_w <= max_width:
                        current_line_tokens.append((word_to_test, is_highlight))
                        current_w += word_w
                    else:
                        if current_line_tokens:
                            lines_data.append((current_line_tokens, is_bullet, indent_w))
                        current_line_tokens = [(word, is_highlight)]
                        current_w = indent_w + draw.textbbox((0, 0), word, font=f_active)[2]
                        is_bullet = False
                        
            if current_line_tokens:
                lines_data.append((current_line_tokens, is_bullet, indent_w))
        
        line_h = draw.textbbox((0, 0), "Hg", font=font_bold)[3] - draw.textbbox((0, 0), "Hg", font=font_bold)[1]
        total_height = len(lines_data) * (line_h + spacing_y)
        
        if total_height <= max_height:
            break
        target_font_size -= 1  

    font_regular = get_font("PublicSans-Regular.ttf", target_font_size)
    font_bold    = get_font("PublicSans-Bold.ttf", target_font_size)
    line_h = draw.textbbox((0, 0), "Hg", font=font_bold)[3] - draw.textbbox((0, 0), "Hg", font=font_bold)[1]
    
    curr_y = start_y
    for tokens_list, has_bullet, left_indent in lines_data:
        curr_x = start_x
        if has_bullet:
            draw.text((curr_x, curr_y), "•", font=font_bold, fill=w_dasar)
            curr_x += left_indent
        else:
            curr_x = start_x + left_indent
            
        for text_val, highlight_flag in tokens_list:
            f_type = font_bold if highlight_flag else font_regular
            f_color = w_hl if highlight_flag else w_dasar
            draw.text((curr_x, curr_y), text_val, font=f_type, fill=f_color)
            curr_x += draw.textbbox((0, 0), text_val, font=f_type)[2]
        curr_y += line_h + 12

# Fungsi Hitung Kategori Khusus PM2.5 (Standar BMKG Terbaru)
def hitung_kategori_pm25(nilai):
    try:
        nilai = float(nilai) 
    except (ValueError, TypeError):
        return "Data Belum Terisi"
        
    if nilai <= 15.5:
        return "Baik"
    elif nilai <= 55.4:
        return "Sedang"
    elif nilai <= 150.4:
        return "Tidak Sehat"
    elif nilai <= 250.4:
        return "Sangat Tidak Sehat"
    else:
        return "Berbahaya"

# Fungsi Hitung Kategori Khusus PM10 (Standar ISPU KLHK/BMKG)
def hitung_kategori_pm10(nilai):
    try:
        nilai = float(nilai) 
    except (ValueError, TypeError):
        return "Data Belum Terisi"
        
    if nilai <= 50:
        return "Baik"
    elif nilai <= 100:
        return "Sedang"
    elif nilai <= 150:
        return "Tidak Sehat"
    elif nilai <= 300:
        return "Sangat Tidak Sehat"
    else:
        return "Berbahaya"

# ==========================================
# 4. AKSI GENERATOR (TOMBOL EKSEKUSI)
# ==========================================
st.markdown("---")
if st.button("🚀 GENERATE INFOGRAFIS ONLINE", type="primary", use_container_width=True):
    if not os.path.exists(BG_FILE):
        st.error(f"File template '{BG_FILE}' tidak ditemukan di server!")
    else:
        with st.spinner("Sedang mengambil data BMKG & menggambar infografis HD..."):
            try:
                df = fetch_data_from_gdrive()
                df.columns = df.columns.str.strip()
                
                col_pm1 = "PM1"   
                col_pm25 = "PM2.5"   
                col_pm10 = "PM10"
                col_jam_pm1  = "Jam_PM1" 
                col_jam_pm25 = "Jam_PM2.5" 
                col_jam_pm10 = "Jam_PM10"
                col_tanggal = "Tanggal"
                col_cuaca   = "Cuaca"

                df_valid = df.dropna(subset=[col_pm10, col_pm25, col_pm1]).copy()
                df_valid = df_valid[pd.to_numeric(df_valid[col_pm10], errors='coerce').notnull()]
                df_valid = df_valid[pd.to_numeric(df_valid[col_pm25], errors='coerce').notnull()]
                df_valid = df_valid[pd.to_numeric(df_valid[col_pm1], errors='coerce').notnull()]
                
                hari_h = df_valid.iloc[-1]
                colors_standard = ["#27ae60", "#2980b9", "#f1c40f"] 
                lim_pm10 = [0, 50, 150, 350]
                lim_pm25 = [0, 15.5, 55.4, 150.4]

                chart_pm10_path = os.path.join(BASE_DIR, 'chart_pm10.png')
                chart_pm25_path = os.path.join(BASE_DIR, 'chart_pm25.png')
                chart_pm1_path  = os.path.join(BASE_DIR, 'chart_pm1.png')

                buat_grafik_conditional(df, col_pm10, lim_pm10, colors_standard, chart_pm10_path)
                buat_grafik_conditional(df, col_pm25, lim_pm25, colors_standard, chart_pm25_path)
                buat_grafik_conditional(df, col_pm1, None, None, chart_pm1_path)

                base_img = Image.open(BG_FILE).convert("RGBA").resize((1080, 1920))
                draw = ImageDraw.Draw(base_img)

                font_poppins       = get_font("Poppins-Bold.ttf", 20)
                font_cuaca_besar   = get_font("Aileron-Regular.otf", 18)  
                font_public_sans   = get_font("PublicSans-Bold.ttf", 18)
                font_public_sans_s = get_font("PublicSans-Bold.ttf", 15)  
                font_spartan_giant = get_font("LeagueSpartan-Bold.ttf", 150) 

                txt_tgl = str(hari_h[col_tanggal])
                bbox_tgl = draw.textbbox((0, 0), txt_tgl, font=font_poppins)
                tgl_w = bbox_tgl[2] - bbox_tgl[0] + 24
                draw.rectangle([335.5, 194.1, 335.5 + tgl_w, 194.1 + 36], fill="#247571")
                draw.text((335.5 + 12, 194.1 + 4), txt_tgl, font=font_poppins, fill="white")

                status_cuaca = str(hari_h[col_cuaca]).strip()
                base_y_bar = 416
                
                icon_path = os.path.join(FOLDER_ICON, f"{status_cuaca}.png")
                if os.path.exists(icon_path):
                    w_icon = Image.open(icon_path).convert("RGBA").resize((36, 54))
                    icon_x = 210
                    icon_y = int(base_y_bar - 18) 
                    base_img.paste(w_icon, (icon_x, icon_y), w_icon)
                    text_x_start = int(icon_x + 30 + 15)
                else:
                    text_x_start = int(200 + 15)

                text_y_pos = int(base_y_bar - 1)
                draw.text((text_x_start, text_y_pos), status_cuaca, font=font_cuaca_besar, fill="white")

                for g_path, pos in [(chart_pm10_path, (8, 512)), (chart_pm25_path, (22, 870)), (chart_pm1_path, (31, 1227))]:
                    g_img = Image.open(g_path)
                    w_original, h_original = g_img.size
                    scale_factor = 0.3333 
                    g_img_hd = g_img.resize((int(w_original * scale_factor), int(h_original * scale_factor)), Image.Resampling.LANCZOS)
                    base_img.paste(g_img_hd, pos, g_img_hd)

                parameters = [
                    {"name": "PM10", "y_box": 516, "y_time": 566, "y_unit_base": 716.5, "val": hari_h[col_pm10], "time": hari_h[col_jam_pm10], "lim": lim_pm10, "colors": colors_standard, "is_pm1": False},
                    {"name": "PM2.5", "y_box": 863, "y_time": 913, "y_unit_base": 1063.5, "val": hari_h[col_pm25], "time": hari_h[col_jam_pm25], "lim": lim_pm25, "colors": colors_standard, "is_pm1": False},
                    {"name": "PM1", "y_box": 1210, "y_time": 1260, "y_unit_base": 1411, "val": hari_h[col_pm1], "time": hari_h[col_jam_pm1], "lim": None, "colors": None, "is_pm1": True}
                ]

                for p in parameters:
                    x1, y1, x2, y2 = 740, p["y_box"], 980, p["y_box"] + 250
                    
                    for offset in range(0, x2-x1, 16):
                        draw.line([(x1+offset, y1), (min(x1+offset+10, x2), y1)], fill="black", width=4)
                        draw.line([(x1+offset, y2), (min(x1+offset+10, x2), y2)], fill="black", width=4)
                    for offset in range(0, y2-y1, 16):
                        draw.line([(x1, y1+offset), (x1, min(y1+offset+10, y2))], fill="black", width=4)
                        draw.line([(x2, y1+offset), (x2, min(y1+offset+10, y2))], fill="black", width=4)

                    bbox_p_name = draw.textbbox((0, 0), p["name"], font=font_public_sans)
                    p_name_w = bbox_p_name[2] - bbox_p_name[0] + 20
                    draw.rectangle([760, p["y_box"] + 10, 760 + p_name_w, p["y_box"] + 40], fill="#247571")
                    draw.text((770, p["y_box"] + 12), p["name"], font=font_public_sans, fill="white")
                    
                    draw.text((760, p["y_time"]), format_jam_otomatis(p["time"]), font=font_public_sans_s, fill="#247571")

                    num_str = str(int(p["val"]))
                    bbox_num = draw.textbbox((0, 0), num_str, font=font_spartan_giant)
                    num_w, num_h = bbox_num[2] - bbox_num[0], bbox_num[3] - bbox_num[1]
                    
                    center_x = x1 + (x2 - x1) / 2
                    center_y = y1 + (y2 - y1) / 2
                    num_x = center_x - (num_w / 2)
                    num_y = center_y - (num_h / 2) + 10  

                    c_formatting = "white" if p["is_pm1"] else dapatkan_warna_indikator(p["val"], p["lim"], p["colors"])
                    for sx in [-3, 0, 3]:
                        for sy in [-3, 0, 3]:
                            draw.text((num_x+sx, num_y+sy), num_str, font=font_spartan_giant, fill="black")
                    draw.text((num_x, num_y), num_str, font=font_spartan_giant, fill=c_formatting)

                    txt_unit = "µg/m³"
                    font_unit = get_font("PublicSans-Bold.ttf", 22)
                    bbox_unit = draw.textbbox((0, 0), txt_unit, font=font_unit)
                    unit_w, unit_h = bbox_unit[2] - bbox_unit[0], bbox_unit[3] - bbox_unit[1]
                    
                    unit_x = center_x - (unit_w / 2)
                    unit_y = y2 - unit_h - 20

                    if p["is_pm1"]:
                        draw.text((unit_x, unit_y), txt_unit, font=font_unit, fill="black")
                    else:
                        draw.rectangle([unit_x - 10, unit_y - 4, unit_x + unit_w + 10, unit_y + unit_h + 6], fill=c_formatting)
                        draw.text((unit_x, unit_y), txt_unit, font=font_unit, fill="white")

                # Memproses Justified Teks dengan Warna Pilihan User dari Web UI
                draw_justified_himbauan_dynamic(draw, txt_himbauan, 8.3, 1590, 800, 250, warna_dasar, warna_highlight)

                nama_file_aman = str(hari_h[col_tanggal]).replace(' ', '_').replace('/', '-')
                nama_output = f"Infografis_Harian_{nama_file_aman}.png"
                nama_output_path = os.path.join(BASE_DIR, nama_output)
                
                # Simpan final image
                final_img = base_img.convert("RGB")
                final_img.save(nama_output_path)

                # Hapus file grafik temporary
                for f_temp in [chart_pm10_path, chart_pm25_path, chart_pm1_path]:
                    if os.path.exists(f_temp): os.remove(f_temp)

                # Tampilkan Preview Hasil di Streamlit Web
                st.success("✨ Infografis Berhasil Dibuat!")
                st.image(final_img, caption="Live Preview Hasil Infografis (HD)", use_container_width=True)
                
                # Tombol Download untuk Admin Web
                img_byte_arr = io.BytesIO()
                final_img.save(img_byte_arr, format='PNG')
                img_byte_arr = img_byte_arr.getvalue()

                st.download_button(
                    label="💾 DOWNLOAD GAMBAR INFOGRAFIS",
                    data=img_byte_arr,
                    file_name=nama_output,
                    mime="image/png",
                    use_container_width=True
                )
                
                st.write("---")
                st.subheader("📝 Narasi Otomatis untuk WhatsApp")
    
                # 🔹 A. Mengambil Hari & Tanggal Otomatis Saat Ini dalam Bahasa Indonesia
                nama_hari = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
                nama_bulan = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
                
                waktu_sekarang = datetime.datetime.now()
                hari_id = nama_hari[waktu_sekarang.weekday()]
                bulan_id = nama_bulan[waktu_sekarang.month]
                tgl_info = f"{hari_id}, {waktu_sekarang.day:02d} {bulan_id} {waktu_sekarang.year}"
    
                # 🔹 B. Mengambil Nilai Riil PM & Cuaca dari baris terakhir DataFrame
                pm1_val = hari_h[col_pm1]
                pm25_val = hari_h[col_pm25]
                pm10_val = hari_h[col_pm10]
                cuaca_val = hari_h[col_cuaca]
    
                # 🔹 C. Mengambil Nilai Tertinggi 7 Harian & Waktu Pengamatan Berdasarkan Waktu yang Ditambah 10 Menit (+10)
                try:
                    df['PM1'] = pd.to_numeric(df['PM1'], errors='coerce')
                    df['PM2.5'] = pd.to_numeric(df['PM2.5'], errors='coerce')
                    df['PM10'] = pd.to_numeric(df['PM10'], errors='coerce')

                    df_bersih = df.dropna(subset=['PM1', 'Tanggal'])

                    df_7harian = df_bersih.tail(7).copy()
    
                    max_pm1_val = df_7harian['PM1'].max()
                    max_pm25_val = df_7harian['PM2.5'].max()
                    max_pm10_val = df_7harian['PM10'].max()
    
                    tgl_max_pm1 = df_7harian.loc[df_7harian['PM1'].idxmax(), 'Tanggal']
                    tgl_max_pm25 = df_7harian.loc[df_7harian['PM2.5'].idxmax(), 'Tanggal']
                    tgl_max_pm10 = df_7harian.loc[df_7harian['PM10'].idxmax(), 'Tanggal']
    
                    max_pm1 = f"{int(max_pm1_val)} µgram/m3 tanggal {tgl_max_pm1}"
                    max_pm25 = f"{int(max_pm25_val)} µgram/m3 tanggal {tgl_max_pm25}"
                    max_pm10 = f"{int(max_pm10_val)} µgram/m3 tanggal {tgl_max_pm10}"
                    
                    # Konversi otomatis ke format +10 menit dengan WITA
                    waktu_info_pm1 = format_jam_otomatis(hari_h[col_jam_pm1])
                    waktu_info_pm25 = format_jam_otomatis(hari_h[col_jam_pm25])
                    waktu_info_pm10 = format_jam_otomatis(hari_h[col_jam_pm10])
                except Exception as e:
                    import traceback
                    st.error(f"Blok TRY gagal karena error: {e}")
                    st.code(traceback.format_exc())
                    
                    max_pm1 = f"{int(pm1_val)} µgram/m3 tanggal {hari_h[col_tanggal]}"
                    max_pm25 = f"{int(pm25_val)} µgram/m3 tanggal {hari_h[col_tanggal]}"
                    max_pm10 = f"{int(pm10_val)} µgram/m3 tanggal {hari_h[col_tanggal]}"
                    
                    waktu_info_pm1 = format_jam_otomatis("15:00")
                    waktu_info_pm25 = format_jam_otomatis("15:00")
                    waktu_info_pm10 = format_jam_otomatis("15:00")

                # Memisahkan kategori perhitungan logika khusus masing-masing parameter
                kat_pm25 = hitung_kategori_pm25(pm25_val)
                kat_pm10 = hitung_kategori_pm10(pm10_val)

                # 🔹 F. Merakit Template Teks WhatsApp
                teks_wa = f"""*Informasi Kualitas Udara Kota Palu Harian*

🗓️ {tgl_info}
🕑 PM1: {waktu_info_pm1}
   PM2.5: {waktu_info_pm25}
   PM10: {waktu_info_pm10}
🏠 Jl. Sapta Marga, Kel. Birobuli Utara, Kec. Palu Selatan

Hasil pemantauan kualitas udara partikulat sebagai berikut:

PM1 = {pm1_val} µgram/m3 
PM2.5 = {pm25_val} µgram/m3 (*{kat_pm25}*)
PM10  = {pm10_val} µgram/m3 (*{kat_pm10}*)
Kondisi Cuaca = *{cuaca_val}*

Nilai Pengamatan Tertinggi 7 Harian:
PM1 = {max_pm1}
PM2.5 = {max_pm25}
PM10 = {max_pm10}

‼️ Himbauan ‼️

1. Menggunakan masker untuk terlindungi dari debu.
2. Tidak membakar sampah di halaman rumah.
3. Apabila Nilai ISPU>100, masyarakat mengurangi aktivitas di luar ruangan.

Salam,

*Stasiun Pemantau Atmosfer Global Lore Lindu Bariri*"""

                st.info("Klik tombol salin di pojok kanan bawah kotak teks untuk menyalin narasi otomatis.")
                st.code(teks_wa, language="text")
            except Exception as e:
                st.error(f"Terjadi Kendala Sistem:\n{str(e)}")
