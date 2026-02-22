import streamlit as st
import google.generativeai as genai
from PIL import Image
import pdfplumber
import io

# ================= 1. 页面配置与全局状态 =================
st.set_page_config(page_title="LxU 专属电商工具集", page_icon="🛠️", layout="wide")
st.title("LxU 专属电商工具集 (Gemini 引擎)")

# 核心：防丢失状态缓存
if 'pdf_keywords' not in st.session_state: st.session_state.pdf_keywords = ""
if 'pdf_title' not in st.session_state: st.session_state.pdf_title = ""
if 'trans_result' not in st.session_state: st.session_state.trans_result = ""
if 'barcode_image' not in st.session_state: st.session_state.barcode_image = None

# ================= 2. 侧边栏配置 =================
with st.sidebar:
    st.markdown("### ⚙️ 全局配置")
    st.info("请填入 Google Gemini API Key")
    api_key = st.text_input("Gemini API Key", type="password")

# ================= 3. 核心大模型调用逻辑 =================
def extract_text_from_pdf(pdf_file):
    text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text: text += page_text + "\n"
    return text

def call_gemini_api(prompt, content_list, api_key):
    """通用的 Gemini 调用接口，支持纯文本或图文混排"""
    genai.configure(api_key=api_key)
    # 使用 1.5 flash 版本，速度极快，极其适合处理电商图文和长文本
    model = genai.GenerativeModel('gemini-1.5-flash') 
    
    # 将 prompt 和 用户上传的内容合并发送
    full_prompt = [prompt] + content_list
    response = model.generate_content(full_prompt)
    return response.text

# ================= 4. 页面布局 =================
tab1, tab2, tab3 = st.tabs(["📑 智能提词与标题", "🇰🇷 营销级本土翻译", "🏷️ 标签与条码生成"])

# ---------- 功能一：智能提词与标题 ----------
with tab1:
    st.subheader("分析产品详情提取卖点 (支持截图/长图/PDF)")
    uploaded_file = st.file_uploader("直接拖拽或粘贴详情页截图", type=["pdf", "png", "jpg", "jpeg"], key="f1_upload")
    
    if st.button("生成竞品词与标题", type="primary"):
        if not api_key:
            st.error("请先在左侧输入 Gemini API Key！")
        elif uploaded_file:
            with st.spinner("Gemini 视觉引擎分析中..."):
                try:
                    prompt = """你是一个韩国Coupang资深运营专家。请直接分析提供的文本或图片内容，执行两个任务：
1. 深入挖掘产品卖点，提取3个核心【韩文】关键词，用于前台竞品查询。
2. 生成一个符合Coupang搜索SEO规范的【韩文】产品标题，要求品牌名固定为'LxU'并且必须放在最前面。

返回格式必须严格如下，不要使用Markdown加粗(不要有**符号)，不要有多余废话：
核心词：[词1], [词2], [词3]
标题：LxU [生成的标题]
"""
                    content_to_send = []
                    if uploaded_file.name.lower().endswith('.pdf'):
                        # PDF 提取文字送给 Gemini
                        text = extract_text_from_pdf(uploaded_file)
                        content_to_send.append(text)
                    else:
                        # 图片直接送给 Gemini 的原生多模态视觉神经！
                        img = Image.open(uploaded_file)
                        content_to_send.append(img)

                    res = call_gemini_api(prompt, content_to_send, api_key)
                    
                    if "核心词：" in res and "标题：" in res:
                        parts = res.split("标题：")
                        st.session_state.pdf_keywords = parts[0].replace("核心词：", "").strip()
                        st.session_state.pdf_title = parts[1].strip()
                    else:
                        st.session_state.pdf_keywords, st.session_state.pdf_title = "格式异常，请看完整输出", res
                    
                    st.success("✅ 生成成功！速度是不是快多了？")
                except Exception as e:
                    st.error(f"调用失败: {str(e)}")
        else:
            st.warning("请上传文件！")
            
    if st.session_state.pdf_keywords:
        st.text_area("核心关键词 (Top 3)", value=st.session_state.pdf_keywords, height=68)
        st.text_area("LxU 专属 Coupang 标题", value=st.session_state.pdf_title, height=68)

# ---------- 功能二：本土化营销翻译 ----------
with tab2:
    st.subheader("电商营销本土化翻译 (支持直接输入或截图识别)")
    
    col1, col2 = st.columns(2)
    with col1:
        text_input = st.text_area("方式1：输入需要翻译的文案", height=150, placeholder="支持中文直接翻译，或韩文文案润色...")
    with col2:
        img_input = st.file_uploader("方式2：上传韩文/中文截图", type=["png", "jpg", "jpeg"], key="f2_upload")
        
    if st.button("开始本土化翻译", type="primary", key="f2_btn"):
        if not api_key:
            st.error("请先在左侧输入 Gemini API Key！")
        elif text_input or img_input:
            with st.spinner("正在注入韩国电商灵魂..."):
                try:
                    prompt = """你是一个韩国本土资深电商营销专家。请分析我提供的文案或图片中的文字，将其翻译、润色为极具“韩国本土电商营销风格”的韩语。
要求：
1. 绝对不能是生硬的机器直译，要符合韩国Coupang消费者的阅读习惯。
2. 带有极强的促单感和场景感，确保用词精准、吸睛。
3. 直接输出最终的韩文结果，不要任何多余的解释。
"""
                    content_to_send = []
                    if text_input:
                        content_to_send.append(text_input)
                    if img_input:
                        img = Image.open(img_input)
                        content_to_send.append(img)
                        
                    st.session_state.trans_result = call_gemini_api(prompt, content_to_send, api_key)
                    st.success("✅ 翻译完成！纯正本土味。")
                except Exception as e:
                    st.error(f"调用失败: {str(e)}")
        else:
            st.warning("请输入文字或上传截图！")

    if st.session_state.trans_result:
        st.text_area("韩文营销文案 (可直接复制)", value=st.session_state.trans_result, height=200)

# ---------- 功能三：标签与条码 ----------
with tab3:
    st.subheader("50x20mm 标准 Code128 标签生成")
    st.info("🚧 待接入图像渲染逻辑...")
