import os
import re
import json
import requests
from bs4 import BeautifulSoup

GAS_WEBHOOK_URL = os.environ.get("GAS_WEBHOOK_URL")

# 対象ダムのリスト (ダム名とCGI用15桁ID)
DAMS = [
    {"name": "宮ヶ瀬ダム", "id": "601011281104002"},
]

def get_storage_rate_from_cgi(dam_id):
    url = f"https://www1.river.go.jp/cgi-bin/DspDamData.exe?ID={dam_id}&KIND=3&PAGE=0"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        # CGIページ特有のShift_JIS(cp932)に文字コードを固定
        res.encoding = "cp932"
        
        soup = BeautifulSoup(res.text, "html.parser")
        text = soup.get_text()

        # 1. 全文テキストから「貯水率」直後の数値を抽出
        match = re.search(r"貯水率[^\d]*([\d\.]+)", text)
        if match:
            return float(match.group(1))

        # 2. テーブル構造から抽出（「貯水率」を含む行の数値セルを順次チェック）
        for tr in soup.find_all("tr"):
            cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            for i, cell in enumerate(cells):
                if "貯水率" in cell:
                    for target in cells[i+1:]:
                        num_match = re.search(r"([\d\.]+)", target)
                        if num_match:
                            return float(num_match.group(1))

        # 失敗時のデバッグ情報出力
        print(f"[DEBUG ID:{dam_id}] 抽出失敗。レスポンス先頭:\n{text[:200]}")

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
