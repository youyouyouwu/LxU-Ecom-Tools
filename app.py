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

# ================= 1. 初始化状态锁 (防止刷新丢失) =================
if 'extraction_results' not in st.session_state:
    st.session_state.extraction_results = [] # 存储识图结果
if 'last_label' not in st.session_state:
    st.session_state.last_label = None     # 存储生成的标签图

# ================= 2. 核心工具函数 =================

def wrap_text_pil(text, font, max_width, draw_surface):
    """自动折行逻辑"""
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
    """50x30mm 高清标签生成 (Code 128)"""
    width, height = 1000, 600 
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)

    def load_font(size, is_bold=False):
        font_paths = [
            "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 
            "/usr/share/fonts/truetype/nanum/NanumGothic.ttf", 
            "NanumGothicBold.ttf", "Arialbd.ttf"
        ]
        if not is_bold: font_paths.reverse()
        for p in font_paths:
            if os.path.exists(p): return ImageFont.truetype(p, size)
        return ImageFont.load_default()

    # 1. 顶部条码
    try:
        code_factory = barcode.get_barcode_class('code128')
        c128 = code_factory(sku, writer=ImageWriter())
        buf = io.BytesIO()
        c128.write(buf, options={"module_height": 22.0, "module_width": 0.4, "font_size": 0, "quiet_zone": 1})
        b_img = Image.open(buf).resize((900, 240))
        img.paste(b_img, (50, 25)) 
    except: pass

    # 2. 绘制文本
    f_sku = load_font(68, is_bold=True)
    f_title = load_font(52, is_bold=True)
    f_bottom = load_font(42)

    draw.text((500, 315), sku, fill='black', font=f_sku, anchor="mm")
    draw.text((500, 560), "MADE IN CHINA", fill='black', font=f_bottom, anchor="mm") #

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

def render_copy_button(text, key):
    """带唯一 Key 的复制组件"""
    html_code = f"""
    <!DOCTYPE html>
    <html><head><style>
        body {{ margin: 0; padding: 2px; font-family: sans-serif; }}
        .container {{ display: flex; align-items: center; }}
        .text-box {{ flex-grow: 1; padding: 8px 12px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; width: 100%; box-sizing: border-box; background: #fdfdfd; }}
        .copy-btn {{ padding: 8px 15px; background: #fff; border: 1px solid #ddd; border-radius: 4px; margin-left: 8px; cursor: pointer; font-weight: bold; min-width: 80px; }}
    </style></head>
    <body><div class="container">
        <input type="text" value="{text}" id="q_{key}" class="text-box" readonly>
        <button onclick="c()" id="b_{key}" class="copy-btn">复制</button>
    </div>
    <script>
    function c() {{
        var i = document.getElementById("q_{key}"); i.select(); document.execCommand("copy");
        var b = document.getElementById("b_{key}"); b.innerText = "✅ 成功";
        setTimeout(()=>{{ b.innerText = "复制"; }}, 2000);
    }}
    </script></body></html>
    """
    components.html(html_code, height=45)

# ================= 3. 页面布局 =================

st.set_page_config(page_title="LxU 测款指挥舱", layout="wide")
st.title("⚡ LxU 测款指挥舱 (双核独立版)")

# 侧边栏仅保留 API 配置
with st.sidebar:
    st.header("⚙️ 引擎配置")
    api_key = st.text_input("Gemini API Key", value=st.secrets.get("GEMINI_API_KEY", ""), type="password")
    if api_key: genai.configure(api_key=api_key)
    else: st.warning("请输入 API Key"); st.stop()

# 主页面分为两列：识图区 (Left) 和 标签区 (Right)
col_left, col_right = st.columns([1.1, 0.9], gap="large")

# --- 左侧板块：极速测款识图 ---
with col_left:
    st.subheader("🎯 测款词语提取")
    st.info("直接在此按 `Ctrl+V` 粘贴图片")
    
    # 识图组件使用独立的 key
    files = st.file_uploader("📥 全局粘贴/拖拽区", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True, key="uploader")
    
    if files:
        if st.button("🚀 开始极速提取", type="primary", use_container_width=True):
            new_results = []
            for f in files:
                model = genai.GenerativeModel("gemini-2.5-flash")
                prompt = "提取5个精准韩文商品名词。JSON格式：{\"keywords\": [{\"kr\": \"名词\", \"cn\": \"翻译\"}...], \"name_cn\": \"LxU [中文]\", \"name_kr\": \"LxU [韩文]\"}"
                with st.spinner(f"正在分析 {f.name}..."):
                    try:
                        res = model.generate_content([f, prompt])
                        clean_json = res.text.replace("```json", "").replace("```", "").strip()
                        new_results.append({"name": f.name, "data": json.loads(clean_json)})
                    except: st.error(f"{f.name} 解析失败")
            st.session_state.extraction_results = new_results

    # 渲染识图结果 (从保险箱取数据)
    for idx, item in enumerate(st.session_state.extraction_results):
        with st.container(border=True):
            st.write(f"📦 **结果：{item['name']}**")
            for i, kw in enumerate(item['data'].get('keywords', [])):
                c1, c2, c3 = st.columns([0.1, 0.6, 0.3])
                c1.write(f"{i+1}")
                with c2: render_copy_button(kw['kr'], f"kw_{idx}_{i}")
                c3.write(f"<div style='padding-top:12px; color:#666;'>{kw['cn']}</div>", unsafe_allow_html=True)
            
            st.write("---")
            render_copy_button(item['data'].get('name_cn', ''), f"cn_{idx}")
            render_copy_button(item['data'].get('name_kr', ''), f"kr_{idx}")

# --- 右侧板块：50x30 标签生成 ---
with col_right:
    st.subheader("🏷️ 50x30 标签工具")
    with st.form("label_form"):
        v_sku = st.text_input("货号 (SKU)", "S0033507379541")
        v_title = st.text_input("品名 (韩文/英文)", "[LxU] 용접돋보기 고글형 확대경")
        v_spec = st.text_input("规格 (Spec)", "1.00배율 2개입")
        submit = st.form_submit_button("🔥 生成高清标签", use_container_width=True)
        
        if submit:
            st.session_state.last_label = make_label_50x30(v_sku, v_title, v_spec)
            st.session_state.last_sku = v_sku

    # 渲染标签预览 (从保险箱取数据)
    if st.session_state.last_label:
        st.image(st.session_state.last_label, use_column_width=True, caption="高清打印预览")
        b = io.BytesIO()
        st.session_state.last_label.save(b, format="PNG", dpi=(300, 300))
        st.download_button(
            label="📥 下载当前标签 (PNG)", 
            data=b.getvalue(), 
            file_name=f"LxU_{st.session_state.last_sku}.png", 
            use_container_width=True,
            key="download_label_btn"
        )
