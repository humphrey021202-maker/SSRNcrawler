from __future__ import annotations
import os, random, asyncio
from typing import List, Dict
from collections import deque
from .config import (
    DATA_DIR, JOURNAL_IDS, JOURNAL_PAGE_RANGE, JOURNAL_URL_TEMPLATE,
    BACKOFF_BASE, BACKOFF_MAX, RETRY_PER_PAGE, CHECKPOINT_FILE,
)
from .checkpoint import save_checkpoint, load_checkpoint
from .scraping import fetch_list_page_text

def _save_progress(journals: List[Dict], idx: int, page_num: int) -> None:
    cursors = []
    cur = journals[idx]
    cursors.append({
        "name": cur["name"], "jid": cur["jid"],
        "page": int(page_num), "end_page": 999999,
        "link_idx": 0, "save_dir": cur["save_dir"], "article_idx": 0,
    })
    for j in range(idx + 1, len(journals)):
        rest = journals[j]
        cursors.append({
            "name": rest["name"], "jid": rest["jid"],
            "page": int(rest.get("page", 1)), "end_page": 999999,
            "link_idx": 0, "save_dir": rest["save_dir"], "article_idx": 0,
        })
    save_checkpoint(deque(cursors), set())

async def scrape_journals_index_snapshot(context) -> None:
    """
    把“目录页的整页文本”落成 .txt（与全文保存风格一致），逐页翻页。
    命中验证 → 随机冷却 → 原地重试同一页；超过重试上限则跳到下一页。
    """
    restored = load_checkpoint(CHECKPOINT_FILE)
    journals: List[Dict] = []

    if restored and restored.get("cursors"):
        print(f"🔁 发现断点 {CHECKPOINT_FILE}，从上次位置继续。")
        for cur in restored["cursors"]:
            journals.append({
                "name": cur["name"],
                "jid": cur["jid"],
                "page": max(1, int(cur["page"])),
                "save_dir": os.path.join(DATA_DIR, cur["name"]),
            })
    else:
        for name, jid in JOURNAL_IDS.items():
            sp, _ = JOURNAL_PAGE_RANGE.get(name, (1, 1))
            journals.append({
                "name": name, "jid": jid, "page": sp,
                "save_dir": os.path.join(DATA_DIR, name),
            })

    try:
        for i, cur in enumerate(journals):
            name, jid, page_num = cur["name"], cur["jid"], int(cur["page"])
            os.makedirs(cur["save_dir"], exist_ok=True)

            sp, ep = JOURNAL_PAGE_RANGE.get(name, (page_num, page_num))
            if page_num < sp: page_num = sp

            print(f"\n===== 期刊 {name} (jid={jid})：从第 {page_num} 页开始，保存目录页整页文本 =====")

            while page_num <= ep:
                url = JOURNAL_URL_TEMPLATE.format(jid=jid, page=page_num)
                file_stem = f"list_{page_num:05d}"
                print(f"🌍 [{name}] 第 {page_num} 页: {url}")

                attempts = 0
                while True:
                    saved, hit_chal, sz = await fetch_list_page_text(
                        context=context,
                        url=url,
                        save_dir=cur["save_dir"],
                        file_stem=file_stem,
                    )

                    if saved:
                        print(f"📝 保存成功：{name}/{file_stem}.html  ({sz} bytes)")
                        from .config import COOKIE_FILE
                        try:
                            await context.storage_state(path=COOKIE_FILE)
                        except Exception:
                            pass
                        _save_progress(journals, i, page_num + 1)   # ✅ 成功才前移
                        page_num += 1
                        break

                    # 未保存到正常目录：挑战或异常
                    attempts += 1
                    if attempts >= RETRY_PER_PAGE:
                        print(f"⏭️ 本页重试 {attempts} 次仍失败 → 跳过到下一页")
                        _save_progress(journals, i, page_num + 1)   # 放弃该页，前移
                        page_num += 1
                        break

                    # 随机冷却后“原地重试同一页”
                    wait_s = random.uniform(BACKOFF_BASE, BACKOFF_MAX)
                    reason = "挑战" if hit_chal else "异常/超时"
                    print(f"🧱 {reason} → 冷却 {wait_s:.1f}s 后原地重试本页")
                    _save_progress(journals, i, page_num)          # 不前移
                    await asyncio.sleep(wait_s)

            print(f"🎯 期刊 {name} 完成（目录页整页文本保存）。")

    except KeyboardInterrupt:
        try:
            _save_progress(journals, i, page_num)
        except Exception:
            pass
        print("🛑 捕获到 Ctrl+C，断点已保存。")

    print("\n🎉 全部期刊目录页抓取完成（整页文本版）")
