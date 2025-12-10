"""
收集 discuss_json 下所有题单名称，生成/更新 favorite_name.json，并打印结果。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, Set


class FavoriteNameTool:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or Path(__file__).resolve().parent
        self.discuss_json_dir = self.base_dir / "discuss_json"
        self.output_path = self.base_dir / "favorite_name.json"

    def _iter_discuss_files(self) -> Iterable[Path]:
        return sorted(self.discuss_json_dir.glob("*.json"))

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

    def collect_names(self) -> Set[str]:
        names: Set[str] = set()
        for path in self._iter_discuss_files():
            try:
                with path.open("r", encoding="utf-8") as f:
                    items = json.load(f)
                if not isinstance(items, list):
                    continue
                for item in items:
                    if isinstance(item, dict) and "name" in item and item["name"]:
                        names.add(str(item["name"]))
            except (json.JSONDecodeError, OSError):
                continue
        return names

    def build_mapping(self) -> Dict[str, str]:
        existing = self._load_existing()
        names = sorted(self.collect_names())
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
