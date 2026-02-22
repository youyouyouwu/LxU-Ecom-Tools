import streamlit as st
import google.generativeai as genai
from PIL import Image, ImageDraw, ImageFont
import barcode
from barcode.writer import ImageWriter
import io
import os
import time

# ================= 1. 页面配置与 Secrets =================
st.set_page_config(page_title="LxU 专属电商工具集-极速版", page_icon="🚀", layout="wide")
st.title("LxU 专属电商工具集 (基于旗舰级 Flash 引擎)")

# 从 Secrets 获取 Key
api_key = st.secrets.get("GEMINI_API_KEY", "")

if not api_key:
    st.error("⚠️ 未在后台检测到 GEMINI_API_KEY，请在 Settings -> Secrets 配置。")
    st.stop()

# 全局配置模型 (参考成功代码的初始化逻辑)
genai.configure(api_key=api_key)

# 初始化 Session State
if 'keywords_res' not in st.session_state: st.session_state.keywords_res = ""
if 'label_img' not in st.session_state: st.session_state.label_img = None

# ================= 2. 核心读取逻辑 (复刻成功代码) =================

def process_long_image_stable(uploaded_file, prompt):
    """
    完全复刻“终极稳定版”中的长图读取流：
    保存临时文件 -> 异步上传 -> 状态轮询 -> 生成内容
    """
    try:
        # 使用你成功代码中的模型版本
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        # 1. 保存临时文件
        temp_path = f"temp_{int(time.time())}_{uploaded_file.name}"
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # 2. 调用 upload_file 异步接口
        gen_file = genai.upload_file(path=temp_path)
        
        # 3. 核心轮询：等待 Google 服务器处理长图
        with st.status(f"⚡ 正在异步解析长图：{uploaded_file.name}", expanded=False) as status:
            while gen_file.state.name == "PROCESSING":
                time.sleep(2)
                gen_file = genai.get_file(gen_file.name)
            status.update(label="✅ 图片解析完成，正在提炼关键词...", state="complete")
        
        # 4. 生成响应
        response = model.generate_content([gen_file, prompt])
        
        # 5. 清理现场
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        return response.text
    except Exception as e:
        return f"❌ 深度读取失败: {str(e)}"

# ================= 3. 标签生成逻辑 (LxU 50x30mm 规范) =================

def generate_label_50x30(sku, title, spec):
    """绘制 50x30mm 标准标签图，底部带 MADE IN CHINA"""
    # 203 DPI 下 50x30mm 约 400x240 像素
    width, height = 400, 240
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)
    
    # 条码绘制
    try:
        code128 = barcode.get('code128', sku, writer=ImageWriter())
        barcode_buffer = io.BytesIO()
        code128.write(barcode_buffer, options={"module_height": 10.0, "font_size": 1, "text_distance": 1})
        barcode_img = Image.open(barcode_buffer).resize((360, 95))
        img.paste(barcode_img, (20, 85))
    except: pass

    # 字体配置
    def load_f(size):
        paths = ["/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf", "C:/Windows/Fonts/msyh.ttc", "Arial.ttf"]
        for p in paths:
            if os.path.exists(p): return ImageFont.truetype(p, size)
        return ImageFont.load_default()

    # 文本内容
    draw.text((200, 35), title, fill='black', font=load_f(28), anchor="mm")
    draw.text((200, 70), spec, fill='black', font=load_f(24), anchor="mm")
    draw.text((200, 190), sku, fill='black', font=load_f(22), anchor="mm")
    # 底部固定标识
    draw.text((200, 220), "MADE IN CHINA", fill='black', font=load_f(22), anchor="mm")
    
    return img

# ================= 4. UI 界面逻辑 =================

tab1, tab2 = st.tabs(["📑 智能提词与详情页分析", "🏷️ 50x30 标签生成"])

with tab1:
    st.subheader("长图详情页提炼 (复刻稳定版引擎)")
    files = st.file_uploader("上传详情页截图 (支持长图)", type=["png", "jpg", "jpeg", "pdf"], accept_multiple_files=True)
    
    if files and st.button("🚀 开始批量解析", type="primary"):
        for f in files:
            # 整合你最核心的 7 大维度指令
            prompt = """
            你是一个韩国Coupang SEO专家。请分析该详情页：
            1. 挖掘20个韩文精准关键词，并提供逗号隔开的代码块版本。
            2. 生成1个以LxU开头的韩文高点击标题。
            3. 提供产品韩语名称。
            所有解释文字用中文。
            """
            res = process_long_image_stable(f, prompt)
            st.markdown(f"### 📊 产品：{f.name} 的分析结果")
            st.markdown(res)
            st.divider()

with tab2:
    st.subheader("50x30mm 货品标签生成器")
    c1, c2, c3 = st.columns(3)
    val_sku = c1.text_input("SKU/条码", "880123456789")
    val_title = c2.text_input("产品标题", "LxU Brand Product")
    val_spec = c3.text_input("规格选项", "Model: Banana | Size: XL")
    
    if st.button("预览并生成标签"):
        st.session_state.label_img = generate_label_50x30(val_sku, val_title, val_spec)
        
    if st.session_state.label_img:
        st.image(st.session_state.label_img, width=400)
        buf = io.BytesIO()
        st.session_state.label_img.save(buf, format="PNG")
        st.download_button("💾 下载标签图", buf.getvalue(), f"LxU_Label_{val_sku}.png")
