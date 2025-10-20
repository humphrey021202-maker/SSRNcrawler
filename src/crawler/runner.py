# src/<你的包>/runner.py
from __future__ import annotations
from typing import List, Dict, Set
import asyncio, os, random
from collections import deque

from .config import (
    DATA_DIR, JOURNAL_IDS, JOURNAL_PAGE_RANGE, JOURNAL_URL_TEMPLATE,
    GLOBAL_DETAIL_CONCURRENCY, ENABLE_GLOBAL_DEDUP,
    BACKOFF_BASE, BACKOFF_MAX, CHECKPOINT_FILE,
)
from .checkpoint import save_checkpoint, load_checkpoint
from .utils import (
    polite_sleep, humanize_page, load_links_on_page, looks_like_challenge,
    extract_abstract_id_from_url, make_filename
)
from .scraping import fetch_article_text

# 全局并发仍限定为 1，更稳
detail_sem = asyncio.Semaphore(GLOBAL_DETAIL_CONCURRENCY)
seen_ids_lock = asyncio.Lock()
seen_ids: Set[str] = set()

LINK_SELECTORS = [
    'a[href*="papers.cfm?abstract_id="]',
    "div.title a",
    ".abstract-title a",
    "a.search-result-title",
]

def save_progress(journals: List[Dict], current_index: int, current_page: int,
                  current_link_idx: int, seen_ids: Set[str]) -> None:
    """
    journals: [{"name":..., "jid":..., "page":..., "link_idx":..., "save_dir":...}, ...]
    current_index: 正在处理的期刊在 journals 列表中的下标
    current_page:  正在处理的页码
    current_link_idx: 当前页里已经处理到的链接序号（从 0 开始；如果刚处理完第 k 条，就传 k）
    """
    snapshot = []

    # 1) 当前期刊的最新游标
    cur = journals[current_index]
    snapshot.append({
        "name": cur["name"],
        "jid": cur["jid"],
        "page": int(current_page),
        "end_page": 999999,          # 顺序模式下用不到，保留字段即可
        "link_idx": int(current_link_idx),
        "save_dir": cur["save_dir"],
        "article_idx": 0,            # 顺序模式不再用编号写名，可占位
    })

    # 2) 其后的剩余期刊（保持原顺序）
    for j in range(current_index + 1, len(journals)):
        rest = journals[j]
        snapshot.append({
            "name": rest["name"],
            "jid": rest["jid"],
            "page": int(rest.get("page", 1)),
            "end_page": 999999,
            "link_idx": int(rest.get("link_idx", 0)),
            "save_dir": rest["save_dir"],
            "article_idx": 0,
        })

    # 写盘
    save_checkpoint(deque(snapshot), seen_ids)

async def scrape_all_journals_rotating(context) -> None:
    """
    顺序抓取每本期刊，自动探测尾页：
    - 列表页/详情页出现一次验证 => 随机冷却 BACKOFF_BASE~BACKOFF_MAX 秒，然后原地重试/继续
    - 列表页连续两页无链接（且非挑战页） => 判定到尾页
    - 网络/超时错误：不加页，原地冷却后重试
    - 断点：精确到“第 N 页的第 K 条”；Ctrl+C 时也会落盘
    - 保存路径：data/<期刊名>/；文件名：{abstract_id}_page{page}_NO.{ordinal}.txt
    """
    restored = load_checkpoint(CHECKPOINT_FILE)
    journals: List[Dict] = []

    if restored and restored.get("cursors"):
        print(f"🔁 发现断点文件 {CHECKPOINT_FILE}，将从上次位置继续。")
        for cur in restored["cursors"]:
            journals.append({
                "name": cur["name"],
                "jid": cur["jid"],
                "page": max(1, int(cur["page"])),
                "link_idx": max(0, int(cur["link_idx"])),
                "save_dir": os.path.join(DATA_DIR, cur["name"]),
            })
    else:
        for name, jid in JOURNAL_IDS.items():
            sp, _ = JOURNAL_PAGE_RANGE.get(name, (1, 1))
            journals.append({
                "name": name,
                "jid": jid,
                "page": sp,
                "link_idx": 0,
                "save_dir": os.path.join(DATA_DIR, name),
            })

    list_page = await context.new_page()
    await humanize_page(list_page)

    try:
        for i, cur in enumerate(journals):
            name = cur["name"]; jid = cur["jid"]; page_num = int(cur["page"])
            os.makedirs(cur["save_dir"], exist_ok=True)

            print(f"\n===== 开始期刊 {name} (jid={jid})，从第 {page_num} 页起 =====")

            empty_pages_in_a_row = 0

            while True:
                list_url = JOURNAL_URL_TEMPLATE.format(jid=jid, page=page_num)
                print(f"\n🌍 [{name}] 第 {page_num} 页: {list_url}")

                # 列表页：网络/超时错误 -> 不加页，原地退避重试
                try:
                    links = await load_links_on_page(list_page, list_url, LINK_SELECTORS)
                except Exception as e:
                    wait_s = random.uniform(BACKOFF_BASE, BACKOFF_MAX)
                    print(f"⚠️ 列表加载失败：{e}\n   ⇢ 冷却 {wait_s:.1f}s 后在同一页重试 …")
                    save_progress(journals, i, page_num, cur.get("link_idx", 0), seen_ids)
                    await asyncio.sleep(wait_s)
                    continue

                # 无链接：挑战 or 真空页
                if not links:
                    try:
                        body = await list_page.inner_text("body")
                    except Exception:
                        body = ""

                    # 验证页：不加页，原地退避重试
                    if looks_like_challenge(body):
                        wait_s = random.uniform(BACKOFF_BASE, BACKOFF_MAX)
                        print(f"🧱 列表页疑似验证，冷却 {wait_s:.1f}s 后重试当前页 …")
                        save_progress(journals, i, page_num, cur.get("link_idx", 0), seen_ids)
                        await asyncio.sleep(wait_s)
                        continue

                    # 真空页：连续两次才判尾页
                    empty_pages_in_a_row += 1
                    if empty_pages_in_a_row >= 2:
                        print(f"✅ [{name}] 连续两页无有效链接（到第 {page_num} 页），判定到尾页，结束该刊。")
                        # 断点：写下一个期刊的起点（或保留当前快照也行）
                        save_progress(journals, i, page_num, cur.get("link_idx", 0), seen_ids)
                        break
                    else:
                        print(f"📭 [{name}] 第 {page_num} 页无有效链接，翻到下一页确认。")
                        # 翻页前落盘（下一页从 0 开始）
                        save_progress(journals, i, page_num, 0, seen_ids)
                        cur["link_idx"] = 0
                        page_num += 1
                        continue
                else:
                    empty_pages_in_a_row = 0  # 有链接即清零

                print(f"📑 [{name}] 第 {page_num} 页共 {len(links)} 条文章链接")

                # 若从断点恢复：跳过已处理完的本页前若干条（link_idx 表示“已处理到的序号”）
                start_ordinal = max(1, int(cur.get("link_idx", 0)) + 1)

                for ordinal, link in enumerate(links, start=1):
                    if ordinal < start_ordinal:
                        continue  # 跳过已处理条目

                    abs_id = extract_abstract_id_from_url(link) or f"unk_{ordinal}"
                    file_stem = make_filename(abs_id, page_num, ordinal)

                    # 去重（可选）
                    if ENABLE_GLOBAL_DEDUP and not abs_id.startswith("unk_"):
                        async with seen_ids_lock:
                            if abs_id in seen_ids:
                                print(f"↩️ 已抓过 abstract_id={abs_id}，跳过")
                                # 进度前移：已处理到 ordinal
                                cur["link_idx"] = ordinal
                                save_progress(journals, i, page_num, ordinal, seen_ids)
                                continue

                    async with detail_sem:
                        saved, hit_challenge, _ = await fetch_article_text(
                            context=context,
                            url=link,
                            save_dir=cur["save_dir"],
                            file_stem=file_stem,
                        )

                    # 去重集合写入
                    if ENABLE_GLOBAL_DEDUP and saved and not abs_id.startswith("unk_"):
                        async with seen_ids_lock:
                            seen_ids.add(abs_id)

                    # 进度前移：已处理到 ordinal
                    cur["link_idx"] = ordinal
                    save_progress(journals, i, page_num, ordinal, seen_ids)

                    # 详情页命中挑战：随机退避，原地继续本页
                    if hit_challenge:
                        wait_s = random.uniform(BACKOFF_BASE, BACKOFF_MAX)
                        print(f"🧱 详情页疑似验证，冷却 {wait_s:.1f}s 后继续本页 …")
                        save_progress(journals, i, page_num, ordinal, seen_ids)
                        await asyncio.sleep(wait_s)

                # 本页处理完 -> 翻页（页内位置归零）
                cur["link_idx"] = 0
                save_progress(journals, i, page_num, 0, seen_ids)
                page_num += 1

            print(f"🎯 期刊 {name} 完成。")

    except KeyboardInterrupt:
        # Ctrl+C：尽力保存当前位置
        try:
            # 找到一个尽可能安全的下标和位置保存
            # 这里假设 i/page_num/cur["link_idx"] 仍在作用域内（若异常早于定义，可再做保护）
            if 'i' in locals() and 'page_num' in locals():
                lk = 0
                try:
                    lk = journals[i].get("link_idx", 0)
                except Exception:
                    pass
                save_progress(journals, i, page_num, lk, seen_ids)
            print("🛑 捕获到 Ctrl+C，已保存断点。")
        except Exception as e:
            print(f"⚠️ Ctrl+C 时保存断点失败：{e}")
    finally:
        try:
            await list_page.close()
        except Exception:
            pass

    print("\n🎉 所有期刊处理完成")
