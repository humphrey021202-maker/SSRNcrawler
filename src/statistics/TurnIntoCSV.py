import os
import re
import pandas as pd

# 输入目录（放你的 article_xxx.txt 文件的文件夹路径）
INPUT_DIR = "E:/SSRNPaperResearch/data/eBusiness & eCommerce eJournal"
OUTPUT_CSV = "eBusiness.csv"

# 判断是否可能是机构的关键词
ORG_KEYWORDS = ["University", "College", "School", "Department", "Institute", "Laboratory", "Center", "Centre"]


def extract_info_from_file(filepath):
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    # 取 "Share:" 和 "Abstract" 之间的内容
    share_match = re.search(r"Share:(.*?)(Abstract)", text, flags=re.S)
    if not share_match:
        return None

    block = share_match.group(1).strip()
    lines = [line.strip() for line in block.splitlines() if line.strip()]

    # 初始化
    title = ""
    publication_info = ""
    posted_year = None
    authors = []
    institutions = []

    # 1. 找标题
    if lines:
        title = lines[0]
        # 如果第二行是 Proceedings / Journal，则作为出版信息
        if len(lines) > 1 and re.search(r"(Proceedings|Journal|Review|Conference)", lines[1], re.I):
            publication_info = lines[1]

    # 2. 找年份（Posted: ...）
    for line in lines:
        m = re.search(r"Posted:.*?(\d{4})", line)
        if m:
            posted_year = m.group(1)
            break

    # 3. 找作者和机构（在 Posted 行之后的部分）
    after_posted = False
    for line in lines:
        if "Posted:" in line:
            after_posted = True
            continue
        if not after_posted:
            continue
        if "Date Written" in line:  # 到达 Date Written 结束
            break
        if any(keyword in line for keyword in ORG_KEYWORDS):
            institutions.append(line)
        else:
            authors.append(line)

    return {
        "file": os.path.basename(filepath),
        "title": title,
        "publication_info": publication_info,
        "year": posted_year,
        "authors": "; ".join(authors),
        "institutions": "; ".join(institutions),
    }


def main():
    records = []
    for filename in os.listdir(INPUT_DIR):
        if filename.endswith(".txt"):
            filepath = os.path.join(INPUT_DIR, filename)
            info = extract_info_from_file(filepath)
            if info:
                records.append(info)

    df = pd.DataFrame(records)
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"✅ 提取完成，共处理 {len(records)} 篇文章，已保存到 {OUTPUT_CSV}")


if __name__ == "__main__":
    main()