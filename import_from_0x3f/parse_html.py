"""
从本地保存的 LeetCode 讨论页 HTML 中提取题单。

解析规则：
- 关注 h2/h3/h4 与其后的 ul。将某个最深层标题（最近一次出现的 h4，否则 h3，否则 h2）
  到下一次出现同级或更高标题之间的所有 ul 中的题目合并为一个题单。
- 如果某个 h4 后面没有出现题目列表，则忽略该 h4（即不会单独生成题单）。
- 题单名称为当前有效标题路径的拼接，如 “h2 / h3 / h4”。

用法:
    python parse_html.py discuss_html/sliding_window.html [-o out.json]
"""

import argparse
import json
import os
import re
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

_PROBLEM_SLUG_RE = re.compile(r"/problems/([^/?#]+)/?")


def _clean_text(text: str) -> str:
    """压缩空白并去除首尾空格。"""
    return re.sub(r"\s+", " ", text or "").strip()


def _extract_slug(href: str) -> Optional[str]:
    match = _PROBLEM_SLUG_RE.search(href or "")
    return match.group(1) if match else None


def _collect_problems_from_ul(ul_tag) -> List[Dict[str, str]]:
    """从一个 ul 中提取题目列表（仅保留含 /problems/ 的链接）。"""
    problems: List[Dict[str, str]] = []
    for li in ul_tag.find_all("li", recursive=False):
        link = li.find("a", href=True)
        if not link:
            continue
        href = link["href"].strip()
        if "problems" not in href:
            continue

        title = _clean_text(link.get_text())
        slug = _extract_slug(href) or ""
        if not title and not slug:
            continue

        problems.append(
            {
                "title": title or slug,
                "titleSlug": slug,
                "url": href,
            }
        )
    return problems


def parse_html_content(html_content: str) -> List[Dict[str, Any]]:
    """
    解析 HTML 字符串，返回题单列表。
    每个元素形如 {"name": "...", "count": n, "problems_title_slugs": "...", "problems": [{title, titleSlug, url}, ...]}。
    """
    soup = BeautifulSoup(html_content, "html.parser")
    body = soup.find("body")
    if not body:
        return []

    # 当前标题栈
    headings: Dict[int, Optional[str]] = {2: None, 3: None, 4: None}
    current_level: Optional[int] = None  # 当前最深层级（2/3/4）
    pending_problems: List[Dict[str, str]] = []
    result: List[Dict[str, Any]] = []

    def finalize_current_group() -> None:
        """输出当前累积的题单。"""
        nonlocal pending_problems
        if not pending_problems:
            return

        name_parts: List[str] = []
        # 按层级拼接已有标题
        for level in (2, 3, 4):
            if (current_level or 0) >= level and headings.get(level):
                name_parts.append(headings[level])  # type: ignore[arg-type]

        group_name = " / ".join(name_parts) if name_parts else "未命名题单"

        slugs = [p.get("titleSlug", "").strip() for p in pending_problems if p.get("titleSlug")]
        slugs_joined = " ".join(slugs)

        result.append(
            {
                "name": group_name,
                "count": len(pending_problems),
                "problems_title_slugs": slugs_joined,
                "problems": pending_problems,
            }
        )
        pending_problems = []

    # 顺序遍历 body 直接子元素，保持文档流顺序
    for elem in body.children:
        tag_name = getattr(elem, "name", None)
        if not tag_name:
            continue

        if tag_name in ("h2", "h3", "h4"):
            finalize_current_group()
            text = _clean_text(elem.get_text())
            if tag_name == "h2":
                headings[2] = text
                headings[3] = None
                headings[4] = None
                current_level = 2
            elif tag_name == "h3":
                headings[3] = text
                headings[4] = None
                current_level = 3
            else:  # h4
                headings[4] = text
                current_level = 4
            continue

        if tag_name == "ul":
            problems = _collect_problems_from_ul(elem)
            if not problems:
                continue

            # 若尚未遇到任何标题，则默认归入二级标题层级
            if current_level is None:
                current_level = 2
            pending_problems.extend(problems)

    finalize_current_group()
    return result


def parse_html_file(html_path: str) -> List[Dict[str, Any]]:
    with open(html_path, "r", encoding="utf-8") as f:
        return parse_html_content(f.read())


def main() -> None:
    parser = argparse.ArgumentParser(description="解析 LeetCode 讨论页 HTML 为题单 JSON")
    parser.add_argument("html", help="HTML 文件路径，例如 discuss_html/sliding_window.html")
    parser.add_argument(
        "-o",
        "--output",
        help="输出 JSON 文件路径（默认打印到 stdout）",
    )
    args = parser.parse_args()

    if not os.path.exists(args.html):
        raise SystemExit(f"文件不存在: {args.html}")

    data = parse_html_file(args.html)
    json_str = json.dumps(data, ensure_ascii=False, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(json_str)
    else:
        print(json_str)

    # 提取所有的 name 放在一个 [] 中打印，方便复制
    names = [group["name"] for group in data]
    print("\n题单名称列表:")
    print(json.dumps(names, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
