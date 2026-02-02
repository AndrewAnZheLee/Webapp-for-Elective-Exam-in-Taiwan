import streamlit as st
import json
import os
import glob

# === 1. 頁面基礎設定 ===
st.set_page_config(
    page_title="分科測驗：前沿科普日報",
    page_icon="🧬",
    layout="wide", # 使用寬螢幕模式
    initial_sidebar_state="expanded"
)

# === 2. 核心邏輯：讀取資料庫 ===
def load_articles():
    base_dir = "articles"
    if not os.path.exists(base_dir):
        return []

    # 搜尋所有子資料夾中的 JSON
    # 結構: articles/physics/xxx.json
    files = glob.glob(f"{base_dir}/**/*.json", recursive=True)
    
    articles = []
    for filepath in files:
        if os.path.isfile(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                    # 補上一些前端需要的屬性
                    # 從路徑判斷科目 (windows/linux 路徑分隔符號處理)
                    folder_name = os.path.basename(os.path.dirname(filepath))
                    data['subject_category'] = folder_name
                    data['filepath'] = filepath
                    
                    articles.append(data)
            except Exception as e:
                print(f"Error loading {filepath}: {e}")
                continue
    
    # 按照 id (通常是日期開頭) 倒序排列，新的在前面
    articles.sort(key=lambda x: x.get('id', ''), reverse=True)
    return articles

def get_subject_emoji(subject):
    if "physics" in subject: return "⚛️"
    if "chemistry" in subject: return "⚗️"
    if "biology" in subject: return "🧬"
    return "📄"

# === 3. 介面佈局 ===

# 載入資料
all_articles = load_articles()

# 側邊欄：標題與篩選
with st.sidebar:
    st.title("🔬 科普日報")
    st.markdown("針對**分科測驗**設計的 AI 讀報機器人。")
    st.divider()

    # 科目篩選器
    subject_filter = st.radio(
        "選擇科目資料夾：",
        ["全部顯示", "physics (物理)", "chemistry (化學)", "biology (生物)"],
        index=0
    )
    
    st.info(f"目前資料庫共有 {len(all_articles)} 篇文章")
    
    # 重新整理按鈕 (Streamlit 只要按 R 或重新整理網頁就會重讀，這裡做個按鈕增加儀式感)
    if st.button("🔄 重新載入資料庫"):
        st.rerun()

# 主畫面內容邏輯
if not all_articles:
    st.warning("📭 資料庫是空的！")
    st.markdown("""
    ### 快速啟動指南：
    1. 執行 `python step2_unified.py` 抓取論文。
    2. 執行 `python step3_ai_processor.py` 生成文章。
    3. 重新整理此頁面。
    """)
else:
    # 1. 根據側邊欄篩選資料
    if subject_filter == "全部顯示":
        filtered_articles = all_articles
    else:
        # 取出括號前的英文單字來比對 (例如 "physics")
        target_sub = subject_filter.split(" ")[0]
        filtered_articles = [a for a in all_articles if a['subject_category'] == target_sub]

    if not filtered_articles:
        st.info("此分類目前沒有文章。趕快去抓幾篇吧！")
    else:
        # 2. 雙欄佈局：左邊選單，右邊閱讀
        col_menu, col_content = st.columns([1, 2.5])

        with col_menu:
            st.subheader("📚 文章列表")
            # 製作選單項目標題
            options = {
                index: f"{get_subject_emoji(a['subject_category'])} {a['meta']['published']} | {a['meta']['title']}"
                for index, a in enumerate(filtered_articles)
            }
            
            # 使用 radio button 當作導航列
            selected_index = st.radio(
                "請點擊閱讀：",
                options=options.keys(),
                format_func=lambda x: options[x],
                label_visibility="collapsed"
            )

        with col_content:
            article = filtered_articles[selected_index]
            meta = article['meta']
            content = article['content']
            
            # === 1. 顯示文章 header ===
            st.markdown(f"### {meta.get('title', '無標題')}")
            c1, c2, c3 = st.columns(3)
            with c1: st.caption(f"**科目：** {article['subject_category'].upper()}")
            with c2: st.caption(f"**日期：** {meta.get('published', '未知')}")
            with c3: st.caption(f"**來源：** [{meta.get('source')}]({meta.get('url', '#')})")
            st.divider()
            
            # === 2. 智慧解析：分離文章與題目 ===
            # 我們設定的分隔符號
            split_marker = "===QUIZ_JSON==="
            
            if split_marker in content:
                # 切割：前面是文章，後面是 JSON 字串
                parts = content.split(split_marker)
                article_text = parts[0]
                json_text = parts[1].strip() # 移除前後空白
                
                # 顯示科普文章本體
                st.markdown(article_text)
                
                # === 3. 互動式測驗區 ===
                st.divider()
                st.subheader("📝 隨堂測驗")
                
                try:
                    # === 修正開始：清洗 AI 雞婆加入的 Markdown 標記 ===
                    # 1. 移除前後空白
                    json_text = parts[1].strip()
                    
                    # 2. 如果 AI 加了 ```json 或 ```，把它們刪掉
                    if json_text.startswith("```"):
                        json_text = json_text.replace("```json", "").replace("```", "").strip()
                    # =================================================
                    
                    # 把 JSON 字串變成 Python 字典
                    quiz_data = json.loads(json_text)
                    
                    # A. 顯示題目
                    st.write(f"**題目：** {quiz_data['question']}")
                    
                    # B. 顯示選項 (Radio Button)
                    # key 很重要！必須加上 article id，否則切換文章時選項會卡住
                    user_choice = st.radio(
                        "請選擇一個答案：",
                        quiz_data['options'],
                        key=f"radio_{article['id']}",
                        index=None  # 預設不選任何一個
                    )
                    
                    # C. 送出按鈕與判斷
                    # 使用 expander 預設隱藏詳解，答對或點開才看得到
                    check_btn = st.button("送出答案", key=f"btn_{article['id']}")
                    
                    if check_btn:
                        if user_choice:
                            # 判斷邏輯：檢查選項開頭是否包含正確答案 (例如 "(A)")
                            # 假設 correct_answer 是 "A"
                            correct_tag = f"({quiz_data['correct_answer']})"
                            
                            if correct_tag in user_choice:
                                st.balloons() # 答對放氣球！
                                st.success(f"🎉 答對了！答案是 {quiz_data['correct_answer']}")
                                st.markdown(f"### 💡 詳解")
                                st.info(quiz_data['explanation'])
                            else:
                                st.error(f"❌ 答錯囉！再試試看？")
                        else:
                            st.warning("請先選擇一個選項喔！")

                    # 如果沒按按鈕，但想直接看詳解 (偷看模式)
                    with st.expander("👁️ 偷看詳解"):
                         st.markdown(f"**正確答案：({quiz_data['correct_answer']})**")
                         st.markdown(quiz_data['explanation'])

                except json.JSONDecodeError:
                    st.error("⚠️ 題目資料解析失敗，請通知管理員 (JSON Error)")
                    # 如果解析失敗，把原始文字印出來除錯
                    st.code(json_text)
            
            else:
                # 舊文章沒有 JSON，直接顯示全文
                st.markdown(content)