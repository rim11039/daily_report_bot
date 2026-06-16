import os
from dotenv import load_dotenv
from notion_checker import get_notion_tasks
from linebot import LineBotApi
from linebot.models import TextSendMessage
from linebot.exceptions import LineBotApiError

load_dotenv()

CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
USER_ID = os.getenv("LINE_USER_ID")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")


def main():
    print("Notionからタスクを取得中...\n")

    task_info = get_notion_tasks(NOTION_TOKEN, NOTION_DATABASE_ID)

    message_text = f"📅 本日のタスク確認\n\n{task_info}"

    print("【LINEに送信しています...】")

    try:
        line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
        line_bot_api.push_message(USER_ID, TextSendMessage(text=message_text))
        print("[SUCCESS] 送信完了しました！")
    except LineBotApiError as e:
        print(f"[ERROR] 送信エラーが発生しました: {e}")


if __name__ == "__main__":
    main()
