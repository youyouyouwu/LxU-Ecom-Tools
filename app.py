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

# ================= 1. 核心工具函数 (锁定 NanumGothic) =================

def make_label_50x30(sku, title, spec):
    """
    生成 LxU 专属 50x30mm 高清标签
    针对韩文 NanumGothic 优化
    """
    # 高清画布
    width, height = 1000, 600 
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)

    def load_font(size):
        # 💡 这里的路径是 linux 系统安装 fonts-nanum 后的标准路径
        font_paths = [
            "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",      # Linux (NanumGothic)
            "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",  # Linux (NanumGothic Bold)
            "NanumGothic.ttf",                                     # 如果你手动上传了字体到仓库
            "C:/Windows/Fonts/malgun.ttf",                         # Windows 本地调试用
            "Arial.ttf"                                            # 最后的兜底
        ]
        for p in font_paths:
            if os.path.exists(p):
                return ImageFont.truetype(p, size)
        
        # 如果还是找不到，就在页面报错提醒
        st.error("🚨 没找到 NanumGothic 字体！请确保仓库里有 packages.txt 或上传了字体文件。")
        return ImageFont.load_default()

    try:
        # 渲染 Code128 条形码
        code128 = barcode.get('code128', sku, writer=ImageWriter())
        buf = io.BytesIO()
        code128.write(buf, options={
            "module_height": 18.0, 
            "module_width": 0.4, 
            "font_size": 1, 
            "quiet_zone": 2
        })
        b_img = Image.open(buf).resize((900, 240))
        img.paste(b_img, (50, 220))
    except:
        pass

    # 绘制文本 (针对 1000x600 画布)
    font_main = load_font(65)
    font_sub = load_font(50)
    font_sku = load_font(45)

    # 标题 (英文或韩文)
    draw.text((500, 80), title, fill='black', font=font_main, anchor="mm")
    # 规格
    draw.text((500, 170), spec, fill='black', font=font_sub, anchor="mm")
    # SKU 文本
    draw.text((500, 510), sku, fill='black', font=font_sku, anchor="mm")
    # 强制产地标识
    draw.text((500, 570), "MADE IN CHINA", fill='black', font=font_sku, anchor="mm")
    
    return img

def render_copy_button(text):
    """一键复制组件"""
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
        setTimeout(lambda=>{{ b.innerText = "复制"; }}, 2000);
    }}
    </script></body></html>
    """
    components.html(html_code, height=45)

def process_api(uploaded_file, prompt):
    model = genai.GenerativeModel("gemini-2.5-flash")
    temp = f"t_{int(time.time())}_{uploaded_file.name}"
    with open(temp, "wb") as f: f.write(uploaded_file.getbuffer())
    g_file = genai.upload_file(path=temp)
    res = model.generate_content([g_file, prompt])
    if os.path.exists(temp): os.remove(temp)
    return res.text

# ================= 2. 界面展示 (LxU 指挥舱) =================

st.set_page_config(page_title="LxU 测款指挥舱", layout="wide")

with st.sidebar:
    st.header("⚙️ 引擎配置")
    api_key = st.text_input("API Key", value=st.secrets.get("GEMINI_API_KEY", ""), type="password")
    if not api_key: st.stop()
    genai.configure(api_key=api_key)
        
    st.divider()
    st.header("🏷️ 50x30 标签生成")
    # 💡 默认展示韩文，方便测试
    v_sku = st.text_input("SKU", "LxU8801234567")
    v_title = st.text_input("韩文品名", "나눔고딕 테스트 상품")
    v_spec = st.text_input("规格 (Spec)", "Size: Large | Qty: 1ea")
    
    if st.button("生成高清标签", use_container_width=True):
        st.session_state.l_img = make_label_50x30(v_sku, v_title, v_spec)
        
    if 'l_img' in st.session_state:
        st.image(st.session_state.l_img, use_column_width=True)
        b = io.BytesIO()
        st.session_state.l_img.save(b, format="PNG", dpi=(300, 300))
        st.download_button("📥 下载标签", b.getvalue(), f"{v_sku}.png", use_container_width=True)

st.title("⚡ LxU 测款指挥舱")
files = st.file_uploader("📥 直接 Ctrl+V 粘贴截图", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True)

if files:
    for f in files:
        with st.expander(f"🖼️ 预览: {f.name}"): st.image(f, use_column_width=True)
        with st.chat_message("assistant"):
            p = """提取精准商品名词。JSON格式：
            {"keywords": [{"kr": "韩文名词", "cn": "中文翻译"}...], "name_cn": "LxU [中文]", "name_kr": "LxU [韩文]"}"""
            with st.spinner("分析中..."): 
                try:
                    raw = process_api(f, p)
                    data = json.loads(raw.replace("```json", "").replace("```", "").strip())
                    st.markdown(f"### 📦 {f.name}")
                    for i, item in enumerate(data.get('keywords', [])):
                        c1, c2, c3 = st.columns([0.5, 6, 4])
                        c1.write(f"{i+1}")
                        with c2: render_copy_button(item.get('kr', ''))
                        c3.write(item.get('cn', ''))
                    st.divider()
                except: st.error("提取失败")
