"""
从 LeetCode 讨论页面拉取题单数据并创建 LeetCode 题单

数据来源: https://leetcode.cn/circle/discuss/
"""

import os
import requests
import json
import re
import argparse
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
from collections import defaultdict
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from leetcode_favorite import LeetCodeClient


LEETCODE_DISCUSS_PRE_URL = "https://leetcode.cn/circle/discuss/"

# 本地保存目录
LOCAL_HTML_DIR = os.path.join(os.path.dirname(__file__), "discuss_html")

DISCUSSION_URL_MAP = {
    "0viNMK": {
        "filename": "sliding_window",
        "title": "滑动窗口与双指针"
    },
    "SqopEo": {
        "filename": "binary_search",
        "title": "二分查找"
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
        "title": "图论"
    },
    "tXLS3i": {
        "filename": "dynamic_programming",
        "title": "DP"
    },
    "mOr1u6": {
        "filename": "data_structure",
        "title": "数据结构"
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


@dataclass
class ProblemInfo:
    """题目信息"""
    title: str
    slug: str
    is_premium: bool = False


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
        """递归克隆元素，只保留允许的标签"""
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
                    clone_element(child, new_tag)
                elif child.string:
                    new_tag.append(child.string.strip())
            
            if new_tag.get_text(strip=True):  # 只添加有内容的元素
                parent.append(new_tag)
    
    # 查找所有标题和列表
    for tag in content_area.find_all(['h1', 'h2', 'h3', 'h4', 'ul', 'ol']):
        clone_element(tag, body)
    
    # 使用紧凑格式避免写入时自动换行/缩进
    return new_soup.decode(formatter="minimal")


def fetch_and_save_discussion_html(discuss_id: str, filename: str) -> bool:
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
    filepath = os.path.join(LOCAL_HTML_DIR, f"{filename}.html")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(simplified_html)
    
    print(f"精简 HTML 已保存到: {filepath}")
    return True


def fetch_all_discussions() -> None:
    """
    获取所有讨论页面并保存
    """
    print(f"\n将获取 {len(DISCUSSION_URL_MAP)} 个讨论页面...")
    
    success_count = 0
    for discuss_id, info in DISCUSSION_URL_MAP.items():
        if fetch_and_save_discussion_html(discuss_id, info["filename"]):
            success_count += 1
    
    print(f"\n完成: 成功 {success_count}/{len(DISCUSSION_URL_MAP)} 个")


def parse_section_title(title: str) -> Tuple[str, str]:
    """
    解析标题，提取序号和名称
    :param title: 原始标题，如 "一、定长...", "§1.1 基础"
    :return: (序号, 名称)，即 ("1", "定长...") 或 ("1.1", "基础")
    """
    if not title:
        return "", ""
    
    # 清理 zero-width spaces 等不可见字符
    title = title.strip()
        
    # 1. 处理 § 格式 (§1.1 基础)
    match = re.match(r'^§([\d.]+)\s*(.*)', title)
    if match:
        return match.group(1), match.group(2)
        
    # 2. 处理中文数字格式 (一、定长...)
    cn_nums = "一二三四五六七八九十"
    match = re.match(rf'^([{cn_nums}]+)、\s*(.*)', title)
    if match:
        cn_num = match.group(1)
        name = match.group(2)
        
        # 中文数字转阿拉伯数字
        val = 0
        if cn_num == '十':
            val = 10
        elif cn_num.startswith('十'):
            # 十一, 十二...
            val = 10 + ("一二三四五六七八九十".index(cn_num[1]) + 1)
        elif cn_num.endswith('十') and len(cn_num) == 2:
             # 二十, 三十...
            val = ("一二三四五六七八九十".index(cn_num[0]) + 1) * 10
        elif len(cn_num) == 1:
            val = "一二三四五六七八九十".index(cn_num) + 1
            
        if val > 0:
            return str(val), name
        
    return "", title


def compact_name_parts(name_parts: List[str], max_length: int = 30, min_part_len: int = 4) -> str:
    """
    拼接名称，并在超长时按各部分均匀缩减
    :param name_parts: 组成名称的各段
    :param max_length: 允许的最大总长度
    :param min_part_len: 每段的最小保留长度
    :return: 缩减后的名称
    """
    parts = [p.strip() for p in name_parts if p and p.strip()]
    if not parts:
        return "未分类"

    total_len = sum(len(p) for p in parts) + (len(parts) - 1)
    if total_len <= max_length:
        return "-".join(parts)

    parts = parts[:]  # copy before mutation
    # 轮询式缩减，每段尽量少砍一点，保持可读性
    while True:
        total_len = sum(len(p) for p in parts) + (len(parts) - 1)
        if total_len <= max_length:
            break

        reduced = False
        for i, p in enumerate(parts):
            if len(p) > min_part_len and total_len > max_length:
                parts[i] = p[:-1]
                total_len -= 1
                reduced = True

        if not reduced:  # 所有段都到达最小长度，最后做硬截断兜底
            joined = "-".join(parts)
            return joined[:max_length]

    return "-".join(parts)


def extract_slug_from_href(href: str) -> Optional[str]:
    """
    从链接中提取题目 slug
    :param href: 题目链接
    :return: 题目 slug
    """
    if not href or 'problems' not in href:
        return None
    
    # 匹配 /problems/xxx/ 或 /problems/xxx
    match = re.search(r'/problems/([^/?#]+)', href)
    if match:
        return match.group(1)
    return None


def parse_html_to_categories(html_filepath: str, root_title: str, category_index: int) -> List[Tuple[str, List[ProblemInfo]]]:
    """
    解析 HTML 文件，提取分类和题目信息
    :param html_filepath: HTML 文件路径
    :param root_title: 根分类标题（如 "滑动窗口与双指针"）
    :param category_index: 分类在列表中的序号（一级序号）
    :return: [(分类名称, 题目列表), ...]
    """
    if not os.path.exists(html_filepath):
        print(f"文件不存在: {html_filepath}")
        return []
    
    with open(html_filepath, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    body = soup.find('body')
    if not body:
        return []
    
    results = []
    h2_seq = 0
    h3_seq_map: Dict[int, int] = defaultdict(int)  # per h2
    h4_seq_map: Dict[Tuple[int, int], int] = defaultdict(int)  # per (h2, h3)
    
    # 遍历所有元素，构建层级结构
    current_h2 = ""  # 当前 h2 标题（如 "一、定长滑动窗口"）
    current_h2_idx = 0
    current_h2_name = ""
    current_h3 = ""  # 当前 h3 标题（如 "§1.1 基础"）
    current_h3_idx = 0
    current_h3_name = ""
    current_h4 = ""  # 当前 h4 标题
    current_h4_idx = 0
    current_h4_name = ""
    
    for element in body.children:
        if not hasattr(element, 'name') or not element.name:
            continue
        
        if element.name == 'h2':
            current_h2 = element.get_text(strip=True)
            h2_seq += 1
            _, current_h2_name = parse_section_title(current_h2)
            current_h2_idx = h2_seq  # 一级内的二级序号使用顺序
            current_h3 = ""  # 重置 h3
            current_h3_idx = 0
            current_h3_name = ""
            current_h4 = ""
            current_h4_idx = 0
            current_h4_name = ""
            h3_seq_map[current_h2_idx] = 0
            h4_seq_map[(current_h2_idx, 0)] = 0
            
        elif element.name == 'h3':
            current_h3 = element.get_text(strip=True)
            _, current_h3_name = parse_section_title(current_h3)
            h3_seq_map[current_h2_idx] += 1
            current_h3_idx = h3_seq_map[current_h2_idx]
            current_h4 = ""
            current_h4_idx = 0
            current_h4_name = ""
            h4_seq_map[(current_h2_idx, current_h3_idx)] = 0

        elif element.name == 'h4':
            current_h4 = element.get_text(strip=True)
            _, current_h4_name = parse_section_title(current_h4)
            key = (current_h2_idx, current_h3_idx)
            h4_seq_map[key] += 1
            current_h4_idx = h4_seq_map[key]
            
        elif element.name == 'ul':
            # 收集这个 ul 中的所有题目
            problems = []
            for li in element.find_all('li', recursive=False):
                a_tag = li.find('a')
                if a_tag:
                    href = a_tag.get('href', '')
                    slug = extract_slug_from_href(href)
                    if slug:
                        title = a_tag.get_text(strip=True)
                        # 检查是否是会员题
                        li_text = li.get_text()
                        is_premium = '会员题' in li_text or '🔒' in li_text
                        problems.append(ProblemInfo(
                            title=title,
                            slug=slug,
                            is_premium=is_premium
                        ))
            
            if problems:
                h2_idx = current_h2_idx
                h2_name = current_h2_name
                h3_idx = current_h3_idx
                h3_name = current_h3_name
                h4_idx = current_h4_idx
                h4_name = current_h4_name
                
                number_parts = [str(category_index)] if category_index else []
                if h2_idx:
                    number_parts.append(str(h2_idx))
                if h3_idx:
                    number_parts.append(str(h3_idx))
                if h4_idx:
                    number_parts.append(str(h4_idx))
                number_str = ".".join(number_parts) if number_parts else ""
                
                name_parts = [number_str] if number_str else []
                h2_display = None
                
                if h4_idx or h4_name:
                    # 有 h4： 序号-h2-h3-h4（若无 h3 则跳过 h3）
                    h2_display = h2_name or current_h2
                    h3_display = h3_name or current_h3
                    h4_display = h4_name or current_h4
                    if h2_display:
                        name_parts.append(h2_display)
                    if h3_display:
                        name_parts.append(h3_display)
                    if h4_display:
                        name_parts.append(h4_display)
                elif h3_idx or h3_name:
                    # 有 h3： 序号-h2-h3
                    h2_display = h2_name or current_h2
                    h3_display = h3_name or current_h3
                    if h2_display:
                        name_parts.append(h2_display)
                    if h3_display:
                        name_parts.append(h3_display)
                else:
                    # 无 h3：序号-分类-h2
                    if root_title:
                        name_parts.append(root_title)
                    h2_display = h2_name or current_h2
                    if h2_display:
                        name_parts.append(h2_display)
                
                # 拼接名称（超长时按各段均匀缩减）
                full_name = compact_name_parts(name_parts, max_length=30)
                # 如果仍然超长，优先去掉 h2 以保留更深层的标题
                if len(full_name) > 30 and h2_display:
                    name_parts_no_h2 = [p for p in name_parts if p != h2_display]
                    if name_parts_no_h2:
                        full_name = compact_name_parts(name_parts_no_h2, max_length=30)
                
                # 检查是否已存在相同名称的分类，如果有则合并
                existing = None
                for i, (name, probs) in enumerate(results):
                    if name == full_name:
                        existing = i
                        break
                
                if existing is not None:
                    # 合并题目
                    existing_slugs = {p.slug for p in results[existing][1]}
                    for p in problems:
                        if p.slug not in existing_slugs:
                            results[existing][1].append(p)
                else:
                    results.append((full_name, problems))
    
    return results


def load_category_from_html(filename: str, title: str, category_index: int) -> List[Tuple[str, List[ProblemInfo]]]:
    """
    从本地 HTML 文件加载分类信息
    :param filename: 文件名（不含扩展名）
    :param title: 分类标题
    :param category_index: 分类序号
    :return: [(分类名称, 题目列表), ...]
    """
    filepath = os.path.join(LOCAL_HTML_DIR, f"{filename}.html")
    return parse_html_to_categories(filepath, title, category_index)


def create_favorite_from_category(
    client: LeetCodeClient,
    category_name: str,
    problems: List[ProblemInfo],
    dry_run: bool = False
) -> Optional[str]:
    """
    从分类创建题单
    :param client: LeetCode 客户端
    :param category_name: 分类名称
    :param problems: 题目列表
    :param dry_run: 是否为试运行
    :return: 题单 slug
    """
    # 过滤掉会员题
    problems = [p for p in problems if not p.is_premium]
    
    if not problems:
        print(f"分类 [{category_name}] 没有非会员题目，跳过")
        return None
    
    # 构建题单名称
    favorite_name = category_name
    
    # 再次确保不超过30字符
    if len(favorite_name) > 30:
        favorite_name = favorite_name[:27] + "..."
    
    if dry_run:
        print(f"[试运行] 将创建题单: {favorite_name}")
        print(f"  包含 {len(problems)} 道题目:")
        for i, p in enumerate(problems[:5], 1):
            print(f"    {i}. {p.title} ({p.slug})")
        if len(problems) > 5:
            print(f"    ... 还有 {len(problems) - 5} 道题目")
        return None
    
    # 实际创建题单
    print(f"正在创建题单: {favorite_name}")
    
    favorite_slug = client.create_favorite_list(favorite_name, is_public=False, description=f"题单: {category_name}")
    
    if not favorite_slug:
        print(f"创建题单失败: {favorite_name}")
        return None
    
    print(f"题单创建成功: {favorite_name} (slug: {favorite_slug})")
    
    # 获取题目 slugs
    slugs = [p.slug for p in problems]
    
    # 分批添加，每批最多 50 个
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
                    fetch_and_save_discussion_html(discuss_id, filename)
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
                    
                    # 从 HTML 文件加载分类
                    categories = load_category_from_html(filename, title, cat_index + 1)
                    
                    if not categories:
                        print(f"未找到分类数据，请先使用选项 1 获取 HTML")
                        continue
                    
                    print(f"\n找到 {len(categories)} 个子分类:")
                    total_problems = 0
                    for i, (name, problems) in enumerate(categories, 1):
                        non_premium = [p for p in problems if not p.is_premium]
                        total_problems += len(non_premium)
                        print(f"{i:3}. {name}")
                    
                    confirm = input(f"\n将创建 {len(categories)} 个题单（共 {total_problems} 道题），确认？(y/n): ").strip().lower()
                    if confirm == 'y':
                        for name, problems in categories:
                            create_favorite_from_category(client, name, problems)
                else:
                    print("无效的分类编号")
            except ValueError:
                print("请输入有效的数字")
                
        elif choice == '4':
            # 创建所有分类的子题单
            print("\n统计所有分类的子题单...")
            
            all_categories = []
            for idx, (discuss_id, filename, title) in enumerate(PROBLEM_CATEGORIES):
                categories = load_category_from_html(filename, title, idx + 1)
                all_categories.extend(categories)
            
            if not all_categories:
                print("未找到任何分类数据，请先使用选项 2 获取所有 HTML")
                continue
            
            total_problems = sum(len([p for p in probs if not p.is_premium]) for _, probs in all_categories)
            print(f"\n找到 {len(all_categories)} 个子分类，共 {total_problems} 道题")
            
            confirm = input(f"\n将创建 {len(all_categories)} 个题单，确认？(y/n): ").strip().lower()
            if confirm == 'y':
                for name, problems in all_categories:
                    create_favorite_from_category(client, name, problems)
                    
        else:
            print("无效的选项")


def main():
    parser = argparse.ArgumentParser(description='从 LeetCode 讨论页面导入题单数据')
    parser.add_argument('--fetch-all', action='store_true', help='获取所有讨论页面 HTML')
    parser.add_argument('--fetch', type=int, help='获取指定分类的讨论页面 HTML (1-12)')
    args = parser.parse_args()
    
    # 加载环境变量
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    load_dotenv(env_path)
    
    csrf_token = os.getenv('csrftoken')
    session_id = os.getenv('LEETCODE_SESSION')
    
    if args.fetch_all:
        fetch_all_discussions()
    elif args.fetch:
        if 1 <= args.fetch <= len(PROBLEM_CATEGORIES):
            discuss_id, filename, title = PROBLEM_CATEGORIES[args.fetch - 1]
            fetch_and_save_discussion_html(discuss_id, filename)
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
                        fetch_and_save_discussion_html(discuss_id, filename)
                    else:
                        print("无效的分类编号")
                except ValueError:
                    print("请输入有效的选项")
        else:
            client = LeetCodeClient(csrf_token, session_id)
            interactive_mode(client)


if __name__ == "__main__":
    main()
