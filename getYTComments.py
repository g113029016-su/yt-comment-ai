import csv
import googleapiclient.discovery
import os
import time

API_KEY = "YOUR_API_KEY_HERE"

def get_all_comments(video_id):
    youtube = googleapiclient.discovery.build(
        "youtube", "v3", developerKey=API_KEY
    )

    rows = []
    next_page_token = None

    while True:
        request = youtube.commentThreads().list(
            part="snippet,replies",
            videoId=video_id,
            maxResults=100,
            pageToken=next_page_token,
            textFormat="plainText"
        )
        response = request.execute()

        for item in response["items"]:
            top = item["snippet"]["topLevelComment"]
            top_id = top["id"]

            # 頂級留言
            rows.append({
                "video_id": video_id,
                "comment_id": top_id,
                "parent_comment_id": top_id,
                "is_reply": False,
                "author": top["snippet"]["authorDisplayName"],
                "text": top["snippet"]["textDisplay"],
                "likeCount": top["snippet"]["likeCount"],
                "publishedAt": top["snippet"]["publishedAt"]
            })

            collected_replies = []

            # API 預設回傳的 replies
            if "replies" in item:
                for reply in item["replies"]["comments"]:
                    collected_replies.append(reply)

            # 如果回應沒拿齊 → 補抓
            if item["snippet"]["totalReplyCount"] > len(collected_replies):
                collected_replies.extend(
                    get_remaining_replies(youtube, top_id)
                )

            # 回應留言
            for reply in collected_replies:
                rows.append({
                    "video_id": video_id,
                    "comment_id": reply["id"],
                    "parent_comment_id": top_id,
                    "is_reply": True,
                    "author": reply["snippet"]["authorDisplayName"],
                    "text": reply["snippet"]["textDisplay"],
                    "likeCount": reply["snippet"]["likeCount"],
                    "publishedAt": reply["snippet"]["publishedAt"]
                })

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    return rows


def get_remaining_replies(youtube, parent_id):
    replies = []
    next_page_token = None

    while True:
        request = youtube.comments().list(
            part="snippet",
            parentId=parent_id,
            maxResults=100,
            pageToken=next_page_token,
            textFormat="plainText"
        )
        response = request.execute()

        replies.extend(response["items"])

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    return replies


def save_to_csv(video_id, rows):
    filename = f"comments_{video_id}.csv"
    fieldnames = [
        "video_id",
        "comment_id",
        "parent_comment_id",
        "is_reply",
        "author",
        "text",
        "likeCount",
        "publishedAt"
    ]

    # 嘗試寫入檔案，如果失敗則使用備用檔名
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            # 如果不是第一次嘗試，使用不同的檔名
            if attempt > 0:
                timestamp = int(time.time())
                filename = f"comments_{video_id}_{timestamp}.csv"
                print(f"⚠️ 原檔案被占用，嘗試使用新檔名：{filename}")
            
            with open(filename, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            
            print(f"✅ 已儲存：{filename}")
            return filename  # 回傳實際使用的檔名
            
        except PermissionError:
            if attempt < max_attempts - 1:
                print(f"⚠️ 檔案 {filename} 被其他程式占用，{2-attempt} 秒後重試...")
                time.sleep(2)
            else:
                # 最後一次嘗試失敗
                raise PermissionError(
                    f"❌ 無法儲存檔案！\n"
                    f"可能原因：\n"
                    f"1. 檔案 {filename} 已被 Excel 或其他程式打開\n"
                    f"2. 資料夾沒有寫入權限\n"
                    f"\n解決方法：\n"
                    f"1. 關閉所有開啟該檔案的程式\n"
                    f"2. 或刪除/重新命名舊的 CSV 檔案"
                )
        except Exception as e:
            raise Exception(f"❌ 儲存檔案時發生錯誤：{str(e)}")


if __name__ == "__main__":
    video_id = input("請輸入 YouTube 影片 ID：").strip()
    rows = get_all_comments(video_id)
    save_to_csv(video_id, rows)

    print(f"共存入 {len(rows)} 則留言（含回應）")
