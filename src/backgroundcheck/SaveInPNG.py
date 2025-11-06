import matplotlib
matplotlib.use('Agg')
import pandas as pd
import matplotlib.pyplot as plt
import re

df = pd.read_csv('E:/SSRNPaperResearch/data/result/ERN_with_English_bg.csv')

# ====== 提取年份 ======
def extract_year(text):
    if not isinstance(text, str):
        return None
    # 匹配 4 位年份数字
    m = re.search(r'(\d{4})', text)
    if m:
        return int(m.group(1))
    return None

df['posted'] = df['posted'].apply(extract_year)
df = df.dropna(subset=['posted'])
df['posted'] = df['posted'].astype(int)

# ====== 筛选年份区间 ======
df = df[df['posted'].between(2014, 2025)]

# ====== 清理分类 ======
df['english_background'] = df['english_background'].astype(str).str.strip()

# ====== 分组统计 ======
count_df = df.groupby(['posted', 'english_background']).size().reset_index(name='count')

pivot_df = count_df.pivot(index='posted', columns='english_background', values='count').fillna(0)
pivot_df = pivot_df.apply(pd.to_numeric, errors='coerce').fillna(0).astype(int)
pivot_df = pivot_df.sort_index()

# ====== 绘图 ======
plt.figure(figsize=(12,7))
pivot_df.plot(kind='bar', width=0.8)

plt.title('English Background Distribution by Year (2014–2025)')
plt.xlabel('Year')
plt.ylabel('Number of Records')
plt.xticks(rotation=45)
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.legend(title='English Background')
plt.tight_layout()

out = 'ERN.png'
plt.savefig(out, dpi=300, bbox_inches='tight')
plt.close()

print("✅ 图生成成功:", out)
print(pivot_df.head())