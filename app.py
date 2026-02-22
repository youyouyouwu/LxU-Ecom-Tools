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
import re

# ================= 1. 状态锁与页面配置 =================
st.set_page_config(page_title="LxU 测款指挥舱", layout="wide")

# 核心状态保护：确保左右板块互不干扰，下载不重置
if 'extractions' not in st.session_state:
    st.session_state.extractions = []
if 'label_preview' not in st.session_state:
    st.session_state.label_preview = None

# ================= 2. 核心工具函数 (1:1 样本复刻) =================

def wrap_text_pil(text, font, max_width, draw_surface):
    """自动折行：确保中间文字不溢出"""
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
    """高清 50x30mm 标签生成器 (Code 128 格式)"""
    width, height = 1000, 600 
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)

    def load_font(size, is_bold=False):
        # 针对 Streamlit Cloud Linux 环境优化路径
        font_paths = [
            "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
            "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
            "C:/Windows/Fonts/malgunbd.ttf", "Arialbd.ttf"
        ]
        if not is_bold: font_paths.reverse()
        for p in font_paths:
            if os.path.exists(p): return ImageFont.truetype(p, size)
        return ImageFont.load_default()

    # --- 1. 绘制条形码 (Code 128) ---
    try:
        code_factory = barcode.get_barcode_class('code128')
        c128 = code_factory(sku, writer=ImageWriter())
        buf = io.BytesIO()
        c128.write(buf, options={"module_height": 22.0, "module_width": 0.4, "font_size": 0, "quiet_zone": 1})
        b_img = Image.open(buf).resize((900, 240))
        img.paste(b_img, (50, 25))
    except: pass

    # --- 2. 绘制文本 (根据样本比例优化) ---
    f_sku = load_font(68, is_bold=True)
    f_title = load_font(52, is_bold=True)
    f_bottom = load_font(42)

    # 货号 SKU
    draw.text((500, 315), sku, fill='black', font=f_sku, anchor="mm")
    # 强制产地标识
    draw.text((500, 560), "MADE IN CHINA", fill='black', font=f_bottom, anchor="mm")

    # 中间标题 (自动折行且垂直居中)
    full_title = f"{title} {spec}".strip()
    max_text_width = 800  # 安全边距
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

def render_copy_button(text, unique_key):
    """带反馈的一键复制按钮"""
    html_code = f"""
    <!DOCTYPE html>
    <html><head><style>
        body {{ margin: 0; padding: 2px; font-family: sans-serif; }}
        .container {{ display: flex; align-items: center; }}
        .text-box {{ flex-grow: 1; padding: 8px 12px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; width: 100%; box-sizing: border-box; background: #fdfdfd; }}
        .copy-btn {{ padding: 8px 15px; background: #fff; border: 1px solid #ddd; border-radius: 4px; margin-left: 8px; cursor: pointer; font-weight: bold; min-width: 90px; transition: 0.2s; }}
    </style></head>
    <body><div class="container">
        <input type="text" value="{text}" id="q_{unique_key}" class="text-box" readonly>
        <button onclick="c()" id="b_{unique_key}" class="copy-btn">复制</button>
    </div>
    <script>
    function c() {{
        var i = document.getElementById("q_{unique_key}"); i.select(); document.execCommand("copy");
        var b = document.getElementById("b_{unique_key}"); b.innerText = "✅ 成功";
        setTimeout(()=>{{ b.innerText = "复制"; }}, 2000);
    }}
    </script></body></html>
    """
    components.html(html_code, height=45)

# ================= 3. 页面布局：识图(左) vs 标签(右) =================

# 侧边栏 API 配置
with st.sidebar:
    st.header("⚙️ 引擎配置")
    api_key = st.text_input("Gemini API Key", value=st.secrets.get("GEMINI_API_KEY", ""), type="password")
    if api_key: genai.configure(api_key=api_key)
    else: st.warning("👈 请先填入 API Key"); st.stop()

st.title("⚡ LxU 测款指挥舱 (最终满血版)")

col_ext, col_lab = st.columns([1.1, 0.9], gap="large")

# --- 板块 1：测款识图提取 (左侧独立板块) ---
with col_ext:
    st.subheader("🎯 极速识图提取")
    st.info("💡 粘贴截图(Ctrl+V)后点击下方按钮")
    files = st.file_uploader("📥 图片上传/粘贴区", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True, key="uploader")
    
    if files:
        if st.button("🚀 开始极速解析", type="primary", use_container_width=True):
            new_exts = []
            for f in files:
                model = genai.GenerativeModel("gemini-2.5-flash")
                prompt = "提取5个韩国买家真实搜索的具体商品名词。禁止说明，必须严格 JSON 格式：{\"keywords\": [{\"kr\": \"名词\", \"cn\": \"翻译\"}...], \"name_cn\": \"LxU [名]\", \"name_kr\": \"LxU [名]\"}"
                with st.spinner(f"分析 {f.name}..."):
                    try:
                        res = model.generate_content([f, prompt])
                        # 强力清洗：只抓取 JSON 部分，防止解析失败
                        json_match = re.search(r"\{.*\}", res.text, re.DOTALL)
                        if json_match:
                            new_exts.append({"file": f.name, "data": json.loads(json_match.group())})
                    except: st.error(f"{f.name} 解析失败")
            st.session_state.extractions = new_exts

    # 渲染结果 (下载时不会消失)
    for idx, item in enumerate(st.session_state.extractions):
        with st.container(border=True):
            st.write(f"📦 **源文件：{item['file']}**")
            for i, kw in enumerate(item['data'].get('keywords', [])):
                c1, c2, c3 = st.columns([0.1, 0.6, 0.3])
                c1.write(f"{i+1}")
                with c2: render_copy_button(kw['kr'], f"kw_{idx}_{i}")
                c3.write(f"<div style='padding-top:12px; color:#666;'>{kw['cn']}</div>", unsafe_allow_html=True)
            st.write("---")
            render_copy_button(item['data'].get('name_cn', ''), f"cn_{idx}")
            render_copy_button(item['data'].get('name_kr', ''), f"kr_{idx}")

# --- 板块 2：50x30 标签工具 (右侧独立板块) ---
with col_right:
    st.subheader("🏷️ 50x30 标签工具")
    with st.form("label_form"):
        v_sku = st.text_input("货号 (SKU)", "S0033507379541")
        v_title = st.text_input("品名", "[LxU] 용접돋보기 고글형 확대경")
        v_spec = st.text_input("规格", "1.00배율 2개입")
        submit = st.form_submit_button("🔥 生成并锁定预览", use_container_width=True)
        
        if submit:
            st.session_state.label_preview = make_label_50x30(v_sku, v_title, v_spec)
            st.session_state.last_sku = v_sku

    if st.session_state.label_preview:
        st.image(st.session_state.label_preview, use_column_width=True, caption="高清打印预览")
        buf = io.BytesIO()
        st.session_state.label_preview.save(buf, format="PNG", dpi=(300, 300))
        st.download_button("📥 下载标签 (PNG)", buf.getvalue(), f"LxU_{st.session_state.last_sku}.png", use_container_width=True)
