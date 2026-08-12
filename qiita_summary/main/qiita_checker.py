import requests
from datetime import datetime, timedelta

from loguru import logger

# 1回のリクエストで取得する件数 (QiitaAPIの上限は100)
PER_PAGE = 100

# APIの応答を待つ上限秒数 (未指定だと応答がない場合に処理が止まり続ける)
REQUEST_TIMEOUT = 30


def get_qiita_trend_items(today: datetime, search_weeks: int, search_stocks: int) -> list[dict]:
    """
    Qiitaから直近 search_weeks 週間で、ストック数が search_stocks 以上の記事を取得する。
    本文(body)を含む構造化データのリストを、LGTM数の多い順に返す。

    返り値の各要素: {"title", "url", "likes", "body", "created_at"}
    エラー時は空リストを返す。
    """
    # 指定の日付を YYYY-MM-DD 形式で取得
    last_week: str = (today - timedelta(weeks=search_weeks)).strftime("%Y-%m-%d")

    # 検索クエリ: 指定期間内に作成され、ストック数が閾値以上の記事
    # ※QiitaAPIの検索構文で数値比較に使えるのは stocks のみ (likes は非対応)
    query: str = f"created:>={last_week} stocks:>={search_stocks}"

    url: str = "https://qiita.com/api/v2/items"
    params: dict = {
        "page": 1,
        "per_page": PER_PAGE,
        "query": query,
    }

    try:
        response: requests.Response = requests.get(
            url, params=params, timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()  # エラーがあれば例外を発生させる
        items: list = response.json()
    except requests.exceptions.RequestException:
        logger.exception("Qiitaのデータ取得に失敗しました")
        return []

    results: list[dict] = []
    for item in items:
        results.append(
            {
                "title": item.get("title", "(無題)"),
                "url": item.get("url", ""),
                "likes": item.get("likes_count", 0),
                "body": item.get("body", ""),
                "created_at": item.get("created_at", "")[:10],
            }
        )

    # QiitaAPIは作成日の降順でしか返さず、ソート指定にも対応していないため、
    # 人気順に扱えるようLGTM数の多い順にこちらで並べ替える
    results.sort(key=lambda x: x["likes"], reverse=True)

    logger.info(f"Qiitaから{len(results)}件取得しました")

    return results


# --- 動作確認用 ---
if __name__ == "__main__":
    for i, article in enumerate(get_qiita_trend_items(datetime.now(), 1, 30), 1):
        print(f"{i}. {article['title']} (LGTM: {article['likes']})")
        print(f"   {article['url']}")
        print(f"   本文文字数: {len(article['body'])}")
