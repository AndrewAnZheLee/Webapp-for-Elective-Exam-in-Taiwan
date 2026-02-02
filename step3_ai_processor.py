import json
import os
import time
import re
import glob
import google.generativeai as genai
from dotenv import load_dotenv

# === 1. 設定區 ===
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ 錯誤：找不到 API Key，請檢查 .env 檔案")
    exit()

genai.configure(api_key=api_key)

# 請使用你之前測試成功的模型 (例如 'models/gemini-pro' 或 'models/gemini-1.5-flash')
# 如果不確定，請先跑 check_models.py
model = genai.GenerativeModel('models/gemini-3-flash-preview') 

# === 2. 輔助函式 ===

def clean_filename(title):
    """
    清除檔名中的非法字元，並限制長度
    """
    # 移除 / \ : * ? " < > | 
    cleaned = re.sub(r'[\\/*?:"<>|]', "_", title)
    # 移除多餘空白
    cleaned = cleaned.strip()
    return cleaned

# 在 step3_ai_processor.py 中修改這一塊

def generate_content(paper_data):
    # 1. 取得科目英文代碼 (從 step2 傳來的)
    raw_subject = paper_data.get('subject', 'science')
    
    # 2. 定義科目對應的中文職稱
    subject_map = {
        "physics": "物理",
        "chemistry": "化學",
        "biology": "生物"
    }
    
    # 轉換成中文，例如 "physics" -> "物理"，若找不到則預設 "自然科"
    teacher_type = subject_map.get(raw_subject, "自然科")
    
    print(f"🤖 AI ({teacher_type}老師) 正在閱讀：{paper_data['title']}...")

    # 3. 根據科目微調 Prompt (動態人設)
    prompt = f"""
    你是一位台灣資深的高中【{teacher_type}】老師，專精於準備「分科測驗」。
    請閱讀以下學術論文摘要，將其轉化為一篇適合高中生閱讀的科普文章。
    
    === 論文資訊 ===
    標題: {paper_data['title']}
    科目: {teacher_type} (對應章節: {paper_data.get('mapping_chapter', '相關領域')})
    摘要: {paper_data['summary']}
    ===============

    請依據以下格式輸出：

    # {paper_data['title']} (中文標題)

    ## 1. 研究背景與課本關聯
    (用 150 字以內，用生活化例子引入。請明確指出這與高中{teacher_type}課本的「{paper_data.get('mapping_chapter')}」章節有何關聯。)

    ## 2. 核心發現
    (用 300-500 字解釋研究內容。請務必使用台灣高中{teacher_type}科的專有名詞。避免過度使用生硬翻譯。)

    ---
    (以下為隱藏資料，請務必嚴格遵守 JSON 格式，不要加 Markdown code block 標記)
    
    ===QUIZ_JSON===
    {{
        "question": "這裡填寫設計好的混合題題目敘述 (請設計一題結合{teacher_type}觀念的應用題)",
        "options": [
            "(A) 選項一內容",
            "(B) 選項二內容",
            "(C) 選項三內容",
            "(D) 選項四內容"
        ],
        "correct_answer": "A",
        "explanation": "這裡填寫詳解，解釋為什麼 A 是對的，其他是錯的。"
    }}
    """

    try:
        # 建議 temperature 維持在 0.5 或 0.4，讓 JSON 格式更穩定，不容易跑版
        response = model.generate_content(prompt, generation_config={"temperature": 0.4})
        return response.text
    except Exception as e:
        print(f"❌ AI 生成失敗: {e}")
        return None
    
def process_single_file(filepath):
    """
    處理單一檔案的完整流程
    """
    # A. 讀取原始資料
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            paper_data = json.load(f)
    except Exception as e:
        print(f"⚠️ 無法讀取檔案 {filepath}: {e}")
        return

    # B. 呼叫 AI
    ai_output = generate_content(paper_data)
    
    if ai_output:
        # C. 準備存檔路徑
        # 取得科目，若無則歸類為 uncategorized
        subject = paper_data.get('subject', 'uncategorized')
        
        # 建立 output 資料夾： articles/physics
        save_folder = f"articles/{subject}"
        os.makedirs(save_folder, exist_ok=True)
        
        # D. 產生檔名：YYYYMMDD_標題.json
        # 加上日期前綴是為了排序方便，標題則是為了好找
        timestamp = time.strftime("%Y%m%d")
        safe_title = clean_filename(paper_data['title'])
        
        # 截斷過長的標題以防作業系統報錯 (保留前 80 字元)
        final_filename = f"{save_folder}/{timestamp}_{safe_title[:80]}.json"
        
        # E. 組合最終資料
        final_article = {
            "id": f"{timestamp}_{safe_title[:10]}", # 簡易 ID
            "meta": paper_data,       # 保留原始 metadata (來源、作者...)
            "content": ai_output,     # AI 寫好的文章
            "processed_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # F. 寫入硬碟
        with open(final_filename, "w", encoding="utf-8") as f:
            json.dump(final_article, f, indent=4, ensure_ascii=False)
        
        print(f"✅ 文章生成成功！")
        print(f"📂 已存檔至：{final_filename}")
        
        # G. 刪除原始檔案 (表示處理完成)
        # 如果你想保留備份，可以把 os.remove 改成 shutil.move
        try:
            os.remove(filepath)
            print(f"🗑️ 已移除原始檔 (Queue Cleared)")
        except Exception as e:
            print(f"⚠️ 原始檔刪除失敗: {e}")
            
    else:
        print("⚠️ 跳過此檔案 (AI 未回傳內容)")

# === 3. 主程式 ===
if __name__ == "__main__":
    base_queue_dir = "raw_queue"
    
    # 檢查佇列資料夾是否存在
    if not os.path.exists(base_queue_dir):
        print(f"📭 資料夾 {base_queue_dir} 不存在。請先執行 Step 2 抓取論文。")
        exit()
        
    print(f"🔍 正在掃描 {base_queue_dir} 下的所有論文...")
    
    # 使用 recursive=True 搜尋所有子資料夾 (physics, biology...)
    files = glob.glob(f"{base_queue_dir}/**/*.json", recursive=True)
    
    if not files:
        print("📭 目前沒有待處理的論文。")
    else:
        print(f"📦 發現 {len(files)} 篇待處理論文，開始批次作業...\n")
        
        for file in files:
            # 確保是檔案不是資料夾
            if os.path.isfile(file):
                process_single_file(file)
                
                # 休息 3 秒，避免 API 使用頻率過高 (Rate Limit)
                print("⏳ 休息 3 秒...")
                time.sleep(3)
                print("-" * 30)
            
        print("\n🎉 所有排程處理完畢！請執行 `streamlit run app.py` 查看成果。")