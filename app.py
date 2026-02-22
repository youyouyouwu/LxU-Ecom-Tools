import streamlit as st
import google.generativeai as genai
from PIL import Image, ImageDraw, ImageFont
import barcode
from barcode.writer import ImageWriter
import pdfplumber
import io
import os

# ================= 1. 页面基础配置 =================
st.set_page_config(page_title="LxU 电商 AI 助手", page_icon="🚀", layout="wide")
st.title("LxU 专属电商工具集 (Gemini 原生多模态)")

# 初始化 Session State (确保切换 Tab 不丢失数据)
for key in ['keywords_res', 'trans_res', 'label_img', 'sku_code']:
    if key not in st.session_state:
        st.session_state[key] = "" if 'img' not in key else None

# ================= 2. 侧边栏 API 配置 =================
with st.sidebar:
    st.header("⚙️ 全局配置")
    api_key = st.text_input("Gemini API Key", type="password", help="请从 Google AI Studio 获取")
    st.divider()
    st.markdown("### 🛠️ 功能说明")
    st.caption("1. 智能提词：支持长图，提取竞品词并生成 LxU 标题")
    st.caption("2. 本土翻译：营销风润色，拒绝机翻")
    st.caption("3. 标签生成：标准 50x30mm 规格")

# ================= 3. 核心功能引擎 =================

def call_gemini(prompt, content_list, key):
    """极致兼容版 Gemini 模型调用"""
    if not key:
        st.error("请在左侧输入 API Key！")
        return None
    try:
        genai.configure(api_key=key)
        # 使用基础模型名称，避开 404 路径报错
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content([prompt] + content_list)
        return response.text
    except Exception as e:
        st.error(f"API 调用失败: {str(e)}")
        return None

def draw_label_50x30(code, title, option):
    """绘制 50mm x 30mm 标签图"""
    # 203 DPI 约为 400x240 像素
    width, height = 400, 240
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)
    
    # --- 1. 生成 Code128 条码 ---
    try:
        code128 = barcode.get('code128', code, writer=ImageWriter())
        barcode_buffer = io.BytesIO()
        code128.write(barcode_buffer, options={"module_height": 10.0, "font_size": 1, "text_distance": 1})
        barcode_img = Image.open(barcode_buffer).resize((360, 95))
        img.paste(barcode_img, (20, 85))
    except: st.error("条码生成失败")

    # --- 2. 加载字体 (针对 Streamlit Cloud 优化) ---
    def load_best_font(size):
        paths = ["/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf", "C:/Windows/Fonts/msyh.ttc", "Arial.ttf"]
        for p in paths:
            if os.path.exists(p): return ImageFont.truetype(p, size)
        return ImageFont.load_default()

    f_title, f_opt, f_footer = load_best_font(28), load_best_font(24), load_best_font(22)

    # --- 3. 写入文本内容 ---
    # 顶部标题
    draw.text((width/2, 35), title, fill='black', font=f_title, anchor="mm")
    # 销售选项
    draw.text((width/2, 70), option, fill='black', font=f_opt, anchor="mm")
    # SKU 文本
    draw.text((width/2, 190), code, fill='black', font=f_footer, anchor="mm")
    # 底部标识 (固定内容)
    draw.text((width/2, 220), "MADE IN CHINA", fill='black', font=f_footer, anchor="mm")
    
    return img

# ================= 4. UI 标签页交互 =================

tab1, tab2, tab3 = st.tabs(["📑 智能提词与标题", "🇰🇷 营销级本土翻译", "🏷️ 50x30 标签生成"])

# --- Tab 1: 智能提词 ---
with tab1:
    st.subheader("分析详情页 (Gemini 视觉引擎，支持长图/PDF)")
    up_f1 = st.file_uploader("点击上传详情页截图", type=["png", "jpg", "jpeg", "pdf"], key="f1")
    if st.button("生成 LxU 运营方案", type="primary"):
        if up_f1:
            with st.spinner("正在读图识别卖点..."):
                prompt = "你是一个韩国Coupang资深运营。请分析内容提取3个核心韩文关键词，并生成一个以LxU开头的韩文产品标题。直接输出，不要废话。"
                if up_f1.name.endswith('.pdf'):
                    with pdfplumber.open(up_f1) as pdf:
                        content = ["".join([page.extract_text() for page in pdf.pages])]
                else:
                    content = [Image.open(up_f1)]
                st.session_state.keywords_res = call_gemini(prompt, content, api_key)

    if st.session_state.keywords_res:
        st.success("✅ 生成完成")
        st.text_area("分析结果", st.session_state.keywords_res, height=180)

# --- Tab 2: 本土翻译 ---
with tab2:
    st.subheader("电商营销语境翻译")
    col1, col2 = st.columns(2)
    txt_in = col1.text_area("文字输入翻译", placeholder="在此粘贴中文描述...")
    img_in = col2.file_uploader("截图识别翻译", type=["png", "jpg", "jpeg"])
    
    if st.button("开始本土翻译", type="primary"):
        with st.spinner("正在润色韩文文案..."):
            prompt = "你是一个韩国本土电商专家，请将文案翻译为地道的、有促单感的韩文营销文案。直接输出结果。"
            contents = [txt_in] if txt_in else []
            if img_in: contents.append(Image.open(img_in))
            st.session_state.trans_res = call_gemini(prompt, contents, api_key)

    if st.session_state.trans_res:
        st.text_area("韩文翻译结果", st.session_state.trans_res, height=200)

# --- Tab 3: 标签生成 ---
with tab3:
    st.subheader("50x30mm 标准货品标签")
    r1, r2, r3 = st.columns(3)
    val_code = r1.text_input("条码/SKU", "880123456789")
    val_title = r2.text_input("产品名", "LxU Brand Product")
    val_spec = r3.text_input("规格选项", "Model: Banana | Size: XL")
    
    if st.button("预览并生成标签"):
        st.session_state.label_img = draw_label_50x30(val_code, val_title, val_spec)
        st.session_state.sku_code = val_code
        
    if st.session_state.label_img:
        st.image(st.session_state.label_img, width=400)
        buf = io.BytesIO()
        st.session_state.label_img.save(buf, format="PNG")
        st.download_button("💾 下载标签图片", buf.getvalue(), f"Label_{st.session_state.sku_code}.png")
