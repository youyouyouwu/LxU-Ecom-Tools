import streamlit as st
import streamlit.components.v1 as components
import google.generativeai as genai
from PIL import Image
import io
import time
import json
import re

# ================= 1. 状态锁初始化 =================
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
        .text-box {{ flex-grow: 1; padding: 8px 12px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; width: 100%; box-sizing: border-box; background: #fdfdfd; color: #333; }}
        .copy-btn {{ padding: 8px 15px; background: #fff; border: 1px solid #ddd; border-radius: 4px; margin-left: 8px; cursor: pointer; font-weight: bold; min-width: 80px; transition: 0.2s; color: #333; }}
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

def process_lxu_image_bytes(img_bytes, prompt):
    """内存直传 + 原生 JSON 极速引擎"""
    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction="你是一个精通韩国 Coupang 选品和竞品分析的专家，品牌名为 LxU。"
        )
        img = Image.open(io.BytesIO(img_bytes))
        response = model.generate_content(
            [img, prompt],
            generation_config={"response_mime_type": "application/json"}
        )
        return response.text
    except Exception as e:
        return f'{{"error": "{str(e)}" }}'

# ================= 3. 界面配置与侧边栏 =================

# 💡 核心改动：initial_sidebar_state="collapsed" 让侧边栏默认收起
st.set_page_config(page_title="品名识别生成工具", layout="wide", initial_sidebar_state="collapsed")

with st.sidebar:
    st.header("⚙️ 引擎配置")
    
    # 默默在后台获取系统保密的 Key，绝对不传给前端
    secret_key = st.secrets.get("GEMINI_API_KEY", "")
    
    # 前端输入框彻底留空！只作为“备用”或者“临时替换”的入口
    manual_key = st.text_input("备用 API Key (可选)", value="", type="password", help="默认使用系统内部隐藏密钥。若需临时替换，可在此输入。")
    
    # 逻辑判断：优先使用手动输入的，没输入就用系统后台的
    final_api_key = manual_key if manual_key else secret_key
    
    if not final_api_key:
        st.warning("👈 系统未配置 API Key，请联系管理员。")
        st.stop()
        
    genai.configure(api_key=final_api_key)
    st.success("✅ 极速引擎已在后台就绪 (密钥已隐藏)")

# ================= 4. 主界面 (测款识图) =================

st.title("🔎 品名识别生成工具")
st.info("💡 **效率提示**：微信截图后粘贴(Ctrl+V)。标题生成已优化为【客观卖点+核心词】的黄金平衡比例，拒绝极端堆砌！")

files = st.file_uploader("📥 [全局粘贴/拖拽区]", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True)

if files:
    if st.button("🚀 开始极速精准提取", type="primary", use_container_width=True):
        new_exts = []
        for idx, f in enumerate(files):
            img_bytes = f.getvalue() 
            
            with st.expander(f"🖼️ 查看图片预览: {f.name}", expanded=False):
                st.image(img_bytes, use_column_width=True)
                
            prompt_full = """
            任务：分析图片，为该商品生成一套完整的Coupang上架信息。
            
            ⚠️ 必须遵守的极其严格规则：
            1. 搜索词(keywords)：提取5个精准查找同款的【实体名词】，绝对禁止泛流量词。
            2. 内部品名(name)：简短精准的实体名词。
            3. 前台销售标题(title_kr)：符合Coupang真实卖家风格。追求【平衡与自然】：核心名词 + 1~2个客观属性/卖点（如材质、适用场景、具体物理功能）+ 1~2个相关热搜词。
               - 【拒绝极端】：不要像机器人一样无脑堆砌长串的同义词，也不要用“安心驾驶、完美、绝对”等夸张做作的主观广告词。适度体现客观卖点以提高点击率。
               - 【格式要求】：绝对禁止使用任何标点符号（包括逗号、句号、括号等），词与词之间只能用纯空格分隔。长度适中，通顺自然。
            
            必须输出纯 JSON 代码：
            {
              "keywords": [{"kr": "精准韩文名词", "cn": "中文翻译"}],
              "name_cn": "LxU [简短中文实体品名]",
              "name_kr": "LxU [韩文实体品名]",
              "title_cn": "LxU [客观卖点与名词结合的中文SEO标题]",
              "title_kr": "LxU [纯空格分隔的韩文无标点SEO标题]"
            }
            """
            with st.spinner(f"⚡ 极限冲刺中 {f.name} ..."):
                res_text = process_lxu_image_bytes(img_bytes, prompt_full)
            
            try:
                json_str = re.search(r"\{.*\}", res_text, re.DOTALL).group() if "{" in res_text else res_text
                data = json.loads(json_str)
                
                new_exts.append({
                    "file": f.name, 
                    "bytes": img_bytes, 
                    "data": data,
                    "kw_history": [],     
                    "name_history": [],
                    "title_history": []   
                })
            except Exception:
                st.error(f"解析失败。原始内容：\n{res_text}")
        
        st.session_state.extractions = new_exts

# ================= 5. 渲染结果区 (带独立刷新 + 撤销返回) =================

if st.session_state.extractions:
    for idx, item in enumerate(st.session_state.extractions):
        st.write("---")
        
        # ---------------- A. 关键词区域 ----------------
        c_title, c_undo_kw, c_btn_kw = st.columns([6, 2, 2])
        with c_title:
            st.markdown("### 🔎 建议搜索关键词")
            
        with c_undo_kw:
            if item.get('kw_history'):
                if st.button("⏪ 撤销返回", key=f"undo_kw_{idx}", use_container_width=True):
                    prev_kw = st.session_state.extractions[idx]['kw_history'].pop()
                    st.session_state.extractions[idx]['data']['keywords'] = prev_kw
                    st.rerun()
                    
        with c_btn_kw:
            if st.button("🔄 换一批搜索词", key=f"btn_kw_{idx}", use_container_width=True):
                prompt_kw = """
                任务：重新提取5个【完全不同于之前】的韩文搜索词。
                规则：必须是买家搜索同款用的【精准实体名词】，绝对禁止形容词、泛流量词和功能卖点！
                只输出 keywords 的 JSON：
                {"keywords": [{"kr": "新韩文实体名词", "cn": "中文翻译"}]}
                """
                success = False
                with st.spinner("🔄 光速挖掘中..."):
                    res_text = process_lxu_image_bytes(item['bytes'], prompt_kw)
                    try:
                        json_str = re.search(r"\{.*\}", res_text, re.DOTALL).group() if "{" in res_text else res_text
                        new_kw_data = json.loads(json_str)
                        
                        current_kw = st.session_state.extractions[idx]['data'].get('keywords', [])
                        st.session_state.extractions[idx]['kw_history'].append(current_kw)
                        
                        st.session_state.extractions[idx]['data']['keywords'] = new_kw_data.get('keywords', [])
                        success = True
                    except Exception:
                        st.error("重抽失败，请再试一次。")
                
                if success:
                    st.rerun()

        for i, kw in enumerate(item['data'].get('keywords', [])):
            c1, c2, c3 = st.columns([0.5, 6, 4])
            c1.markdown(f"**{i+1}**")
            with c2: render_copy_button(kw.get('kr', ''), f"kw_{idx}_{i}")
            c3.markdown(f"<div style='padding-top:12px; color:#666;'>{kw.get('cn', '')}</div>", unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # ---------------- B. 内部品名区域 ----------------
        n_title, n_undo_name, n_btn_name = st.columns([6, 2, 2])
        with n_title:
            st.markdown("##### 🏷️ 内部实体管理品名")
            
        with n_undo_name:
            if item.get('name_history'):
                if st.button("⏪ 撤销返回", key=f"undo_name_{idx}", use_container_width=True):
                    prev_name = st.session_state.extractions[idx]['name_history'].pop()
                    st.session_state.extractions[idx]['data']['name_cn'] = prev_name['name_cn']
                    st.session_state.extractions[idx]['data']['name_kr'] = prev_name['name_kr']
                    st.rerun()
                    
        with n_btn_name:
            if st.button("🔄 换一个品名", key=f"btn_name_{idx}", use_container_width=True):
                prompt_name = """
                任务：生成一个【全新】的 LxU 品牌内部管理品名。必须简短、精准、是实体名词。
                只输出 JSON：
                {"name_cn": "LxU [新中文实体品名]", "name_kr": "LxU [新韩文实体品名]"}
                """
                success = False
                with st.spinner("🔄 光速命名中..."):
                    res_text = process_lxu_image_bytes(item['bytes'], prompt_name)
                    try:
                        json_str = re.search(r"\{.*\}", res_text, re.DOTALL).group() if "{" in res_text else res_text
                        new_name_data = json.loads(json_str)
                        
                        current_name = {
                            "name_cn": st.session_state.extractions[idx]['data'].get('name_cn', ''),
                            "name_kr": st.session_state.extractions[idx]['data'].get('name_kr', '')
                        }
                        st.session_state.extractions[idx]['name_history'].append(current_name)
                        
                        st.session_state.extractions[idx]['data']['name_cn'] = new_name_data.get('name_cn', '')
                        st.session_state.extractions[idx]['data']['name_kr'] = new_name_data.get('name_kr', '')
                        success = True
                    except Exception:
                        st.error("重命名失败，请再试一次。")
                
                if success:
                    st.rerun()

        nc1, nc2 = st.columns([1, 9])
        nc1.write("CN 中文")
        with nc2: render_copy_button(item['data'].get('name_cn', ''), f"name_cn_{idx}")
        
        kc1, kc2 = st.columns([1, 9])
        kc1.write("KR 韩文")
        with kc2: render_copy_button(item['data'].get('name_kr', ''), f"name_kr_{idx}")
        
        st.markdown("<br>", unsafe_allow_html=True)

        # ---------------- C. 前台销售标题区域 ----------------
        t_title, t_undo_title, t_btn_title = st.columns([6, 2, 2])
        with t_title:
            st.markdown("##### 🛒 前台销售标题 (Coupang SEO)")
            
        with t_undo_title:
            if item.get('title_history'):
                if st.button("⏪ 撤销返回", key=f"undo_title_{idx}", use_container_width=True):
                    prev_title = st.session_state.extractions[idx]['title_history'].pop()
                    st.session_state.extractions[idx]['data']['title_cn'] = prev_title['title_cn']
                    st.session_state.extractions[idx]['data']['title_kr'] = prev_title['title_kr']
                    st.rerun()
                    
        with t_btn_title:
            if st.button("🔄 换一个标题", key=f"btn_title_{idx}", use_container_width=True):
                prompt_title = """
                任务：为该商品生成一套【全新】的Coupang前台销售标题（含中文翻译）。
                要求：
                1. 追求【平衡与自然】：结合“核心实体名词”与“适度客观卖点（如材质、具体功能特性）”。
                2. 【拒绝极端】：绝对不要无脑堆砌一堆废话同义词，也绝对不要使用“安全、完美、放心”等做作的主观夸张形容词。自然通顺即可。
                3. 【绝对禁止】使用任何标点符号（只能用纯空格分隔）。
                只输出 JSON：
                {
                  "title_cn": "LxU [客观卖点与名词结合的中文SEO标题]",
                  "title_kr": "LxU [纯空格分隔的韩文无标点SEO标题]"
                }
                """
                success = False
                with st.spinner("🔄 正在重写平衡版销售标题..."):
                    res_text = process_lxu_image_bytes(item['bytes'], prompt_title)
                    try:
                        json_str = re.search(r"\{.*\}", res_text, re.DOTALL).group() if "{" in res_text else res_text
                        new_title_data = json.loads(json_str)
                        
                        current_title = {
                            "title_cn": st.session_state.extractions[idx]['data'].get('title_cn', ''),
                            "title_kr": st.session_state.extractions[idx]['data'].get('title_kr', '')
                        }
                        st.session_state.extractions[idx]['title_history'].append(current_title)
                        
                        st.session_state.extractions[idx]['data']['title_cn'] = new_title_data.get('title_cn', '')
                        st.session_state.extractions[idx]['data']['title_kr'] = new_title_data.get('title_kr', '')
                        success = True
                    except Exception:
                        st.error("标题重写失败，请再试一次。")
                
                if success:
                    st.rerun()

        tc_cn1, tc_cn2 = st.columns([1, 9])
        tc_cn1.write("CN 中文")
        with tc_cn2: render_copy_button(item['data'].get('title_cn', ''), f"title_cn_{idx}")

        tc_kr1, tc_kr2 = st.columns([1, 9])
        tc_kr1.write("KR 韩文")
        with tc_kr2: render_copy_button(item['data'].get('title_kr', ''), f"title_kr_{idx}")
