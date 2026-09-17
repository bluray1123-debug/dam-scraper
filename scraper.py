import os
import re
import json
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup

RAW_GAS_URL = os.environ.get("GAS_WEBHOOK_URL", "")

# 対象ダムのリスト (ダム名とCGI用15桁ID)
DAMS = [
    {"name": "サンルダム", "id": "601011281104002"},
    {"name": "宮ヶ瀬ダム", "id": "1368030799020"},
    {"name": "八ッ場ダム", "id": "303031283317025"},
]

def clean_url(raw_url):
    """URLの前後の空白・クォーテーションを除去し、https://を補正"""
    if not raw_url:
        return ""
    url = raw_url.strip().strip("'\"")
    if url and not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    return url

def extract_rate_from_soup(soup):
    for tr in soup.find_all("tr"):
        cols = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
        if len(cols) >= 5:
            if re.search(r"\d{4}/\d{1,2}/\d{1,2}", cols[0]) and re.search(r"\d{1,2}:\d{2}", cols[1]):
                for col in reversed(cols):
                    match = re.search(r"([\d\.]+)", col)
                    if match:
                        try:
                            val = float(match.group(1))
                            if 0 <= val <= 100:
                                return val
                        except ValueError:
                            continue
    return None

def get_storage_rate_from_cgi(dam_id):
    url = f"https://www1.river.go.jp/cgi-bin/DspDamData.exe?ID={dam_id}&KIND=3&PAGE=0"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = "euc-jp"
        soup = BeautifulSoup(res.text, "html.parser")

        rate = extract_rate_from_soup(soup)
        if rate is not None:
            return rate

        frames = soup.find_all(["frame", "iframe"])
        for frame in frames:
            src = frame.get("src")
            if not src:
                continue
            frame_url = urljoin(url, src)

            res_frame = requests.get(frame_url, headers=headers, timeout=10)
            res_frame.encoding = "euc-jp"
            soup_frame = BeautifulSoup(res_frame.text, "html.parser")

            rate = extract_rate_from_soup(soup_frame)
            if rate is not None:
                return rate

    except Exception as e:
        print(f"ID {dam_id} 取得時エラー: {e}")
    return None

def fetch_and_send():
    gas_url = clean_url(RAW_GAS_URL)
    if not gas_url:
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
    print(f"GASへ送信中... (送信先: {gas_url[:30]}...)")
    payload = {"damList": dam_list}
    res = requests.post(
        gas_url,
        data=json.dumps(payload),
        headers={"Content-Type": "application/json"},
        timeout=30
    )
    print("GAS送信結果:", res.text)

if __name__ == "__main__":
    fetch_and_send()
