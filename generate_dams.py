import re
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup

def is_storage_rate_missing(dam_id):
    """CGI画面を確認し、貯水率が『-』表記か判定する"""
    url = f"https://www1.river.go.jp/cgi-bin/DspDamData.exe?ID={dam_id}&KIND=3&PAGE=0"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        res.encoding = "euc-jp"
        soup = BeautifulSoup(res.text, "html.parser")

        frames = soup.find_all(["frame", "iframe"])
        for frame in frames:
            src = frame.get("src")
            if src:
                res_f = requests.get(urljoin(url, src), headers=headers, timeout=5)
                res_f.encoding = "euc-jp"
                soup = BeautifulSoup(res_f.text, "html.parser")

        for tr in soup.find_all("tr"):
            cols = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            if len(cols) >= 5 and re.search(r"\d{4}/\d{1,2}/\d{1,2}", cols[0]):
                for col in reversed(cols):
                    if col == "-":
                        return True
                    if re.search(r"[\d\.]+", col):
                        return False
    except Exception:
        pass
    return False

def generate_dams_code():
    url = "https://www.mlit.go.jp/mizukokudo/mizsei/mizukokudo_mizsei_tk2_000024.html"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    res = requests.get(url, headers=headers, timeout=15)
    res.encoding = res.apparent_encoding
    soup = BeautifulSoup(res.text, "html.parser")

    dams = []
    seen_ids = set()

    # ページ内のすべてのリンクから 15桁のID を全件探索
    for a in soup.find_all("a"):
        href = a.get("href", "")
        match = re.search(r"ID=(\d{15})", href)
        if not match:
            continue

        dam_id = match.group(1)
        if dam_id in seen_ids:
            continue

        # 親行（tr）またはセル（td）からダム名を柔軟に抽出
        dam_name = ""
        tr = a.find_parent("tr")
        if tr:
            cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            # 「ダム」の文字が含まれるセルを優先的に取得
            dam_cells = [c for c in cells if "ダム" in c]
            if dam_cells:
                dam_name = dam_cells[0]
            elif len(cells) >= 2:
                dam_name = cells[-2] if len(cells) > 2 else cells[0]

        # リンクテキスト自体に「ダム」が含まれる場合の補助
        if not dam_name or "ダム" not in dam_name:
            a_text = a.get_text(strip=True)
            if "ダム" in a_text:
                dam_name = a_text

        # ダム名の整形（かっこや余計な改行を除去）
        dam_name = re.sub(r"[\s\n\t]+", "", dam_name)
        dam_name = re.sub(r"（.*?）|\(.*?\)", "", dam_name)

        if dam_name and dam_id not in seen_ids:
            seen_ids.add(dam_id)
            dams.append({"name": dam_name, "id": dam_id})

    print(f"# 取得完了: 計 {len(dams)} 基 (貯水率『-』のチェック中...)")
    print("DAMS = [")
    
    for d in dams:
        is_missing = is_storage_rate_missing(d["id"])
        if is_missing:
            print(f'    {{"name": "{d["name"]}", "id": "{d["id"]}", "max_capacity": None}},  # ← 貯水率「-」のため要入力')
        else:
            print(f'    {{"name": "{d["name"]}", "id": "{d["id"]}"}},')
            
    print("]")

if __name__ == "__main__":
    generate_dams_code()
