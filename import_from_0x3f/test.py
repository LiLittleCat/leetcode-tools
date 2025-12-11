from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List


def load_mapping(path: Path) -> Dict[str, str]:
    """读取 favorite_name.json，期望为 {old: new} 字典。"""
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        return {str(k): str(v) for k, v in data.items()}
    raise ValueError("favorite_name.json 格式错误，预期为字典。")


def load_ordered(path: Path) -> List[Dict[str, str]]:
    """兼容两种格式的 favorite_name_ordered.json：列表格式或旧版字典格式。"""
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        result = []
        for item in data:
            if isinstance(item, dict) and "old" in item:
                result.append({"old": str(item["old"]), "new": str(item.get("new", ""))})
        return result
    if isinstance(data, dict):
        return [{"old": str(k), "new": str(v)} for k, v in data.items()]
    raise ValueError("favorite_name_ordered.json 格式错误，预期为列表或字典。")


def write_ordered(path: Path, items: List[Dict[str, str]]) -> None:
    """写回列表格式的 favorite_name_ordered.json。"""
    with path.open("w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    mapping_path = base_dir / "favorite_name.json"
    ordered_path = base_dir / "favorite_name_ordered.json"

    mapping = load_mapping(mapping_path)
    ordered = load_ordered(ordered_path)

    # 按 key 覆盖 new 字段
    for item in ordered:
        old = item["old"]
        if old in mapping:
            item["new"] = mapping[old]

    write_ordered(ordered_path, ordered)
    print(f"已更新 {ordered_path.name}，共 {len(ordered)} 条。")


if __name__ == "__main__":
    main()
