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
st.set_page_config(page_title="LxU 电商 AI 助手-稳定版", page_icon="🚀", layout="wide")
st.title("LxU 专属电商工具集 (Flash 稳定版)")

# 初始化 Session State
state_keys = ['keywords_res', 'trans_res', 'label_img', 'last_sku']
for key in state_keys:
    if key not in st.session_state:
        st.session_state[key] = "" if 'img' not in key else None

# ================= 2. 侧边栏 API 配置 =================
with st.sidebar:
    st.header("⚙️ 引擎配置")
    # 优先调用 Secrets 中的 Key
    sc_key = st.secrets.get("GEMINI_API_KEY", "")
    api_key = st.text_input("Gemini API Key", value=sc_key, type="password")
    st.info("模式：长图上传流 (支持 1688/Coupang 详情页)")
    st.divider()
    st.markdown("### 🏷️ 标签规范\n- 尺寸: 50x30mm\n- 包含: MADE IN CHINA")

# ================= 3. 核心工具函数 =================

def process_file_and_call_gemini(prompt, uploaded_file, key):
    """参考成功代码：采用 upload_file + get_file 轮询逻辑"""
    if not key:
        st.error("请在左侧配置 API Key！")
        return None
    
    genai.configure(api_key=key)
    # 强制匹配成功案例中的模型名称逻辑
    model = genai.GenerativeModel(model_name="gemini-1.5-flash") 

    try:
        # 1. 临时保存文件以供上传
        temp_path = f"temp_{int(time.time())}_{uploaded_file.name}"
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # 2. 上传至 Google 服务器
        gen_file = genai.upload_file(path=temp_path)
        
        # 3. 轮询检查状态 (防止 404 或 Processing 错误)
        with st.status("正在上传并解析长图...", expanded=False) as status:
            while gen_file.state.name == "PROCESSING":
                time.sleep(2)
                gen_file = genai.get_file(gen_file.name)
            status.update(label="解析完成，正在提炼文案...", state="complete")
        
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
    width, height = 400, 240 # 203 DPI 换算像素
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)
    
    # 条码生成 (Code128)
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

    # 绘制文本：标题、规格、SKU、产地
    draw.text((200, 35), title, fill='black', font=get_f(28), anchor="mm")
    draw.text((200, 70), option, fill='black', font=get_f(24), anchor="mm")
    draw.text((200, 190), code, fill='black', font=get_f(22), anchor="mm")
    draw.text((200, 220), "MADE IN CHINA", fill='black', font=get_f(22), anchor="mm")
    return img

# ================= 4. 前端交互界面 =================

t1, t2, t3 = st.tabs(["📑 智能提词(稳定版)", "🇰🇷 本土化翻译", "🏷️ 50x30 标签生成"])

# 功能一：详情页智能分析
with t1:
    st.subheader("分析详情页 (支持超长图片)")
    up_f1 = st.file_uploader("上传详情页截图", type=["png", "jpg", "jpeg", "pdf"], key="u1")
    if st.button("生成 LxU 提词方案", type="primary"):
        if up_f1:
            # 整合你要求的 7 大维度精简版指令
            prompt = "你是一个韩国Coupang运营专家。分析图片提取：3个韩文关键词，1个LxU开头的韩文标题。直接输出结果。"
            st.session_state.keywords_res = process_file_and_call_gemini(prompt, up_f1, api_key)

    if st.session_state.keywords_res:
        st.text_area("提词结果", st.session_state.keywords_res, height=200)

# 功能二：营销翻译
with t2:
    st.subheader("营销级本土化翻译")
    cola, colb = st.columns(2)
    t_in = cola.text_area("文字翻译", placeholder="输入中文内容...")
    i_in = colb.file_uploader("截图翻译", type=["png", "jpg", "jpeg"])
    
    if st.button("开始本土化翻译", type="primary"):
        prompt = "你是一个韩国本土电商专家，请将内容翻译为地道的、有促单感的韩文营销文案。直接输出。"
        if i_in:
            st.session_state.trans_res = process_file_and_call_gemini(prompt + f"\n参考文案: {t_in}", i_in, api_key)
        else:
            genai.configure(api_key=api_key)
            m = genai.GenerativeModel('gemini-1.5-flash')
            st.session_state.trans_res = m.generate_content(prompt + t_in).text

    if st.session_state.trans_res:
        st.text_area("翻译结果", st.session_state.trans_res, height=200)

# 功能三：标准标签生成
with t3:
    st.subheader("50x30mm 打印规范标签")
    c1, c2, c3 = st.columns(3)
    sk = c1.text_input("SKU/条码数字", "880123456789")
    ti = c2.text_input("产品标题 (LxU)", "LxU Product Title")
    op = c3.text_input("销售规格", "Size: L | Color: White")
    
    if st.button("生成预览并下载"):
        st.session_state.label_img = generate_label_50x30(sk, ti, op)
        st.session_state.last_sku = sk
        
    if st.session_state.label_img:
        st.image(st.session_state.label_img, width=400)
        b = io.BytesIO()
        st.session_state.label_img.save(b, format="PNG")
        st.download_button("💾 下载标签 (PNG)", b.getvalue(), f"LxU_{st.session_state.last_sku}.png")
