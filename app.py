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

# ================= 1. 核心工具函数 (样本 1:1 复刻版) =================

def wrap_text_pil(text, font, max_width, draw_surface):
    """
    辅助函数：计算文本宽度并实现自动折行
    返回: 包含多行文本的列表
    """
    lines = []
    # 如果文本包含换行符，先按换行符分割
    paragraphs = text.split('\n')
    
    for paragraph in paragraphs:
        words = paragraph.split(' ')
        current_line = words[0]
        for word in words[1:]:
            # 尝试把下一个词加到当前行，计算宽度
            test_line = current_line + " " + word
            # 使用 textlength 获取精确像素宽度
            bbox = draw_surface.textlength(test_line, font=font)
            if bbox <= max_width:
                current_line = test_line
            else:
                # 如果超宽，就保存当前行，开始新的一行
                lines.append(current_line)
                current_line = word
        lines.append(current_line)
    return lines

def make_label_50x30(sku, title, spec):
    """
    生成 LxU 专属 50x30mm 高清标签 (完美复刻样本布局)
    布局逻辑：两头固定，中间标题自适应折行居中
    """
    width, height = 1000, 600 
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)

    def load_font(size, is_bold=False):
        # 优先加载粗体 Nanum，更接近样本
        font_paths = [
            "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 
            "/usr/share/fonts/truetype/nanum/NanumGothic.ttf", 
            "NanumGothicBold.ttf", "NanumGothic.ttf",
            "C:/Windows/Fonts/malgunbd.ttf", "C:/Windows/Fonts/malgun.ttf",
            "Arialbd.ttf", "Arial.ttf"
        ]
        # 如果没要求粗体，反转列表优先找普通体
        if not is_bold: font_paths.reverse()
            
        for p in font_paths:
            if os.path.exists(p): return ImageFont.truetype(p, size)
        return ImageFont.load_default()

    # --- 1. 绘制顶部条形码 (固定位置) ---
    try:
        code128 = barcode.get('code128', sku, writer=ImageWriter())
        buf = io.BytesIO()
        # 调整参数让条码更宽、更密，接近样本
        code128.write(buf, options={"module_height": 25.0, "module_width": 0.42, "font_size": 0, "quiet_zone": 1})
        b_img = Image.open(buf)
        # 强制拉伸到指定宽度和高度
        b_img = b_img.resize((960, 260)) 
        # 贴在顶部靠上位置
        img.paste(b_img, (20, 20))
    except: pass

    # --- 字体定义 (参考样本大小比例) ---
    # SKU字体：极大，粗体
    f_sku = load_font(75, is_bold=True)
    # 标题字体：大，粗体
    f_title = load_font(70, is_bold=True)
    # 底部字体：中等
    f_bottom = load_font(45)

    # --- 2. 绘制 SKU 文本 (固定在条码正下方) ---
    # y=320 大概在条码下方
    draw.text((500, 320), sku, fill='black', font=f_sku, anchor="mm")

    # --- 3. 绘制底部 MADE IN CHINA (固定在最底部) ---
    # y=570 非常靠近底部边缘
    draw.text((500, 570), "MADE IN CHINA", fill='black', font=f_bottom, anchor="mm")

    # --- 4. 绘制中间标题 (自适应折行 + 垂直居中) ---
    # 组合标题和规格
    full_title = f"{title} {spec}".strip()
    
    # 设置最大宽度 (留边距) 和行间距
    max_text_width = 920
    line_padding = 10 
    # 获取单行文字高度
    line_height = f_title.getbbox("A")[3] + line_padding
    
    # 计算自动折行后的文本行列表
    wrapped_lines = wrap_text_pil(full_title, f_title, max_text_width, draw)
    
    # 计算文本块总高度
    total_text_height = len(wrapped_lines) * line_height
    
    # 核心算式：计算在 SKU 和底部文字之间的中心点 Y 坐标
    # SKU底部约在 y=360, 底部文字顶部约在 y=550, 中间区域中心约在 y=455
    center_y_area = 455
    start_y = center_y_area - (total_text_height / 2) + (line_height / 2) - 5 # 微调向上一点

    # 循环绘制每一行
    current_y = start_y
    for line in wrapped_lines:
        draw.text((500, current_y), line, fill='black', font=f_title, anchor="mm")
        current_y += line_height
    
    return img

# ================= 2. 其他界面辅助函数 (保持不变) =================
def render_copy_button(text):
    html_code = f"""
    <!DOCTYPE html>
    <html><head><style>
        body {{ margin: 0; padding: 2px; font-family: sans-serif; }}
        .container {{ display: flex; align-items: center; }}
        .text-box {{ flex-grow: 1; padding: 8px 12px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; width: 100%; box-sizing: border-box; background: #fdfdfd; }}
        .copy-btn {{ padding: 8px 15px; background: #fff; border: 1px solid #ddd; border-radius: 4px; margin-left: 8px; cursor: pointer; font-weight: bold; min-width: 80px; }}
    </style></head>
    <body><div class="container">
        <input type="text" value="{text}" id="q" class="text-box" readonly>
        <button onclick="c()" id="b" class="copy-btn">复制</button>
    </div>
    <script>
    function c() {{
        var i = document.getElementById("q"); i.select(); document.execCommand("copy");
        var b = document.getElementById("b"); b.innerText = "✅ 已复制";
        setTimeout(()=>{{ b.innerText = "复制"; }}, 2000);
    }}
    </script></body></html>
    """
    components.html(html_code, height=45)

# ================= 3. 主界面逻辑 =================

st.set_page_config(page_title="LxU 测款指挥舱", layout="wide")

with st.sidebar:
    st.header("⚙️ 引擎配置")
    api_key = st.text_input("API Key", value=st.secrets.get("GEMINI_API_KEY", ""), type="password")
    if not api_key: st.stop()
    genai.configure(api_key=api_key)
        
    st.divider()
    st.header("🏷️ 50x30 标签生成 (样本复刻版)")
    # 使用你样本里的数据作为默认值，方便对比
    v_sku = st.text_input("货号 (SKU)", "S0033507379541")
    # 我把标题写长一点，测试自动折行效果
    v_title = st.text_input("品名 (自动折行测试)", "[LxU] 용접돋보기 고글형 확대경")
    v_spec = st.text_input("规格", "1.00배율 2개입")
    
    if st.button("生成标签并预览", use_container_width=True, type="primary"):
        st.session_state.l_img = make_label_50x30(v_sku, v_title, v_spec)
        
    if 'l_img' in st.session_state:
        st.image(st.session_state.l_img, use_column_width=True, caption="完美复刻样本布局")
        b = io.BytesIO()
        # 注入 300 DPI 以供打印
        st.session_state.l_img.save(b, format="PNG", dpi=(300, 300))
        st.download_button("📥 下载标签 (PNG)", b.getvalue(), f"{v_sku}.png", use_container_width=True)

st.title("⚡ LxU 测款指挥舱")
st.info("💡 **提示**：侧边栏的标签生成已更新为【样本复刻版】。标题过长会自动折行并居中。")

files = st.file_uploader("📥 全局粘贴/拖拽区", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True)

if files:
    for f in files:
        with st.expander(f"🖼️ 图片预览: {f.name}", expanded=False):
            st.image(f, use_column_width=True)
            
        with st.chat_message("assistant"):
            try:
                model = genai.GenerativeModel("gemini-2.5-flash")
                prompt = "任务：分析图片，提取 5 个精准韩文商品名词。输出纯 JSON (keywords: kr, cn; name_cn; name_kr)。内部品名必须以 LxU 开头。"
                res = model.generate_content([f, prompt])
                data = json.loads(res.text.replace("```json", "").replace("```", "").strip())
                
                st.markdown(f"### 📦 {f.name} 提取结果")
                for i, item in enumerate(data.get('keywords', [])):
                    c1, c2, c3 = st.columns([0.5, 6, 4])
                    c1.markdown(f"**{i+1}**")
                    with c2: render_copy_button(item.get('kr', ''))
                    c3.write(item.get('cn', ''))
                
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("##### 🏷️ 内部管理品名")
                lc1, lc2 = st.columns([1, 9])
                lc1.write("CN 中文")
                with lc2: render_copy_button(data.get('name_cn', ''))
                lk1, lk2 = st.columns([1, 9])
                lk1.write("KR 韩文")
                with lk2: render_copy_button(data.get('name_kr', ''))
                st.divider()
            except:
                st.error("解析失败，请重试。")
