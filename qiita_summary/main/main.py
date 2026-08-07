import os
from datetime import datetime

from dotenv import load_dotenv
from qiita_checker import get_qiita_trend_items
from gemini_summarizer import summarize_article
from notion_writer import create_summary_page, page_exists_with_url
from linebot import LineBotApi
from linebot.models import TextSendMessage
from linebot.exceptions import LineBotApiError

# .env ファイルの内容を読み込む
load_dotenv()

CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
USER_ID = os.getenv("LINE_USER_ID")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
QIITA_SUMMARY_DATABASE_ID = os.getenv("QIITA_SUMMARY_DATABASE_ID")


def main():
    print("Qiitaトレンド記事を取得中...\n")

    # 1. Qiitaトレンド記事の取得 (本文付き)
    articles = get_qiita_trend_items(per_page=3)

    if not articles:
        message_text = "📚 本日のQiitaトレンド要約\n\n該当する記事が見つかりませんでした。"
        _send_line(message_text)
        return

    today = datetime.now().strftime("%Y-%m-%d")
    line_lines = ["📚 本日のQiitaトレンド要約\n"]

    # 2〜3. 各記事をClaudeで要約し、Notionに書き込む
    for i, article in enumerate(articles, 1):
        title = article["title"]
        url = article["url"]
        likes = article["likes"]

        # 同一URLのページが既にNotionにある場合は要約も書き込みも行わない
        if page_exists_with_url(NOTION_TOKEN, QIITA_SUMMARY_DATABASE_ID, url):
            print(f"[{i}/{len(articles)}] 登録済みのためスキップ: {title}")
            line_lines.append(f"{i}. {title} (LGTM: {likes})")
            line_lines.append("（登録済みのためスキップ）")
            line_lines.append(f"{url}\n")
            continue

        print(f"[{i}/{len(articles)}] 要約中: {title}")
        summary = summarize_article(title, article["body"])

        print(f"[{i}/{len(articles)}] Notionに書き込み中...")
        ok = create_summary_page(
            token=NOTION_TOKEN,
            database_id=QIITA_SUMMARY_DATABASE_ID,
            title=title,
            url=url,
            likes=likes,
            summary=summary,
            date=today,
        )
        if not ok:
            print(f"[WARN] Notionへの書き込みに失敗しました: {title}")

        # LINE用: タイトル・URL・要約の先頭行
        first_line = summary.splitlines()[0] if summary else ""
        line_lines.append(f"{i}. {title} (LGTM: {likes})")
        line_lines.append(f"{first_line}")
        line_lines.append(f"{url}\n")

    line_lines.append("📝 詳しい要約はNotionに保存しました。")
    message_text = "\n".join(line_lines)

    # 4. LINEへの送信
    _send_line(message_text)


def _send_line(message_text: str):
    print("【LINEに送信しています...】")
    try:
        line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
        line_bot_api.push_message(USER_ID, TextSendMessage(text=message_text))
        print("[SUCCESS] 送信完了しました！")
    except LineBotApiError as e:
        print(f"[ERROR] 送信エラーが発生しました: {e}")


if __name__ == "__main__":
    main()
