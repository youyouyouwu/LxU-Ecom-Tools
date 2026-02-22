import streamlit as st
import streamlit.components.v1 as components
import google.generativeai as genai
from PIL import Image, ImageDraw, ImageFont
import barcode
from barcode.writer import ImageWriter
import io
import os
import time
import json

# ================= 1. 核心工具函数 (高清修复逻辑) =================

def make_label_50x30(sku, title, spec):
    """
    生成高清 50x30mm 标签
    优化点：高分辨率画布 (1000x600) + 字体路径增强
    """
    # 提升画布分辨率至 1000x600，打印更清晰
    width, height = 1000, 600 
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)

    def load_font(size):
        # 增加 Linux (Streamlit Cloud) 常见的韩文/中文字体路径
        font_paths = [
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",   # Linux 通用 CJK
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf", # 备用
            "C:/Windows/Fonts/malgun.ttf", # Windows 韩文 (Malgun Gothic)
            "C:/Windows/Fonts/msyh.ttc",   # Windows 中文
            "Arial.ttf"
        ]
        for p in font_paths:
            if os.path.exists(p):
                return ImageFont.truetype(p, size)
        return ImageFont.load_default()

    try:
        # 渲染条形码 (Code128)
        # 增加 module_width 提升条码本身的生成精度
        code128 = barcode.get('code128', sku, writer=ImageWriter())
        buf = io.BytesIO()
        code128.write(buf, options={
            "module_height": 18.0, 
            "module_width": 0.4, 
            "font_size": 1, 
            "text_distance": 1,
            "quiet_zone": 2
        })
        b_img = Image.open(buf)
        # 保持比例缩放并居中
        b_img = b_img.resize((900, 240))
        img.paste(b_img, (50, 220))
    except Exception as e:
        st.error(f"条码生成失败: {e}")

    # 绘制文本 (使用更大的字号确保清晰)
    # 品牌及品名 (居中)
    draw.text((500, 80), title, fill='black', font=load_font(65), anchor="mm")
    # 规格选项 (居中)
    draw.text((500, 170), spec, fill='black', font=load_font(55), anchor="mm")
    # SKU 文本 (条码下方)
    draw.text((500, 500), sku, fill='black', font=load_font(50), anchor="mm")
    # 产地标识
    draw.text((500, 565), "MADE IN CHINA", fill='black', font=load_font(45), anchor="mm")
    
    return img

def render_copy_button(text):
    """一键复制 HTML 组件"""
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        body {{ margin: 0; padding: 2px; font-family: sans-serif; }}
        .container {{ display: flex; align-items: center; }}
        .text-box {{ flex-grow: 1; padding: 8px 12px; border: 1px solid #d1d5db; border-radius: 4px; background-color: #f9fafb; color: #111827; font-size: 14px; outline: none; margin-right: 10px; width: 100%; box-sizing: border-box; }}
        .copy-btn {{ padding: 8px 15px; background-color: #ffffff; border: 1px solid #d1d5db; border-radius: 4px; cursor: pointer; color: #374151; font-size: 13px; font-weight: bold; min-width: 90px; transition: all 0.2s; white-space: nowrap; box-sizing: border-box; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }}
        .copy-btn:hover {{ background-color: #f3f4f6; }}
    </style>
    </head>
    <body>
    <div class="container">
        <input type="text" value="{text}" id="inputBox" class="text-box" readonly>
        <button onclick="copyText()" id="copyBtn" class="copy-btn">复制</button>
    </div>
    <script>
    function copyText() {{
        var copyText = document.getElementById("inputBox");
        copyText.select();
        document.execCommand("copy"); 
        var btn = document.getElementById("copyBtn");
        btn.innerText = "✅ 复制成功";
        btn.style.backgroundColor = "#dcfce7";
        btn.style.borderColor = "#86efac";
        btn.style.color = "#166534";
        setTimeout(function(){{
            btn.innerText = "复制";
            btn.style.backgroundColor = "#ffffff";
            btn.style.borderColor = "#d1d5db";
            btn.style.color = "#374151";
        }}, 2000); 
    }}
    </script>
    </body>
    </html>
    """
    components.html(html_code, height=45)

def process_lxu_long_image(uploaded_file, prompt):
    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash", 
            system_instruction="你是一个精通韩国 Coupang 选品和竞品分析的专家，品牌名为 LxU。"
        )
        temp_name = f"temp_{int(time.time())}_{uploaded_file.name}"
        with open(temp_name, "wb") as f:
            f.write(uploaded_file.getbuffer())
        gen_file = genai.upload_file(path=temp_name)
        response = model.generate_content([gen_file, prompt])
        if os.path.exists(temp_name): os.remove(temp_name)
        return response.text
    except Exception as e:
        return f"❌ 引擎执行出错: {str(e)}"

# ================= 2. 侧边栏 (设置与标签生成) =================

st.set_page_config(page_title="LxU 测款指挥舱", layout="wide")

with st.sidebar:
    st.header("⚙️ 引擎配置")
    secret_key = st.secrets.get("GEMINI_API_KEY", "")
    api_key = st.text_input("Gemini API Key", value=secret_key, type="password")
    if not api_key:
        st.warning("👈 请填入 API Key")
        st.stop()
    else:
        st.success("✅ 付费级引擎就绪")
        
    st.divider()
    
    st.header("🏷️ 50x30 标签生成")
    # 默认值优化
    val_sku = st.text_input("货号 (SKU)", "8801234567891")
    val_title = st.text_input("品名 (支持中韩文)", "LxU 3색 타이어 공기압 모니터링 캡")
    val_spec = st.text_input("规格", "Model: C159 | Qty: 4pcs")
    
    if st.button("生成高清标签图", use_container_width=True):
        st.session_state.label_img = make_label_50x30(val_sku, val_title, val_spec)
        
    if 'label_img' in st.session_state and st.session_state.label_img:
        # 显示预览
        st.image(st.session_state.label_img, use_column_width=True, caption="高清预览 (50x30mm)")
        
        # 转换为下载字节流
        buf = io.BytesIO()
        st.session_state.label_img.save(buf, format="PNG", dpi=(300, 300))
        st.download_button(
            label="📥 下载标签 (PNG)", 
            data=buf.getvalue(), 
            file_name=f"LxU_Label_{val_sku}.png", 
            mime="image/png",
            use_container_width=True
        )

genai.configure(api_key=api_key)

# ================= 3. 主页面 (测款对话流) =================

st.title("⚡ LxU 测款指挥舱")
st.info("💡 **操作提醒**：直接在空白处按 `Ctrl+V` 粘贴截图即可！")

files = st.file_uploader("📥 [全局粘贴/拖拽区]", type=["png", "jpg", "jpeg", "webp", "pdf"], accept_multiple_files=True)

if files:
    for f in files:
        with st.expander(f"🖼️ 查看图片预览: {f.name}", expanded=False):
            st.image(f, use_column_width=True)
            
        with st.chat_message("assistant"):
            prompt = """
            任务：极简模式测款提取。必须严格按 JSON 输出：
            {
              "keywords": [{"kr": "名词", "cn": "翻译"}...],
              "name_cn": "LxU [中文名]",
              "name_kr": "LxU [韩文名]"
            }
            """
            with st.spinner(f"⚡ 正在分析 {f.name} ..."):
                res_text = process_lxu_long_image(f, prompt)
            
            try:
                json_str = res_text.replace("```json", "").replace("```", "").strip()
                data = json.loads(json_str)
                st.markdown(f"### 📦 {f.name} 提取结果")
                for i, item in enumerate(data.get('keywords', [])):
                    c1, c2, c3 = st.columns([0.5, 6, 4])
                    c1.markdown(f"<div style='padding-top:12px;'>{i+1}</div>", unsafe_allow_html=True)
                    with c2: render_copy_button(item.get('kr', ''))
                    c3.markdown(f"<div style='padding-top:12px; color:#666;'>{item.get('cn', '')}</div>", unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
                nc1, nc2 = st.columns([1, 9])
                nc1.markdown("<div style='padding-top:12px;'>中文名</div>", unsafe_allow_html=True)
                with nc2: render_copy_button(data.get('name_cn', ''))
                kc1, kc2 = st.columns([1, 9])
                kc1.markdown("<div style='padding-top:12px;'>韩文名</div>", unsafe_allow_html=True)
                with kc2: render_copy_button(data.get('name_kr', ''))
            except:
                st.error("解析失败")
            st.divider()
