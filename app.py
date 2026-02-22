import streamlit as st
import google.generativeai as genai
from PIL import Image, ImageDraw, ImageFont
import barcode
from barcode.writer import ImageWriter
import io
import os
import time

# ================= 1. 页面配置与 Secrets (复刻成功版) =================
st.set_page_config(page_title="LxU 测品工厂-终极稳定版", layout="wide")
st.title("⚡ LxU 专属电商工具集 (旗舰级 Flash 引擎)")

# --- 核心：默认调用后台 Secrets 里的 Key ---
api_key = st.secrets.get("GEMINI_API_KEY", None)

if not api_key:
    st.error("⚠️ 未在后台检测到 GEMINI_API_KEY，请点击页面右上角 Settings -> Secrets 配置。")
    st.stop()

# 配置 API (使用你成功的初始化方式)
genai.configure(api_key=api_key)

# 初始化状态
if 'keywords_res' not in st.session_state: st.session_state.keywords_res = ""
if 'label_img' not in st.session_state: st.session_state.label_img = None

# ================= 2. 核心识图引擎 (复刻成功版文件流) =================

def run_lxu_flash_engine(uploaded_file, prompt):
    """
    完全复刻你提供的“读取长图”成功逻辑：
    保存临时文件 -> 异步上传 -> 状态轮询 -> 生成内容
    """
    try:
        # 使用你代码中能跑通的特定模型别名
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash", 
            system_instruction="你是一个精通韩国 Coupang 运营的 SEO 专家，品牌名为 LxU。"
        )
        
        # 1. 物理保存临时文件
        temp_name = f"temp_{int(time.time())}_{uploaded_file.name}"
        with open(temp_name, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # 2. 调用上传接口
        gen_file = genai.upload_file(path=temp_name)
        
        # 3. 轮询检查状态 (解决 404 和读取失败的关键)
        with st.status(f"⚡ Flash 引擎正在飞速扫描：{uploaded_file.name}", expanded=False) as status:
            while gen_file.state.name == "PROCESSING":
                time.sleep(2)
                gen_file = genai.get_file(gen_file.name)
            status.update(label="✅ 解析完成，正在生成策略...", state="complete")
        
        # 4. 生成核心内容
        response = model.generate_content([gen_file, prompt])
        
        # 5. 清理文件
        if os.path.exists(temp_name):
            os.remove(temp_name)
            
        return response.text
    except Exception as e:
        return f"❌ 引擎启动失败: {str(e)}"

# ================= 3. 标签生成逻辑 (50x30mm 规范) =================

def draw_label_50x30(sku, title, spec):
    """生成 50x30mm 标准标签，底部固定 MADE IN CHINA"""
    width, height = 400, 240 # 203 DPI 像素
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)
    
    # 条码绘制
    try:
        code128 = barcode.get('code128', sku, writer=ImageWriter())
        buf = io.BytesIO()
        code128.write(buf, options={"module_height": 10.0, "font_size": 1, "text_distance": 1})
        b_img = Image.open(buf).resize((360, 95))
        img.paste(b_img, (20, 85))
    except: pass

    # 字体兼容性加载
    def load_f(s):
        ps = ["/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf", "C:/Windows/Fonts/msyh.ttc", "Arial.ttf"]
        for p in ps:
            if os.path.exists(p): return ImageFont.truetype(p, s)
        return ImageFont.load_default()

    draw.text((200, 35), title, fill='black', font=load_f(28), anchor="mm")
    draw.text((200, 70), spec, fill='black', font=load_f(24), anchor="mm")
    draw.text((200, 190), sku, fill='black', font=load_f(22), anchor="mm")
    draw.text((200, 220), "MADE IN CHINA", fill='black', font=load_f(22), anchor="mm")
    
    return img

# ================= 4. UI 交互界面 =================

tab1, tab2 = st.tabs(["📑 详情页提词分析", "🏷️ 50x30 标签生成"])

with tab1:
    st.subheader("分析产品详情 (支持 1688/Coupang 长图)")
    files = st.file_uploader("上传截图", type=["png", "jpg", "jpeg", "pdf"], accept_multiple_files=True)
    
    if files and st.button("🚀 启动 LxU 全自动提炼", type="primary"):
        for f in files:
            # 使用你最习惯的分析指令
            prompt = """
            请分析该产品并完成：
            1. 提取20个韩文精准关键词，放入逗号隔开的代码块。
            2. 生成一个以 LxU 开头的韩文产品标题。
            3. 撰写5条本土化韩文好评。
            除关键词和评价原文外，所有解释必须用中文。
            """
            res_text = run_lxu_flash_engine(f, prompt)
            st.markdown(f"### 📦 产品报告：{f.name}")
            st.markdown(res_text)
            st.divider()

with tab2:
    st.subheader("50x30mm 标准货品标签")
    c1, c2, c3 = st.columns(3)
    sk = c1.text_input("SKU/条码数字", "880123456789")
    ti = c2.text_input("产品标题 (LxU)", "LxU Product")
    op = c3.text_input("规格选项", "Color: White | Size: XL")
    
    if st.button("预览并生成标签"):
        st.session_state.label_img = draw_label_50x30(sk, ti, op)
        
    if st.session_state.label_img:
        st.image(st.session_state.label_img, width=400)
        buf = io.BytesIO()
        st.session_state.label_img.save(buf, format="PNG")
        st.download_button("💾 下载标签图", buf.getvalue(), f"LxU_{sk}.png")
