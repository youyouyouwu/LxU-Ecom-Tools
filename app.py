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
    # 优先调用 Secrets 中的 Key，模仿你成功的代码环境
    sc_key = st.secrets.get("GEMINI_API_KEY", "")
    api_key = st.text_input("Gemini API Key", value=sc_key, type="password")
    st.info("模式：服务器端文件轮询流 (针对超长详情页优化)")
    st.divider()
    st.markdown("### 🏷️ 标签规范\n- 尺寸: 50x30mm\n- 包含: MADE IN CHINA")

# ================= 3. 核心工具函数 =================

def process_file_and_call_gemini(prompt, uploaded_file, key):
    """【核心修复】：完全对齐成功代码的上传与调用逻辑"""
    if not key:
        st.error("请在左侧配置 API Key！")
        return None
    
    # 1. 配置 API
    genai.configure(api_key=key)
    
    # 2. 模型初始化 (参考你成功的代码：使用 system_instruction)
    try:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash", 
            system_instruction="你是一个精通韩国 Coupang 运营的 SEO 专家，品牌名为 LxU。"
        )

        # 3. 临时保存文件
        temp_path = f"temp_{int(time.time())}_{uploaded_file.name}"
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # 4. 上传至 Google 服务器
        gen_file = genai.upload_file(path=temp_path)
        
        # 5. 状态轮询 (这是解决 404/Processing 的关键)
        with st.status("正在上传并极速扫描长图...", expanded=False) as status:
            while gen_file.state.name == "PROCESSING":
                time.sleep(2)
                gen_file = genai.get_file(gen_file.name)
            status.update(label="解析完成，正在提炼文案...", state="complete")
        
        # 6. 生成内容 (注意：这里使用你成功的两参数调用方式)
        response = model.generate_content([gen_file, prompt])
        
        # 7. 清理临时文件
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

    # 字体加载
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

# ================= 4. UI 布局 =================

t1, t2, t3 = st.tabs(["📑 智能提词(旗舰版)", "🇰🇷 本土化翻译", "🏷️ 50x30 标签生成"])

with t1:
    st.subheader("分析详情页 (支持超长图片/PDF)")
    up_f1 = st.file_uploader("上传截图", type=["png", "jpg", "jpeg", "pdf"], key="u1")
    if st.button("生成 LxU 提词方案", type="primary"):
        if up_f1:
            prompt = "请帮我分析该产品，找到符合韩国搜索习惯的3个核心韩文关键词，并生成一个以LxU开头的韩文标题。直接输出结果。"
            st.session_state.keywords_res = process_file_and_call_gemini(prompt, up_f1, api_key)

    if st.session_state.keywords_res:
        st.markdown(st.session_state.keywords_res)

with t2:
    st.subheader("营销级本土化翻译")
    cola, colb = st.columns(2)
    t_in = cola.text_area("文案输入")
    i_in = colb.file_uploader("截图输入", type=["png", "jpg", "jpeg"])
    
    if st.button("开始本土翻译"):
        prompt = "你是一个韩国本土电商专家，请将内容翻译/润色为极具促单感的韩文营销文案。直接输出。"
        if i_in:
            st.session_state.trans_res = process_file_and_call_gemini(prompt + f"\n参考文案: {t_in}", i_in, api_key)
        else:
            genai.configure(api_key=api_key)
            m = genai.GenerativeModel('gemini-1.5-flash')
            st.session_state.trans_res = m.generate_content(prompt + t_in).text

    if st.session_state.trans_res:
        st.text_area("结果", st.session_state.trans_res, height=200)

with t3:
    st.subheader("50x30mm 标签生成")
    c1, c2, c3 = st.columns(3)
    sk = c1.text_input("条码数字", "880123456789")
    ti = c2.text_input("产品标题", "LxU Product")
    op = c3.text_input("规格", "Size: L | Color: White")
    
    if st.button("生成标签"):
        st.session_state.label_img = generate_label_50x30(sk, ti, op)
        st.session_state.last_sku = sk
        
    if st.session_state.label_img:
        st.image(st.session_state.label_img, width=400)
        b = io.BytesIO()
        st.session_state.label_img.save(b, format="PNG")
        st.download_button("📥 下载标签", b.getvalue(), f"LxU_{st.session_state.last_sku}.png")
