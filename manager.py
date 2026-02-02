import subprocess
import time
import sys
import os

# === 設定區 ===
# 你想要一次抓幾篇論文？
BATCH_SIZE = 20

# 每次抓取的間隔秒數 (避免被 API 封鎖)
FETCH_INTERVAL = 2

def run_script(script_name):
    """
    執行 Python 腳本並等待完成
    使用 sys.executable 確保使用當前 VS Code 的 Python 環境
    """
    print(f"🚀 正在執行：{script_name}...")
    
    try:
        # check=True 代表如果腳本執行錯誤 (return code != 0) 會跳出 Exception
        result = subprocess.run(
            [sys.executable, script_name], 
            check=True,
            text=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {script_name} 執行失敗！錯誤碼：{e.returncode}")
        return False
    except Exception as e:
        print(f"❌ 無法執行 {script_name}: {e}")
        return False

# === 主流程 ===
if __name__ == "__main__":
    print("="*40)
    print(f"🤖 科普日報自動化總管 啟動")
    print(f"🎯 本次目標：抓取 {BATCH_SIZE} 篇新論文並製作教材")
    print("="*40)

    # 1. 批次執行 Step 2 (抓取資料)
    print(f"\n[第一階段] 開始抓取論文 (共 {BATCH_SIZE} 次)...")
    success_count = 0
    
    for i in range(BATCH_SIZE):
        print(f"\n--- 第 {i+1} / {BATCH_SIZE} 篇 ---")
        if run_script("step2_fetch_papers.py"):
            success_count += 1
        
        # 休息一下
        if i < BATCH_SIZE - 1:
            print(f"⏳ 休息 {FETCH_INTERVAL} 秒...")
            time.sleep(FETCH_INTERVAL)

    print("-" * 30)
    print(f"📊 抓取報告：成功 {success_count} / 失敗 {BATCH_SIZE - success_count}")

    if success_count == 0:
        print("⚠️ 沒有抓到任何論文，終止後續動作。")
        exit()

    # 2. 執行 Step 3 (AI 處理)
    # 因為 Step 3 現在會自動掃描 raw_queue 裡的所有檔案，所以只要跑一次就好
    print("\n[第二階段] 呼叫 AI 進行轉譯與出題...")
    time.sleep(2) # 緩衝一下
    
    run_script("step3_ai_processor.py")

    # 3. 提示開啟 App
    print("\n" + "="*40)
    print("🎉 全部作業完成！")
    print("="*40)
    
    # 檢查是否要在這裡直接啟動 Streamlit?
    # 通常建議手動開，但如果你想自動開，可以把下面註解拿掉
    
    user_input = input("❓ 是否要現在啟動 App 介面? (y/n): ")
    if user_input.lower() == 'y':
        print("正在啟動 Streamlit...")
        os.system("streamlit run app.py")