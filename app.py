import streamlit as st
import google.generativeai as genai
from PIL import Image, ImageDraw, ImageFont
import barcode
from barcode.writer import ImageWriter
import io
import os
import time

# ================= 1. 页面配置与 Secrets 调用 =================
st.set_page_config(page_title="LxU 测品工厂-终极版", layout="wide")
st.title("⚡ LxU 专属电商工具集 (Flash 稳定版)")

# 自动从后台 Secrets 读取 Key
api_key = st.secrets.get("GEMINI_API_KEY", None)

if not api_key:
    st.error("⚠️ 未在后台检测到 GEMINI_API_KEY，请在 Settings -> Secrets 填入并 Save。")
    st.stop()

# 配置 API (使用你成功的初始化方式)
genai.configure(api_key=api_key)

# 状态保持
if 'keywords_res' not in st.session_state: st.session_state.keywords_res = ""
if 'label_img' not in st.session_state: st.session_state.label_img = None

# ================= 2. 核心识图引擎 (复刻成功代码文件流) =================

def run_lxu_stable_engine(uploaded_file, prompt):
    """采用 upload_file 逻辑解决 404 和长图读取问题"""
    try:
        # 使用你环境下最稳定的模型命名
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash", 
            system_instruction="你是一个精通韩国 Coupang 运营的 SEO 专家，品牌名为 LxU。"
        )
        
        # 1. 保存物理临时文件
        temp_name = f"temp_{int(time.time())}_{uploaded_file.name}"
        with open(temp_name, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # 2. 上传文件至 Google 云端
        gen_file = genai.upload_file(path=temp_name)
        
        # 3. 轮询状态：等待长图解析完毕
        with st.status(f"⚡ 正在深度扫描长图：{uploaded_file.name}", expanded=False) as status:
            while gen_file.state.name == "PROCESSING":
                time.sleep(2)
                gen_file = genai.get_file(gen_file.name)
            status.update(label="✅ 解析完成，正在提炼 LxU 专属方案...", state="complete")
        
        # 4. 调用模型生成内容
        response = model.generate_content([gen_file, prompt])
        
        # 5. 清理缓存
        if os.path.exists(temp_name):
            os.remove(temp_name)
            
        return response.text
    except Exception as e:
        return f"❌ 处理失败: {str(e)}"

# ================= 3. 标签绘制逻辑 (50x30mm 规范) =================

def make_label_50x30(sku, title, spec):
    """50x30mm 标准布局：标题 + 规格 + 条码 + MADE IN CHINA"""
    width, height = 400, 240 # 203 DPI
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)
    
    # 条码生成 (Code128)
    try:
        code128 = barcode.get('code128', sku, writer=ImageWriter())
        buf = io.BytesIO()
        code128.write(buf, options={"module_height": 10.0, "font_size": 1, "text_distance": 1})
        b_img = Image.open(buf).resize((360, 95))
        img.paste(b_img, (20, 85))
    except: pass

    # 字体兼容性配置
    def load_f(s):
        ps = ["/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf", "C:/Windows/Fonts/msyh.ttc", "Arial.ttf"]
        for p in ps:
            if os.path.exists(p): return ImageFont.truetype(p, s)
        return ImageFont.load_default()

    # 绘制文本：品牌标题、规格选项、SKU、MADE IN CHINA
    draw.text((200, 35), title, fill='black', font=load_f(28), anchor="mm")
    draw.text((200, 70), spec, fill='black', font=load_f(24), anchor="mm")
    draw.text((200, 190), sku, fill='black', font=load_f(22), anchor="mm")
    draw.text((200, 220), "MADE IN CHINA", fill='black', font=load_f(22), anchor="mm")
    
    return img

# ================= 4. UI 交互 =================

tab1, tab2 = st.tabs(["📑 详情页识图提词", "🏷️ 50x30 标签生成"])

with tab1:
    st.subheader("分析详情页 (针对精铺测品优化)")
    files = st.file_uploader("上传截图", type=["png", "jpg", "jpeg", "pdf"], accept_multiple_files=True)
    
    if files and st.button("🚀 启动全自动分析", type="primary"):
        for f in files:
            prompt = "请分析该产品。1.提取20个韩文精准关键词。2.生成1个以 LxU 开头的本土化韩文标题。所有解释说明用中文。"
            res = run_lxu_stable_engine(f, prompt)
            st.markdown(f"### 📦 结果：{f.name}")
            st.markdown(res)
            st.divider()

with tab2:
    st.subheader("50x30mm 标准出货标签")
    c1, c2, c3 = st.columns(3)
    val_sku = c1.text_input("条码内容", "880123456789")
    val_title = c2.text_input("产品标题", "LxU Brand Product")
    val_spec = c3.text_input("销售规格", "Model: Banana | Color: Yellow")
    
    if st.button("预览并生成高清标签"):
        st.session_state.label_img = make_label_50x30(val_sku, val_title, val_spec)
        
    if st.session_state.label_img:
        st.image(st.session_state.label_img, width=400)
        buf = io.BytesIO()
        st.session_state.label_img.save(buf, format="PNG")
        st.download_button("📥 下载标签图片", buf.getvalue(), f"LxU_{val_sku}.png")
