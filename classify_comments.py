import pandas as pd
import jieba
import time

# 安全的檔案寫入函數
def safe_write_csv(df, filename, max_attempts=3):
    """
    安全地寫入 CSV 檔案，如果失敗會重試
    """
    for attempt in range(max_attempts):
        try:
            # 如果不是第一次嘗試，使用不同的檔名
            actual_filename = filename
            if attempt > 0:
                timestamp = int(time.time())
                name_parts = filename.rsplit('.', 1)
                actual_filename = f"{name_parts[0]}_{timestamp}.{name_parts[1]}"
                print(f"⚠️ 原檔案被占用，嘗試使用新檔名：{actual_filename}")
            
            df.to_csv(actual_filename, index=False, encoding="utf-8-sig")
            print(f"✅ 已儲存：{actual_filename}")
            return actual_filename
            
        except PermissionError:
            if attempt < max_attempts - 1:
                print(f"⚠️ 檔案 {filename} 被其他程式占用，{2-attempt} 秒後重試...")
                time.sleep(2)
            else:
                raise PermissionError(
                    f"❌ 無法儲存檔案 {filename}！\n"
                    f"可能原因：檔案已被 Excel 或其他程式打開\n"
                    f"解決方法：關閉所有開啟該檔案的程式，或刪除舊檔案"
                )
        except Exception as e:
            raise Exception(f"❌ 儲存檔案時發生錯誤：{str(e)}")
    
    return filename  # 如果都失敗，返回原檔名


# ========= 1. 載入 NTUSD 詞典 =========
def load_word_set(path):
    with open(path, "r", encoding="cp950") as f:
        return set(w.strip() for w in f if w.strip())

POSITIVE_WORDS = load_word_set("ntusd_positive.txt")
NEGATIVE_WORDS = load_word_set("ntusd_negative.txt")

# ========= 2. 疑問詞設定 =========
QUESTION_WORDS = [
    "為什麼", "為何", "怎麼", "怎麼會", "怎麼做", "怎麼辦",
    "為啥", "難道", "嗎", "呢", "問題",
    "請問", "想問", "可不可以", "能不能", "有沒有", "會不會",
    "是不是", "我不懂", "看不懂", "不明白", "搞不清楚"
]

QUESTION_PUNCT = ["?", "？"]

# 加入常見多字詞，避免被切開
for w in ["看不懂", "我不懂", "搞不清楚"]:
    jieba.add_word(w)

# ========= 3. 情緒計分 =========
def sentiment_score(words):
    score = 0
    for w in words:
        if w in POSITIVE_WORDS:
            score += 1
        elif w in NEGATIVE_WORDS:
            score -= 1
    return score

def sentiment_label(score, pos_th=2, neg_th=-2):
    if score >= pos_th:
        return "positive"
    elif score <= neg_th:
        return "negative"
    else:
        return "neutral"

# ========= 4. 問題判斷 =========
def is_question(text):
    if any(p in text for p in QUESTION_PUNCT):
        return True
    for q in QUESTION_WORDS:
        if q in text:
            return True
    return False

# ========= 5. 單筆留言分類 =========
def classify_text(text):
    words = list(jieba.cut(text))
    score = sentiment_score(words)

    return {
        "sentiment_score": score,
        "sentiment": sentiment_label(score),
        "is_question": is_question(text)
    }

# ========= 6. 主程式 =========
def main(video_id:str):
    # 讀取 CSV
    df = pd.read_csv(f"comments_{video_id}.csv")

    # 確認有 text 欄位
    if "text" not in df.columns:
        raise ValueError("CSV 必須包含 'text' 欄位")

    # 套用分類
    results = df["text"].astype(str).apply(classify_text)

    # 拆成欄位
    df["sentiment_score"] = results.apply(lambda x: x["sentiment_score"])
    df["sentiment"] = results.apply(lambda x: x["sentiment"])
    df["is_question"] = results.apply(lambda x: x["is_question"])

    # 使用安全寫入函數
    filename = f"comments_{video_id}.csv"
    safe_write_csv(df, filename)
    
    print(f"✅ 分類完成，已輸出 {filename}")

if __name__ == "__main__":
    video_id = input("請輸入 YouTube 影片 ID：").strip()
    main(video_id)
