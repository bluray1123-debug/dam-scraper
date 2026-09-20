import json
import os
import re
import requests
from bs4 import BeautifulSoup

RAW_GAS_URL = os.environ.get("GAS_WEBHOOK_URL", "")

OSHIMA_DAM = {
    "name": "大島ダム",
    "url": "https://www.water.go.jp/mizu/chubu/realtime/p020201_60/302_1.html",
    "max_capacity": 11300.0,  # 有効貯水容量: 11,300 千m3
}


def clean_url(raw_url):
    if not raw_url:
        return ""
    url = raw_url.strip().strip("'\"")
    if url and not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    return url


def fetch_oshima_dam():
    dam_name = OSHIMA_DAM["name"]
    url = OSHIMA_DAM["url"]
    max_capacity = OSHIMA_DAM["max_capacity"]

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }

    try:
        res = requests.get(url, headers=headers, timeout=15)
        res.encoding = res.apparent_encoding
        soup = BeautifulSoup(res.text, "html.parser")

        valid_rows = []

        # テーブルの各行を解析
        for tr in soup.find_all("tr"):
            cols = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]

            # データ行の特定: 1列目または2列目に時刻(00:00〜23:00)が含まれる行
            # 例: ["18:00", "232.39", "7470", "0.59", ...]
            if len(cols) >= 3 and any(
                re.search(r"\d{1,2}:\d{2}", c) for c in cols[:2]
            ):
                # 時刻の次の列（貯水位）、その次の列（有効貯水量）を取得
                # 時刻が入っているインデックスを探す
                time_idx = 0 if re.search(r"\d{1,2}:\d{2}", cols[0]) else 1

                # 貯水量の列（時刻の2つ後ろの列）
                storage_col_idx = time_idx + 2
                if len(cols) > storage_col_idx:
                    storage_str = cols[storage_col_idx].replace(",", "")
                    match = re.search(r"^([\d\.]+)$", storage_str)
                    if match:
                        try:
                            val = float(match.group(1))
                            if 0 < val <= max_capacity * 1.2:
                                valid_rows.append(val)
                        except ValueError:
                            pass

        # 最下段（最新データ）の有効貯水量を使用
        if valid_rows:
            latest_storage = valid_rows[-1]
            calculated_rate = round((latest_storage / max_capacity) * 100, 1)

            print(
                f"[取得成功] {dam_name}: {calculated_rate}% (最新の有効貯水量:"
                f" {latest_storage}千m³ より計算)",
                flush=True,
            )
            return {"dam_name": dam_name, "storage_rate": calculated_rate}

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
        print(
            "※ GAS_WEBHOOK_URL が未設定のため、GASへの送信はスキップしました。"
        )


if __name__ == "__main__":
    main()
