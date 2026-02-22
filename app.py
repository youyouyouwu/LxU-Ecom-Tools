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

# ================= 1. 核心工具函数 (Code 128 深度优化版) =================

def make_label_50x30(sku, title, spec):
    """
    生成 LxU 专属 50x30mm 高清标签
    BarCode 格式：Code 128 (Coupang 标准)
    """
    width, height = 1000, 600 
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)

    def load_font(size):
        # 💡 已配置 packages.txt，首选 Nanum 字体
        font_paths = [
            "/usr/share/fonts/truetype/nanum/NanumGothic.ttf", 
            "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf",
            "NanumGothic.ttf", 
            "C:/Windows/Fonts/malgun.ttf", 
            "Arial.ttf"
        ]
        for p in font_paths:
            if os.path.exists(p):
                return ImageFont.truetype(p, size)
        return ImageFont.load_default()

    try:
        # ✅ 确认为 Code 128 格式，适配物流扫描
        code_factory = barcode.get_barcode_class('code128')
        c128 = code_factory(sku, writer=ImageWriter())
        
        buf = io.BytesIO()
        # 优化 module_width 和 height，确保条码清晰且不重叠
        c128.write(buf, options={
            "module_height": 20.0, 
            "module_width": 0.45, 
            "font_size": 1, 
            "quiet_zone": 2
        })
        b_img = Image.open(buf).resize((920, 260))
        img.paste(b_img, (40, 210))
    except Exception as e:
        st.error(f"条码生成失败: {e}")

    f_main = load_font(65)
    f_sub = load_font(50)
    f_sku = load_font(48)

    # 居中绘制：品名、规格、货号
    draw.text((500, 85), title, fill='black', font=f_main, anchor="mm")
    draw.text((500, 175), spec, fill='black', font=f_sub, anchor="mm")
    draw.text((500, 505), sku, fill='black', font=f_sku, anchor="mm")
    # 强制合规项：MADE IN CHINA
    draw.text((500, 565), "MADE IN CHINA", fill='black', font=f_sku, anchor="mm")
    
    return img

def render_copy_button(text):
    """一键复制 HTML 组件"""
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

# ================= 2. 界面核心逻辑 =================

st.set_page_config(page_title="LxU 测款指挥舱", layout="wide")

with st.sidebar:
    st.header("⚙️ 引擎配置")
    api_key = st.text_input("Gemini API Key", value=st.secrets.get("GEMINI_API_KEY", ""), type="password")
    if not api_key: st.stop()
    genai.configure(api_key=api_key)
        
    st.divider()
    st.header("🏷️ 50x30 标签生成")
    v_sku = st.text_input("货号 (SKU)", "LxU8801234567")
    v_title = st.text_input("品名 (含韩文)", "타이어 공기압 모니터링 캡")
    v_spec = st.text_input("规格", "Size: L | 4pcs")
    
    if st.button("生成高清标签图", use_container_width=True):
        st.session_state.l_img = make_label_50x30(v_sku, v_title, v_spec)
        
    if 'l_img' in st.session_state:
        st.image(st.session_state.l_img, use_column_width=True)
        b = io.BytesIO()
        st.session_state.l_img.save(b, format="PNG", dpi=(300, 300))
        st.download_button("📥 下载标签 (PNG)", b.getvalue(), f"{v_sku}.png", use_container_width=True)

st.title("⚡ LxU 测款指挥舱")
st.info("🚀 **效率满点**：微信截图后，直接在网页空白处 `Ctrl+V`。所有的识图和词语提取均已针对 Coupang 商品名词进行深度优化。")

files = st.file_uploader("📥 全局粘贴/拖拽区", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True)

if files:
    for f in files:
        with st.expander(f"🖼️ 图片预览: {f.name}", expanded=False):
            st.image(f, use_column_width=True)
            
        with st.chat_message("assistant"):
            try:
                model = genai.GenerativeModel("gemini-2.5-flash")
                prompt = "分析图片，提取 5 个精准韩文商品名词。输出纯 JSON (keywords: kr, cn; name_cn; name_kr)。内部品名必须以 LxU 开头。"
                res = model.generate_content([f, prompt])
                data = json.loads(res.text.replace("```json", "").replace("```", "").strip())
                
                st.markdown(f"### 📦 {f.name} 测品提取结果")
                for i, item in enumerate(data.get('keywords', [])):
                    c1, c2, c3 = st.columns([0.5, 6, 4])
                    c1.markdown(f"**{i+1}**")
                    with c2: render_copy_button(item.get('kr', ''))
                    c3.write(item.get('cn', ''))
                
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("##### 🏷️ 内部管理品名")
                lc1, lc2 = st.columns([1, 9])
                lc1.write("CN 中文")
                with lc2: render_copy_button(data.get('name_cn', ''))
                lk1, lk2 = st.columns([1, 9])
                lk1.write("KR 韩文")
                with lk2: render_copy_button(data.get('name_kr', ''))
                st.divider()
            except:
                st.error("解析失败，请检查 API 或图片内容。")
