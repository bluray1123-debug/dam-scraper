import os
import re
import json
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup

GAS_WEBHOOK_URL = os.environ.get("GAS_WEBHOOK_URL")

# 対象ダムのリスト (ダム名とCGI用15桁ID)
DAMS = [
    {"name": "サンルダム", "id": "601011281104002"},
    # {"name": "宮ヶ瀬ダム", "id": "宮ヶ瀬ダムの15桁ID"},
]

def get_storage_rate_from_cgi(dam_id):
    url = f"https://www1.river.go.jp/cgi-bin/DspDamData.exe?ID={dam_id}&KIND=3&PAGE=0"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = "euc-jp"
        soup = BeautifulSoup(res.text, "html.parser")

        # 1. 表が iframe / frame で埋め込まれているか判定し、子画面を取得
        iframe = soup.find(["iframe", "frame"])
        if iframe and iframe.get("src"):
            iframe_url = urljoin(url, iframe["src"])
            res_frame = requests.get(iframe_url, headers=headers, timeout=10)
            res_frame.encoding = "euc-jp"
            soup = BeautifulSoup(res_frame.text, "html.parser")

        # 2. 表のヘッダーから「貯水率」の列番号を特定
        storage_col_idx = None
        tables = soup.find_all("table")

        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                headers_text = [th.get_text(strip=True) for th in row.find_all(["th", "td"])]
                for idx, h in enumerate(headers_text):
                    if "貯水率" in h:
                        storage_col_idx = idx
                        break
                if storage_col_idx is not None:
                    break

            # 3. 列番号が見つかったら、データ行（数値が存在する先頭の行）から最新値を抽出
            if storage_col_idx is not None:
                for row in rows:
                    cols = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
                    if len(cols) > storage_col_idx:
                        val_str = cols[storage_col_idx]
                        num_match = re.search(r"([\d\.]+)", val_str)
                        if num_match:
                            return float(num_match.group(1))

        # 4. バックアップ処理（テキスト全体から「貯水率」直後の数値を探索）
        text = soup.get_text()
        match = re.search(r"貯水率[^\d]*([\d\.]+)", text)
        if match:
            return float(match.group(1))

    except Exception as e:
        print(f"ID {dam_id} 取得時エラー: {e}")
    return None

def fetch_and_send():
    if not GAS_WEBHOOK_URL:
        print("エラー: GAS_WEBHOOK_URL が設定されていません。")
        return

    dam_list = []
    for dam in DAMS:
        rate = get_storage_rate_from_cgi(dam["id"])
        if rate is not None:
            print(f"[取得成功] {dam['name']}: {rate}%")
            dam_list.append({
                "dam_name": dam["name"],
                "storage_rate": rate
            })
        else:
            print(f"[取得失敗] {dam['name']}")

    if not dam_list:
        print("送信対象データが0件のため終了します。")
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
