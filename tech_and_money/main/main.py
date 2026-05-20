import os
from dotenv import load_dotenv
from stock_checker import get_stock_data
from qiita_checker import get_qiita_trend
from linebot import LineBotApi
from linebot.models import TextSendMessage
from linebot.exceptions import LineBotApiError

# .env ファイルの内容を読み込む
load_dotenv()

CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
USER_ID = os.getenv('LINE_USER_ID')
STOCK_CODE = os.getenv('STOCK_CODE')

def main():
    print("データを取得中...\n")
    
    # 1. 各データの取得
    stock_info: str = get_stock_data(STOCK_CODE)
    qiita_info: str = get_qiita_trend()
    
    # 2. メッセージの結合
    message_text: str = f"☀️ おはようございます！本日のレポートです。\n\n{stock_info}\n\n{qiita_info}"
    
    print("【LINEに送信しています...】")
    
    # 3. LINEへの送信
    try:
        line_bot_api: LineBotApi = LineBotApi(CHANNEL_ACCESS_TOKEN)
        line_bot_api.push_message(USER_ID, TextSendMessage(text=message_text))
        print("✅ 送信完了しました！スマホのLINEを確認してください。")
    except LineBotApiError as e:
        print(f"❌ 送信エラーが発生しました: {e}")

if __name__ == "__main__":
    main()