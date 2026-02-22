import streamlit as st
import google.generativeai as genai
from PIL import Image, ImageDraw, ImageFont
import barcode
from barcode.writer import ImageWriter
import pdfplumber
import io
import os

# ================= 1. 页面配置与状态初始化 =================
st.set_page_config(page_title="LxU 电商 AI 助手", page_icon="🚀", layout="wide")
st.title("LxU 专属电商工具集 (Gemini 引擎)")

# 初始化 Session State
state_keys = ['pdf_keywords', 'trans_result', 'label_img', 'last_code']
for key in state_keys:
    if key not in st.session_state:
        st.session_state[key] = "" if 'img' not in key else None

# ================= 2. 侧边栏配置 =================
with st.sidebar:
    st.header("⚙️ 全局配置")
    # 提醒：Gemini Key 目前建议直接在侧边栏手动输入
    api_key = st.text_input("Gemini API Key", type="password", help="从 Google AI Studio 获取")
    st.divider()
    st.markdown("### 🛠️ 使用指南")
    st.caption("1. 粘贴/上传截图可自动识别韩文卖点")
    st.caption("2. 50x30mm 标签自带 MADE IN CHINA 标识")

# ================= 3. 核心工具函数 =================

def call_gemini_api(prompt, contents, key):
    """极致兼容版 Gemini 调用"""
    if not key:
        st.error("请先在左侧输入 API Key！")
        return None
    try:
        genai.configure(api_key=key)
        # 核心修复：使用最基础的模型名称，避开 404 错误
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content([prompt] + contents)
        return response.text
    except Exception as e:
        st.error(f"API 调用失败: {str(e)}")
        return None

def generate_label_50x30(code, title, option):
    """生成 50x30mm 标准货品标签"""
    width, height = 400, 240
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)
    
    # --- 条码渲染 ---
    try:
        code128 = barcode.get('code128', code, writer=ImageWriter())
        barcode_buffer = io.BytesIO()
        code128.write(barcode_buffer, options={"module_height": 10.0, "font_size": 1, "text_distance": 1})
        barcode_img = Image.open(barcode_buffer).resize((360, 100))
        img.paste(barcode_img, (20, 85))
    except: st.error("条码生成失败")

    # --- 字体加载 ---
    def get_font(size):
        # 优先寻找中文字体，否则回退
        font_candidates = ["/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf", "C:/Windows/Fonts/msyh.ttc", "Arial.ttf"]
        for p in font_candidates:
            if os.path.exists(p): return ImageFont.truetype(p, size)
        return ImageFont.load_default()

    f_t, f_o, f_f = get_font(28), get_font(24), get_font(20)

    # 绘制内容
    draw.text((width/2, 35), title, fill='black', font=f_t, anchor="mm")
    draw.text((width/2, 70), option, fill='black', font=f_o, anchor="mm")
    draw.text((width/2, 195), code, fill='black', font=f_f, anchor="mm")
    draw.text((width/2, 220), "MADE IN CHINA", fill='black', font=f_f, anchor="mm")
    return img

# ================= 4. 前端交互界面 =================

t1, t2, t3 = st.tabs(["📑 智能提词/标题", "🇰🇷 本土化翻译", "🏷️ 50x30 标签生成"])

# --- Tab 1: 提词/标题 ---
with t1:
    st.subheader("分析产品详情 (Gemini 原生多模态)")
    up_f = st.file_uploader("点击上传或直接将截图拖入此处", type=["png", "jpg", "jpeg", "pdf"], key="up1")
    if st.button("生成 LxU 专属方案", type="primary"):
        if up_f:
            with st.spinner("Gemini 正在读图..."):
                prompt = "你是一个Coupang运营专家。请分析图片并输出：3个韩文核心关键词，1个以LxU开头的韩文标题。直接输出结果。"
                content = [Image.open(up_f)] if not up_f.name.endswith('.pdf') else [extract_text_from_pdf(up_f)]
                st.session_state.pdf_keywords = call_gemini_api(prompt, content, api_key)

    if st.session_state.pdf_keywords:
        st.success("✅ 分析完成")
        st.text_area("建议结果", st.session_state.pdf_keywords, height=180)

# --- Tab 2: 翻译 ---
with t2:
    st.subheader("营销级本土化翻译")
    cola, colb = st.columns(2)
    with cola: tin = st.text_area("文字输入", placeholder="在此输入中文或韩文...")
    with colb: iin = st.file_uploader("截图识别翻译", type=["png", "jpg", "jpeg"])
    
    if st.button("开始本土翻译", type="primary"):
        with st.spinner("正在润色..."):
            prompt = "你是一个韩国本土电商专家，将内容翻译/润色为极具促单感的本土韩文。直接输出。"
            conts = [tin] if tin else []
            if iin: conts.append(Image.open(iin))
            st.session_state.trans_result = call_gemini_api(prompt, conts, api_key)
    
    if st.session_state.trans_result:
        st.text_area("翻译结果", st.session_state.trans_result, height=180)

# --- Tab 3: 标签 ---
with t3:
    st.subheader("50x30mm 打印规范标签")
    r1, r2, r3 = st.columns(3)
    c_code = r1.text_input("SKU/条码", "880123456789")
    c_name = r2.text_input("产品名", "LxU Brand Product")
    c_spec = r3.text_input("规格", "Color: Yellow | Size: L")
    
    if st.button("生成标签图片"):
        st.session_state.label_img = generate_label_50x30(c_code, c_name, c_spec)
        st.session_state.last_code = c_code
        
    if st.session_state.label_img:
        st.image(st.session_state.label_img, width=400)
        buf = io.BytesIO()
        st.session_state.label_img.save(buf, format="PNG")
        st.download_button("💾 下载并去打印", buf.getvalue(), f"{st.session_state.last_code}.png")

def extract_text_from_pdf(f):
    with pdfplumber.open(f) as p: return "".join([page.extract_text() for page in p.pages])
