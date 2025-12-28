import pandas as pd
from google import genai
import time

# --- 設定 ---
GEMINI_API_KEY = "YOUR_API_KEY_HERE"
BATCH_SIZE = 50  # 每 50 條留言分析一次，避免單次 Token 太大
DELAY_SECONDS = 15 # 每批次間隔 15 秒，確保 RPM 不會超標

client = genai.Client(api_key=GEMINI_API_KEY)

def safe_analyze(csv_file_path:str, question:str):
    df = pd.read_csv(csv_file_path)
    all_comments = df['text'].dropna().tolist()
    
    # 分批處理
    for i in range(0, len(all_comments), BATCH_SIZE):
        batch = all_comments[i : i + BATCH_SIZE]
        content = "\n".join([f"- {c}" for c in batch])
        
        prompt = f"你是一個專業的留言分析師，我的問題或需求是：{question}\n請依據以下 {len(batch)} 則留言為資料回答：\n{content}"
        
        try:
            print(f"正在處理第 {i+1} ~ {i+len(batch)} 則留言...")
            response = client.models.generate_content(
                model='gemini-2.5-flash-lite', # Flash 是免費版最穩定的
                contents=prompt
            )
            print("分析結果：", response.text)
            
            # 存檔邏輯...(這部分暫略)
            
            # *** 關鍵：強制冷卻 ***
            time.sleep(DELAY_SECONDS) 
            
        except Exception as e:
            if "429" in str(e):
                print("觸發頻率限制！冷卻 60 秒...")
                time.sleep(60)
            else:
                print(f"發生錯誤: {e}")

def analyze_comments_all(file_path, question, selected_comments=None):
    """
    分析 YouTube 留言
    
    參數:
        file_path: CSV 檔案路徑
        question: 使用者問題
        selected_comments: 選中的評論列表 (list)，如果為 None 則讀取所有評論
    """
    try:
        # 1. 如果有選中的評論，直接使用；否則讀取 CSV
        if selected_comments is not None and len(selected_comments) > 0:
            comments = selected_comments
        else:
            # 讀取 CSV
            df = pd.read_csv(file_path)
            
            if 'text' not in df.columns:
                return "錯誤：找不到 'text' 欄位。"
            
            # 提取前 100 則非空留言（避免超出單次 Token 限制太遠）
            comments = df['text'].dropna().head(100).tolist()
        
        all_comments_text = "\n".join([f"- {c}" for c in comments])

        # 2.1 擇一設定 Prompt (問答 prompt)
        prompt = f"""
        請針對以下 YouTube 留言完成問題回覆或需求。除了回復本身不需要其他前後導引詞，並且限制以250字以下簡潔方式生成回覆，
        問題或需求：{question}

        留言列表：
        {all_comments_text}
        """
        
        # 2.2 設定 Prompt (分析報告 prompt)
        # prompt = f"""
        # 請針對以下 YouTube 留言進行內容分析報告（繁體中文）：
        
        # 1. 情緒摘要：分析整體觀眾的情緒傾向。
        # 2. 熱門話題：總結出最常被提到的 3 個主題。
        # 3. 具體建議：創作者應該如何回應這些留言或改進未來的影片？

        # 留言列表：
        # {all_comments_text}
        # """

        # 3. 呼叫 Gemini 2.0 或 1.5 Flash
        # 免費方案目前推薦使用 'gemini-2.0-flash' 或 'gemini-1.5-flash'
        print(f"正在分析 {len(comments)} 則留言...")
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite", 
            contents=prompt
        )
        
        return response.text

    except Exception as e:
        return f"發生錯誤: {e}"

if __name__ == "__main__":
    video_id = input("請輸入 YouTube 影片 ID：").strip()
    question = input("請輸入要對 Gemini 說的話：").strip()
    csv_file_path = f"comments_{video_id}.csv"
    # safe_analyze(csv_file_path, question)
    safe_analyze(csv_file_path, question)
