import os
import re
import json
import requests
from bs4 import BeautifulSoup

GAS_WEBHOOK_URL = os.environ.get("GAS_WEBHOOK_URL")

# 対象ダムのリスト (ダム名とCGI用15桁ID)
# 大島ダムなどのIDも必要に応じて追記してください
DAMS = [
    {"name": "宮ヶ瀬ダム", "id": "601011281104002"},
    # {"name": "大島ダム", "id": "ここに15桁のIDを入力"},
]

def get_storage_rate_from_cgi(dam_id):
    url = f"https://www1.river.go.jp/cgi-bin/DspDamData.exe?ID={dam_id}&KIND=3&PAGE=0"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = res.apparent_encoding
        soup = BeautifulSoup(res.text, "html.parser")
        
        # 1. 正規表現で「貯水率◯◯%」のパターンを全体テキストから抽出
        text = soup.get_text()
        match = re.search(r"貯水率[^\d]*([\d\.]+)\s*%", text)
        if match:
            return float(match.group(1))
        
        # 2. 表のセル（td/th）から「貯水率」の隣の数値を抽出
        for tr in soup.find_all("tr"):
            cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            for i, cell in enumerate(cells):
                if "貯水率" in cell and i + 1 < len(cells):
                    val_str = re.sub(r"[^\d\.]", "", cells[i+1])
                    if val_str:
                        return float(val_str)
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
