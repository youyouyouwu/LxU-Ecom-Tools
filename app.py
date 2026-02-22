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

# 初始化 Session State，防止页面刷新数据丢失
state_keys = ['pdf_keywords', 'trans_result', 'label_img', 'last_code']
for key in state_keys:
    if key not in st.session_state:
        st.session_state[key] = "" if 'img' not in key else None

# ================= 2. 侧边栏配置 =================
with st.sidebar:
    st.header("⚙️ 全局配置")
    api_key = st.text_input("Gemini API Key", type="password", help="从 Google AI Studio 获取")
    st.divider()
    st.markdown("""
    **LxU 运营助手说明：**
    1. **智能提词**：分析截图生成 Coupang 标题。
    2. **本土翻译**：营销级韩语润色。
    3. **标签生成**：50x30mm 规范打印。
    """)

# ================= 3. 核心工具函数 =================

def call_gemini_api(prompt, contents, key):
    """通用 Gemini 调用逻辑"""
    if not key:
        st.error("请在侧边栏配置 API Key！")
        return None
    try:
        genai.configure(api_key=key)
        # 使用最新稳定的模型名称
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content([prompt] + contents)
        return response.text
    except Exception as e:
        st.error(f"API 调用失败: {str(e)}")
        return None

def generate_label_50x30(code, title, option):
    """生成 50x30mm 标签 (203 DPI)"""
    # 尺寸：400x240 像素
    width, height = 400, 240
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)
    
    # --- 1. 条码生成 ---
    try:
        code128 = barcode.get('code128', code, writer=ImageWriter())
        # 渲染条码，去掉默认大字文本，我们手动绘制
        barcode_buffer = io.BytesIO()
        code128.write(barcode_buffer, options={"module_height": 10.0, "font_size": 1, "text_distance": 1})
        barcode_raw = Image.open(barcode_buffer)
        # 缩放并粘贴条码
        barcode_img = barcode_raw.resize((360, 100))
        img.paste(barcode_img, (20, 85))
    except Exception as e:
        st.error(f"条码生成失败: {e}")

    # --- 2. 文本绘制 ---
    # 尝试加载字体 (适配 Linux/Streamlit Cloud)
    def get_font(size):
        font_paths = [
            "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf", # Common in Linux
            "C:/Windows/Fonts/msyh.ttc", # Windows
            "Arial.ttf" # Fallback
        ]
        for p in font_paths:
            if os.path.exists(p):
                return ImageFont.truetype(p, size)
        return ImageFont.load_default()

    font_title = get_font(28)
    font_option = get_font(24)
    font_footer = get_font(20)

    # 绘制标题 (居中)
    draw.text((width/2, 35), title, fill='black', font=font_title, anchor="mm")
    # 绘制选项 (居中)
    draw.text((width/2, 70), option, fill='black', font=font_option, anchor="mm")
    # 绘制数字
    draw.text((width/2, 195), code, fill='black', font=font_footer, anchor="mm")
    # 绘制 Made in China
    draw.text((width/2, 220), "MADE IN CHINA", fill='black', font=font_footer, anchor="mm")
    
    return img

# ================= 4. 前端交互界面 =================

tab1, tab2, tab3 = st.tabs(["📑 智能提词/标题", "🇰🇷 本土化翻译", "🏷️ 50x30 标签生成"])

# --- Tab 1: 提词分析 ---
with tab1:
    st.subheader("分析产品详情 (提取卖点与标题)")
    up_file = st.file_uploader("上传详情页截图或PDF", type=["png", "jpg", "jpeg", "pdf"])
    if st.button("开始分析", type="primary"):
        if up_file:
            with st.spinner("Gemini 视觉引擎处理中..."):
                prompt = """作为韩国Coupang运营专家，请分析该产品：
                1. 提取3个高转化的【韩文】搜索关键词。
                2. 生成一个【韩文】标题，必须以 'LxU' 开头，符合SEO规范。
                直接输出结果，不要解释。"""
                input_data = []
                if up_file.type == "application/pdf":
                    with pdfplumber.open(up_file) as pdf:
                        text = "".join([p.extract_text() for p in pdf.pages])
                        input_data.append(text)
                else:
                    input_data.append(Image.open(up_file))
                
                st.session_state.pdf_keywords = call_gemini_api(prompt, input_data, api_key)
    
    if st.session_state.pdf_keywords:
        st.success("分析完成！")
        st.text_area("建议方案", value=st.session_state.pdf_keywords, height=200)

# --- Tab 2: 营销翻译 ---
with tab2:
    st.subheader("中韩文营销翻译 (带视觉识别)")
    col_l, col_r = st.columns(2)
    with col_l:
        txt_input = st.text_area("输入需要翻译的内容", placeholder="比如：这款猫窝保暖性极好，适合冬天...")
    with col_r:
        img_input = st.file_uploader("或上传带有文字的截图", type=["png", "jpg", "jpeg"])
    
    if st.button("翻译并润色", type="primary"):
        with st.spinner("正在转换为本土营销语..."):
            prompt = "你是一个韩国本土电商专家，请将内容翻译为地道的、有促单感的韩文营销文案。直接输出韩文。"
            contents = [txt_input] if txt_input else []
            if img_input: contents.append(Image.open(img_input))
            st.session_state.trans_result = call_gemini_api(prompt, contents, api_key)

    if st.session_state.trans_result:
        st.text_area("润色结果", value=st.session_state.trans_result, height=200)

# --- Tab 3: 标签生成 ---
with tab3:
    st.subheader("50mm x 30mm 标准货品标签")
    c1, c2, c3 = st.columns(3)
    in_code = c1.text_input("条码/SKU编号", value="880123456789")
    in_title = c2.text_input("产品名称", value="LxU 宠物用品")
    in_opt = c3.text_input("销售规格", value="款式: 奶油黄 - L码")
    
    if st.button("生成标签预览", type="primary"):
        st.session_state.label_img = generate_label_50x30(in_code, in_title, in_opt)
        st.session_state.last_code = in_code

    if st.session_state.label_img:
        st.image(st.session_state.label_img, width=400)
        # 下载准备
        buf = io.BytesIO()
        st.session_state.label_img.save(buf, format="PNG")
        st.download_button(
            label="💾 下载标签图片",
            data=buf.getvalue(),
            file_name=f"Label_{st.session_state.last_code}.png",
            mime="image/png"
        )
