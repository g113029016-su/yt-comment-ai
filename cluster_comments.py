import pandas as pd
import numpy as np
import time
import os

from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import umap

import jieba
from sklearn.feature_extraction.text import TfidfVectorizer

os.environ["OMP_NUM_THREADS"] = "1"


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


# 基本清洗
def clean_comment_df(
    df,
    text_col="text",
    id_col="comment_id",
    min_len=3
):
    df_clean = df.copy()

    df_clean[text_col] = df_clean[text_col].astype(str).str.strip()

    df_clean = df_clean[
        df_clean[text_col].str.len() >= min_len
    ]

    return df_clean[[id_col, text_col]]


# 自動找「合理的群數」
def find_best_k(embeddings, k_min=2, k_max=12):
    scores = {}
    for k in range(k_min, k_max + 1):
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(embeddings)
        score = silhouette_score(embeddings, labels)
        scores[k] = score
        print(f"k={k}, silhouette={score:.4f}")
    return scores


# 看每一群在講什麼
def show_cluster_samples(df, n=5):
    for cid in sorted(df.cluster.unique()):
        print(f"\n===== Cluster {cid} =====")
        samples = df[df.cluster == cid].text.sample(
            min(n, len(df[df.cluster == cid])),
            random_state=42
        )
        for s in samples:
            print("-", s)


# 分析群集關鍵字
def jieba_tokenizer(text):
    return [
        w for w in jieba.lcut(text)
        if w.strip()
        # and w not in stopwords
        and len(w) > 1
    ]


def extract_cluster_keywords(
    df,
    cluster_id,
    top_n=10,
    min_df=2
):
    texts = df[df.cluster == cluster_id].text.tolist()

    if len(texts) < 3:
        return []

    vectorizer = TfidfVectorizer(
        tokenizer=jieba_tokenizer,
        min_df=min_df,
        max_df=0.9
    )

    tfidf = vectorizer.fit_transform(texts)
    words = vectorizer.get_feature_names_out()

    scores = np.asarray(tfidf.mean(axis=0)).ravel()

    top_idx = scores.argsort()[::-1][:top_n]

    return [(words[i], round(scores[i], 4)) for i in top_idx]


def build_cluster_keyword_df(
    cluster_keywords,
    video_id,
    top_k=10
):
    rows = []

    for cluster_id, keywords in cluster_keywords.items():
        words = [w for w, _ in keywords[:top_k]]
        rows.append({
            "video_id": video_id,
            "cluster_n": int(cluster_id),  # 確保是整數
            "cluster_keywords": " ".join(words)
        })

    return pd.DataFrame(rows)


def main(video_id):
    # 資料載入
    df = pd.read_csv(f"comments_{video_id}.csv")
    comments = df["text"]

    df_clean = clean_comment_df(df, text_col="text", id_col="comment_id", min_len=3)

    comments = df_clean["text"].tolist()
    comment_ids = df_clean["comment_id"].tolist()

    print(f"有效留言數：{len(comments)}")

    # 建立「中文語意向量」
    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

    embeddings = model.encode(
        comments,
        batch_size=64,
        show_progress_bar=True,
        normalize_embeddings=True
    )

    # 降維，讓聚類更穩定
    reducer = umap.UMAP(
        n_neighbors=15,
        n_components=5,
        metric="cosine",
        random_state=42
    )

    reduced_embeddings = reducer.fit_transform(embeddings)

    scores = find_best_k(reduced_embeddings, 2, 10)
    best_k = max(scores, key=scores.get)
    print("建議群數：", best_k)

    # 正式聚類
    kmeans = KMeans(
        n_clusters=best_k,
        random_state=42,
        n_init=20
    )

    labels = kmeans.fit_predict(reduced_embeddings)

    # 整理結果
    df_cluster = pd.DataFrame({
        "comment_id": comment_ids,
        "text": comments,
        "cluster": labels.astype(int)  # 確保是整數
    })

    df_cluster.head()
    show_cluster_samples(df_cluster, n=5)

    cluster_keywords = {}

    for cid in sorted(df_cluster.cluster.unique()):
        keywords = extract_cluster_keywords(df_cluster, cid, top_n=10)
        cluster_keywords[cid] = keywords

    for cid, kws in cluster_keywords.items():
        print(f"\n===== Cluster {cid} =====")
        for w, s in kws:
            print(f"{w} ({s})")

    cluster_kw_df = build_cluster_keyword_df(cluster_keywords, video_id=video_id, top_k=10)
    
    # 使用安全寫入函數
    output_path = "cluster_keywords.csv"
    safe_write_csv(cluster_kw_df, output_path)

    # 合併聚類結果到原始 DataFrame
    df = df.merge(df_cluster[["comment_id", "cluster"]], on="comment_id", how="left")
    
    # 使用安全寫入函數
    safe_write_csv(df, f"comments_{video_id}.csv")


if __name__ == "__main__":
    video_id = input("請輸入 YouTube 影片 ID：").strip()
    main(video_id)
