import os
import json
import requests

RIVER_API_URL = "https://www.river.go.jp/kawabou/api/dam/getDamStateList"
GAS_WEBHOOK_URL = os.environ.get("GAS_WEBHOOK_URL")

def fetch_and_send():
    if not GAS_WEBHOOK_URL:
        print("エラー: GAS_WEBHOOK_URL が設定されていません。")
        return

    # ブラウザからのアクセスに偽装するためのヘッダー群
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.river.go.jp/kawabou/ipDamState.do",
        "Accept-Language": "ja,en-US;q=0.9,en;q=0.8"
    }

    try:
        response = requests.get(RIVER_API_URL, headers=headers, timeout=15)
        print(f"HTTP Status: {response.status_code}")

        if response.status_code != 200:
            print(f"国交省API取得失敗: Status {response.status_code}")
            print("受信データ先頭:", response.text[:200])
            return

        # JSONパースの安全化
        try:
            data = response.json()
        except json.JSONDecodeError:
            print("エラー: APIからJSONではなくHTML等が返却されました。")
            print("【レスポンス内容（先頭300文字）】:")
            print(response.text[:300])
            return

        dam_list = []
        for item in data.get("damList", []):
            dam_name = item.get("damName")
            storage_rate = item.get("storageRate")

            # デバッグログ（大島・宮ヶ瀬の確認用）
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

        # GASへ送信
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
