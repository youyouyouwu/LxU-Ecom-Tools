import streamlit as st
import google.generativeai as genai
from PIL import Image, ImageDraw, ImageFont
import barcode
from barcode.writer import ImageWriter
import io
import os
import time

# ================= 1. 页面配置与 Secrets 调用 =================
st.set_page_config(page_title="LxU 测品工厂-旗舰版", layout="wide")
st.title("⚡ LxU 专属电商工具集 (Flash 极速引擎)")

# 自动从后台 Secrets 读取你刚才设置的 Key
api_key = st.secrets.get("GEMINI_API_KEY", None)

if not api_key:
    st.error("⚠️ 未在后台检测到 GEMINI_API_KEY，请确保在 Settings -> Secrets 中点击了 Save。")
    st.stop()

# 初始化 API 配置
genai.configure(api_key=api_key)

# 状态保持逻辑
if 'keywords_res' not in st.session_state: st.session_state.keywords_res = ""
if 'label_img' not in st.session_state: st.session_state.label_img = None

# ================= 2. 核心识图引擎 (复刻你成功的读取逻辑) =================

def process_lxu_file(uploaded_file, prompt):
    """
    完全对齐你成功代码中的“异步上传+轮询”机制
    这是解决 404 错误和长图读取失败的唯一终极方案
    """
    try:
        # 使用你成功代码中指定的模型名称
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash", 
            system_instruction="你是一个精通韩国 Coupang 运营的 SEO 专家，品牌名为 LxU。"
        )
        
        # 1. 物理保存临时文件
        temp_name = f"temp_{int(time.time())}_{uploaded_file.name}"
        with open(temp_name, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # 2. 将文件推送到 Google 服务器端进行解析
        gen_file = genai.upload_file(path=temp_name)
        
        # 3. 核心轮询：等待服务器处理完毕 (针对详情页长图至关重要)
        with st.status(f"⚡ 正在深度解析详情页：{uploaded_file.name}", expanded=False) as status:
            while gen_file.state.name == "PROCESSING":
                time.sleep(2)
                gen_file = genai.get_file(gen_file.name)
            status.update(label="✅ 解析完成，正在提炼 LxU 专属方案...", state="complete")
        
        # 4. 生成分析结果
        response = model.generate_content([gen_file, prompt])
        
        # 5. 清理临时缓存
        if os.path.exists(temp_name):
            os.remove(temp_name)
            
        return response.text
    except Exception as e:
        return f"❌ 引擎连接失败，请检查 Key 权限: {str(e)}"

# ================= 3. 标签绘制逻辑 (50x30mm 标准) =================

def make_label_50x30(sku, title, spec):
    """按照 50x30mm 规范绘制，底部强制带 MADE IN CHINA"""
    # 203 DPI 标准像素尺寸
    width, height = 400, 240
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)
    
    # --- 条码部分 ---
    try:
        code128 = barcode.get('code128', sku, writer=ImageWriter())
        buf = io.BytesIO()
        code128.write(buf, options={"module_height": 10.0, "font_size": 1, "text_distance": 1})
        b_img = Image.open(buf).resize((360, 95))
        img.paste(b_img, (20, 85))
    except: pass

    # --- 字体加载 (优先适配 Linux 环境) ---
    def load_font(size):
        font_paths = ["/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf", "C:/Windows/Fonts/msyh.ttc", "Arial.ttf"]
        for p in font_paths:
            if os.path.exists(p): return ImageFont.truetype(p, size)
        return ImageFont.load_default()

    # 绘制：品牌标题、规格选项、SKU、MADE IN CHINA
    draw.text((200, 35), title, fill='black', font=load_font(28), anchor="mm")
    draw.text((200, 70), spec, fill='black', font=load_font(24), anchor="mm")
    draw.text((200, 190), sku, fill='black', font=load_font(22), anchor="mm")
    draw.text((200, 220), "MADE IN CHINA", fill='black', font=load_font(22), anchor="mm")
    
    return img

# ================= 4. 前端交互界面 =================

tab1, tab2 = st.tabs(["📑 详情页提词分析", "🏷️ 50x30 标签生成"])

# --- Tab 1: 详情页智能分析 ---
with tab1:
    st.subheader("分析产品详情 (支持超长图片)")
    files = st.file_uploader("直接上传详情页截图", type=["png", "jpg", "jpeg", "pdf"], accept_multiple_files=True)
    
    if files and st.button("🚀 启动全自动提炼", type="primary"):
        for f in files:
            # 整合你要求的核心运营指令
            prompt = """
            任务：分析此图片。
            1. 提取20个高流量韩文精准关键词。
            2. 生成1个以 LxU 开头的本土化韩文标题。
            3. 提供10条本土化韩文好评。
            除关键词和评价原文外，所有分析说明必须用中文。
            """
            res = process_lxu_file(f, prompt)
            st.markdown(f"### 📦 报告结果：{f.name}")
            st.markdown(res)
            st.divider()

# --- Tab 2: 出货标签生成 ---
with tab2:
    st.subheader("50x30mm 标准货品标签")
    c1, c2, c3 = st.columns(3)
    val_sku = c1.text_input("SKU/条码内容", "880123456789")
    val_title = c2.text_input("产品标题 (LxU)", "LxU Brand Product")
    val_spec = c3.text_input("销售规格", "Model: Banana | Color: Yellow")
    
    if st.button("预览并生成高清标签"):
        st.session_state.label_img = make_label_50x30(val_sku, val_title, val_spec)
        
    if st.session_state.label_img:
        st.image(st.session_state.label_img, width=400)
        buf = io.BytesIO()
        st.session_state.label_img.save(buf, format="PNG")
        st.download_button("📥 下载标签图片", buf.getvalue(), f"LxU_{val_sku}.png")
