import streamlit as st
import google.generativeai as genai
from PIL import Image, ImageDraw, ImageFont
import barcode
from barcode.writer import ImageWriter
import io
import os
import time

# ================= 1. 页面配置与双保险密钥 =================
st.set_page_config(page_title="LxU 测品工厂-终极解锁版", layout="wide")
st.title("⚡ LxU 专属电商工具集 (2.5 Flash 极速引擎)")

# 侧边栏双保险：优先读 Secrets，读不到就允许手动输入
with st.sidebar:
    st.header("⚙️ 引擎配置")
    secret_key = st.secrets.get("GEMINI_API_KEY", "")
    api_key = st.text_input("Gemini API Key (双保险)", value=secret_key, type="password")
    if not api_key:
        st.warning("👈 请在左侧填入你的 API Key，或在后台 Secrets 配置。")
        st.stop()
    else:
        st.success("✅ 密钥已就绪")

# 初始化 API 配置
genai.configure(api_key=api_key)

# 状态保持
if 'keywords_res' not in st.session_state: st.session_state.keywords_res = ""
if 'label_img' not in st.session_state: st.session_state.label_img = None

# ================= 2. 核心识图引擎 (强制 2.5-flash 通道) =================

def process_lxu_long_image(uploaded_file, prompt):
    """采用 upload_file 逻辑 + 强制 2.5-flash 解决 404 报错"""
    try:
        # ⚠️ 核心修复：强制使用你之前成功代码中的特殊别名 
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash", 
            system_instruction="你是一个精通韩国 Coupang 运营的专家，品牌名为 LxU。"
        )
        
        # 1. 物理保存临时文件
        temp_name = f"temp_{int(time.time())}_{uploaded_file.name}"
        with open(temp_name, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # 2. 上传文件至 Google 服务器
        gen_file = genai.upload_file(path=temp_name)
        
        # 3. 轮询状态：等待处理完毕
        with st.status(f"⚡ 引擎正在强力扫描详情页：{uploaded_file.name}", expanded=False) as status:
            while gen_file.state.name == "PROCESSING":
                time.sleep(2)
                gen_file = genai.get_file(gen_file.name)
            status.update(label="✅ 解析完成，正在提炼 LxU 专属文案...", state="complete")
        
        # 4. 生成报告
        response = model.generate_content([gen_file, prompt])
        
        # 5. 清理缓存
        if os.path.exists(temp_name):
            os.remove(temp_name)
            
        return response.text
    except Exception as e:
        return f"❌ 引擎执行出错: {str(e)}"

# ================= 3. 标签绘制逻辑 (50x30mm) =================

def make_label_50x30(sku, title, spec):
    """生成 50x30mm 标签"""
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

tab1, tab2 = st.tabs(["📑 详情页识图分析", "🏷️ 50x30 标签生成"])

with tab1:
    st.subheader("精铺测品详情页分析 (支持长图)")
    files = st.file_uploader("上传那张香蕉猫窝的图片", type=["png", "jpg", "jpeg", "pdf"], accept_multiple_files=True)
    
    if files and st.button("🚀 启动 LxU 全自动提炼", type="primary"):
        for f in files:
            prompt = """
            任务：深入分析此图片内容。
            1. 提取20个符合韩国本土搜索习惯的韩文精准关键词。
            2. 生成1个以 LxU 开头的高点击率 SEO 标题。
            3. 撰写5条自然语气、本土化表达的商品好评。
            要求：除关键词和评价原文外，所有分析解释文字必须用中文。
            """
            res_text = process_lxu_long_image(f, prompt)
            st.markdown(f"### 📦 提炼结果：{f.name}")
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
