"""
从 LeetCode 讨论页面拉取题单数据并创建 LeetCode 题单

数据来源: https://leetcode.cn/circle/discuss/
"""

import os
import sys
import requests
import json
import re
import argparse
from pathlib import Path
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from bs4 import BeautifulSoup

# 保证可以引用项目根目录下的模块
BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from leetcode_favorite import LeetCodeClient  # noqa: E402
import parse_html as html_parser  # noqa: E402


LEETCODE_DISCUSS_PRE_URL = "https://leetcode.cn/circle/discuss/"

# 本地保存目录
LOCAL_HTML_DIR = BASE_DIR / "discuss_html"
LOCAL_JSON_DIR = BASE_DIR / "discuss_json"

DISCUSSION_URL_MAP = {
    "0viNMK": {
        "filename": "sliding_window",
        "title": "滑动窗口与双指针"
    },
    "SqopEo": {
        "filename": "binary_search",
        "title": "二分算法"
    },
    "9oZFK9": {
        "filename": "monotonic_stack",
        "title": "单调栈"
    },
    "YiXPXW": {
        "filename": "grid",
        "title": "网格图"
    },
    "dHn9Vk": {
        "filename": "bitwise_operations",
        "title": "位运算"
    },
    "01LUak": {
        "filename": "graph",
        "title": "图论算法"
    },
    "tXLS3i": {
        "filename": "dynamic_programming",
        "title": "动态规划"
    },
    "mOr1u6": {
        "filename": "data_structure",
        "title": "常用数据结构"
    },
    "IYT3ss": {
        "filename": "math",
        "title": "数学算法"
    },
    "g6KTKL": {
        "filename": "greedy",
        "title": "贪心与思维"
    },
    "K0n2gO": {
        "filename": "trees",
        "title": "链表、树与回溯"
    },
    "SJFwQI": {
        "filename": "string",
        "title": "字符串"
    },
}

# 分类列表：(discuss_id, filename, title)
PROBLEM_CATEGORIES = [
    (discuss_id, info["filename"], info["title"]) 
    for discuss_id, info in DISCUSSION_URL_MAP.items()
]



def fetch_discussion_html(discuss_id: str) -> Optional[str]:
    """
    从 LeetCode 获取讨论页面的 HTML
    :param discuss_id: 讨论 ID，如 "0viNMK"
    :return: HTML 内容
    """
    url = f"{LEETCODE_DISCUSS_PRE_URL}{discuss_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    
    try:
        print(f"正在获取: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"获取讨论页面失败: {e}")
        return None


def extract_heading_and_list_elements(html_content: str) -> str:
    """
    从 HTML 中提取 h1, h2, h3, ul, li 元素
    :param html_content: 原始 HTML 内容
    :return: 提取后的精简 HTML
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 创建新的 HTML 文档
    new_soup = BeautifulSoup("<html><head><meta charset='utf-8'></head><body></body></html>", 'html.parser')
    body = new_soup.find('body')
    
    # 查找文章内容区域
    # 优先查找 'break-words' (常见于动态渲染的 LeetCode 讨论页)
    content_area = soup.find('div', class_=re.compile(r'break-words', re.I))
    if not content_area:
        content_area = soup.find('div', class_=re.compile(r'content|article|post|topic', re.I))
    if not content_area:
        content_area = soup
    
    # 提取所有 h1, h2, h3, h4, ul, ol, li 元素
    allowed_tags = ['h1', 'h2', 'h3', 'h4', 'ul', 'ol', 'li', 'a', 'p']
    
    def clone_element(element, parent):
        """递归克隆元素，只保留允许的标签; li 里只保留包含题目链接"""
        if element.name in allowed_tags:
            # 过滤掉不包含题目链接的 li 元素
            if element.name == 'li':
                has_problem_link = False
                for a_tag in element.find_all('a'):
                    href = a_tag.get('href', '')
                    if href and 'problems' in href:
                        has_problem_link = True
                        break
                if not has_problem_link:
                    return

            new_tag = new_soup.new_tag(element.name)
            # 保留 href 属性
            if element.name == 'a' and element.get('href'):
                new_tag['href'] = element.get('href')
            
            for child in element.children:
                if hasattr(child, 'name') and child.name:
                    if element.name == 'li' and child.name != 'a':
                        continue  # li 里只保留 a 标签
                    clone_element(child, new_tag)
                elif child.string:
                    if element.name != 'li':
                        # li 里不保留纯文本
                        new_tag.append(child.string.strip())
            
            if new_tag.get_text(strip=True):  # 只添加有内容的元素
                parent.append(new_tag)
    
    # 查找所有标题和列表
    for tag in content_area.find_all(['h1', 'h2', 'h3', 'h4', 'ul', 'ol']):
        clone_element(tag, body)
    
    # 使用紧凑格式避免写入时自动换行/缩进
    # return new_soup.decode(formatter="minimal")
    return str(new_soup.prettify())


def save_json_from_html_content(
    simplified_html: str,
    filename: str,
    category_index: Optional[int] = None,
    category_title: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """使用 parse_html 解析精简 HTML 并保存为 JSON。"""
    os.makedirs(LOCAL_JSON_DIR, exist_ok=True)
    data = html_parser.parse_html_content(simplified_html)

    # 在 name 前面添加序号和专题名称
    if category_index is not None and category_title:
        prefix = f"{category_index} {category_title}"
        for item in data:
            base_name = item.get("name", "")
            item["name"] = f"{prefix} / {base_name}" if base_name else prefix

    json_path = LOCAL_JSON_DIR / f"{filename}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"解析结果已保存到: {json_path}")
    return data


def fetch_and_save_discussion_html(
    discuss_id: str,
    filename: str,
    category_index: Optional[int] = None,
    category_title: Optional[str] = None,
) -> bool:
    """
    获取讨论页面 HTML 并保存到本地
    :param discuss_id: 讨论 ID
    :param filename: 保存的文件名（不含扩展名）
    :return: 是否成功
    """
    # 确保目录存在
    os.makedirs(LOCAL_HTML_DIR, exist_ok=True)
    
    # 获取 HTML
    html_content = fetch_discussion_html(discuss_id)
    if not html_content:
        return False
    
    # 提取精简内容
    simplified_html = extract_heading_and_list_elements(html_content)

    # 保存精简 HTML
    filepath = LOCAL_HTML_DIR / f"{filename}.html"
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(simplified_html)

    print(f"精简 HTML 已保存到: {filepath}")
    save_json_from_html_content(simplified_html, filename, category_index, category_title)
    return True


def fetch_all_discussions() -> None:
    """
    获取所有讨论页面并保存
    """
    print(f"\n将获取 {len(DISCUSSION_URL_MAP)} 个讨论页面...")

    success_count = 0
    for idx, (discuss_id, info) in enumerate(DISCUSSION_URL_MAP.items(), 1):
        if fetch_and_save_discussion_html(discuss_id, info["filename"], idx, info["title"]):
            success_count += 1

    print(f"\n完成: 成功 {success_count}/{len(DISCUSSION_URL_MAP)} 个")


def load_category_from_json(filename: str) -> List[Dict[str, Any]]:
    """从保存的 JSON 中加载分类信息。"""
    path = LOCAL_JSON_DIR / f"{filename}.json"
    if not path.exists():
        print(f"JSON 文件不存在: {path}")
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def create_favorite_from_category(
    client: LeetCodeClient,
    category: Dict[str, Any],
    dry_run: bool = False
) -> Optional[str]:
    """
    使用 JSON 分类数据创建题单。
    """
    favorite_name = category.get("name") or "未命名题单"
    problems: List[Dict[str, str]] = category.get("problems", [])

    if not problems:
        print(f"分类 [{favorite_name}] 没有题目，跳过")
        return None

    if dry_run:
        print(f"[试运行] 将创建题单: {favorite_name}")
        print(f"  包含 {len(problems)} 道题目:")
        for i, p in enumerate(problems[:5], 1):
            print(f"    {i}. {p.get('title', '')} ({p.get('titleSlug', '')})")
        if len(problems) > 5:
            print(f"    ... 还有 {len(problems) - 5} 道题目")
        return None

    print(f"正在创建题单: {favorite_name}")

    favorite_slug = client.create_favorite_list(favorite_name, is_public=False, description=f"题单: {favorite_name}")

    if not favorite_slug:
        print(f"创建题单失败: {favorite_name}")
        return None

    print(f"题单创建成功: {favorite_name} (slug: {favorite_slug})")

    slugs = [p.get("titleSlug") for p in problems if p.get("titleSlug")]

    batch_size = 50
    total_added = 0

    for i in range(0, len(slugs), batch_size):
        batch = slugs[i:i + batch_size]
        if client.batch_add_questions_to_favorite(favorite_slug, batch):
            total_added += len(batch)
            print(f"  已添加 {total_added}/{len(slugs)} 道题目")
        else:
            print(f"  批量添加失败，当前位置: {i}")

    print(f"完成: 共添加 {total_added} 道题目到题单 [{favorite_name}]")
    return favorite_slug


def display_available_categories():
    """显示可用的分类列表"""
    print("\n可用的题单分类:")
    print("-" * 50)
    for i, (discuss_id, filename, title) in enumerate(PROBLEM_CATEGORIES, 1):
        print(f"{i:2}. {title} ({filename})")
    print("-" * 50)



def interactive_mode(client: LeetCodeClient):
    """
    交互模式
    :param client: LeetCode 客户端
    """
    while True:
        display_available_categories()
        print("\n操作选项:")
        print("1. 获取讨论页面 HTML（单个）")
        print("2. 获取所有讨论页面 HTML")
        print("3. 创建指定分类的子题单")
        print("4. 创建所有分类的子题单")
        print("q. 退出")
        
        choice = input("\n请选择操作: ").strip().lower()
        
        if choice == 'q':
            break
        
        if choice == '1':
            # 获取单个讨论页面 HTML
            cat_input = input("\n请输入分类编号 (1-12): ").strip()
            try:
                cat_index = int(cat_input) - 1
                if 0 <= cat_index < len(PROBLEM_CATEGORIES):
                    discuss_id, filename, title = PROBLEM_CATEGORIES[cat_index]
                    fetch_and_save_discussion_html(discuss_id, filename, cat_index + 1, title)
                else:
                    print("无效的分类编号")
            except ValueError:
                print("请输入有效的数字")
                
        elif choice == '2':
            # 获取所有讨论页面 HTML
            fetch_all_discussions()
            
        elif choice == '3':
            # 创建指定分类的子题单
            cat_input = input("\n请输入分类编号 (1-12): ").strip()
            try:
                cat_index = int(cat_input) - 1
                if 0 <= cat_index < len(PROBLEM_CATEGORIES):
                    discuss_id, filename, title = PROBLEM_CATEGORIES[cat_index]

                    categories = load_category_from_json(filename)

                    if not categories:
                        print(f"未找到分类数据，请先使用选项 1 获取 HTML/JSON")
                        continue

                    print(f"\n找到 {len(categories)} 个子分类:")
                    total_problems = 0
                    for i, cat in enumerate(categories, 1):
                        probs = cat.get("problems", [])
                        total_problems += len(probs)
                        print(f"{i:3}. {cat.get('name')}")

                    confirm = input(f"\n将创建 {len(categories)} 个题单（共 {total_problems} 道题），确认？(y/n): ").strip().lower()
                    if confirm == 'y':
                        for cat in categories:
                            create_favorite_from_category(client, cat)
                else:
                    print("无效的分类编号")
            except ValueError:
                print("请输入有效的数字")

        elif choice == '4':
            # 创建所有分类的子题单
            print("\n统计所有分类的子题单...")

            all_categories = []
            for idx, (discuss_id, filename, title) in enumerate(PROBLEM_CATEGORIES):
                categories = load_category_from_json(filename)
                all_categories.extend(categories)

            if not all_categories:
                print("未找到任何分类数据，请先使用选项 2 获取所有 HTML/JSON")
                continue

            total_problems = sum(len(cat.get("problems", [])) for cat in all_categories)
            print(f"\n找到 {len(all_categories)} 个子分类，共 {total_problems} 道题")

            confirm = input(f"\n将创建 {len(all_categories)} 个题单，确认？(y/n): ").strip().lower()
            if confirm == 'y':
                for cat in all_categories:
                    create_favorite_from_category(client, cat)
                    
        else:
            print("无效的选项")


def main():
    parser = argparse.ArgumentParser(description='从 LeetCode 讨论页面导入题单数据')
    parser.add_argument('--fetch-all', action='store_true', help='获取所有讨论页面 HTML')
    parser.add_argument('--fetch', type=int, help='获取指定分类的讨论页面 HTML (1-12)')
    args = parser.parse_args()
    
    # 加载环境变量
    env_path = ROOT_DIR / '.env'
    load_dotenv(env_path)
    
    csrf_token = os.getenv('csrftoken')
    session_id = os.getenv('LEETCODE_SESSION')
    
    if args.fetch_all:
        fetch_all_discussions()
    elif args.fetch:
        if 1 <= args.fetch <= len(PROBLEM_CATEGORIES):
            discuss_id, filename, title = PROBLEM_CATEGORIES[args.fetch - 1]
            fetch_and_save_discussion_html(discuss_id, filename, args.fetch, title)
        else:
            print(f"无效的分类编号: {args.fetch}")
    else:
        if not csrf_token or not session_id:
            # 直接获取 HTML 不需要登录
            print("\n选择要获取的讨论页面:")
            print("a. 获取所有讨论页面")
            print("或输入分类编号 (1-12)")
            
            display_available_categories()
            
            fetch_input = input("\n请选择: ").strip().lower()
            
            if fetch_input == 'a':
                fetch_all_discussions()
            else:
                try:
                    cat_index = int(fetch_input) - 1
                    if 0 <= cat_index < len(PROBLEM_CATEGORIES):
                        discuss_id, filename, title = PROBLEM_CATEGORIES[cat_index]
                        fetch_and_save_discussion_html(discuss_id, filename, cat_index + 1, title)
                    else:
                        print("无效的分类编号")
                except ValueError:
                    print("请输入有效的选项")
        else:
            client = LeetCodeClient(csrf_token, session_id)
            interactive_mode(client)


if __name__ == "__main__":
    main()
