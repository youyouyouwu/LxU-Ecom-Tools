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

# ================= 1. 页面配置与侧边栏 =================
st.set_page_config(page_title="LxU 测款指挥舱", layout="wide")

with st.sidebar:
    st.header("⚙️ 引擎配置")
    secret_key = st.secrets.get("GEMINI_API_KEY", "")
    api_key = st.text_input("Gemini API Key", value=secret_key, type="password")
    if not api_key:
        st.warning("👈 请在此填入 API Key，或在后台 Secrets 配置。")
        st.stop()
    else:
        st.success("✅ 付费级 2.5 极速引擎已就绪！")
        
    st.divider()
    
    st.header("🏷️ 50x30 标签生成")
    val_sku = st.text_input("条码内容 (SKU)", "880123456789")
    val_title = st.text_input("产品标题", "LxU Brand Product")
    val_spec = st.text_input("规格选项", "Model: Banana | Color: Yellow")
    
    if st.button("生成高清标签图", use_container_width=True):
        st.session_state.label_img = make_label_50x30(val_sku, val_title, val_spec)
        
    if 'label_img' in st.session_state and st.session_state.label_img:
        st.image(st.session_state.label_img, use_column_width=True)
        buf = io.BytesIO()
        st.session_state.label_img.save(buf, format="PNG")
        st.download_button("📥 下载标签 (PNG)", buf.getvalue(), f"LxU_{val_sku}.png", use_container_width=True)

genai.configure(api_key=api_key)

# ================= 2. 独立定制的一键复制组件 =================
def render_copy_button(text):
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        body {{ margin: 0; padding: 2px; font-family: "Microsoft YaHei", sans-serif; }}
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

# ================= 3. 极简识图引擎 =================
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
        
        # 不再使用全屏 status，改用更轻量的 spinner
        response = model.generate_content([gen_file, prompt])
        
        if os.path.exists(temp_name):
            os.remove(temp_name)
            
        return response.text
    except Exception as e:
        return f"❌ 引擎执行出错: {str(e)}"

# ================= 4. 标签绘制逻辑 (50x30mm) =================
def make_label_50x30(sku, title, spec):
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

# ================= 5. 主交互界面 =================

st.title("⚡ LxU 测款指挥舱")

st.info("💡 **效率秘籍**：请先使用微信截图。然后在当前网页的**任意空白处**点一下鼠标，直接按键盘 `Ctrl+V`，无需按回车即可极速提取！", icon="🚀")

# 隐藏了边框的 uploader，专门用来接管全局粘贴
files = st.file_uploader("📥 [全局粘贴区] 支持直接拖拽或 Ctrl+V 粘贴图片", type=["png", "jpg", "jpeg", "webp", "pdf"], accept_multiple_files=True)

if files:
    with st.chat_message("user"):
        cols = st.columns(min(len(files), 4))
        for idx, f in enumerate(files):
            cols[idx % 4].image(f, caption=f.name, use_column_width=True)
            
    with st.chat_message("assistant"):
        for f in files:
            prompt = """
            任务：极简模式测款提取。
            请直接分析产品图，**必须严格按照以下 JSON 格式输出结果**。
            严禁输出任何废话、Markdown 表格或解释文字，只能输出纯 JSON 代码：
            
            ⚠️ 【极其重要的搜索词提取规则】：
            提取的 5 个韩文搜索词【必须是韩国买家在 Coupang 真实搜索时使用的具体商品名词】（例如：胎压监测帽、汽车气门嘴盖、轮胎压力测试盖）。
            【严禁】输出任何缺乏购物意图的形容词、功能描述或泛泛之词。所有的词都必须能直接拿到前台精准搜出该类目商品！
            
            {
              "keywords": [
                {"kr": "精准商品名词1", "cn": "中文翻译1"},
                {"kr": "精准商品名词2", "cn": "中文翻译2"},
                {"kr": "精准商品名词3", "cn": "中文翻译3"},
                {"kr": "精准商品名词4", "cn": "中文翻译4"},
                {"kr": "精准商品名词5", "cn": "中文翻译5"}
              ],
              "name_cn": "LxU [简短精准的中文品名]",
              "name_kr": "LxU [对应的韩文品名]"
            }
            """
            with st.spinner(f"⚡ 正在深度扫描核心商品词..."):
                res_text = process_lxu_long_image(f, prompt)
            
            try:
                json_str = res_text.replace("```json", "").replace("```", "").strip()
                data = json.loads(json_str)
                
                st.markdown("##### 🔍 前台精准竞品搜索词")
                for i, item in enumerate(data.get('keywords', [])):
                    c1, c2, c3 = st.columns([0.5, 6, 4])
                    c1.markdown(f"<div style='padding-top:12px; font-weight:bold; color:#555;'>{i+1}</div>", unsafe_allow_html=True)
                    with c2:
                        render_copy_button(item.get('kr', ''))
                    c3.markdown(f"<div style='padding-top:12px; color:#666;'>{item.get('cn', '')}</div>", unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                st.markdown("##### 🏷️ 内部管理品名")
                nc1, nc2 = st.columns([1, 9])
                nc1.markdown("<div style='padding-top:12px; color:#555;'>CN 中文</div>", unsafe_allow_html=True)
                with nc2:
                    render_copy_button(data.get('name_cn', ''))
                
                kc1, kc2 = st.columns([1, 9])
                kc1.markdown("<div style='padding-top:12px; color:#555;'>KR 韩文</div>", unsafe_allow_html=True)
                with kc2:
                    render_copy_button(data.get('name_kr', ''))
                
            except Exception as parse_err:
                st.error("解析数据结构失败，原始返回如下：")
                st.markdown(res_text)
                
            st.divider()
