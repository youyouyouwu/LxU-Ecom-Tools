import streamlit as st
import streamlit.components.v1 as components
import google.generativeai as genai
from PIL import Image, ImageDraw, ImageFont
import barcode
from barcode.writer import ImageWriter
import io
import os
import time
import json

# ================= 1. 核心工具函数 (布局与逻辑) =================

def wrap_text_pil(text, font, max_width, draw_surface):
    """自动折行函数"""
    lines = []
    paragraphs = text.split('\n')
    for paragraph in paragraphs:
        words = paragraph.split(' ')
        current_line = words[0]
        for word in words[1:]:
            test_line = current_line + " " + word
            if draw_surface.textlength(test_line, font=font) <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        lines.append(current_line)
    return lines

def make_label_50x30(sku, title, spec):
    """50x30mm 标签 1:1 复刻版 (Code 128)"""
    width, height = 1000, 600 
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)

    def load_font(size, is_bold=False):
        font_paths = [
            "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 
            "/usr/share/fonts/truetype/nanum/NanumGothic.ttf", 
            "C:/Windows/Fonts/malgunbd.ttf", "Arial.ttf"
        ]
        if not is_bold: font_paths.reverse()
        for p in font_paths:
            if os.path.exists(p): return ImageFont.truetype(p, size)
        return ImageFont.load_default()

    # --- 1. 顶部条形码 (Code 128) ---
    try:
        code_factory = barcode.get_barcode_class('code128')
        c128 = code_factory(sku, writer=ImageWriter())
        buf = io.BytesIO()
        c128.write(buf, options={"module_height": 22.0, "module_width": 0.4, "font_size": 0, "quiet_zone": 1})
        b_img = Image.open(buf).resize((900, 240)) 
        img.paste(b_img, (50, 25)) 
    except: pass

    # --- 2. 绘制 SKU (条码正下方) ---
    f_sku = load_font(68, is_bold=True)
    draw.text((500, 315), sku, fill='black', font=f_sku, anchor="mm")

    # --- 3. 绘制底部 MADE IN CHINA ---
    f_bottom = load_font(42)
    draw.text((500, 560), "MADE IN CHINA", fill='black', font=f_bottom, anchor="mm")

    # --- 4. 绘制中间标题 (防溢出折行) ---
    f_title = load_font(52, is_bold=True)
    full_title = f"{title} {spec}".strip()
    max_text_width = 800
    line_padding = 6 
    line_height = f_title.getbbox("A")[3] + line_padding
    wrapped_lines = wrap_text_pil(full_title, f_title, max_text_width, draw)
    
    center_y_area = 450
    start_y = center_y_area - ((len(wrapped_lines) * line_height) / 2) + (line_height / 2)

    current_y = start_y
    for line in wrapped_lines:
        draw.text((500, current_y), line, fill='black', font=f_title, anchor="mm")
        current_y += line_height
    return img

def render_copy_button(text):
    """带反馈的一键复制按钮"""
    html_code = f"""
    <!DOCTYPE html>
    <html><head><style>
        body {{ margin: 0; padding: 2px; font-family: sans-serif; }}
        .container {{ display: flex; align-items: center; }}
        .text-box {{ flex-grow: 1; padding: 8px 12px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; width: 100%; box-sizing: border-box; background: #fdfdfd; }}
        .copy-btn {{ padding: 8px 15px; background: #fff; border: 1px solid #ddd; border-radius: 4px; margin-left: 8px; cursor: pointer; font-weight: bold; min-width: 80px; transition: 0.2s; }}
    </style></head>
    <body><div class="container">
        <input type="text" value="{text}" id="q" class="text-box" readonly>
        <button onclick="c()" id="b" class="copy-btn">复制</button>
    </div>
    <script>
    function c() {{
        var i = document.getElementById("q"); i.select(); document.execCommand("copy");
        var b = document.getElementById("b"); b.innerText = "✅ 成功";
        b.style.background = "#dcfce7"; b.style.borderColor = "#86efac";
        setTimeout(()=>{{ b.innerText = "复制"; b.style.background = "#fff"; b.style.borderColor = "#ddd"; }}, 2000);
    }}
    </script></body></html>
    """
    components.html(html_code, height=45)

# ================= 2. 界面配置与侧边栏 =================

st.set_page_config(page_title="LxU 测款指挥舱", layout="wide")

with st.sidebar:
    st.header("⚙️ 引擎配置")
    api_key = st.text_input("API Key", value=st.secrets.get("GEMINI_API_KEY", ""), type="password")
    if not api_key: st.stop()
    genai.configure(api_key=api_key)
        
    st.divider()
    st.header("🏷️ 50x30 标签 (紧凑版)")
    v_sku = st.text_input("货号 (SKU)", "S0033507379541")
    v_title = st.text_input("品名", "[LxU] 용접돋보기 고글형 확대경")
    v_spec = st.text_input("规格", "1.00배율 2개입")
    
    if st.button("生成标签并预览", use_container_width=True, type="primary"):
        st.session_state.l_img = make_label_50x30(v_sku, v_title, v_spec)
        
    if 'l_img' in st.session_state:
        st.image(st.session_state.l_img, use_column_width=True)
        b = io.BytesIO()
        st.session_state.l_img.save(b, format="PNG", dpi=(300, 300))
        st.download_button("📥 下载标签", b.getvalue(), f"{v_sku}.png", use_container_width=True)

# ================= 3. 主界面 (识图流) =================

st.title("⚡ LxU 测款指挥舱")
st.info("💡 **操作秘籍**：微信截图后直接按 `Ctrl+V` 粘贴。图片会自动进入下方折叠区预览。")

files = st.file_uploader("📥 全局粘贴/拖拽区", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True)

if files:
    for f in files:
        with st.expander(f"🖼️ 预览: {f.name}", expanded=False):
            st.image(f, use_column_width=True)
            
        with st.chat_message("assistant"):
            try:
                model = genai.GenerativeModel("gemini-2.5-flash")
                # 强化 Prompt，确保 JSON 纯净
                prompt = """任务：作为 LxU 专家，提取 5 个精准韩文商品名词。
                必须严格按 JSON 输出，禁止任何额外说明：
                {
                  "keywords": [{"kr": "韩文名词", "cn": "翻译"}...],
                  "name_cn": "LxU [中文品名]",
                  "name_kr": "LxU [对应韩文品名]"
                }"""
                with st.spinner(f"⚡ 正在深度分析 {f.name} ..."):
                    res = model.generate_content([f, prompt])
                    # 强力清洗数据
                    clean_res = res.text.replace("```json", "").replace("```", "").strip()
                    data = json.loads(clean_res)
                
                st.markdown(f"### 📦 {f.name} 提取结果")
                for i, item in enumerate(data.get('keywords', [])):
                    c1, c2, c3 = st.columns([0.5, 6, 4])
                    c1.write(f"**{i+1}**")
                    with c2: render_copy_button(item.get('kr', ''))
                    c3.write(f"<div style='padding-top:12px;'>{item.get('cn', '')}</div>", unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("##### 🏷️ 内部管理品名")
                nc1, nc2 = st.columns([1, 9]); nc1.write("中文")
                with nc2: render_copy_button(data.get('name_cn', ''))
                kc1, kc2 = st.columns([1, 9]); kc1.write("韩文")
                with kc2: render_copy_button(data.get('name_kr', ''))
                st.divider()
            except Exception as e:
                st.error(f"提取失败，原因：{str(e)}")
