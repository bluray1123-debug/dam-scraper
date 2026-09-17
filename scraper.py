import os
import json
import requests

RIVER_API_URL = "https://www.river.go.jp/kawabou/api/dam/getDamStateList"
TOP_PAGE_URL = "https://www.river.go.jp/kawabou/ipDamState.do"
GAS_WEBHOOK_URL = os.environ.get("GAS_WEBHOOK_URL")

def fetch_and_send():
    if not GAS_WEBHOOK_URL:
        print("エラー: GAS_WEBHOOK_URL が設定されていません。")
        return

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": TOP_PAGE_URL,
        "Accept-Language": "ja,en-US;q=0.9,en;q=0.8"
    }

    # セッションを作成（Cookieを保持）
    session = requests.Session()
    session.headers.update(headers)

    try:
        # 1. まずトップページにアクセスしてセッション(Cookie)を取得
        init_res = session.get(TOP_PAGE_URL, timeout=15)
        print(f"トップページ取得 Status: {init_res.status_code}")

        # 2. セッションを保持した状態でAPIを叩く（POST通信）
        response = session.post(RIVER_API_URL, json={}, timeout=15)
        print(f"API応答 Status: {response.status_code}")

        # POSTで取り込めなかった場合はGETで試行
        if not response.text.startswith("{") and not response.text.startswith("["):
            response = session.get(RIVER_API_URL, timeout=15)

        try:
            data = response.json()
        except json.JSONDecodeError:
            print("エラー: セッション確立後もJSONが取得できませんでした。")
            print("【レスポンス内容（先頭300文字）】:")
            print(response.text[:300])
            return

        dam_list = []
        for item in data.get("damList", []):
            dam_name = item.get("damName")
            storage_rate = item.get("storageRate")

            # デバッグ用ログ（宮ヶ瀬・大島の検出確認）
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

        # 3. GASへ送信
        payload = {"damList": dam_list}
        res = requests.post(
            GAS_WEBHOOK_URL,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        print("GAS送信結果:", res.text)

    except Exception as e:
        print("処理中に例外エラーが発生しました:", str(e))

if __name__ == "__main__":
    fetch_and_send()
