"""检查 CSV 中的视频列表"""
import csv

with open("hd_with_audio.csv", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

print(f"共 {len(rows)} 条视频")
for i, r in enumerate(rows[:5]):
    title = r["视频标题"][:30]
    quality = r["画质"]
    print(f"  [{i+1}] {title} | 画质:{quality}")
