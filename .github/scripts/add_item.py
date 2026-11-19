import json
import os
import re
from PIL import Image, ImageDraw, ImageFont

raw_data_str = os.environ.get("RAW_DATA", "{}").strip()
cast = os.environ.get("CAST", "").strip()
item_format = os.environ.get("FORMAT", "写真集").strip()
label = os.environ.get("LABEL", "その他").strip()
genre = os.environ.get("GENRE", "グラビア").strip()
af_html = os.environ.get("AF_HTML", "").strip()
custom_memo = os.environ.get("CUSTOM_MEMO", "").strip()

# 1. ブックマークレットデータのパース
try:
    raw = json.loads(raw_data_str)
except Exception:
    raw = {"title": raw_data_str, "date": "", "price": 0, "raw_memo": ""}

title = raw.get("title", "").strip()
date = raw.get("date", "").strip()
price = int(raw.get("price", 0))
raw_memo = raw.get("raw_memo", "").strip()

# 2. アフィリエイトHTMLから image と url を抽出
img_match = re.search(r'<img[^>]+src="([^"]+)"', af_html)
url_match = re.search(r'<a[^>]+href="([^"]+)"', af_html)

image_url = img_match.group(1) if img_match else ""
item_url = url_match.group(1) if url_match else (af_html if af_html.startswith("http") else "")

# 3. メモ整形
if custom_memo:
    memo = custom_memo.replace("\\n", "\n")
else:
    sentences = [s.strip() for s in re.split(r'[。！!？?]', raw_memo) if len(s.strip()) > 4][:3]
    memo = "\n".join([f"{s}。" for s in sentences]) if sentences else title

# 4. 既存items.jsonのキー順に合わせたデータ作成
new_item = {
    "title": title,
    "cast": cast if cast else title.split()[0],
    "format": item_format,
    "label": label,
    "genre": genre,
    "date": date,
    "price": price,
    "image": image_url,
    "url": item_url,
    "memo": memo
}

json_path = "items.json"
if os.path.exists(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        items = json.load(f)
else:
    items = []

items.insert(0, new_item)

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(items, f, ensure_ascii=False, indent=2)

# 5. X告知用PNG画像の自動生成（1200x675 16:9）
os.makedirs("x_posts", exist_ok=True)
W, H = 1200, 675

COLOR_MAP = {
    "写真集": ((219, 39, 119), (255, 241, 248), (157, 23, 77)),
    "グラビア本・雑誌": ((234, 88, 12), (255, 247, 237), (154, 52, 18)),
    "デジタル写真集": ((2, 132, 199), (240, 249, 255), (7, 89, 133)),
}
accent, bg_color, dark_text = COLOR_MAP.get(item_format, ((234, 88, 12), (255, 247, 237), (154, 52, 18)))

img = Image.new("RGB", (W, H), bg_color)
draw = ImageDraw.Draw(img)

draw.rectangle([24, 24, W - 24, H - 24], outline=accent, width=6)
draw.rectangle([24, 24, W - 24, 130], fill=accent)

font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
if not os.path.exists(font_path):
    font_path = "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc"

font_badge = ImageFont.truetype(font_path, 38)
font_cast = ImageFont.truetype(font_path, 48)
font_title = ImageFont.truetype(font_path, 38)
font_memo = ImageFont.truetype(font_path, 28)
font_footer = ImageFont.truetype(font_path, 28)

draw.text((60, 56), f"【{item_format} / {label} / {genre}】", fill=(255, 255, 255), font=font_badge)

# 出演者・タレント名（cast）を強調表示
cast_display = new_item["cast"]
draw.text((60, 155), f"◆ {cast_display}", fill=dark_text, font=font_cast)

def wrap_text(text, max_chars=26):
    lines = []
    for paragraph in text.split("\n"):
        while len(paragraph) > max_chars:
            lines.append(paragraph[:max_chars])
            paragraph = paragraph[max_chars:]
        if paragraph:
            lines.append(paragraph)
    return lines

y = 225
for line in wrap_text(title, 26)[:2]:
    draw.text((60, y), line, fill=(30, 30, 35), font=font_title)
    y += 52

y += 16
for line in wrap_text(memo, 34)[:3]:
    draw.text((60, y), line, fill=(75, 75, 85), font=font_memo)
    y += 40

draw.line([(60, H - 125), (W - 60, H - 125)], fill=accent, width=3)
date_prefix = "配信日：" if item_format == "デジタル写真集" else "発売日："
release_str = f"{date_prefix}{date}" if date else "予約受付中"
price_str = f"価格：{price:,}円（税込）" if price else ""
draw.text((60, H - 100), f"{release_str} ｜ {price_str}", fill=dark_text, font=font_footer)

img.save("x_posts/latest_post.png")

cast_tag = f"#{cast_display.replace(' ', '')}" if cast_display else ""
post_text = f"""【新刊{item_format}情報】

{cast_display}
『{title}』

{memo}

📅 {release_str}
💰 {price_str}

{cast_tag} #{genre} #写真集

👇予約・詳細リンクはリプ欄へ！"""

with open("x_posts/latest_post.txt", "w", encoding="utf-8") as f:
    f.write(post_text)

print("=== 生成されたX投稿文 ===")
print(post_text)
