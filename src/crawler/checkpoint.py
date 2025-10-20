from __future__ import annotations
import json, os, time
from typing import List, Dict, Set, Optional
from collections import deque
from .config import CHECKPOINT_FILE, PERSIST_SEEN_IDS, ENABLE_GLOBAL_DEDUP

def snapshot_cursors(dq: deque) -> List[Dict]:
    out = []
    for cur in dq:
        out.append({
            "name": cur["name"],
            "jid": cur["jid"],
            "page": cur["page"],
            "end_page": cur["end_page"],
            "link_idx": cur["link_idx"],
            "save_dir": cur["save_dir"],
            "article_idx": cur["article_idx"],
        })
    return out

def save_checkpoint(dq: deque, seen_ids: Set[str], path: str = CHECKPOINT_FILE):
    data = {
        "version": 1,
        "saved_at": int(time.time()),
        "cursors": snapshot_cursors(dq),
    }
    if PERSIST_SEEN_IDS and ENABLE_GLOBAL_DEDUP:
        data["seen_ids"] = sorted(list(seen_ids))

    tmp = path + ".tmp"
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Windows 有时文件被占用，replace 可能抛 PermissionError
    try:
        os.replace(tmp, path)
    except PermissionError:
        # 忽略：下次再尝试，不要让全局崩溃
        print(f"⚠️ 无法替换 {path}（被占用或无权限），跳过本次保存。")

def load_checkpoint(path: str = CHECKPOINT_FILE) -> Optional[Dict]:
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("version") != 1:
            return None
        return data
    except Exception as e:
        print(f"⚠️ 断点文件损坏或不可读：{e}，从头开始。")
        return None
