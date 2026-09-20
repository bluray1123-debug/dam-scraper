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

        # 1. ページ内に直接「貯水率（%）」が記載されているか検索
        for element in soup.find_all(["td", "th", "div", "span"]):
            text = element.get_text(strip=True)
            match = re.search(r"([\d\.]+)\s*%", text)
            if match:
                val = float(match.group(1))
                if 0 <= val <= 100:
                    print(
                        f"[取得成功] {dam_name}: {val}% (直接表記)", flush=True
                    )
                    return {"dam_name": dam_name, "storage_rate": val}

        # 2. 貯留量（千m3）の数値から 11300 千m3 を基準に貯水率(%)を計算
        for tr in soup.find_all("tr"):
            cols = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            for item in cols:
                # カンマを除去して数値のみ抽出 (例: 8,500.0 -> 8500.0)
                clean_item = item.replace(",", "")
                match = re.search(r"^([\d\.]+)$", clean_item)
                if match:
                    try:
                        storage_val = float(match.group(1))
                        # 0 < 貯留量 <= 11300 * 1.2 (洪水時等の余幅) の範囲内の数値を検出
                        if 100 < storage_val <= (max_capacity * 1.2):
                            calculated_rate = round(
                                (storage_val / max_capacity) * 100, 1
                            )
                            if 0 <= calculated_rate <= 100:
                                print(
                                    f"[取得成功] {dam_name}: {calculated_rate}%"
                                    f" (貯留量: {storage_val}千m³ より計算)",
                                    flush=True,
                                )
                                return {
                                    "dam_name": dam_name,
                                    "storage_rate": calculated_rate,
                                }
                    except ValueError:
                        pass

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
