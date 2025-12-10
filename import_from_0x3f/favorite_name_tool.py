"""
收集 discuss_json 下所有题单名称，生成/更新 favorite_name.json，并打印结果。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Tuple, Union


class FavoriteNameTool:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or Path(__file__).resolve().parent
        self.discuss_json_dir = self.base_dir / "discuss_json"
        self.output_path = self.base_dir / "favorite_name_ordered.json"

    def _iter_discuss_files(self) -> Iterable[Path]:
        # 先按文件名排序，保证专题顺序稳定
        return sorted(self.discuss_json_dir.glob("*.json"))

    @staticmethod
    def _parse_chinese_num(text: str) -> Union[int, None]:
        cn_map = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
        if not text:
            return None
        if text in cn_map:
            return cn_map[text]
        # 十三、三十、三十二
        if text.startswith("十"):
            tail = text[1:]
            return 10 + (cn_map.get(tail, 0) if tail else 0)
        if text.endswith("十"):
            head = text[:-1]
            return cn_map.get(head, 0) * 10 if head in cn_map else None
        if "十" in text and len(text) == 2:
            head, tail = text[0], text[1]
            if head in cn_map and tail in cn_map:
                return cn_map[head] * 10 + cn_map[tail]
        return None

    @classmethod
    def _numeric_parts(cls, part: str) -> Union[Tuple[int, Tuple[int, ...]], None]:
        """提取段落的数字序号，如 '§1.2' '1.3.4' '一、'."""
        s = part.strip()
        if s.startswith("§"):
            s = s[1:].strip()
        if "、" in s:
            cn_prefix = s.split("、", 1)[0]
            num = cls._parse_chinese_num(cn_prefix)
            if num is not None:
                return (num, ())
        num = cls._parse_chinese_num(s)
        if num is not None:
            return (num, ())
        import re

        m = re.match(r"^(\d+(?:\.\d+)*)", s)
        if m:
            nums = tuple(int(x) for x in m.group(1).split("."))
            return (nums[0], nums[1:])
        return None

    @classmethod
    def _segment_key(cls, segment: str) -> Tuple[int, Union[Tuple[int, ...], str]]:
        numeric = cls._numeric_parts(segment)
        if numeric is not None:
            primary, rest = numeric
            return (0, (primary, *rest))
        return (1, segment.lower())

    @classmethod
    def name_sort_key(cls, name: str) -> Tuple:
        segments = name.split(" / ")
        return tuple(cls._segment_key(seg) for seg in segments)

    def _load_existing(self) -> Dict[str, str]:
        if not self.output_path.exists():
            return {}
        try:
            with self.output_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                # 仅保留字符串键
                return {str(k): str(v) for k, v in data.items()}
        except json.JSONDecodeError:
            pass
        return {}

    def collect_names(self) -> List[str]:
        seen = set()
        ordered: List[str] = []
        for path in self._iter_discuss_files():
            try:
                with path.open("r", encoding="utf-8") as f:
                    items = json.load(f)
                if not isinstance(items, list):
                    continue
                for item in items:
                    if isinstance(item, dict) and "name" in item and item["name"]:
                        name = str(item["name"])
                        if name not in seen:
                            seen.add(name)
                            ordered.append(name)
            except (json.JSONDecodeError, OSError):
                continue
        return ordered

    def build_mapping(self) -> Dict[str, str]:
        existing = self._load_existing()
        names = sorted(self.collect_names(), key=self.name_sort_key)
        return {name: existing.get(name, "") for name in names}

    def write(self) -> Dict[str, str]:
        mapping = self.build_mapping()
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with self.output_path.open("w", encoding="utf-8") as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)
        return mapping


def main() -> None:
    tool = FavoriteNameTool()
    mapping = tool.write()
    print(json.dumps(mapping, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
