import streamlit as st
import streamlit.components.v1 as components
import google.generativeai as genai
import io
import os
import time
import json
import re

# ================= 1. 状态锁初始化 =================
# 核心改动：我们需要把图片的二进制数据存下来，方便后续"刷新"时随时调用
if 'extractions' not in st.session_state:
    st.session_state.extractions = []

# ================= 2. 核心工具函数 =================

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

def process_lxu_image_bytes(img_bytes, filename, prompt):
    """支持直接读取字节流的 Gemini 识图核心"""
    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction="你是一个精通韩国 Coupang 选品和竞品分析的专家，品牌名为 LxU。"
        )
        temp_name = f"temp_{int(time.time())}_{filename}"
        with open(temp_name, "wb") as f:
            f.write(img_bytes)
        gen_file = genai.upload_file(path=temp_name)
        response = model.generate_content([gen_file, prompt])
        if os.path.exists(temp_name): os.remove(temp_name)
        return response.text
    except Exception as e:
        return f"❌ 引擎执行出错: {str(e)}"

# ================= 3. 界面配置与侧边栏 =================

st.set_page_config(page_title="LxU 测款指挥舱", layout="wide")

with st.sidebar:
    st.header("⚙️ 引擎配置")
    secret_key = st.secrets.get("GEMINI_API_KEY", "")
    api_key = st.text_input("Gemini API Key", value=secret_key, type="password")
    if not api_key:
        st.warning("👈 请输入 API Key 以启动系统")
        st.stop()
    genai.configure(api_key=api_key)
    st.success("✅ 极速引擎已就绪")

# ================= 4. 主界面 (测款识图) =================

st.title("⚡ LxU 测款指挥舱 (精准找品版)")
st.info("💡 **效率提示**：微信截图后粘贴(Ctrl+V)。已增加独立刷新功能，哪个结果不满意就单刷哪个！")

files = st.file_uploader("📥 [全局粘贴/拖拽区]", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True)

if files:
    if st.button("🚀 开始精准提取竞品词", type="primary", use_container_width=True):
        new_exts = []
        for idx, f in enumerate(files):
            img_bytes = f.getvalue() # 保存图片的二进制数据
            
            with st.expander(f"🖼️ 查看图片预览: {f.name}", expanded=False):
                st.image(img_bytes, use_column_width=True)
                
            with st.chat_message("assistant"):
                prompt_full = """
                任务：分析图片，提取5个用于在Coupang前台精准查找同款竞品的韩文搜索词。
                ⚠️ 极其严格规则：必须是具体的实体商品名词，禁止泛流量词，禁止形容词和卖点。
                必须输出纯 JSON 代码：
                {
                  "keywords": [{"kr": "精准韩文商品名词", "cn": "准确中文翻译"}],
                  "name_cn": "LxU [简短精准的中文实体品名]",
                  "name_kr": "LxU [对应的韩文实体品名]"
                }
                """
                with st.spinner(f"⚡ 首次提取中 {f.name} ..."):
                    res_text = process_lxu_image_bytes(img_bytes, f.name, prompt_full)
                
                try:
                    json_str = re.search(r"\{.*\}", res_text, re.DOTALL).group()
                    data = json.loads(json_str)
                    new_exts.append({"file": f.name, "bytes": img_bytes, "data": data})
                except Exception:
                    st.error(f"解析失败。原始内容：\n{res_text}")
        
        st.session_state.extractions = new_exts

# ================= 5. 渲染结果区 (带独立刷新功能) =================

if st.session_state.extractions:
    for idx, item in enumerate(st.session_state.extractions):
        st.write("---")
        
        # ---------------- A. 关键词区域 ----------------
        c_title, c_btn = st.columns([8, 2])
        with c_title:
            st.markdown(f"### 📦 {item['file']} 精准提取结果")
        with c_btn:
            # 独立刷新按钮：只更新关键词
            if st.button("🔄 换一批搜索词", key=f"btn_kw_{idx}", use_container_width=True):
                prompt_kw = """
                任务：重新分析图片，提取5个【完全不同于之前】的韩文搜索词。
                规则依然极其严格：必须是Coupang买家搜索同款用的【实体名词】，禁止形容词、泛流量词和卖点！
                只输出 keywords 部分的 JSON：
                {"keywords": [{"kr": "新韩文实体名词", "cn": "中文翻译"}]}
                """
                with st.spinner("🔄 正在重新挖掘竞品搜索词..."):
                    res_text = process_lxu_image_bytes(item['bytes'], item['file'], prompt_kw)
                    try:
                        json_str = re.search(r"\{.*\}", res_text, re.DOTALL).group()
                        new_kw_data = json.loads(json_str)
                        # 更新保险箱里的数据
                        st.session_state.extractions[idx]['data']['keywords'] = new_kw_data.get('keywords', [])
                        st.rerun() # 强制刷新页面显示新数据
                    except:
                        st.error("重抽失败，请再试一次。")

        # 渲染关键词
        for i, kw in enumerate(item['data'].get('keywords', [])):
            c1, c2, c3 = st.columns([0.5, 6, 4])
            c1.markdown(f"**{i+1}**")
            with c2: render_copy_button(kw.get('kr', ''), f"kw_{idx}_{i}")
            c3.markdown(f"<div style='padding-top:12px; color:#666;'>{kw.get('cn', '')}</div>", unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # ---------------- B. 内部品名区域 ----------------
        n_title, n_btn = st.columns([8, 2])
        with n_title:
            st.markdown("##### 🏷️ 内部实体管理品名")
        with n_btn:
            # 独立刷新按钮：只更新内部品名
            if st.button("🔄 换一个品名", key=f"btn_name_{idx}", use_container_width=True):
                prompt_name = """
                任务：重新分析图片，为该商品生成一个【全新】的 LxU 品牌内部管理品名。
                必须简短、精准、是实体名词。只输出 JSON：
                {"name_cn": "LxU [全新中文实体品名]", "name_kr": "LxU [全新韩文实体品名]"}
                """
                with st.spinner("🔄 正在重新命名..."):
                    res_text = process_lxu_image_bytes(item['bytes'], item['file'], prompt_name)
                    try:
                        json_str = re.search(r"\{.*\}", res_text, re.DOTALL).group()
                        new_name_data = json.loads(json_str)
                        st.session_state.extractions[idx]['data']['name_cn'] = new_name_data.get('name_cn', '')
                        st.session_state.extractions[idx]['data']['name_kr'] = new_name_data.get('name_kr', '')
                        st.rerun() # 强制刷新页面显示新数据
                    except:
                        st.error("重命名失败，请再试一次。")

        # 渲染内部品名
        nc1, nc2 = st.columns([1, 9])
        nc1.write("CN 中文")
        with nc2: render_copy_button(item['data'].get('name_cn', ''), f"name_cn_{idx}")
        
        kc1, kc2 = st.columns([1, 9])
        kc1.write("KR 韩文")
        with kc2: render_copy_button(item['data'].get('name_kr', ''), f"name_kr_{idx}")
