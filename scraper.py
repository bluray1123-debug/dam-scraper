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
    {"name": "宇連ダム", "id": "1368050651020", "max_capacity": 28420},  # max_capacityを追加
    # ... 他のダム
]


def clean_url(raw_url):
    if not raw_url:
        return ""
    url = raw_url.strip().strip("'\"")
    if url and not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    return url


def extract_data_from_table(soup, max_capacity=None):
    """
    HTMLテーブルから最新（最上段）のデータを解析
    """
    for tr in soup.find_all("tr"):
        cols = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
        
        # 日時行の特定 (例: 2026/09/18 00:30 ...)
        if len(cols) >= 3 and re.search(r"\d{4}/\d{1,2}/\d{1,2}", cols[0]) and re.search(r"\d{1,2}:\d{2}", cols[1]):
            
            # 1. max_capacity が指定されている場合：行内の数値から貯水量を検出して計算
            if max_capacity:
                # 行内の全カラムから数値のみを抽出（日付・時刻以外のカラムから）
                for val_str in cols[2:]:
                    # 数値（小数含む）を抽出
                    match = re.search(r"^([\d\.]+)$", val_str)
                    if match:
                        try:
                            val = float(match.group(1))
                            # 貯水量は有効容量と同程度〜それ以下で、流入量等の小さな値(数十以下)と区別できる想定
                            # （例: 宇連ダムなら 0 < val <= max_capacity * 1.2）
                            if 0 < val <= max_capacity * 1.2:
                                calculated_rate = round((val / max_capacity) * 100, 1)
                                if 0 <= calculated_rate <= 100:
                                    return calculated_rate
                        except (ValueError, ZeroDivisionError):
                            continue

            # 2. max_capacity が指定されていない場合：本来の「貯水率」列を参照
            rate_str = cols[-1]
            
            # 欠測・未配信の "-" や空文字の場合は計算不可としてスキップ
            if rate_str in ["-", "ー", "", "欠測"]:
                return None
                
            match = re.search(r"([\d\.]+)", rate_str)
            if match:
                try:
                    val = float(match.group(1))
                    if 0 <= val <= 100:
                        return val
                except ValueError:
                    pass

    return None


def fetch_single_dam(dam, session):
    dam_name = dam["name"]
    dam_id = dam["id"]
    max_capacity = dam.get("max_capacity")
    
    url = f"https://www1.river.go.jp/cgi-bin/DspDamData.exe?ID={dam_id}&KIND=3&PAGE=0"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    try:
        res = session.get(url, headers=headers, timeout=10)
        res.encoding = "euc-jp"
        soup = BeautifulSoup(res.text, "html.parser")

        # 親ページからの解析
        rate = extract_data_from_table(soup, max_capacity)
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

            rate = extract_data_from_table(soup_frame, max_capacity)
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
    session = requests.Session()

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
