import getYTComments
import classify_comments
import cluster_comments


if __name__ == "__main__":
    video_id = input("請輸入 YouTube 影片 ID：").strip()
    rows = getYTComments.get_all_comments(video_id)
    getYTComments.save_to_csv(video_id, rows)

    print(f"共存入 {len(rows)} 則留言（含回應）")

    classify_comments.main(video_id)

    cluster_comments.main(video_id)