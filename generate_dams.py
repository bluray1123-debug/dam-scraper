import re
import requests
from bs4 import BeautifulSoup

# 15桁IDが元ページに存在しない主要ダムのID辞書（補完用）
KNOWN_IDS = {
    "宮ヶ瀬ダム": "1368030799020",
    "宇連ダム": "1368050651020",
    "矢木沢ダム": "1368030799010",
    "草木ダム": "303031283315020",
    "下久保ダム": "303031283318020",
    "岩屋ダム": "305071285521010",
    "早明浦ダム": "308061288801010",
    "一庫ダム": "306051286603010",
}

def generate_dams_code():
    url = "https://www.mlit.go.jp/mizukokudo/mizsei/mizukokudo_mizsei_tk2_000024.html"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    res = requests.get(url, headers=headers, timeout=15)
    res.encoding = res.apparent_encoding
    soup = BeautifulSoup(res.text, "html.parser")

    # 1. ページ内の全リンクから15桁IDを収集
    id_map = {}
    for a in soup.find_all("a"):
        href = a.get("href", "")
        match = re.search(r"ID=(\d{15})", href)
        if match:
            dam_id = match.group(1)
            # 親要素からダム名を取得
            tr = a.find_parent("tr")
            if tr:
                texts = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                dam_names = [t for t in texts if "ダム" in t or "遊水地" in t]
                if dam_names:
                    name = re.sub(r"（.*?）|\(.*?\)", "", dam_names[0])
                    id_map[name] = dam_id

    # 2. ページ全体のテキストから全132基のダム名を抽出
    page_text = soup.get_text()
    # 「〜ダム」または「渡良瀬遊水地」にマッチ
    raw_dams = re.findall(r"([一-龠ぁ-ヶーA-Za-z0-9]+(?:ダム|渡良瀬遊水地))", page_text)
    
    # 重複を除外してリスト化
    all_dams = []
    seen = set()
    for dam in raw_dams:
        dam_clean = re.sub(r"（.*?）|\(.*?\)", "", dam)
        if dam_clean not in seen and len(dam_clean) > 2:
            seen.add(dam_clean)
            all_dams.append(dam_clean)

    print(f"# 抽出完了: 全 {len(all_dams)} 基")
    print("DAMS = [")
    
    for dam_name in all_dams:
        # ページ内URLから取れたID -> 知られている既知ID -> 未設定ID の順で判定
        dam_id = id_map.get(dam_name) or KNOWN_IDS.get(dam_name)
        
        if dam_id:
            # 特殊な計算が必要なダム（宇連ダム等）
            if dam_name == "宇連ダム":
                print(f'    {{"name": "{dam_name}", "id": "{dam_id}", "max_capacity": 28420}},')
            else:
                print(f'    {{"name": "{dam_name}", "id": "{dam_id}"}},')
        else:
            # ページ内にIDリンクがないダム
            print(f'    {{"name": "{dam_name}", "id": "要ID入力"}},')

    print("]")

if __name__ == "__main__":
    generate_dams_code()
