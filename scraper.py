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
    # {"name": "宮ヶ瀬ダム", "id": "ここに15桁のIDを入力"},
]

def extract_rate_from_soup(soup):
    """
    HTMLから日付・時刻形式が存在するデータ行を探し、末尾の貯水率（数値）を返す
    """
    for tr in soup.find_all("tr"):
        cols = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
        if len(cols) >= 5:
            # 1列目が日付(YYYY/MM/DD)、2列目が時刻(HH:MM)の行をデータ行として認識
            if re.search(r"\d{4}/\d{1,2}/\d{1,2}", cols[0]) and re.search(r"\d{1,2}:\d{2}", cols[1]):
                # 行の末尾側から数値（貯水率）を探索
                for col in reversed(cols):
                    match = re.search(r"([\d\.]+)", col)
                    if match:
                        try:
                            val = float(match.group(1))
                            if 0 <= val <= 100:  # 貯水率として適切な範囲か確認
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

        # 1. 親ページ自体のテーブルから抽出試行
        rate = extract_rate_from_soup(soup)
        if rate is not None:
            return rate

        # 2. フレーム（frame / iframe）タグを検出して巡回
        frames = soup.find_all(["frame", "iframe"])
        print(f"[DEBUG ID:{dam_id}] 検出されたフレーム数: {len(frames)}")

        for frame in frames:
            src = frame.get("src")
            if not src:
                continue
            frame_url = urljoin(url, src)
            print(f"[DEBUG ID:{dam_id}] フレーム読込: {frame_url}")

            res_frame = requests.get(frame_url, headers=headers, timeout=10)
            res_frame.encoding = "euc-jp"
            soup_frame = BeautifulSoup(res_frame.text, "html.parser")

            rate = extract_rate_from_soup(soup_frame)
            if rate is not None:
                return rate

        print(f"[DEBUG ID:{dam_id}] データ行（日付・時刻）の抽出に失敗しました。")

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
