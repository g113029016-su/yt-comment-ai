import streamlit as st
import pandas as pd
import os
import plotly.express as px

# 匯入你原本的模組
import getYTComments
import classify_comments
import cluster_comments
from gemini_API import analyze_comments_all

# 設定網頁標題與圖示
st.set_page_config(page_title="YouTube 留言 AI 分析助手", layout="wide")

st.title("📊 YouTube 留言 AI 分析助手")
st.markdown("輸入影片 ID，自動抓取留言、分類情緒、聚類話題，並與 AI 對話！")

# 初始化 session state
if 'selected_indices' not in st.session_state:
    st.session_state.selected_indices = []
if 'ai_response' not in st.session_state:
    st.session_state.ai_response = None

# --- 側邊欄：輸入區 ---
with st.sidebar:
    st.header("設定")
    video_id = st.text_input("YouTube 影片 ID", placeholder="例如：dQw4w9WgXcQ")
    process_btn = st.button("開始抓取與分析", type="primary")

# --- 主要內容區 ---
if video_id:
    csv_file = f"comments_{video_id}.csv"

    if process_btn:
        with st.status("正在處理中...", expanded=True) as status:
            try:
                st.write("1. 正在從 YouTube 抓取留言...")
                rows = getYTComments.get_all_comments(video_id)
                saved_filename = getYTComments.save_to_csv(video_id, rows)
                
                # 確保 saved_filename 不是 None
                if saved_filename and saved_filename != csv_file:
                    csv_file = saved_filename
                    st.warning(f"⚠️ 原檔案被占用，已儲存為：{saved_filename}")
                elif saved_filename:
                    csv_file = saved_filename
                
                st.write("2. 正在進行情緒分類與問題辨識...")
                classify_comments.main(video_id)
                
                st.write("3. 正在進行語意聚類 (這可能需要一點時間)...")
                cluster_comments.main(video_id)
                
                status.update(label="全部處理完成！", state="complete", expanded=False)
                st.success(f"已成功分析 {len(rows)} 則留言！")
                
                # 重置選擇
                st.session_state.selected_indices = []
                
            except PermissionError as e:
                status.update(label="發生錯誤！", state="error", expanded=True)
                st.error(str(e))
                st.info("💡 **快速解決方法：**\n\n"
                       "1. 關閉所有 Excel 視窗（包括 comments_*.csv 和 cluster_keywords.csv）\n\n"
                       "2. 或直接刪除以下檔案：\n"
                       f"   - comments_{video_id}.csv\n"
                       "   - cluster_keywords.csv\n\n"
                       "3. 然後重新點擊「開始抓取與分析」\n\n"
                       "💡 **提示：** cluster_keywords.csv 會在分析時自動重新生成，刪除是安全的！")
            except Exception as e:
                status.update(label="發生錯誤！", state="error", expanded=True)
                st.error(f"發生錯誤：{str(e)}")
                st.info("請檢查影片 ID 是否正確，或稍後再試。")

    # 如果檔案存在，顯示分析結果
    if os.path.exists(csv_file):
        df = pd.read_csv(csv_file)
        
        # 將 cluster 欄位轉換為整數（移除小數點）
        if 'cluster' in df.columns:
            df['cluster'] = df['cluster'].fillna(-1).astype(int)
            df.loc[df['cluster'] == -1, 'cluster'] = pd.NA
        
        # === 第一排：數據指標 ===
        col1, col2, col3 = st.columns(3)
        col1.metric("總留言數", len(df))
        col2.metric("問題數量", df["is_question"].sum())
        col3.metric("平均情緒得分", round(df["sentiment_score"].mean(), 2))

        # === 第二排：圖表 ===
        st.divider()
        c1, c2 = st.columns(2)
        
        with c1:
            st.subheader("情緒分佈圖")
            fig_sent = px.pie(df, names='sentiment', color='sentiment',
                             color_discrete_map={'positive':'green', 'neutral':'gray', 'negative':'red'})
            st.plotly_chart(fig_sent, use_container_width=True)
            
        with c2:
            st.subheader("話題聚類分佈")
            if "cluster" in df.columns:
                fig_cluster = px.histogram(df, x='cluster', color='cluster')
                st.plotly_chart(fig_cluster, use_container_width=True)

        # === 第三排：話題聚類總覽 ===
        if "cluster" in df.columns:
            st.divider()
            st.subheader("🏷️ 話題聚類總覽")
            
            # 讀取 cluster_keywords.csv
            cluster_keywords_file = "cluster_keywords.csv"
            
            if os.path.exists(cluster_keywords_file):
                try:
                    kw_df = pd.read_csv(cluster_keywords_file)
                    # 只取當前 video_id 的關鍵字
                    kw_df = kw_df[kw_df['video_id'] == video_id]
                    
                    if len(kw_df) > 0:
                        # 使用卡片式呈現
                        cols = st.columns(len(kw_df))
                        
                        for idx, (_, row) in enumerate(kw_df.iterrows()):
                            with cols[idx]:
                                cluster_n = int(row['cluster_n'])  # 確保是整數
                                keywords = row['cluster_keywords']
                                
                                # 計算這個聚類有多少則評論
                                cluster_count = len(df[df['cluster'] == cluster_n])
                                
                                # 使用不同顏色的 emoji 代表不同聚類
                                cluster_icons = ['🔵', '🟢', '🟡', '🟠', '🔴', '🟣', '🟤', '⚫', '⚪', '🔷']
                                icon = cluster_icons[cluster_n % len(cluster_icons)]
                                
                                st.markdown(f"### {icon} 聚類 {cluster_n}")
                                st.metric("評論數量", f"{cluster_count} 則")
                                st.caption("**關鍵字：**")
                                # 顯示關鍵字，每個關鍵字用標籤樣式
                                keywords_list = keywords.split()[:8]  # 最多顯示8個
                                keywords_html = ' '.join([f'`{kw}`' for kw in keywords_list])
                                st.markdown(keywords_html)
                    else:
                        st.info("尚未生成聚類關鍵字")
                        
                except Exception as e:
                    st.warning(f"無法讀取聚類關鍵字：{e}")
            else:
                st.info("聚類關鍵字檔案不存在，請先完成分析")

        # === 第四排：篩選選項 ===
        st.divider()
        st.subheader("🔍 篩選評論")
        
        col_filter1, col_filter2, col_filter3 = st.columns(3)
        
        with col_filter1:
            sentiment_filter = st.multiselect(
                "情緒篩選",
                options=['positive', 'neutral', 'negative'],
                default=['positive', 'neutral', 'negative'],
                key="sentiment_filter"
            )
        
        with col_filter2:
            question_filter = st.selectbox(
                "是否為問題",
                options=['全部', '是', '否'],
                key="question_filter"
            )
        
        with col_filter3:
            if "cluster" in df.columns:
                # 取得所有聚類編號並轉換為整數
                cluster_numbers = sorted([int(x) for x in df['cluster'].dropna().unique()])
                cluster_options = ['全部'] + cluster_numbers
                cluster_filter = st.selectbox(
                    "話題聚類",
                    options=cluster_options,
                    key="cluster_filter"
                )
            else:
                cluster_filter = '全部'
        
        # 應用篩選
        filtered_df = df.copy()
        
        # 情緒篩選
        if sentiment_filter:
            filtered_df = filtered_df[filtered_df['sentiment'].isin(sentiment_filter)]
        
        # 問題篩選
        if question_filter == '是':
            filtered_df = filtered_df[filtered_df['is_question'] == True]
        elif question_filter == '否':
            filtered_df = filtered_df[filtered_df['is_question'] == False]
        
        # 聚類篩選
        if cluster_filter != '全部' and "cluster" in df.columns:
            filtered_df = filtered_df[filtered_df['cluster'] == cluster_filter]
        
        # 重置索引以便後續使用
        filtered_df = filtered_df.reset_index(drop=True)
        
        st.info(f"篩選後共有 {len(filtered_df)} 則留言")

        # === 第四排：評論選擇表格 ===
        st.divider()
        st.subheader("📝 選擇要分析的留言")
        
        # 全選/取消全選按鈕
        col_select1, col_select2, col_select3 = st.columns([1, 1, 8])
        with col_select1:
            if st.button("全選"):
                st.session_state.selected_indices = list(range(len(filtered_df)))
                st.rerun()
        with col_select2:
            if st.button("取消全選"):
                st.session_state.selected_indices = []
                st.rerun()
        
        # 準備顯示用的資料框
        display_df = filtered_df.copy()
        
        # 加入情緒和問題的視覺化標記
        def format_sentiment(row):
            icons = {'positive': '🟢', 'neutral': '⚪', 'negative': '🔴'}
            sentiment_icon = icons.get(row['sentiment'], '⚪')
            question_icon = '❓' if row['is_question'] else ''
            return f"{sentiment_icon} {question_icon}"
        
        display_df.insert(0, '標記', display_df.apply(format_sentiment, axis=1))
        
        # 加入選擇欄位
        display_df.insert(0, '選擇', False)
        
        # 設置已選中的項目
        if st.session_state.selected_indices:
            for idx in st.session_state.selected_indices:
                if idx < len(display_df):
                    display_df.at[idx, '選擇'] = True
        
        # 選擇要顯示的欄位
        display_columns = ['選擇', '標記', 'author', 'text', 'sentiment', 'likeCount', 'publishedAt']
        if 'cluster' in display_df.columns:
            display_columns.append('cluster')
        
        # 使用 data_editor 讓使用者可以勾選
        edited_df = st.data_editor(
            display_df[display_columns],
            hide_index=True,
            use_container_width=True,
            height=400,
            disabled=[col for col in display_columns if col != '選擇'],  # 只有選擇欄可以編輯
            column_config={
                "選擇": st.column_config.CheckboxColumn(
                    "選擇",
                    help="勾選要分析的留言",
                    default=False,
                ),
                "標記": st.column_config.TextColumn(
                    "標記",
                    help="🟢=正面 ⚪=中立 🔴=負面 ❓=問題",
                    width="small"
                ),
                "author": st.column_config.TextColumn(
                    "作者",
                    width="medium"
                ),
                "text": st.column_config.TextColumn(
                    "留言內容",
                    width="large"
                ),
                "sentiment": st.column_config.TextColumn(
                    "情緒",
                    width="small"
                ),
                "likeCount": st.column_config.NumberColumn(
                    "按讚數",
                    width="small"
                ),
                "publishedAt": st.column_config.TextColumn(
                    "發布時間",
                    width="medium"
                ),
                "cluster": st.column_config.NumberColumn(
                    "聚類",
                    width="small"
                ) if 'cluster' in display_df.columns else None
            },
            key="comment_selector"
        )
        
        # 更新選中的索引
        new_selected = edited_df[edited_df['選擇'] == True].index.tolist()
        if new_selected != st.session_state.selected_indices:
            st.session_state.selected_indices = new_selected
        
        # 顯示選中數量
        selected_count = len([x for x in edited_df['選擇'] if x])
        st.markdown(f"**已選擇 {selected_count} 則留言**")
        
        # 獲取選中的評論文字
        selected_comments = filtered_df.iloc[st.session_state.selected_indices]['text'].tolist() if st.session_state.selected_indices else []

        # === 第五排：AI 問答區域 ===
        st.divider()
        st.subheader("🤖 向 AI 提問")
        
        col_ai1, col_ai2 = st.columns([8, 2])
        
        with col_ai1:
            user_question = st.text_area(
                "輸入你的問題或需求",
                placeholder="例如：總結這些評論的主要意見\n例如：這些負面評論主要在抱怨什麼？\n例如：根據這些評論，我應該如何改進影片？",
                height=100,
                key="user_question"
            )
        
        with col_ai2:
            st.write("")  # 空行對齊
            st.write("")  # 空行對齊
            ask_btn = st.button("🚀 詢問 AI", type="primary", use_container_width=True)
        
        # 顯示選中的評論數量提示
        if len(selected_comments) > 0:
            st.info(f"💡 將分析 {len(selected_comments)} 則選中的留言")
        else:
            st.warning("⚠️ 尚未選擇任何留言，AI 將分析所有留言（最多100則）")
        
        # AI 分析
        if ask_btn and user_question:
            with st.spinner("Gemini 正在思考中..."):
                # 傳入選中的評論（如果有的話）
                selected = selected_comments if len(selected_comments) > 0 else None
                answer = analyze_comments_all(csv_file, user_question, selected_comments=selected)
                st.session_state.ai_response = answer
        
        # 顯示 AI 回應
        if st.session_state.ai_response:
            st.success("✅ AI 分析完成！")
            st.markdown("### 🤖 AI 分析建議：")
            st.info(st.session_state.ai_response)

        # === 第六排：下載功能 ===
        st.divider()
        
        # 下載按鈕
        col_dl1, col_dl2 = st.columns(2)
        
        with col_dl1:
            csv_all = filtered_df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 下載所有篩選後的留言",
                data=csv_all,
                file_name=f"filtered_comments_{video_id}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col_dl2:
            if selected_comments:
                selected_df = filtered_df.iloc[st.session_state.selected_indices]
                csv_selected = selected_df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📥 下載選中的留言",
                    data=csv_selected,
                    file_name=f"selected_comments_{video_id}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.button(
                    label="📥 下載選中的留言（請先選擇）",
                    disabled=True,
                    use_container_width=True
                )

else:
    st.info("👈 請在左側輸入影片 ID 並點擊開始分析。")
