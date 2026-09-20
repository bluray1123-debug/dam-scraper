import json
import os
import re
import requests
from bs4 import BeautifulSoup

# 環境変数からGASのWebhook URLを取得
RAW_GAS_URL = os.environ.get("GAS_WEBHOOK_URL", "")

OSHIMA_DAM = {
    "name": "大島ダム",
    "url": "https://www.water.go.jp/mizu/chubu/realtime/p020201_60/302_1.html",
}


def clean_url(raw_url):
    if not raw_url:
        return ""
    url = raw_url.strip().strip("'\"")
    if url and not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    return url


def fetch_oshima_dam():
    """大島ダムの最新貯水量（または貯水率）を取得"""
    dam_name = OSHIMA_DAM["name"]
    url = OSHIMA_DAM["url"]
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    try:
        res = requests.get(url, headers=headers, timeout=10)
        # Shift_JIS等の文字化けを防ぐため自動判別
        res.encoding = res.apparent_encoding
        soup = BeautifulSoup(res.text, "html.parser")

        # テーブルから行を取得
        for tr in soup.find_all("tr"):
            cols = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]

            # 行内のテキストから数字＋%（貯水率）を探索
            for item in cols:
                match = re.search(r"([\d\.]+)\s*%", item)
                if match:
                    val = float(match.group(1))
                    if 0 <= val <= 100:
                        print(f"[取得成功] {dam_name}: {val}%", flush=True)
                        return {"dam_name": dam_name, "storage_rate": val}

                # 貯水量（千m3）の数値取得が必要な場合
                # テーブル構造に合わせて条件分岐を調整可能

    except Exception as e:
        print(f"[エラー] {dam_name}: {e}", flush=True)

    print(f"[取得失敗] {dam_name}", flush=True)
    return None


def main():
    gas_url = clean_url(RAW_GAS_URL)

    result = fetch_oshima_dam()
    if not result:
        print("データを取得できなかったため処理を終了します。")
        return

    # GASへ送信（GAS_WEBHOOK_URLが設定されている場合）
    if gas_url:
        print(f"GASへ送信中... (送信先: {gas_url[:30]}...)")
        payload = {"damList": [result]}

        try:
            res = requests.post(
                gas_url,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            print("GAS送信結果:", res.text)
        except Exception as e:
            print("GAS送信エラー:", e)
    else:
        print("※ GAS_WEBHOOK_URL が未設定のため、GASへの送信はスキップしました。")


if __name__ == "__main__":
    main()
