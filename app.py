import streamlit as st
import google.generativeai as genai
from PIL import Image, ImageDraw, ImageFont
import barcode
from barcode.writer import ImageWriter
import io
import os
import time

# ================= 1. 页面配置与双保险密钥 =================
st.set_page_config(page_title="LxU 极简测款助手", layout="wide")
st.title("⚡ LxU 极简测款助手 (付费极速版)")

# 侧边栏双保险
with st.sidebar:
    st.header("⚙️ 引擎配置")
    secret_key = st.secrets.get("GEMINI_API_KEY", "")
    api_key = st.text_input("Gemini API Key", value=secret_key, type="password")
    if not api_key:
        st.warning("👈 请在左侧填入 API Key，或在后台 Secrets 配置。")
        st.stop()
    else:
        st.success("✅ 付费级 API 密钥已就绪，无惧并发限流！")

genai.configure(api_key=api_key)

if 'keywords_res' not in st.session_state: st.session_state.keywords_res = ""
if 'label_img' not in st.session_state: st.session_state.label_img = None

# ================= 2. 极简识图引擎 =================

def process_lxu_long_image(uploaded_file, prompt):
    """异步长图解析，付费通道满血输出"""
    try:
        # 付费通道下，1.5-flash 是目前官方最稳定、性价比极高的旗舰轻量模型
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash", 
            system_instruction="你是一个精通韩国 Coupang 选品和竞品分析的专家，品牌名为 LxU。"
        )
        
        temp_name = f"temp_{int(time.time())}_{uploaded_file.name}"
        with open(temp_name, "wb") as f:
            f.write(uploaded_file.getbuffer())

        gen_file = genai.upload_file(path=temp_name)
        
        with st.status(f"⚡ 正在极速扫描：{uploaded_file.name}", expanded=False) as status:
            while gen_file.state.name == "PROCESSING":
                time.sleep(2)
                gen_file = genai.get_file(gen_file.name)
            status.update(label="✅ 提取完成！", state="complete")
        
        response = model.generate_content([gen_file, prompt])
        
        if os.path.exists(temp_name):
            os.remove(temp_name)
            
        return response.text
    except Exception as e:
        return f"❌ 引擎执行出错: {str(e)}"

# ================= 3. 标签绘制逻辑 (50x30mm) =================

def make_label_50x30(sku, title, spec):
    """50x30 标签，自带 MADE IN CHINA"""
    width, height = 400, 240 
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)
    
    try:
        code128 = barcode.get('code128', sku, writer=ImageWriter())
        buf = io.BytesIO()
        code128.write(buf, options={"module_height": 10.0, "font_size": 1, "text_distance": 1})
        b_img = Image.open(buf).resize((360, 95))
        img.paste(b_img, (20, 85))
    except: pass

    def load_font(size):
        font_paths = ["/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf", "C:/Windows/Fonts/msyh.ttc", "Arial.ttf"]
        for p in font_paths:
            if os.path.exists(p): return ImageFont.truetype(p, size)
        return ImageFont.load_default()

    draw.text((200, 35), title, fill='black', font=load_font(28), anchor="mm")
    draw.text((200, 70), spec, fill='black', font=load_font(24), anchor="mm")
    draw.text((200, 190), sku, fill='black', font=load_font(22), anchor="mm")
    draw.text((200, 220), "MADE IN CHINA", fill='black', font=load_font(22), anchor="mm")
    
    return img

# ================= 4. 前端交互界面 =================

tab1, tab2 = st.tabs(["🎯 极简测款提词", "🏷️ 50x30 标签生成"])

with tab1:
    st.subheader("核心竞品词与内部品名提取 (支持长图)")
    files = st.file_uploader("上传测款图片", type=["png", "jpg", "jpeg", "pdf"], accept_multiple_files=True)
    
    if files and st.button("🚀 极速提取核心信息", type="primary"):
        for f in files:
            # 强指令：锁死 Markdown 表格格式
            prompt = """
            任务：极简模式测款提取。
            请直接分析产品图，**必须严格按照以下 Markdown 表格的格式输出结果**。
            严禁输出任何废话、前言、问候语或额外解释。
            
            | 数据维度 | 提取结果 |
            | :--- | :--- |
            | 🔍 前台竞品搜索词 | [提取3-5个最核心韩文词，附带中文翻译，词与词之间用英文逗号隔开] |
            | 🏷️ 内部管理品名 | [生成1个简短精准的品名，包含中文与韩文] |
            """
            res_text = process_lxu_long_image(f, prompt)
            st.markdown(f"### 📦 测品提取：{f.name}")
            # 使用 st.markdown 渲染美观的表格
            st.markdown(res_text)
            st.divider()

with tab2:
    st.subheader("50x30mm 标准货品标签")
    c1, c2, c3 = st.columns(3)
    val_sku = c1.text_input("条码内容 (SKU)", "880123456789")
    val_title = c2.text_input("产品标题", "LxU Brand Product")
    val_spec = c3.text_input("规格选项", "Model: Banana | Color: Yellow")
    
    if st.button("生成高清标签图"):
        st.session_state.label_img = make_label_50x30(val_sku, val_title, val_spec)
        
    if st.session_state.label_img:
        st.image(st.session_state.label_img, width=400)
        buf = io.BytesIO()
        st.session_state.label_img.save(buf, format="PNG")
        st.download_button("📥 下载标签 (PNG)", buf.getvalue(), f"LxU_{val_sku}.png")
