import os
import json
import requests
from playwright.sync_api import sync_playwright

TOP_PAGE_URL = "https://www.river.go.jp/kawabou/ipDamState.do"
GAS_WEBHOOK_URL = os.environ.get("GAS_WEBHOOK_URL")

def fetch_and_send():
    if not GAS_WEBHOOK_URL:
        print("エラー: GAS_WEBHOOK_URL が設定されていません。")
        return

    dam_data = None

    # ヘッドレスブラウザでページを開き、内部で発生するAPI通信を監視・取得
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # getDamStateListの通信が発生したらレスポンスJSONをキャッチ
        def handle_response(response):
            nonlocal dam_data
            if "getDamStateList" in response.url and response.status == 200:
                try:
                    dam_data = response.json()
                    print("APIレスポンスのキャッチに成功しました！")
                except Exception as e:
                    print("APIレスポンスのJSONパースに失敗:", e)

        page.on("response", handle_response)

        print("ページにアクセス中...")
        try:
            page.goto(TOP_PAGE_URL, wait_until="networkidle", timeout=30000)
        except Exception as e:
            print("ページ読み込み完了待機中のメッセージ:", e)

        browser.close()

    if not dam_data:
        print("エラー: getDamStateList のデータがキャッチできませんでした。")
        return

    dam_list = []
    for item in dam_data.get("damList", []):
        dam_name = item.get("damName")
        storage_rate = item.get("storageRate")

        # 宮ヶ瀬・大島の検出確認用ログ
        if dam_name and ("大島" in dam_name or "宮" in dam_name):
            print(f"[DEBUG 検出] 名前: '{dam_name}', 貯水率: {storage_rate}")

        if dam_name and storage_rate is not None:
            dam_list.append({
                "dam_name": dam_name,
                "storage_rate": float(storage_rate)
            })

    print(f"取得成功: {len(dam_list)} 件のダムデータ")

    if not dam_list:
        print("送信対象のダムデータが0件のため処理を中断します。")
        return

    # GASへデータ送信
    payload = {"damList": dam_list}
    res = requests.post(
        GAS_WEBHOOK_URL,
        data=json.dumps(payload),
        headers={"Content-Type": "application/json"},
        timeout=30
    )
    print("GAS送信結果:", res.text)

if __name__ == "__main__":
    fetch_and_send()
