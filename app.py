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
import re # 💡 引入正则，强力清洗 JSON

# ================= 1. 初始化状态锁 (确保识图结果不因下载而消失) =================
if 'extraction_data' not in st.session_state:
    st.session_state.extraction_data = []

# ================= 2. 核心工具函数 =================

def wrap_text_pil(text, font, max_width, draw_surface):
    """自动折行函数 (第二功能核心)"""
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
    """第二功能：50x30mm 紧凑版标签 (保持不动)"""
    width, height = 1000, 600 
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)

    def load_font(size, is_bold=False):
        font_paths = [
            "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 
            "/usr/share/fonts/truetype/nanum/NanumGothic.ttf", 
            "NanumGothicBold.ttf", "C:/Windows/Fonts/malgunbd.ttf"
        ]
        if not is_bold: font_paths.reverse()
        for p in font_paths:
            if os.path.exists(p): return ImageFont.truetype(p, size)
        return ImageFont.load_default()

    try:
        code_factory = barcode.get_barcode_class('code128')
        c128 = code_factory(sku, writer=ImageWriter())
        buf = io.BytesIO()
        c128.write(buf, options={"module_height": 22.0, "module_width": 0.4, "font_size": 0, "quiet_zone": 1})
        b_img = Image.open(buf).resize((900, 240))
        img.paste(b_img, (50, 25)) 
    except: pass

    f_sku = load_font(68, is_bold=True)
    f_title = load_font(52, is_bold=True)
    f_bottom = load_font(42)

    draw.text((500, 315), sku, fill='black', font=f_sku, anchor="mm")
    draw.text((500, 560), "MADE IN CHINA", fill='black', font=f_bottom, anchor="mm")

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
    """带 ✅ 反馈的复制组件"""
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
st.title("⚡ LxU 测款指挥舱 (双核稳健版)")

with st.sidebar:
    st.header("⚙️ 引擎配置")
    api_key = st.text_input("Gemini API Key", value=st.secrets.get("GEMINI_API_KEY", ""), type="password")
    if api_key: genai.configure(api_key=api_key)
    else: st.warning("请输入 API Key"); st.stop()

col_left, col_right = st.columns([1.1, 0.9], gap="large")

# --- 左侧板块：识图词提取 (第一功能完善版) ---
with col_left:
    st.subheader("🎯 测款识图提取")
    st.info("直接按 `Ctrl+V` 粘贴图片或点击上传")
    
    files = st.file_uploader("📥 图片上传区", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True, key="uploader")
    
    if files:
        if st.button("🚀 极速提取核心词", type="primary", use_container_width=True):
            new_data = []
            for f in files:
                model = genai.GenerativeModel("gemini-2.5-flash")
                # 💡 使用你指定的“之前能用”的 Prompt
                prompt = """
                任务：极简模式测款提取。
                请直接分析产品图，**必须严格按照以下 JSON 格式输出结果**。
                严禁输出任何废话、Markdown 表格或解释文字，只能输出纯 JSON 代码：

                ⚠️ 【极其重要的搜索词提取规则】：
                提取的 5 个韩文搜索词【必须是韩国买家在 Coupang 真实搜索时使用的具体商品名词】。
                【严禁】输出任何缺乏购物意图的形容词、功能描述或泛泛之词。
                
                {
                  "keywords": [
                    {"kr": "词1", "cn": "翻译1"},
                    {"kr": "词2", "cn": "翻译2"},
                    {"kr": "词3", "cn": "翻译3"},
                    {"kr": "词4", "cn": "翻译4"},
                    {"kr": "词5", "cn": "翻译5"}
                  ],
                  "name_cn": "LxU [品名]",
                  "name_kr": "LxU [品名]"
                }
                """
                with st.spinner(f"正在深度解析 {f.name}..."):
                    try:
                        res = model.generate_content([f, prompt])
                        # 💡 强力清洗：利用正则提取大括号内的内容，彻底告别“解析失败”
                        json_match = re.search(r"\{.*\}", res.text, re.DOTALL)
                        if json_match:
                            parsed_json = json.loads(json_match.group())
                            new_data.append({"filename": f.name, "result": parsed_json})
                        else:
                            st.error(f"{f.name} 未能识别到有效的 JSON 数据")
                    except Exception as e:
                        st.error(f"{f.name} 识图出错: {str(e)}")
            st.session_state.extraction_data = new_data

    # 展示识图结果
    for idx, item in enumerate(st.session_state.extraction_data):
        with st.container(border=True):
            st.write(f"📦 **源文件：{item['filename']}**")
            for i, kw in enumerate(item['result'].get('keywords', [])):
                c1, c2, c3 = st.columns([0.1, 0.6, 0.3])
                c1.write(f"**{i+1}**")
                with c2: render_copy_button(kw['kr'], f"kw_{idx}_{i}")
                c3.write(f"<div style='padding-top:12px; color:#666;'>{kw['cn']}</div>", unsafe_allow_html=True)
            st.write("---")
            render_copy_button(item['result'].get('name_cn', ''), f"cn_{idx}")
            render_copy_button(item['result'].get('name_kr', ''), f"kr_{idx}")

# --- 右侧板块：50x30 标签生成 (第二功能锁定版) ---
with col_right:
    st.subheader("🏷️ 标签生成工具")
    with st.form("label_form"):
        v_sku = st.text_input("货号 (SKU)", "S0033507379541")
        v_title = st.text_input("品名 (韩/英)", "[LxU] 용접돋보기 고글형 확대경")
        v_spec = st.text_input("规格", "1.00배율 2개입")
        submit = st.form_submit_button("生成高清预览", use_container_width=True)
        
        if submit:
            st.session_state.current_label_img = make_label_50x30(v_sku, v_title, v_spec)
            st.session_state.current_sku = v_sku

    if 'current_label_img' in st.session_state:
        st.image(st.session_state.current_label_img, use_column_width=True)
        buf = io.BytesIO()
        st.session_state.current_label_img.save(buf, format="PNG", dpi=(300, 300))
        st.download_button("📥 下载标签 (PNG)", buf.getvalue(), f"{st.session_state.current_sku}.png", use_container_width=True)
