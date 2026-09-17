import os
import re
import json
import requests
import concurrent.futures
from urllib.parse import urljoin
from bs4 import BeautifulSoup

RAW_GAS_URL = os.environ.get("GAS_WEBHOOK_URL", "")

DAMS = [
    {"name": "岩尾内ダム", "id": "1368010125140"},
    {"name": "サンルダム", "id": "601011281104002"},
    {"name": "鹿ノ子ダム", "id": "1368011128090"},
    {"name": "留萌ダム", "id": "601021281109010"},
    {"name": "大雪ダム", "id": "1368010325180"},
    {"name": "豊平峡ダム", "id": "1368010332630"},
    # ... その他のダム定義
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
    """HTML解析ロジック"""
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

def fetch_single_dam(dam, session):
    """1つのダムの貯水率を取得する関数（スレッド用）"""
    dam_name = dam["name"]
    dam_id = dam["id"]
    url = f"https://www1.river.go.jp/cgi-bin/DspDamData.exe?ID={dam_id}&KIND=3&PAGE=0"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    try:
        res = session.get(url, headers=headers, timeout=10)
        res.encoding = "euc-jp"
        soup = BeautifulSoup(res.text, "html.parser")

        # 親ページからの取得
        rate = extract_rate_from_soup(soup)
        if rate is not None:
            print(f"[取得成功] {dam_name}: {rate}%", flush=True)
            return {"dam_name": dam_name, "storage_rate": rate}

        # iframeページの探索
        frames = soup.find_all(["frame", "iframe"])
        for frame in frames:
            src = frame.get("src")
            if not src:
                continue
            frame_url = urljoin(url, src)

            res_frame = session.get(frame_url, headers=headers, timeout=10)
            res_frame.encoding = "euc-jp"
            soup_frame = BeautifulSoup(res_frame.text, "html.parser")

            rate = extract_rate_from_soup(soup_frame)
            if rate is not None:
                print(f"[取得成功] {dam_name}: {rate}%", flush=True)
                return {"dam_name": dam_name, "storage_rate": rate}

    except Exception as e:
        print(f"[エラー] {dam_name} (ID: {dam_id}): {e}", flush=True)

    print(f"[取得失敗] {dam_name}", flush=True)
    return None

def fetch_and_send():
    gas_url = clean_url(RAW_GAS_URL)
    if not gas_url:
        print("エラー: GAS_WEBHOOK_URL が設定されていません。")
        return

    print("並列スクレイピングを開始します...", flush=True)
    dam_list = []

    # HTTPセッションの使い回し（TCPコネクション再利用による高速化）
    session = requests.Session()

    # 最大15スレッドで並列実行（サーバーに負荷をかけすぎない範囲設定）
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        futures = [executor.submit(fetch_single_dam, dam, session) for dam in DAMS]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                dam_list.append(result)

    print(f"取得完了: {len(dam_list)}/{len(DAMS)} 件", flush=True)

    if not dam_list:
        print("送信対象データが0件のため終了します。")
        return

    # GASへデータ送信
    print(f"GASへ送信中... (送信先: {gas_url[:30]}...)")
    payload = {"damList": dam_list}
    
    try:
        res = requests.post(
            gas_url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        print("GAS送信結果:", res.text)
    except Exception as e:
        print("GAS送信エラー:", e)

if __name__ == "__main__":
    fetch_and_send()
