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

# ================= 1. 核心工具函数 (紧凑防溢出优化版) =================

def wrap_text_pil(text, font, max_width, draw_surface):
    """辅助函数：实现自动折行"""
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
    """
    生成 LxU 专属 50x30mm 高清标签
    优化：收紧布局，防止打印溢出
    """
    width, height = 1000, 600 
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)

    def load_font(size, is_bold=False):
        # 优先读取 NanumGothic
        font_paths = [
            "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 
            "/usr/share/fonts/truetype/nanum/NanumGothic.ttf", 
            "C:/Windows/Fonts/malgunbd.ttf", "Arialbd.ttf"
        ]
        if not is_bold: font_paths.reverse()
        for p in font_paths:
            if os.path.exists(p): return ImageFont.truetype(p, size)
        return ImageFont.load_default()

    # --- 1. 顶部条形码 (Code 128) ---
    try:
        code128 = barcode.get('code128', sku, writer=ImageWriter())
        buf = io.BytesIO()
        # 略微缩小条码宽度，留出边缘
        code128.write(buf, options={"module_height": 22.0, "module_width": 0.4, "font_size": 0, "quiet_zone": 1})
        b_img = Image.open(buf).resize((900, 240)) # 从960收缩到900
        img.paste(b_img, (50, 25)) 
    except: pass

    # --- 2. 字体定义 (全线缩小，防止溢出) ---
    f_sku = load_font(68, is_bold=True)     # 从75下调
    f_title = load_font(52, is_bold=True)   # 从70下调，核心优化点
    f_bottom = load_font(42)                # 从45下调

    # --- 3. 绘制 SKU ---
    draw.text((500, 315), sku, fill='black', font=f_sku, anchor="mm")

    # --- 4. 绘制底部 MADE IN CHINA (固定位置) ---
    draw.text((500, 560), "MADE IN CHINA", fill='black', font=f_bottom, anchor="mm")

    # --- 5. 绘制中间标题 (增加左右边距 + 紧凑行距) ---
    full_title = f"{title} {spec}".strip()
    
    # 安全宽度：从920收缩到800，确保左右大留白
    max_text_width = 800
    line_padding = 6 # 紧凑行间距
    line_height = f_title.getbbox("A")[3] + line_padding
    
    wrapped_lines = wrap_text_pil(full_title, f_title, max_text_width, draw)
    total_text_height = len(wrapped_lines) * line_height
    
    # 在 SKU (y=350) 和 底部 (y=540) 之间的中心区域
    center_y_area = 450
    start_y = center_y_area - (total_text_height / 2) + (line_height / 2)

    current_y = start_y
    for line in wrapped_lines:
        draw.text((500, current_y), line, fill='black', font=f_title, anchor="mm")
        current_y += line_height
    
    return img

# ================= 2. 交互界面逻辑 =================

def render_copy_button(text):
    html_code = f"""
    <!DOCTYPE html>
    <html><head><style>
        body {{ margin: 0; padding: 2px; font-family: sans-serif; }}
        .container {{ display: flex; align-items: center; }}
        .text-box {{ flex-grow: 1; padding: 8px 12px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; width: 100%; box-sizing: border-box; background: #fdfdfd; }}
        .copy-btn {{ padding: 8px 15px; background: #fff; border: 1px solid #ddd; border-radius: 4px; margin-left: 8px; cursor: pointer; font-weight: bold; min-width: 80px; }}
    </style></head>
    <body><div class="container">
        <input type="text" value="{text}" id="q" class="text-box" readonly>
        <button onclick="c()" id="b" class="copy-btn">复制</button>
    </div>
    <script>
    function c() {{
        var i = document.getElementById("q"); i.select(); document.execCommand("copy");
        var b = document.getElementById("b"); b.innerText = "✅ 已复制";
        setTimeout(()=>{{ b.innerText = "复制"; }}, 2000);
    }}
    </script></body></html>
    """
    components.html(html_code, height=45)

st.set_page_config(page_title="LxU 测款指挥舱", layout="wide")

with st.sidebar:
    st.header("⚙️ 引擎配置")
    api_key = st.text_input("API Key", value=st.secrets.get("GEMINI_API_KEY", ""), type="password")
    if not api_key: st.stop()
    genai.configure(api_key=api_key)
        
    st.divider()
    st.header("🏷️ 50x30 标签 (紧凑打印版)")
    v_sku = st.text_input("货号 (SKU)", "S0033507379541")
    v_title = st.text_input("品名", "[LxU] 용접돋보기 고글형 확대경")
    v_spec = st.text_input("规格", "1.00배율 2개입")
    
    if st.button("生成标签并预览", use_container_width=True, type="primary"):
        st.session_state.l_img = make_label_50x30(v_sku, v_title, v_spec)
        
    if 'l_img' in st.session_state:
        st.image(st.session_state.l_img, use_column_width=True, caption="已优化安全边距，防止溢出")
        b = io.BytesIO()
        st.session_state.l_img.save(b, format="PNG", dpi=(300, 300))
        st.download_button("📥 下载标签 (PNG)", b.getvalue(), f"{v_sku}.png", use_container_width=True)

st.title("⚡ LxU 测款指挥舱")
files = st.file_uploader("📥 直接 Ctrl+V 粘贴截图", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True)

if files:
    for f in files:
        with st.expander(f"🖼️ 预览: {f.name}"): st.image(f, use_column_width=True)
        with st.chat_message("assistant"):
            try:
                model = genai.GenerativeModel("gemini-2.5-flash")
                prompt = "提取 5 个精准韩文商品名词。JSON格式：{\"keywords\": [{\"kr\": \"名词\", \"cn\": \"翻译\"}...], \"name_cn\": \"LxU [中文]\", \"name_kr\": \"LxU [韩文]\"}"
                res = model.generate_content([f, prompt])
                data = json.loads(res.text.replace("```json", "").replace("```", "").strip())
                st.markdown(f"### 📦 {f.name}")
                for i, item in enumerate(data.get('keywords', [])):
                    c1, c2, c3 = st.columns([0.5, 6, 4])
                    c1.write(f"{i+1}")
                    with c2: render_copy_button(item.get('kr', ''))
                    c3.write(item.get('cn', ''))
                st.divider()
            except: st.error("提取失败")
