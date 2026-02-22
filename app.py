import streamlit as st
import time
import requests
import json
import pdfplumber
import io
import base64
import urllib.parse

# ================= 1. 页面配置与全局状态 =================
st.set_page_config(page_title="LxU 专属电商工具集", page_icon="🛠️", layout="wide")
st.title("LxU 专属电商工具集")
import streamlit as st
import time
import requests
import json
import pdfplumber
import io
import base64
import urllib.parse

# ================= 1. 页面配置与全局状态 =================
st.set_page_config(page_title="LxU 专属电商工具集", page_icon="🛠️", layout="wide")
st.title("LxU 专属电商工具集")

# 初始化状态 (保证切换 Tab 时数据不丢失)
if 'pdf_keywords' not in st.session_state: st.session_state.pdf_keywords = ""
if 'pdf_title' not in st.session_state: st.session_state.pdf_title = ""
if 'trans_result' not in st.session_state: st.session_state.trans_result = ""
if 'barcode_image' not in st.session_state: st.session_state.barcode_image = None

# ================= 2. 侧边栏：API 密钥配置 =================
with st.sidebar:
    st.markdown("### ⚙️ 全局配置")
    st.info("请填入百度千帆(文心一言)的 API 密钥")
    api_key = st.text_input("API Key", type="password")
    secret_key = st.text_input("Secret Key", type="password")

# ================= 3. 核心函数定义 =================

# 获取百度 API 的 Access Token (全局通用)
def get_access_token(ak, sk):
    url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={ak}&client_secret={sk}"
    payload = ""
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    response = requests.request("POST", url, headers=headers, data=payload)
    return response.json().get("access_token")

# 提取 PDF 文本
def extract_text_from_pdf(pdf_file):
    text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

# 提取 图片 文本 (调用百度 OCR，已加入自动多语种检测)
def extract_text_from_image(image_bytes, token):
    url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/accurate_basic?access_token={token}"
    # 图片需要 base64 编码后再 urlencode
    img_b64 = base64.b64encode(image_bytes).decode()
    
    # 强制加入 language_type=auto_detect 参数，兼容韩文和中文截图
    payload = f"image={urllib.parse.quote(img_b64)}&language_type=auto_detect"
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    result = response.json()
    
    if "words_result" in result:
        # 将识别出的每一行文字拼接到一起
        extracted_text = "\n".join([item["words"] for item in result["words_result"]])
        return extracted_text
    else:
        return ""

# 调用文心一言大模型生成标题和关键词
def call_wenxin_api(text, token):
    url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-lite-8k?access_token={token}"
    
    prompt = f"""你是一个韩国Coupang资深运营专家。以下是提取出的产品详情页文本(可能包含中文或韩文)。请执行两个任务：
1. 深入分析产品卖点，提取3个核心【韩文】关键词，用于前台竞品查询。
2. 生成一个符合Coupang搜索SEO规范的【韩文】产品标题，要求品牌名固定为'LxU'并且必须放在标题的最前面，风格吸睛、准确，不要堆砌无意义的词汇。

返回格式请严格按照以下要求，不要有任何额外废话：
核心词：[词1], [词2], [词3]
标题：LxU [生成的标题]

产品详情页文本：
{text[:2000]} 
"""
    payload = json.dumps({"messages": [{"role": "user", "content": prompt}]})
    headers = {'Content-Type': 'application/json'}
    
    response = requests.request("POST", url, headers=headers, data=payload)
    return response.json().get("result", "API 请求失败或解析错误")

# ================= 4. UI 布局与交互 =================
tab1, tab2, tab3 = st.tabs(["📑 智能提词与标题", "🇰🇷 营销级本土翻译", "🏷️ 标签与条码生成"])

# --- 功能一：详情页提词与 Coupang 标题生成 ---
with tab1:
    st.subheader("分析产品详情页 (支持 PDF/图片)")
    uploaded_file = st.file_uploader("上传产品详情页 (PDF / PNG / JPG)", type=["pdf", "png", "jpg", "jpeg"], key="file_uploader")
    
    if st.button("开始提取与生成", type="primary"):
        if not api_key or not secret_key:
            st.error("请先在左侧边栏输入 API Key 和 Secret Key！")
        elif uploaded_file is not None:
            with st.spinner("正在提取文字并调用大模型分析... (图片OCR可能需要几秒钟)"):
                try:
                    # 1. 获取 Token
                    token = get_access_token(api_key, secret_key)
                    if not token:
                        st.error("获取 Access Token 失败，请检查 API Key 和 Secret Key 是否正确。")
                        st.stop()
                    
                    # 2. 根据文件类型分流提取文字
                    extracted_text = ""
                    file_type = uploaded_file.name.split('.')[-1].lower()
                    
                    if file_type == "pdf":
                        extracted_text = extract_text_from_pdf(uploaded_file)
                    elif file_type in ["png", "jpg", "jpeg"]:
                        image_bytes = uploaded_file.read()
                        extracted_text = extract_text_from_image(image_bytes, token)
                        
                    # 3. 检查是否成功提取到文字
                    if not extracted_text.strip():
                        st.warning("未能从文件中提取到文字。如果是图片，请确保图片内包含清晰的文字。")
                    else:
                        # 4. 调用 API 获取结果
                        ai_result = call_wenxin_api(extracted_text, token)
                        
                        # 5. 解析返回结果
                        if "核心词：" in ai_result and "标题：" in ai_result:
                            parts = ai_result.split("标题：")
                            st.session_state.pdf_keywords = parts[0].replace("核心词：", "").strip()
                            st.session_state.pdf_title = parts[1].strip()
                        else:
                            st.session_state.pdf_keywords = "未严格按格式返回，请看下方完整内容"
                            st.session_state.pdf_title = ai_result
                            
                        st.success("✅ 分析完成！")
                except Exception as e:
                    st.error(f"发生错误: {e}")
        else:
            st.warning("请先上传文件！")
            
    # 展示结果
    if st.session_state.pdf_keywords or st.session_state.pdf_title:
        st.text_area("核心关键词 (Top 3) - 点击即可复制去搜索竞品", value=st.session_state.pdf_keywords, height=68)
        st.text_area("Coupang 专属标题 - 品牌前置优化", value=st.session_state.pdf_title, height=68)

# --- 功能二：本土化营销翻译 (暂存占位) ---
with tab2:
    st.subheader("电商营销语境韩文翻译")
    st.info("🚧 翻译功能底层逻辑待接入...")

# --- 功能三：Code128 标签生成 (暂存占位) ---
with tab3:
    st.subheader("50x20mm 标准 Code128 标签生成")
    st.info("🚧 标签渲染功能底层逻辑待接入...")
# 初始化状态
if 'pdf_keywords' not in st.session_state: st.session_state.pdf_keywords = ""
if 'pdf_title' not in st.session_state: st.session_state.pdf_title = ""
if 'trans_result' not in st.session_state: st.session_state.trans_result = ""
if 'barcode_image' not in st.session_state: st.session_state.barcode_image = None

# ================= 2. 侧边栏：API 密钥配置 =================
with st.sidebar:
    st.markdown("### ⚙️ 全局配置")
    st.info("请填入百度千帆(文心一言)的 API 密钥")
    api_key = st.text_input("API Key", type="password")
    secret_key = st.text_input("Secret Key", type="password")

# ================= 3. 核心函数定义 =================

# 获取百度 API 的 Access Token (全局通用)
def get_access_token(ak, sk):
    url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={ak}&client_secret={sk}"
    payload = ""
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    response = requests.request("POST", url, headers=headers, data=payload)
    return response.json().get("access_token")

# 提取 PDF 文本
def extract_text_from_pdf(pdf_file):
    text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

# 提取 图片 文本 (调用百度 OCR)
def extract_text_from_image(image_bytes, token):
    url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/accurate_basic?access_token={token}"
    # 图片需要 base64 编码后再 urlencode
    img_b64 = base64.b64encode(image_bytes).decode()
    payload = f"image={urllib.parse.quote(img_b64)}"
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    result = response.json()
    
    if "words_result" in result:
        # 将识别出的每一行文字拼接到一起
        extracted_text = "\n".join([item["words"] for item in result["words_result"]])
        return extracted_text
    else:
        return ""

# 调用文心一言大模型生成标题和关键词
def call_wenxin_api(text, token):
    url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-lite-8k?access_token={token}"
    
    prompt = f"""你是一个韩国Coupang资深运营专家。以下是提取出的产品详情页文本。请执行两个任务：
1. 提取3个核心韩文关键词，用于前台竞品查询。
2. 生成一个符合Coupang搜索SEO规范的韩文产品标题，要求品牌名固定为'LxU'并且必须放在标题的最前面，风格吸睛、准确，不要堆砌无意义的词汇。

返回格式请严格按照以下要求，不要有任何额外废话：
核心词：[词1], [词2], [词3]
标题：LxU [生成的标题]

产品详情页文本：
{text[:2000]} # 截取前2000字防止超长
"""
    payload = json.dumps({"messages": [{"role": "user", "content": prompt}]})
    headers = {'Content-Type': 'application/json'}
    
    response = requests.request("POST", url, headers=headers, data=payload)
    return response.json().get("result", "API 请求失败或解析错误")

# ================= 4. UI 布局与交互 =================
tab1, tab2, tab3 = st.tabs(["📑 智能提词与标题", "🇰🇷 营销级本土翻译", "🏷️ 标签与条码生成"])

# --- 功能一：详情页提词与 Coupang 标题生成 ---
with tab1:
    st.subheader("分析产品详情页 (支持 PDF/图片)")
    # 【升级】支持了常见图片格式
    uploaded_file = st.file_uploader("上传产品详情页 (PDF / PNG / JPG)", type=["pdf", "png", "jpg", "jpeg"], key="file_uploader")
    
    if st.button("开始提取与生成", type="primary"):
        if not api_key or not secret_key:
            st.error("请先在左侧边栏输入 API Key 和 Secret Key！")
        elif uploaded_file is not None:
            with st.spinner("正在提取文字并调用大模型分析... (图片OCR可能需要几秒钟)"):
                try:
                    # 1. 获取 Token (优先获取，因为 OCR 和大模型都要用)
                    token = get_access_token(api_key, secret_key)
                    if not token:
                        st.error("获取 Access Token 失败，请检查 API Key 和 Secret Key 是否正确。")
                        st.stop()
                    
                    # 2. 根据文件类型分流提取文字
                    extracted_text = ""
                    file_type = uploaded_file.name.split('.')[-1].lower()
                    
                    if file_type == "pdf":
                        extracted_text = extract_text_from_pdf(uploaded_file)
                    elif file_type in ["png", "jpg", "jpeg"]:
                        image_bytes = uploaded_file.read()
                        extracted_text = extract_text_from_image(image_bytes, token)
                        
                    # 3. 检查是否成功提取到文字
                    if not extracted_text.strip():
                        st.warning("未能从文件中提取到文字。如果是图片，请确保图片内包含清晰的文字。")
                    else:
                        # 4. 调用 API 获取结果
                        ai_result = call_wenxin_api(extracted_text, token)
                        
                        # 5. 解析返回结果
                        if "核心词：" in ai_result and "标题：" in ai_result:
                            parts = ai_result.split("标题：")
                            st.session_state.pdf_keywords = parts[0].replace("核心词：", "").strip()
                            st.session_state.pdf_title = parts[1].strip()
                        else:
                            st.session_state.pdf_keywords = "未严格按格式返回，请看下方完整内容"
                            st.session_state.pdf_title = ai_result
                            
                        st.success("✅ 分析完成！")
                except Exception as e:
                    st.error(f"发生错误: {e}")
        else:
            st.warning("请先上传文件！")
            
    # 展示结果
    if st.session_state.pdf_keywords or st.session_state.pdf_title:
        st.text_area("核心关键词 (Top 3) - 点击即可复制去搜索竞品", value=st.session_state.pdf_keywords, height=68)
        st.text_area("Coupang 专属标题 - 品牌前置优化", value=st.session_state.pdf_title, height=68)

# --- 功能二：本土化营销翻译 (暂存占位) ---
with tab2:
    st.subheader("电商营销语境韩文翻译")
    st.info("🚧 翻译功能底层逻辑待接入...")

# --- 功能三：Code128 标签生成 (暂存占位) ---
with tab3:
    st.subheader("50x20mm 标准 Code128 标签生成")
    st.info("🚧 标签渲染功能底层逻辑待接入...")
