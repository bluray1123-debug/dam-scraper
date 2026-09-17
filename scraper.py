import requests
from bs4 import BeautifulSoup

# 宮ヶ瀬ダムの例
url = "https://www1.river.go.jp/cgi-bin/DspDamData.exe?ID=601011281104002&KIND=3&PAGE=0"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

res = requests.get(url, headers=headers, timeout=10)
res.encoding = res.apparent_encoding  # 文字化け防止

soup = BeautifulSoup(res.text, "html.parser")

# HTML内のテーブルから貯水率のセルを抽出
# ※実際のHTML構造に合わせてtd/thのインデックスを指定
tables = soup.find_all("table")
if tables:
    print("HTML取得成功！テーブルデータを解析可能です。")
