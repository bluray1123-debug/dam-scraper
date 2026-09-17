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
    {"name": "宇連ダム", "id": "1368050651020", "max_capacity": 28420},
]

def clean_url(raw_url):
    if not raw_url:
        return ""
    url = raw_url.strip().strip("'\"")
    if url and not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    return url

def parse_dam_soup(soup, max_capacity=None):
    idx_rate = None
    idx_volume = None

    # 1. ページ全体の全テーブルから「貯水率」「貯水量」の列番号を特定
    for tr in soup.find_all("tr"):
        headers = [th.get_text(strip=True) for th in tr.find_all(["th", "td"])]
        for idx, h in enumerate(headers):
            if "貯水率" in h and idx_rate is None:
                idx_rate = idx
            if "貯水量" in h and idx_volume is None:
                idx_volume = idx

    # 2. データ行（日付・時刻が存在する行）を解析
    for tr in soup.find_all("tr"):
        cols = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
        if len(cols) >= 5 and re.search(r"\d{4}/\d{1,2}/\d{1,2}", cols[0]) and re.search(r"\d{1,2}:\d{2}", cols[1]):
            
            # 貯水率列の決定（検出失敗時は末尾または6列目をデフォルト指定）
            target_rate_idx = idx_rate if idx_rate is not None else (6 if len(cols) > 6 else -1)
            
            # パターンA: 貯水率列から数値を抽出
            if 0 <= target_rate_idx < len(cols):
                rate_str = cols[target_rate_idx]
                m_rate = re.search(r"([\d\.]+)", rate_str)
                if m_rate:
                    return float(m_rate.group(1))

            # パターンB: 貯水率が「-」等で取得できず、max_capacity が指定されている場合計算
            target_vol_idx = idx_volume if idx_volume is not None else (3 if len(cols) > 3 else -1)
            if max_capacity and 0 <= target_vol_idx < len(cols):
                vol_str = cols[target_vol_idx]
                m_vol = re.search(r"([\d\.]+)", vol_str)
                if m_vol:
                    volume = float(m_vol.group(1))
                    calc_rate = round((volume / max_capacity) * 100, 1)
                    print(f"  [自動計算] 貯水量:{volume} / 容量:{max_capacity} -> {calc_rate}%")
                    return calc_rate

    return None

def get_storage_rate_from_cgi(dam):
    dam_id = dam["id"]
    max_capacity = dam.get("max_capacity")
    url = f"https://www1.river.go.jp/cgi-bin/DspDamData.exe?ID={dam_id}&KIND=3&PAGE=0"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = "euc-jp"
        soup = BeautifulSoup(res.text, "html.parser")

        rate = parse_dam_soup(soup, max_capacity)
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

            rate = parse_dam_soup(soup_frame, max_capacity)
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
        rate = get_storage_rate_from_cgi(dam)
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
