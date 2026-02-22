import streamlit as st
import google.generativeai as genai
from PIL import Image, ImageDraw, ImageFont
import barcode
from barcode.writer import ImageWriter
import pdfplumber
import io
import os
import time

# ================= 1. 页面配置 =================
st.set_page_config(page_title="LxU 电商 AI 助手-旗舰版", page_icon="🚀", layout="wide")
st.title("LxU 专属电商工具集 (Flash 稳定版)")

# 初始化 Session State
state_keys = ['keywords_res', 'trans_res', 'label_img', 'last_sku']
for key in state_keys:
    if key not in st.session_state:
        st.session_state[key] = "" if 'img' not in key else None

# ================= 2. 侧边栏 API 配置 =================
with st.sidebar:
    st.header("⚙️ 引擎配置")
    # 优先从 Secrets 获取，没有则手动输入
    sc_key = st.secrets.get("GEMINI_API_KEY", "")
    api_key = st.text_input("Gemini API Key", value=sc_key, type="password")
    st.info("当前模式：混合文件处理流 (支持超长详情页)")
    st.divider()
    st.markdown("### 🏷️ 标签规范\n- 尺寸: 50x30mm\n- 包含: MADE IN CHINA")

# ================= 3. 核心工具函数 =================

def process_file_and_call_gemini(prompt, uploaded_file, key):
    """参考成功代码：采用先上传、后轮询的稳定流"""
    if not key:
        st.error("请在左侧配置 API Key！")
        return None
    
    genai.configure(api_key=key)
    # 使用你之前代码中成功的模型名称
    model = genai.GenerativeModel(model_name="gemini-1.5-flash") 

    try:
        # 1. 保存临时文件
        temp_path = f"temp_upload_{uploaded_file.name}"
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # 2. 上传至 Google 服务器
        gen_file = genai.upload_file(path=temp_path)
        
        # 3. 轮询检查状态 (解决 404 或处理中报错)
        while gen_file.state.name == "PROCESSING":
            time.sleep(2)
            gen_file = genai.get_file(gen_file.name)
        
        # 4. 生成内容
        response = model.generate_content([gen_file, prompt])
        
        # 5. 清理临时文件
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        return response.text
    except Exception as e:
        st.error(f"处理失败: {str(e)}")
        return None

def generate_label_50x30(code, title, option):
    """标准 50x30mm 标签绘制"""
    width, height = 400, 240 # 203 DPI
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)
    
    # 条码生成
    try:
        code128 = barcode.get('code128', code, writer=ImageWriter())
        barcode_buffer = io.BytesIO()
        code128.write(barcode_buffer, options={"module_height": 10.0, "font_size": 1, "text_distance": 1})
        barcode_img = Image.open(barcode_buffer).resize((360, 95))
        img.paste(barcode_img, (20, 85))
    except: pass

    # 字体加载逻辑
    def get_f(s):
        ps = ["/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf", "C:/Windows/Fonts/msyh.ttc", "Arial.ttf"]
        for p in ps:
            if os.path.exists(p): return ImageFont.truetype(p, s)
        return ImageFont.load_default()

    draw.text((200, 35), title, fill='black', font=get_f(28), anchor="mm")
    draw.text((200, 70), option, fill='black', font=get_f(24), anchor="mm")
    draw.text((200, 190), code, fill='black', font=get_f(22), anchor="mm")
    draw.text((200, 220), "MADE IN CHINA", fill='black', font=get_f(22), anchor="mm")
    return img

# ================= 4. 前端交互 =================

t1, t2, t3 = st.tabs(["📑 智能提词(稳定版)", "🇰🇷 本土化翻译", "🏷️ 50x30 标签生成"])

with t1:
    st.subheader("分析详情页 (支持超长图片)")
    up_f1 = st.file_uploader("上传详情页截图", type=["png", "jpg", "jpeg", "pdf"], key="u1")
    if st.button("生成 LxU 提词方案", type="primary"):
        if up_f1:
            with st.spinner("⚡ 正在通过 Flash 引擎扫描长图..."):
                prompt = "你是一个韩国Coupang运营专家。请分析图片并输出：3个韩文核心关键词，1个以LxU开头的韩文标题。不要Markdown加粗。"
                st.session_state.keywords_res = process_file_and_call_gemini(prompt, up_f1, api_key)

    if st.session_state.keywords_res:
        st.text_area("提词结果", st.session_state.keywords_res, height=200)

with t2:
    st.subheader("营销级本土化翻译")
    cola, colb = st.columns(2)
    t_in = cola.text_area("文字翻译", placeholder="输入中文...")
    i_in = colb.file_uploader("截图翻译", type=["png", "jpg", "jpeg"])
    
    if st.button("开始本土化润色"):
        with st.spinner("正在注入本土灵魂..."):
            prompt = "你是一个韩国本土电商专家，请将内容翻译为地道的、有促单感的韩文营销文案。直接输出结果。"
            if i_in:
                st.session_state.trans_res = process_file_and_call_gemini(prompt + f"\n附加文案: {t_in}", i_in, api_key)
            else:
                genai.configure(api_key=api_key)
                m = genai.GenerativeModel('gemini-1.5-flash')
                st.session_state.trans_res = m.generate_content(prompt + t_in).text

    if st.session_state.trans_res:
        st.text_area("翻译结果", st.session_state.trans_res, height=200)

with t3:
    st.subheader("50x30mm 打印规范标签")
    c1, c2, c3 = st.columns(3)
    sk = c1.text_input("SKU/条码", "880123456789")
    ti = c2.text_input("产品名", "LxU Brand")
    op = c3.text_input("规格", "Size: L | Color: White")
    
    if st.button("生成预览"):
        st.session_state.label_img = generate_label_50x30(sk, ti, op)
        st.session_state.last_sku = sk
        
    if st.session_state.label_img:
        st.image(st.session_state.label_img, width=400)
        b = io.BytesIO()
        st.session_state.label_img.save(b, format="PNG")
        st.download_button("💾 下载标签", b.getvalue(), f"LxU_{st.session_state.last_sku}.png")
