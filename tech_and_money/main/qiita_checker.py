import requests
from datetime import datetime, timedelta

def get_qiita_trend():
    """
    Qiitaから直近1週間でLGTM数が多い記事を3件取得する
    """
    # 1週間前の日付を YYYY-MM-DD 形式で取得
    last_week: str = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    # 検索クエリ: 1週間以内に作成され、LGTMが30以上の記事
    query: str = f"created:>={last_week} stocks:>30"
    
    url: str = "https://qiita.com/api/v2/items"
    params: dict = {
        "page": 1,
        "per_page": 3,  # 上位3件を取得
        "query": query
    }
    
    try:
        response: requests.Response = requests.get(url, params=params)
        response.raise_for_status() # エラーがあれば例外を発生させる
        items: list = response.json()
        
        if not items:
            return "該当するQiita記事が見つかりませんでした。"
            
        result_text: str = "📚 今週のQiita注目記事\n"
        for i, item in enumerate(items, 1):
            title: str = item.get("title")
            url: str = item.get("url")
            lgtm: int = item.get("likes_count", 0)
            result_text += f"{i}. {title} (LGTM: {lgtm})\n{url}\n\n"
            
        return result_text.strip()
        
    except requests.exceptions.RequestException as e:
        return f"Qiitaのデータ取得に失敗しました: {e}"

# --- 動作確認用 ---
if __name__ == "__main__":
    print(get_qiita_trend())