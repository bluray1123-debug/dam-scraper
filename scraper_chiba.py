import json
import os
import re
import requests
from bs4 import BeautifulSoup

RAW_GAS_URL = os.environ.get("GAS_WEBHOOK_URL", "")
TARGET_URL = "https://www.pref.chiba.lg.jp/suisei/chosui/chosuijoukyou.html"


def clean_url(raw_url):
    if not raw_url:
        return ""
    url = raw_url.strip().strip("'\"")
    if url and not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    return url


def parse_number(text):
    """カンマ付き数値文字列を float に変換"""
    if not text:
        return None
    cleaned = re.sub(r"[^\d\.]", "", text)
    if cleaned:
        try:
            return float(cleaned)
        except ValueError:
            pass
    return None


def fetch_chiba_dams():
    """千葉県水道用ダムのデータを取得して貯水率を計算"""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }

    dam_results = []

    try:
        res = requests.get(TARGET_URL, headers=headers, timeout=15)
        res.encoding = res.apparent_encoding
        soup = BeautifulSoup(res.text, "html.parser")

        # ページ内のテーブルを探索
        for table in soup.find_all("table"):
            rows = table.find_all("tr")
            if not rows:
                continue

            for tr in rows:
                cols = [
                    td.get_text(strip=True) for td in tr.find_all(["td", "th"])
                ]

                # 列数が不足している場合はスキップ
                if len(cols) < 5:
                    continue

                no_val = cols[0]
                dam_name_raw = cols[1]

                # No が数字(1, 2, 3...)の行のみを対象にする (ハイフン "-" の小計・合計行はスキップ)
                if not re.match(r"^\d+$", no_val):
                    continue

                # ダム名に「ダム」表記を付与（例: "東" -> "東ダム"）
                dam_name = (
                    dam_name_raw
                    if dam_name_raw.endswith("ダム")
                    else f"{dam_name_raw}ダム"
                )

                # 有効貯水量 (3列目) と 貯水量 (4列目) の抽出
                valid_capacity = parse_number(cols[3])
                current_storage = parse_number(cols[4])

                if valid_capacity and current_storage is not None:
                    if valid_capacity > 0:
                        # 貯水量 ÷ 有効貯水量 で小数点第一位まで算出
                        calculated_rate = round(
                            (current_storage / valid_capacity) * 100, 1
                        )

                        print(
                            f"[取得成功] {dam_name}: {calculated_rate}% "
                            f"(貯水量: {current_storage:,} / 有効: {valid_capacity:,})",
                            flush=True,
                        )

                        dam_results.append(
                            {
                                "dam_name": dam_name,
                                "storage_rate": calculated_rate,
                            }
                        )

    except Exception as e:
        print(f"[エラー] 千葉県ダムデータの取得失敗: {e}", flush=True)

    return dam_results


def main():
    gas_url = clean_url(RAW_GAS_URL)

    results = fetch_chiba_dams()
    if not results:
        print("データを取得できなかったため処理を終了します。")
        return

    print(f"取得完了: {len(results)} 件の千葉県ダムデータ", flush=True)

    if gas_url:
        print(f"GASへ送信中... (送信先: {gas_url[:30]}...)")
        payload = {"damList": results}

        try:
            res = requests.post(
                gas_url,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
                timeout=60,
            )
            print("GAS送信結果:", res.text)
        except Exception as e:
            print("GAS送信エラー:", e)
    else:
        print(
            "※ GAS_WEBHOOK_URL が未設定のため、GASへの送信はスキップしました。"
        )


if __name__ == "__main__":
    main()
