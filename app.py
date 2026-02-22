import streamlit as st
import streamlit.components.v1 as components
import google.generativeai as genai
from PIL import Image
import io
import os
import time
import json
import re

# ================= 1. 核心工具函数 =================

def render_copy_button(text, key):
    """带 ✅ 成功反馈的一键复制按钮"""
    html_code = f"""
    <!DOCTYPE html>
    <html><head><style>
        body {{ margin: 0; padding: 2px; font-family: sans-serif; }}
        .container {{ display: flex; align-items: center; }}
        .text-box {{ flex-grow: 1; padding: 8px 12px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; width: 100%; box-sizing: border-box; background: #fdfdfd; }}
        .copy-btn {{ padding: 8px 15px; background: #fff; border: 1px solid #ddd; border-radius: 4px; margin-left: 8px; cursor: pointer; font-weight: bold; min-width: 80px; transition: 0.2s; }}
    </style></head>
    <body><div class="container">
        <input type="text" value="{text}" id="q_{key}" class="text-box" readonly>
        <button onclick="c()" id="b_{key}" class="copy-btn">复制</button>
    </div>
    <script>
    function c() {{
        var i = document.getElementById("q_{key}"); i.select(); document.execCommand("copy");
        var b = document.getElementById("b_{key}"); b.innerText = "✅ 成功";
        b.style.background = "#dcfce7"; b.style.borderColor = "#86efac";
        setTimeout(()=>{{ b.innerText = "复制"; b.style.background = "#fff"; b.style.borderColor = "#ddd"; }}, 2000);
    }}
    </script></body></html>
    """
    components.html(html_code, height=45)

def process_lxu_long_image(uploaded_file, prompt):
    """Gemini 2.5 识图核心"""
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

# ================= 2. 界面配置与侧边栏 =================

st.set_page_config(page_title="LxU 测款指挥舱", layout="wide")

with st.sidebar:
    st.header("⚙️ 引擎配置")
    # 尝试从 Secrets 获取，或手动输入
    secret_key = st.secrets.get("GEMINI_API_KEY", "")
    api_key = st.text_input("Gemini API Key", value=secret_key, type="password")
    if not api_key:
        st.warning("👈 请输入 API Key 以启动系统")
        st.stop()
    genai.configure(api_key=api_key)
    st.success("✅ 极速引擎已就绪")

# ================= 3. 主界面 (测款识图) =================

st.title("⚡ LxU 测款指挥舱 (识图专用版)")
st.info("💡 **效率提示**：微信截图后，在网页任意空白处点击并按 `Ctrl+V`。预览图会自动折叠。")

# 全局粘贴区域
files = st.file_uploader("📥 [全局粘贴/拖拽区]", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True)

if files:
    for idx, f in enumerate(files):
        # 预览折叠逻辑
        with st.expander(f"🖼️ 查看图片预览: {f.name}", expanded=False):
            st.image(f, use_column_width=True)
            
        with st.chat_message("assistant"):
            # 强化后的精准 Prompt
            prompt = """
            任务：作为精通韩国 Coupang 的专家，提取精准商品名词。
            必须严格按照以下 JSON 输出，禁止任何说明：
            {
              "keywords": [{"kr": "精准韩文名词", "cn": "中文翻译"}...],
              "name_cn": "LxU [简短精准的中文品名]",
              "name_kr": "LxU [对应的韩文品名]"
            }
            """
            with st.spinner(f"⚡ 正在分析 {f.name} ..."):
                res_text = process_lxu_long_image(f, prompt)
            
            try:
                # 强力清洗 JSON 格式，防止解析失败
                json_str = re.search(r"\{.*\}", res_text, re.DOTALL).group()
                data = json.loads(json_str)
                
                st.markdown(f"### 📦 {f.name} 提取结果")
                
                # 关键词提取展示
                for i, item in enumerate(data.get('keywords', [])):
                    c1, c2, c3 = st.columns([0.5, 6, 4])
                    c1.markdown(f"**{i+1}**")
                    with c2:
                        render_copy_button(item.get('kr', ''), f"kw_{idx}_{i}")
                    c3.markdown(f"<div style='padding-top:12px; color:#666;'>{item.get('cn', '')}</div>", unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # 内部品名提取展示
                st.markdown("##### 🏷️ 内部管理品名 (LxU 品牌)")
                nc1, nc2 = st.columns([1, 9])
                nc1.write("CN 中文")
                with nc2:
                    render_copy_button(data.get('name_cn', ''), f"name_cn_{idx}")
                
                kc1, kc2 = st.columns([1, 9])
                kc1.write("KR 韩文")
                with kc2:
                    render_copy_button(data.get('name_kr', ''), f"name_kr_{idx}")
                
                st.divider()
            except Exception:
                st.error(f"解析失败。原始内容：\n{res_text}")
