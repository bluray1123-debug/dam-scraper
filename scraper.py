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
    {"name": "滝里ダム", "id": "1368010332170"},
    {"name": "金山ダム", "id": "1368010332390"},
    {"name": "忠別ダム", "id": "1368010125190"},
    {"name": "漁川ダム", "id": "1368010332730"},
    {"name": "定山渓ダム", "id": "1368010332520"},
    {"name": "桂沢ダム", "id": "1368010332300"},
    {"name": "夕張シューパロダム", "id": "601031281101001"},
    {"name": "美利河ダム", "id": "1368010523040"},
    {"name": "二風谷ダム", "id": "1368010724030"},
    {"name": "十勝ダム", "id": "1368010829060"},
    {"name": "札内川ダム", "id": "1368010829410"},
    {"name": "浅瀬石川ダム", "id": "602071282222010"},
    {"name": "津軽ダム", "id": "302071282203001"},
    {"name": "四十四田ダム", "id": "1368020475050"},
    {"name": "鳴子ダム", "id": "602041282223010"},
    {"name": "胆沢ダム", "id": "1368020475200"},
    {"name": "御所ダム", "id": "1368020475070"},
    {"name": "湯田ダム", "id": "1368020475190"},
    {"name": "田瀬ダム", "id": "1368020475150"},
    {"name": "釜房ダム", "id": "602021282224010"},
    {"name": "七ヶ宿ダム", "id": "1368020182060"},
    {"name": "三春ダム", "id": "1368020166040"},
    {"name": "摺上川ダム", "id": "602011282219010"},
    {"name": "玉川ダム", "id": "602091282226010"},
    {"name": "長井ダム", "id": "602111282217030"},
    {"name": "寒河江ダム", "id": "602111282221020"},
    {"name": "白川ダム", "id": "602111282221010"},
    {"name": "月山ダム", "id": "1368021260020"},
    {"name": "矢木沢ダム", "id": "1368030799010"},
    {"name": "藤原ダム", "id": "1368030375030"},
    {"name": "川俣ダム", "id": "1368030376040"},
    {"name": "川治ダム", "id": "1368030376090"},
    {"name": "渡良瀬遊水地", "id": "1368030345200"},
    {"name": "草木ダム", "id": "303031283315020"},
    {"name": "薗原ダム", "id": "1368030375130"},
    {"name": "相俣ダム", "id": "1368030375090"},
    {"name": "奈良俣ダム", "id": "1368030375020"},
    {"name": "八ッ場ダム", "id": "303031283317025"},
    {"name": "五十里ダム", "id": "1368030376050"},
    {"name": "湯西川ダム", "id": "303031283318170"},
    {"name": "下久保ダム", "id": "303031283318020"},
    {"name": "二瀬ダム", "id": "1368030478030"},
    {"name": "浦山ダム", "id": "1368030446220"},
    {"name": "滝沢ダム", "id": "1368030446230"},
    {"name": "宮ヶ瀬ダム", "id": "1368030799020"},
    {"name": "大石ダム", "id": "1368040137060"},
    {"name": "大川ダム", "id": "1368040260090"},
    {"name": "三国川ダム", "id": "1368040333130"},
    {"name": "大町ダム", "id": "1368040365050"},
    {"name": "宇奈月ダム", "id": "1368040646030"},
    {"name": "手取川ダム", "id": "1368041150050"},
    {"name": "長島ダム", "id": "1365150315010"},
    {"name": "新豊根ダム", "id": "1368050544030"},
    {"name": "小渋ダム", "id": "1368050570170"},
    {"name": "美和ダム", "id": "1368050570120"},
    {"name": "宇連ダム", "id": "1368050651020", "max_capacity": 28420},
    {"name": "矢作ダム", "id": "305071285520010"},
    {"name": "小里川ダム", "id": "605081285511350"},
    {"name": "丸山ダム", "id": "1368050931255"},
    {"name": "味噌川ダム", "id": "1368050931035"},
    {"name": "阿木川ダム", "id": "1368050931320"},
    {"name": "牧尾ダム", "id": "1368050900080", "max_capacity": 68000},
    {"name": "岩屋ダム", "id": "1368050931090"},
    {"name": "横山ダム", "id": "1368050931150"},
    {"name": "徳山ダム", "id": "605091285502400"},
    {"name": "蓮ダム", "id": "1368051260060"},
    {"name": "日吉ダム", "id": "1368060475010"},
    {"name": "天ヶ瀬ダム", "id": "1368060475060"},
    {"name": "布目ダム", "id": "1368060475080"},
    {"name": "比奈知ダム", "id": "1368060475090"},
    {"name": "高山ダム", "id": "1368060475070"},
    {"name": "室生ダム", "id": "1368060475110"},
    {"name": "青蓮寺ダム", "id": "1368060475100"},
    {"name": "一庫ダム", "id": "1368060444010"},
    {"name": "大滝ダム", "id": "1368060260010"},
    {"name": "猿谷ダム", "id": "1368060176040"},
    {"name": "九頭竜ダム", "id": "1368060778130"},
    {"name": "真名川ダム", "id": "1368060778090"},
    {"name": "菅沢ダム", "id": "1368070333090"},
    {"name": "尾原ダム", "id": "607041287705020"},
    {"name": "志津見ダム", "id": "607041287705010"},
    {"name": "殿ダム", "id": "607011287704010"},
    {"name": "土師ダム", "id": "1368070552110"},
    {"name": "灰塚ダム", "id": "607051287711010"},
    {"name": "苫田ダム", "id": "1368071340100"},
    {"name": "八田原ダム", "id": "1368071050020"},
    {"name": "温井ダム", "id": "1368070953030"},
    {"name": "弥栄ダム", "id": "1368070853010"},
    {"name": "島地川ダム", "id": "1368070760060"},
    {"name": "池田ダム", "id": "1368080700040", "max_capacity": 12650},
    {"name": "早明浦ダム", "id": "1368080700010"},
    {"name": "柳瀬ダム", "id": "1368080775010", "max_capacity": 28800},
    {"name": "富郷ダム", "id": "1368080700050"},
    {"name": "新宮ダム", "id": "1368080700030", "max_capacity": 6700},
    {"name": "長安口ダム", "id": "608061288803010"},
    {"name": "石手川ダム", "id": "1368080150020"},
    {"name": "鹿野川ダム", "id": "1368080255010"},
    {"name": "野村ダム", "id": "1368080276020"},
    {"name": "横瀬川ダム", "id": "1368080364020"},
    {"name": "大渡ダム", "id": "1368080477030"},
    {"name": "中筋川ダム", "id": "1368080364010"},
    {"name": "耶馬溪ダム", "id": "1368092060090"},
    {"name": "松原ダム", "id": "609061289920020"},
    {"name": "江川ダム", "id": "1368090600040"},
    {"name": "寺内ダム", "id": "1368090600030"},
    {"name": "下筌ダム", "id": "609061289920060"},
    {"name": "厳木ダム", "id": "1368090235070"},
    {"name": "嘉瀬川ダム", "id": "609051289901010"},
    {"name": "竜門ダム", "id": "1368090853060"},
    {"name": "緑川ダム", "id": "1368091050080"},
    {"name": "鶴田ダム", "id": "1368091270070"},
    {"name": "福地ダム", "id": "601320190001010"},
    {"name": "新川ダム", "id": "601330190001010"},
    {"name": "安波ダム", "id": "601340190001010"},
    {"name": "普久川ダム", "id": "601340190001020"},
    {"name": "辺野喜ダム", "id": "601010190001010"},
    {"name": "漢那ダム", "id": "601290190001010"},
    {"name": "羽地ダム", "id": "601070190002010"},
    {"name": "大保ダム", "id": "609999999999002"},
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
    HTMLテーブルから最新（正時含む）の有効なデータを解析
    """
    for tr in soup.find_all("tr"):
        cols = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
        
        # 日時行の特定 (例: 2026/09/18 00:40 ...)
        if len(cols) >= 3 and re.search(r"\d{4}/\d{1,2}/\d{1,2}", cols[0]) and re.search(r"\d{1,2}:\d{2}", cols[1]):
            
            # 1. max_capacity が指定されている場合：最新の貯水量から計算
            if max_capacity:
                for val_str in cols[2:]:
                    match = re.search(r"^([\d\.]+)$", val_str)
                    if match:
                        try:
                            val = float(match.group(1))
                            if 0 < val <= max_capacity * 1.2:
                                calculated_rate = round((val / max_capacity) * 100, 1)
                                if 0 <= calculated_rate <= 100:
                                    return calculated_rate
                        except (ValueError, ZeroDivisionError):
                            continue

            # 2. max_capacity 未指定の場合：上から順に見て「-」以外の貯水率が入っている最新の行を採用
            rate_str = cols[-1]
            
            # ハイフンや空文字、欠測の場合は上位の行（より新しい時刻）に値がないため、そのまま次の行（過去の時刻）へ探索を進める
            if rate_str in ["-", "ー", "", "欠測"]:
                continue
                
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
