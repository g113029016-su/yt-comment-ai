# 📊 YouTube AI 創作者助手：進階留言分析與決策系統

這是一個為 YouTuber 打造的智慧化留言管理平台。除了自動化抓取與情緒分類，本系統更導入了語意聚類技術與互動式 AI 問答，協助創作者從海量評論中精準提取讀者回饋。

## 網站
github:
Streamlit:

## ✨ 進階功能亮點
- **互動式留言篩選**：可根據情緒（正向/負向/中立）、是否為問題、以及話題聚類進行多重過濾。
- **話題聚類總覽 (Topic Clustering)**：自動生成話題卡片與關鍵字標籤，快速掌握觀眾討論熱點。
- **精準留言分析**：支援「勾選特定留言」進行 AI 分析，讓 Gemini 針對您感興趣的特定評論提供見解。
- **數據視覺化**：整合 Plotly 動態圖表，直觀呈現情緒分佈與話題比例。
- **多功能匯出**：支援下載所有篩選後的留言或僅下載選中的留言，方便後續保存或研究。

## 🛠️ 技術棧
- **Frontend**: Streamlit
- **NLP / Embedding**: Sentence-Transformers, Jieba
- **Dimension Reduction**: UMAP
- **Clustering**: K-Means (Scikit-learn)
- **AI Engine**: Google Gemini 1.5 Flash
- **Data Visualization**: Plotly