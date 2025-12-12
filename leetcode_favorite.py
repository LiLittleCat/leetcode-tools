import requests
import json
import os
import re
from pathlib import Path
from typing import Optional, List, Dict, TypedDict, Any
from dataclasses import dataclass
from datetime import datetime
from prettytable import PrettyTable
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent


def _parse_markdown_favorite_list(content: str) -> Dict[str, List[Dict[str, str]]]:
    """Parse a markdown file with sections like:

    ## Category
    - [Name](url)
    - Name
    """
    data: Dict[str, List[Dict[str, str]]] = {}
    current_category: Optional[str] = None

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            current_category = line[3:].strip()
            if current_category:
                data.setdefault(current_category, [])
            continue

        if not current_category:
            continue

        if not line.startswith("-"):
            continue

        # - [Name](url)
        m = re.match(r"^-\s*\[(?P<name>[^\]]+)\]\((?P<url>[^\)]+)\)\s*$", line)
        if m:
            data[current_category].append({"name": m.group("name"), "url": m.group("url")})
            continue

        # - Name
        m2 = re.match(r"^-\s*(?P<name>.+?)\s*$", line)
        if m2:
            data[current_category].append({"name": m2.group("name")})

    return data


def generate_favorite_list_file(
    favorite_infos: List[Dict[str, str]],
    category_name: str,
    output_filename: str = "favorite_list.md",
    merge_mode: str = "upsert",
) -> None:
    """生成题单列表文件。

    - 同一分类覆盖（category_name 相同）
    - 不同分类追加
    - 链接使用题单第一题，并包含 envType/envId（envId=题单 slug）
    """
    output_path = BASE_DIR / output_filename

    existing_data: Dict[str, List[Dict[str, str]]] = {}
    if output_path.exists():
        try:
            existing_data = _parse_markdown_favorite_list(output_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"读取现有题单列表文件失败: {e}，将覆盖")
            existing_data = {}

    new_entries: List[Dict[str, str]] = []
    for info in favorite_infos:
        name = (info.get("name") or "").strip() or "未命名"
        slug = (info.get("slug") or "").strip()
        first_problem_slug = (info.get("first_problem_slug") or "").strip()

        entry: Dict[str, str] = {"name": name}
        if slug and first_problem_slug:
            entry["url"] = (
                f"https://leetcode.cn/problems/{first_problem_slug}/"
                f"?envType=problem-list-v2&envId={slug}"
            )
        new_entries.append(entry)

    merged_data = dict(existing_data)

    if merge_mode not in {"replace", "upsert"}:
        raise ValueError("merge_mode must be 'replace' or 'upsert'")

    if merge_mode == "replace":
        merged_data[category_name] = new_entries
    else:
        def key_for_entry(entry: Dict[str, str]) -> str:
            url = entry.get("url") or ""
            m_env = re.search(r"(?:\?|&)envId=([^&]+)", url)
            if m_env:
                return f"env:{m_env.group(1)}"
            return f"name:{entry.get('name', '').strip()}"

        existing_entries = merged_data.get(category_name, [])
        index: Dict[str, Dict[str, str]] = {}
        order: List[str] = []

        for e in existing_entries:
            k = key_for_entry(e)
            if k not in index:
                order.append(k)
            index[k] = dict(e)

        for e in new_entries:
            k = key_for_entry(e)
            if k not in index:
                order.append(k)
            index[k] = dict(e)

        merged_data[category_name] = [index[k] for k in order if k in index]

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines: List[str] = ["# LeetCode 题单列表", "", f"更新时间: {now}", ""]

    for cat in sorted(merged_data.keys()):
        lines.append(f"## {cat}")
        lines.append("")
        for entry in merged_data[cat]:
            n = entry.get("name", "未命名")
            url = entry.get("url")
            if url:
                lines.append(f"- [{n}]({url})")
            else:
                lines.append(f"- {n}")
        lines.append("")

    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"题单列表已保存到: {output_path}")

class FavoriteInfo(TypedDict):
    coverUrl: Optional[str]
    coverEmoji: Optional[str]
    coverBackgroundColor: Optional[str]
    hasCurrentQuestion: bool
    isPublicFavorite: bool
    lastQuestionAddedAt: Optional[str]
    name: str
    slug: str
    favoriteType: str

@dataclass
class FavoriteListResponse:
    favorites: List[FavoriteInfo]
    hasMore: bool
    totalLength: int

class TopicTag(TypedDict):
    name: str
    nameTranslated: str
    slug: str

class Question(TypedDict):
    difficulty: str
    id: str
    paidOnly: bool
    questionFrontendId: str
    status: Optional[str]
    title: str
    titleSlug: str
    translatedTitle: str
    isInMyFavorites: bool
    frequency: Optional[float]
    acRate: float
    topicTags: List[TopicTag]

class QuestionListResponse(TypedDict):
    questions: List[Question]
    totalLength: int
    hasMore: bool

class LeetCodeClient:
    def __init__(self, csrf_token: str, session_id: str):
        """
        初始化 LeetCode 客户端
        :param csrf_token: LeetCode 的 csrf token
        :param session_id: LeetCode 的 session id (LEETCODE_SESSION cookie)
        """
        self.base_url = "https://leetcode.cn/graphql"
        self.headers = {
            "Content-Type": "application/json",
            "X-CSRFToken": csrf_token,
            "Cookie": f"csrftoken={csrf_token}; LEETCODE_SESSION={session_id}"
        }

    def get_favorite_lists(self) -> tuple[List[FavoriteInfo], List[FavoriteInfo]]:
        """
        获取所有题单，包括自己创建的和收藏的
        :return: (自己创建的题单列表, 收藏的题单列表)
        """
        query = """
        query myFavoriteList {
            myCreatedFavoriteList {
                favorites {
                    coverUrl
                    coverEmoji
                    coverBackgroundColor
                    hasCurrentQuestion
                    isPublicFavorite
                    lastQuestionAddedAt
                    name
                    slug
                    favoriteType
                }
                hasMore
                totalLength
            }
            myCollectedFavoriteList {
                hasMore
                totalLength
                favorites {
                    coverUrl
                    coverEmoji
                    coverBackgroundColor
                    hasCurrentQuestion
                    isPublicFavorite
                    name
                    slug
                    lastQuestionAddedAt
                    favoriteType
                }
            }
        }
        """

        response = requests.post(
            self.base_url,
            headers=self.headers,
            json={"query": query, "operationName": "myFavoriteList"}
        )

        data = response.json()
        if "data" in data:
            created = data["data"]["myCreatedFavoriteList"]["favorites"]
            collected = data["data"]["myCollectedFavoriteList"]["favorites"]
            return created, collected
        else:
            print("获取题单列表失败")
            return [], []

    def create_favorite_list(self, name: str, is_public: bool = True, description: str = "") -> Optional[str]:
        """
        创建新的题单
        :param name: 题单名称
        :param is_public: 是否公开
        :param description: 题单描述
        :return: 题单的 slug，如果创建失败则返回 None
        """
        query = """
        mutation createEmptyFavorite($description: String, $favoriteType: FavoriteTypeEnum!, $isPublicFavorite: Boolean = true, $name: String!) {
            createEmptyFavorite(
                description: $description
                favoriteType: $favoriteType
                isPublicFavorite: $isPublicFavorite
                name: $name
            ) {
                ok
                error
                favoriteSlug
            }
        }
        """
        
        variables = {
            "name": name,
            "description": description,
            "favoriteType": "NORMAL",
            "isPublicFavorite": is_public
        }

        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json={
                    "query": query,
                    "variables": variables,
                    "operationName": "createEmptyFavorite"
                }
            )
            response.raise_for_status()  # 检查 HTTP 错误
            data = response.json()
            
            if not data:
                print("创建题单失败: 服务器返回空响应")
                return None
                
            if "errors" in data:
                error_msg = data["errors"][0].get("message", "未知错误")
                print(f"创建题单失败: {error_msg}")
                return None
                
            if not data.get("data"):
                print("创建题单失败: 响应中没有数据")
                return None
                
            create_result = data["data"].get("createEmptyFavorite", {})
            if create_result.get("ok"):
                return create_result.get("favoriteSlug")
            else:
                error = create_result.get("error", "未知错误")
                print(f"创建题单失败: {error}")
                return None
                
        except requests.RequestException as e:
            print(f"创建题单失败: 网络错误 - {str(e)}")
            return None
        except Exception as e:
            print(f"创建题单失败: {str(e)}")
            return None

    def update_favorite_emoji(self, favorite_slug: str, emoji: str) -> bool:
        """
        更新题单的封面表情
        :param favorite_slug: 题单的 slug
        :param emoji: 新的封面表情
        :return: 是否更新成功
        """
        query = """
        mutation updateFavoriteV2($favoriteSlug: String!, $favoriteRequest: UpdateFavoriteRequestV2!) {
            updateFavoriteV2(favoriteSlug: $favoriteSlug, favoriteRequest: $favoriteRequest) {
                ok
                error
            }
        }
        """

        variables = {
            "favoriteSlug": favorite_slug,
            "favoriteRequest": {
                "coverEmoji": emoji
            }
        }

        response = requests.post(
            self.base_url,
            headers=self.headers,
            json={
                "query": query,
                "variables": variables,
                "operationName": "updateFavoriteV2"
            }
        )

        data = response.json()
        if data.get("data", {}).get("updateFavoriteV2", {}).get("ok"):
            return True
        else:
            error = data.get("data", {}).get("updateFavoriteV2", {}).get("error", "未知错误")
            print(f"更新题单封面表情失败: {error}")
            return False

    def add_question_to_favorite(self, favorite_slug: str, question_id: str) -> bool:
        """
        向题单添加题目（使用题目的 ID）
        :param favorite_slug: 题单的 slug
        :param question_id: 题目的 ID（如 "1"），注意这不是题目的前端编号
        :return: 是否添加成功
        """
        query = """
        mutation addQuestionToFavorite($favoriteIdHash: String!, $questionId: String!) {
            addQuestionToFavorite(favoriteIdHash: $favoriteIdHash, questionId: $questionId) {
                ok
                error
                favoriteIdHash
                questionId
            }
        }
        """

        variables = {
            "favoriteIdHash": favorite_slug,
            "questionId": question_id
        }

        response = requests.post(
            self.base_url,
            headers=self.headers,
            json={
                "query": query,
                "variables": variables
            }
        )

        data = response.json()
        if data.get("data", {}).get("addQuestionToFavorite", {}).get("ok"):
            return True
        else:
            error = data.get("data", {}).get("addQuestionToFavorite", {}).get("error", "未知错误")
            print(f"添加题目失败: {error}")
            print(f"请确保输入的是题目的 ID，而不是题目的前端编号 (questionFrontendId) 或 slug")
            return False

    def batch_add_questions_to_favorite(self, favorite_slug: str, question_slugs: List[str]) -> bool:
        """
        批量向题单添加题目（使用题目的 titleSlug）
        :param favorite_slug: 题单的 slug
        :param question_slugs: 题目的 titleSlug 列表（如 ["two-sum", "add-two-numbers"]）
        :return: 是否添加成功
        """
        query = """
        mutation batchAddQuestionsToFavorite($favoriteSlug: String!, $questionSlugs: [String]!) {
            batchAddQuestionsToFavorite(
                favoriteSlug: $favoriteSlug
                questionSlugs: $questionSlugs
            ) {
                ok
                error
            }
        }
        """

        variables = {
            "favoriteSlug": favorite_slug,
            "questionSlugs": question_slugs
        }

        response = requests.post(
            self.base_url,
            headers=self.headers,
            json={
                "query": query,
                "variables": variables
            }
        )

        data = response.json()
        if data.get("data", {}).get("batchAddQuestionsToFavorite", {}).get("ok"):
            return True
        else:
            error = data.get("data", {}).get("batchAddQuestionsToFavorite", {}).get("error", "未知错误")
            print(f"批量添加题目失败: {error}")
            return False

    def get_favorite_questions(self, favorite_slug: str, skip: int = 0, limit: int = 5000) -> Optional[QuestionListResponse]:
        """
        获取题单中的题目列表
        :param favorite_slug: 题单的 slug
        :param skip: 跳过的题目数量
        :param limit: 返回的题目数量限制
        :return: 题目列表信息，如果获取失败则返回 None
        """
        query = """
        query favoriteQuestionList($favoriteSlug: String!, $filter: FavoriteQuestionFilterInput, $searchKeyword: String, 
            $filtersV2: QuestionFilterInput, $sortBy: QuestionSortByInput, $limit: Int, $skip: Int, $version: String = "v2") {
            favoriteQuestionList(
                favoriteSlug: $favoriteSlug
                filter: $filter
                filtersV2: $filtersV2
                searchKeyword: $searchKeyword
                sortBy: $sortBy
                limit: $limit
                skip: $skip
                version: $version
            ) {
                questions {
                    difficulty
                    id
                    paidOnly
                    questionFrontendId
                    status
                    title
                    titleSlug
                    translatedTitle
                    isInMyFavorites
                    frequency
                    acRate
                    topicTags {
                        name
                        nameTranslated
                        slug
                    }
                }
                totalLength
                hasMore
            }
        }
        """

        variables = {
            "skip": skip,
            "limit": limit,
            "favoriteSlug": favorite_slug,
            "filtersV2": {
                "filterCombineType": "ALL",
                "statusFilter": {"questionStatuses": [], "operator": "IS"},
                "difficultyFilter": {"difficulties": [], "operator": "IS"},
                "languageFilter": {"languageSlugs": [], "operator": "IS"},
                "topicFilter": {"topicSlugs": [], "operator": "IS"},
                "acceptanceFilter": {},
                "frequencyFilter": {},
                "lastSubmittedFilter": {},
                "publishedFilter": {},
                "companyFilter": {"companySlugs": [], "operator": "IS"},
                "positionFilter": {"positionSlugs": [], "operator": "IS"},
                "premiumFilter": {"premiumStatus": [], "operator": "IS"}
            },
            "searchKeyword": "",
            "sortBy": {"sortField": "CUSTOM", "sortOrder": "ASCENDING"}
        }

        response = requests.post(
            self.base_url,
            headers=self.headers,
            json={
                "query": query,
                "variables": variables,
                "operationName": "favoriteQuestionList"
            }
        )

        data = response.json()
        if "data" in data and "favoriteQuestionList" in data["data"]:
            return data["data"]["favoriteQuestionList"]
        else:
            print("获取题单题目列表失败")
            return None

    def remove_question_from_favorite(self, favorite_slug: str, question_slug: str) -> bool:
        """
        从题单中移除题目
        :param favorite_slug: 题单的 slug
        :param question_slug: 题目的 slug
        :return: 是否移除成功
        """
        query = """
        mutation removeQuestionFromFavoriteV2($favoriteSlug: String!, $questionSlug: String!) {
            removeQuestionFromFavoriteV2(
                favoriteSlug: $favoriteSlug
                questionSlug: $questionSlug
            ) {
                ok
                error
            }
        }
        """

        variables = {
            "favoriteSlug": favorite_slug,
            "questionSlug": question_slug
        }

        response = requests.post(
            self.base_url,
            headers=self.headers,
            json={
                "query": query,
                "variables": variables,
                "operationName": "removeQuestionFromFavoriteV2"
            }
        )

        data = response.json()
        if data.get("data", {}).get("removeQuestionFromFavoriteV2", {}).get("ok"):
            return True
        else:
            error = data.get("data", {}).get("removeQuestionFromFavoriteV2", {}).get("error", "未知错误")
            print(f"移除题目失败: {error}")
            return False

    def delete_favorite(self, favorite_slug: str) -> bool:
        """
        删除题单
        :param favorite_slug: 题单的 slug
        :return: 是否删除成功
        """
        query = """mutation deleteFavoriteV2($favoriteSlug: String!) {
  deleteFavoriteV2(favoriteSlug: $favoriteSlug) {
    ok
    error
  }
}"""

        variables = {
            "favoriteSlug": favorite_slug
        }

        response = requests.post(
            self.base_url,
            headers=self.headers,
            json={
                "query": query,
                "variables": variables,
                "operationName": "deleteFavoriteV2"
            }
        )

        try:
            data = response.json()
            
            # 检查是否存在 GraphQL 错误
            if "errors" in data:
                error_msg = data["errors"][0].get("message", "未知错误")
                print(f"删除题单失败: {error_msg}")
                return False
            
            # 检查正常响应
            result = data.get("data", {}).get("deleteFavoriteV2", {})
            if result and result.get("ok"):
                return True
            else:
                error_msg = result.get("error", "未知错误") if result else "响应数据为空"
                print(f"删除题单失败: {error_msg}")
                return False
        except Exception as e:
            print(f"删除题单失败: 解析响应时出错 - {str(e)}")
            return False

    def remove_favorite_from_collection(self, favorite_slug: str) -> bool:
        """
        取消收藏题单
        :param favorite_slug: 题单的 slug
        :return: 是否取消收藏成功
        """
        query = """
        mutation removeFavoriteFromMyCollectionV2($favoriteSlug: String!) {
            removeFavoriteFromMyCollectionV2(favoriteSlug: $favoriteSlug) {
                ok
                error
            }
        }
        """

        variables = {
            "favoriteSlug": favorite_slug
        }

        response = requests.post(
            self.base_url,
            headers=self.headers,
            json={
                "query": query,
                "variables": variables,
                "operationName": "removeFavoriteFromMyCollectionV2"
            }
        )

        try:
            data = response.json()
            
            if "errors" in data:
                error_msg = data["errors"][0].get("message", "未知错误")
                print(f"取消收藏题单失败: {error_msg}")
                return False
            
            result = data.get("data", {}).get("removeFavoriteFromMyCollectionV2", {})
            if result and result.get("ok"):
                return True
            else:
                error_msg = result.get("error", "未知错误") if result else "响应数据为空"
                print(f"取消收藏题单失败: {error_msg}")
                return False
        except Exception as e:
            print(f"取消收藏题单失败: 解析响应时出错 - {str(e)}")
            return False

    def get_public_favorite_lists(self, user_slug: str) -> Optional[List[FavoriteInfo]]:
        """
        获取指定用户的公开题单列表
        :param user_slug: 用户的 slug
        :return: 题单列表，如果获取失败则返回 None
        """
        query = """
        query createdPublicFavoriteList($userSlug: String!) {
            createdPublicFavoriteList(userSlug: $userSlug) {
                hasMore
                totalLength
                favorites {
                    slug
                    coverUrl
                    coverEmoji
                    coverBackgroundColor
                    name
                    isPublicFavorite
                    lastQuestionAddedAt
                    hasCurrentQuestion
                    viewCount
                    description
                    questionNumber
                    isDefaultList
                }
            }
        }
        """

        variables = {
            "userSlug": user_slug
        }

        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json={
                    "query": query,
                    "variables": variables,
                    "operationName": "createdPublicFavoriteList"
                }
            )
            response.raise_for_status()
            data = response.json()
            
            if "errors" in data:
                error_msg = data["errors"][0].get("message", "未知错误")
                print(f"获取公开题单列表失败: {error_msg}")
                return None
                
            result = data.get("data", {}).get("createdPublicFavoriteList", {})
            if result:
                return result.get("favorites", [])
            else:
                print("获取公开题单列表失败: 响应数据为空")
                return None
        except Exception as e:
            print(f"获取公开题单列表失败: {str(e)}")
            return None

    def add_favorite_to_collection(self, favorite_slug: str) -> bool:
        """
        收藏题单
        :param favorite_slug: 题单的 slug
        :return: 是否收藏成功
        """
        query = """
        mutation addFavoriteToMyCollectionV2($favoriteSlug: String!) {
            addFavoriteToMyCollectionV2(favoriteSlug: $favoriteSlug) {
                ok
                error
            }
        }
        """

        variables = {
            "favoriteSlug": favorite_slug
        }

        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json={
                    "query": query,
                    "variables": variables,
                    "operationName": "addFavoriteToMyCollectionV2"
                }
            )
            response.raise_for_status()
            data = response.json()
            
            if "errors" in data:
                error_msg = data["errors"][0].get("message", "未知错误")
                print(f"收藏题单失败: {error_msg}")
                return False
                
            result = data.get("data", {}).get("addFavoriteToMyCollectionV2", {})
            if result and result.get("ok"):
                return True
            else:
                error = result.get("error", "未知错误") if result else "响应数据为空"
                print(f"收藏题单失败: {error}")
                return False
        except Exception as e:
            print(f"收藏题单失败: {str(e)}")
            return False

    def fork_favorite(self, favorite_slug: str) -> Optional[str]:
        """
        复制（fork）题单
        :param favorite_slug: 题单的 slug
        :return: 新题单的 slug，如果失败则返回 None
        """
        query = """
        mutation forkFavoriteV2($favoriteSlug: String!) {
            forkFavoriteV2(favoriteSlug: $favoriteSlug) {
                ok
                error
                slug
            }
        }
        """

        variables = {
            "favoriteSlug": favorite_slug
        }

        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json={
                    "query": query,
                    "variables": variables,
                    "operationName": "forkFavoriteV2"
                }
            )
            response.raise_for_status()
            data = response.json()
            
            if "errors" in data:
                error_msg = data["errors"][0].get("message", "未知错误")
                print(f"复制题单失败: {error_msg}")
                return None
                
            result = data.get("data", {}).get("forkFavoriteV2", {})
            if result and result.get("ok"):
                return result.get("slug")
            else:
                error = result.get("error", "未知错误") if result else "响应数据为空"
                print(f"复制题单失败: {error}")
                return None
        except Exception as e:
            print(f"复制题单失败: {str(e)}")
            return None

def format_time(time_str: Optional[str]) -> str:
    """
    格式化时间字符串
    """
    if not time_str:
        return "从未"
    try:
        dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M")
    except:
        return time_str

def display_favorite_types(created_count: int, collected_count: int) -> None:
    """
    显示题单类型及数量
    """
    print("\n题单类型:")
    print("----------------------------------------")
    print(f"1. 我创建的题单 ({created_count})")
    print(f"2. 我收藏的题单 ({collected_count})")
    print("----------------------------------------")

def display_favorites(favorites: List[FavoriteInfo]) -> None:
    """
    显示题单列表
    """
    print("\n题单列表:")
    
    table = PrettyTable()
    table.field_names = ["编号", "题单类型", "题单名称", "状态", "最后更新", "slug"]
    # 设置对齐方式
    table.align["编号"] = "r"  # 右对齐
    table.align["题单类型"] = "c"  # 居中对齐
    table.align["题单名称"] = "l"  # 左对齐
    table.align["状态"] = "c"  # 居中对齐
    table.align["最后更新"] = "l"  # 左对齐
    table.align["slug"] = "l"  # 左对齐
    for i, favorite in enumerate(favorites, 1):
        emoji = favorite['coverEmoji'] if favorite.get('coverEmoji') else '📚'
        name = f"{emoji} {favorite['name']}"
        last_added = format_time(favorite.get('lastQuestionAddedAt'))
        status = '🔓 公开' if favorite['isPublicFavorite'] else '🔒 私有'
        favorite_type = "📝 创建" if favorite.get('is_created') else "⭐ 收藏"
        slug = favorite['slug']
        
        table.add_row([i, favorite_type, name, status, last_added, slug])
    
    print(table)

def display_questions(questions: List[Question], total_length: int) -> None:
    """
    显示题目列表
    """
    print(f"\n题目列表 (共 {total_length} 题):")
    
    table = PrettyTable()
    # 暂时隐藏 通过率 标签
    # table.field_names = ["编号", "题号", "状态", "难度", "题目", "slug", "通过率", "标签"]
    table.field_names = ["编号", "题号", "状态", "难度", "题目", "slug"]
    # 设置对齐方式
    table.align["编号"] = "r"  # 右对齐
    table.align["题号"] = "r"  # 右对齐
    table.align["状态"] = "c"  # 居中对齐
    table.align["难度"] = "c"  # 居中对齐
    table.align["题目"] = "l"  # 左对齐
    table.align["slug"] = "l"  # 左对齐
    # table.align["通过率"] = "r"  # 右对齐
    # table.align["标签"] = "l"  # 左对齐
    table.border = True  # 显示边框
    table.hrules = False  # 显示横向分割线
    
    difficulty_map = {
        "EASY": "🟢 简单",
        "MEDIUM": "🟡 中等",
        "HARD": "🔴 困难"
    }
    status_map = {
        "SOLVED": "✅",
        "TO_DO": "⬜",
        None: "⬜"
    }
    
    for i, question in enumerate(questions, 1):
        difficulty = difficulty_map.get(question['difficulty'], question['difficulty'])
        status = status_map.get(question.get('status'))
        paid = "🔒" if question['paidOnly'] else ""
        title = f"{paid} {question['translatedTitle']}"
        slug = question['titleSlug']
        tags = [tag['nameTranslated'] or tag['name'] for tag in question['topicTags']]
        tags_str = ', '.join(tags) if tags else "无"
        ac_rate = f"{question['acRate']:.1%}"
        
        table.add_row([
            i,
            question['questionFrontendId'],
            status,
            difficulty,
            title,
            slug,
            # ac_rate,
            # tags_str
        ])
    
    print(table)

def get_question_ids() -> List[str]:
    """
    获取要添加的题目 ID 列表
    """
    print("\n请输入要添加的题目 ID（如 1，多个 ID 用逗号分隔，输入 q 返回）:")
    print("注意：这里需要输入题目的 ID，而不是题目编号。题目 ID 可以从题目页面的 URL 中获取。")
    print("例如：题目 'Two Sum' 的 URL 是 https://leetcode.cn/problems/two-sum/，其 ID 是 1")
    ids = input().strip()
    if ids.lower() == 'q':
        return []
    return [id.strip() for id in re.split(r'[,\s]+', ids) if id.strip()]

def get_yes_no_input(prompt: str, default: bool = True) -> bool:
    """
    获取用户的是/否输入
    :param prompt: 提示信息
    :param default: 默认值，True 表示默认是，False 表示默认否
    :return: 用户的选择，是返回 True，否返回 False
    """
    default_hint = "(Y/n)" if default else "(y/N)"
    user_input = input(f"{prompt} {default_hint}: ").strip().lower()
    if user_input == 'q':
        return False
    if default:
        return user_input not in ['n', 'no']
    else:
        return user_input in ['y', 'yes']

def display_menu():
    """显示主菜单"""
    print("\n=== LeetCode 题单管理工具 ===")
    
    #     print("1️⃣ 📝 创建题单")
    # print("2️⃣ ❌ 删除题单")
    # print("3️⃣ 👀 查看题单")
    # print("4️⃣ ➕ 新增题目")
    # print("5️⃣ ➖ 删除题目")
    # print("6️⃣ ⭐ 收藏他人题单")
    # print("7️⃣ 📋 复制他人题单")
    # print("8️⃣ ⚡ 快速创建题单")
    # print("=" * 30)
    # print("请选择操作（输入 q 退出）：")

    table = PrettyTable()
    table.field_names = ["选项", "功能"]
    table.align = "l"  # 左对齐
    table.border = True  # 显示边框
    table.hrules = False  # 不显示横向分割线
    
    table.add_row(["1", "📝创建题单"])
    table.add_row(["2", "❌删除题单"])
    table.add_row(["3", "👀查看题单"])
    table.add_row(["4", "➕新增题目"])
    table.add_row(["5", "➖删除题目"])
    table.add_row(["6", "⭐收藏他人题单"])
    table.add_row(["7", "📋复制他人题单"])
    table.add_row(["8", "⚡快速创建题单"])
    
    print(table)

def add_questions_to_favorite(client: LeetCodeClient, favorite_slug: str, favorite_name: str) -> None:
    """
    向题单中添加题目
    :param client: LeetCode 客户端实例
    :param favorite_slug: 题单的 slug
    :param favorite_name: 题单的名称
    """
    while True:
        # 显示当前题目
        response = client.get_favorite_questions(favorite_slug)
        if response:
            display_questions(response['questions'], response['totalLength'])
        
        print("\n请选择添加题目的方式：")
        print("1. 使用题目 ID（如 1）")
        print("2. 使用题目 slug（如 binary-tree-level-order-traversal）")
        
        choice = input("\n请输入选项编号（输入 q 返回）: ").strip().lower()
        
        if choice == 'q':
            break
        
        if choice == "1":
            question_ids = get_question_ids()
            if not question_ids:
                continue
                
            has_changes = False
            for qid in question_ids:
                if client.add_question_to_favorite(favorite_slug, qid):
                    print(f"成功添加题目 {qid} 到题单")
                    has_changes = True
                else:
                    print(f"添加题目 {qid} 失败")
        
        elif choice == "2":
            question_slugs = get_question_slugs()
            if not question_slugs:
                continue
                
            if client.batch_add_questions_to_favorite(favorite_slug, question_slugs):
                print(f"成功批量添加 {len(question_slugs)} 个题目到题单")
                has_changes = True
            else:
                print("批量添加题目失败")
            
        else:
            print("无效的选项，请重新选择")
            continue
        
        # 如果成功添加了题目，重新获取并显示题目列表
        if has_changes:
            print("\n更新后的题目列表:")
            response = client.get_favorite_questions(favorite_slug)
            if response:
                display_questions(response['questions'], response['totalLength'])
                
        if not get_yes_no_input("\n是否继续添加题目？"):
            break

def get_question_slugs() -> List[str]:
    """
    获取要添加的题目 slug 列表
    """
    print("\n请输入要添加的题目 slug（如 two-sum，多个 slug 用逗号分隔，输入 q 返回）:")
    slugs = input().strip()
    if slugs.lower() == 'q':
        return []
    return [slug.strip() for slug in re.split(r'[,\s]+', slugs) if slug.strip()]

def delete_favorite_list(client: LeetCodeClient, favorite: dict, is_batch: bool = False) -> bool:
    """
    删除题单或取消收藏
    :param client: LeetCode 客户端实例
    :param favorite: 题单信息
    :param is_batch: 是否为批量操作
    :return: 操作是否成功
    """
    if not favorite['is_created']:  # 收藏的题单
        if not is_batch:
            print("\n这是一个收藏的题单，将执行取消收藏操作")
            if not get_yes_no_input("确认要取消收藏这个题单吗？"):
                return False
        if client.remove_favorite_from_collection(favorite['slug']):
            print(f"成功取消收藏题单: {favorite['name']}")
            return True
    else:  # 自己创建的题单
        if not is_batch:
            if not get_yes_no_input("确认要删除这个题单吗？"):
                return False
        if client.delete_favorite(favorite['slug']):
            print(f"成功删除题单: {favorite['name']}")
            return True
    return False

def display_public_favorites(favorites: List[FavoriteInfo]) -> None:
    """
    显示用户的公开题单列表
    """
    print("\n公开题单列表:")
    
    table = PrettyTable()
    table.field_names = ["编号", "题单名称", "题目数量", "查看次数", "最后更新", "slug"]
    # 设置对齐方式
    table.align["编号"] = "r"  # 右对齐
    table.align["题单名称"] = "l"  # 左对齐
    table.align["题目数量"] = "r"  # 右对齐
    table.align["查看次数"] = "r"  # 右对齐
    table.align["最后更新"] = "l"  # 左对齐
    table.align["slug"] = "l"  # 左对齐
    
    for i, favorite in enumerate(favorites, 1):
        emoji = favorite.get('coverEmoji', '📚')
        name = f"{emoji} {favorite['name']}"
        last_added = format_time(favorite.get('lastQuestionAddedAt'))
        question_count = favorite.get('questionNumber', 0)
        view_count = favorite.get('viewCount', 0)
        slug = favorite['slug']
        
        table.add_row([i, name, question_count, view_count, last_added, slug])
    
    print(table)

def view_and_operate_public_favorites(client: LeetCodeClient, user_slug: str, operation_type: str) -> None:
    """
    查看并操作用户的公开题单
    :param client: LeetCode 客户端实例
    :param user_slug: 用户的 slug
    :param operation_type: 操作类型，'collect' 表示收藏，'fork' 表示复制
    """
    public_favorites = client.get_public_favorite_lists(user_slug)
    if not public_favorites:
        return
        
    while True:
        display_public_favorites(public_favorites)
        print("\n请选择操作：")
        print("1. 查看题单内容")
        print(f"2. {'收藏' if operation_type == 'collect' else '复制'}题单")
        
        choice = input("\n请输入选项编号（输入 q 返回）: ").strip().lower()
        
        if choice == 'q':
            break
            
        if choice == "1":  # 查看题单内容
            while True:
                try:
                    index_input = input("\n请输入要查看的题单编号（输入 q 返回）: ").strip().lower()
                    if index_input == 'q':
                        break
                        
                    index = int(index_input) - 1
                    if 0 <= index < len(public_favorites):
                        selected_favorite = public_favorites[index]
                        print(f"\n已选择题单: {selected_favorite['name']}")
                        
                        response = client.get_favorite_questions(selected_favorite['slug'])
                        if not response or not response['questions']:
                            print("题单中没有题目")
                            continue
                            
                        display_questions(response['questions'], response['totalLength'])
                        
                        if response['hasMore']:
                            if get_yes_no_input("\n还有更多题目，是否继续查看？"):
                                skip = len(response['questions'])
                                response = client.get_favorite_questions(selected_favorite['slug'], skip=skip)
                                if not response:
                                    break
                        input("\n按回车键返回...")
                        break
                    else:
                        print("无效的题单编号，请重新输入")
                except ValueError:
                    print("请输入有效的数字")
                    continue
                
        elif choice == "2":  # 收藏或复制题单
            while True:
                try:
                    index_input = input(f"\n请输入要{'收藏' if operation_type == 'collect' else '复制'}的题单编号（输入 q 返回）: ").strip().lower()
                    if index_input == 'q':
                        break
                        
                    index = int(index_input) - 1
                    if 0 <= index < len(public_favorites):
                        selected_favorite = public_favorites[index]
                        print(f"\n已选择题单: {selected_favorite['name']}")
                        
                        # 添加二次确认
                        if not get_yes_no_input(f"确认要{'收藏' if operation_type == 'collect' else '复制'}这个题单吗？"):
                            continue
                        
                        if operation_type == 'collect':
                            if client.add_favorite_to_collection(selected_favorite['slug']):
                                print("成功收藏题单")
                                break
                        else:  # fork
                            new_slug = client.fork_favorite(selected_favorite['slug'])
                            if new_slug:
                                print(f"成功复制题单，新题单的 slug 为: {new_slug}")
                                # 写出题单名称 + 链接（复制后的题单名仍使用原名）
                                first_problem_slug = ""
                                resp = client.get_favorite_questions(new_slug)
                                if resp and resp.get('questions'):
                                    first_problem_slug = resp['questions'][0].get('titleSlug', '')
                                generate_favorite_list_file(
                                    [{"name": selected_favorite['name'], "slug": new_slug, "first_problem_slug": first_problem_slug}],
                                    category_name="复制题单",
                                    merge_mode="upsert",
                                )
                                break
                    else:
                        print("无效的题单编号，请重新输入")
                except ValueError:
                    print("请输入有效的数字")
                    continue
        else:
            print("无效的选项，请重新输入")

def parse_quick_create_input(input_text: str) -> tuple[str, List[str]]:
    """
    解析快速创建题单的输入
    :param input_text: 输入文本，格式为：标题\n题目1 题目2 题目3...
    :return: (标题, 题目列表)
    """
    lines = [line.strip() for line in input_text.strip().split('\n')]
    if len(lines) < 2:
        return "", []
    return lines[0], lines[1].split()

def quick_create_favorite(client: LeetCodeClient) -> None:
    """
    快速创建题单
    :param client: LeetCode 客户端实例
    """
    print("\n请输入题单信息，格式如下（每项用回车分隔）：")
    print("第1行：题单标题")
    print("第2行：题目的 titleslug（多个题目用空格分隔）")
    print("第3行：q 结束标志")
    print("\n示例：")
    print("滑动窗口经典题目")
    print("longest-substring-without-repeating-characters minimum-window-substring sliding-window-maximum")
    print("q")
    print("\n请输入（直接输入 q 取消创建）：")
    
    # 收集所有输入行直到遇到单独的 'q'
    lines = []
    while True:
        line = input().strip()
        if line.lower() == 'q':
            if not lines:  # 如果还没有输入任何内容就输入 q，则返回
                return
            break
        lines.append(line)
    
    input_text = '\n'.join(lines)
    title, slugs = parse_quick_create_input(input_text)
    
    if not title:
        print("错误：标题不能为空")
        return
        
    if not slugs:
        print("错误：至少需要输入一个题目")
        return
        
    # 创建题单（使用空描述）
    favorite_slug = client.create_favorite_list(title, True, "")
    if not favorite_slug:
        return
        
    print(f"\n成功创建题单: {title}")
    
    # 批量添加题目
    if client.batch_add_questions_to_favorite(favorite_slug, slugs):
        print(f"成功批量添加 {len(slugs)} 个题目到题单")
        # 写出题单名称 + 链接（使用第一题）
        first_problem_slug = slugs[0] if slugs else ""
        generate_favorite_list_file(
            [{"name": title, "slug": favorite_slug, "first_problem_slug": first_problem_slug}],
            category_name="快速创建题单",
            merge_mode="upsert",
        )
        # 显示题单内容
        response = client.get_favorite_questions(favorite_slug)
        if response:
            display_questions(response['questions'], response['totalLength'])
    else:
        print("批量添加题目失败")


def export_all_favorites_to_md(client: LeetCodeClient, all_favorites: List[dict]) -> None:
    """遍历所有题单，写入 favorite_list.md。

    - 覆盖分类：我创建的题单 / 我收藏的题单
    - 其它分类内容保留
    """
    created_infos: List[Dict[str, str]] = []
    collected_infos: List[Dict[str, str]] = []

    total = len(all_favorites)
    for idx, fav in enumerate(all_favorites, 1):
        slug = (fav.get('slug') or '').strip()
        name = (fav.get('name') or '').strip() or '未命名'

        first_problem_slug = ""
        if slug:
            try:
                resp = client.get_favorite_questions(slug, skip=0, limit=1)
                if resp and resp.get('questions'):
                    first_problem_slug = resp['questions'][0].get('titleSlug', '')
            except Exception as e:
                print(f"获取题单第一题失败 ({idx}/{total}) {name}: {e}")

        info = {"name": name, "slug": slug, "first_problem_slug": first_problem_slug}
        if fav.get('is_created'):
            created_infos.append(info)
        else:
            collected_infos.append(info)

    # 覆盖两个分类段，保留文件中的其它分类
    generate_favorite_list_file(created_infos, category_name="我创建的题单", merge_mode="replace")
    generate_favorite_list_file(collected_infos, category_name="我收藏的题单", merge_mode="replace")

def main():
    # 加载 .env 文件中的配置
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    load_dotenv(env_path)
    
    # 从环境变量中获取配置
    csrf_token = os.getenv('csrftoken')
    session_id = os.getenv('LEETCODE_SESSION')
    
    if not csrf_token or not session_id:
        print("\n错误：请在 .env 文件中配置以下信息：")
        print("csrftoken=你的csrftoken")
        print("LEETCODE_SESSION=你的LEETCODE_SESSION")
        print("\n这些信息可以从浏览器的 Cookie 中获取")
        return

    client = LeetCodeClient(csrf_token, session_id)

    def get_all_favorites():
        """获取所有题单列表"""
        created_favorites, collected_favorites = client.get_favorite_lists()
        all_favorites = []
        for favorite in created_favorites:
            favorite['is_created'] = True
            all_favorites.append(favorite)
        for favorite in collected_favorites:
            favorite['is_created'] = False
            all_favorites.append(favorite)
        return all_favorites

    while True:
        # 获取并显示题单列表
        all_favorites = get_all_favorites()
        if all_favorites:
            display_favorites(all_favorites)
        else:
            print("\n当前没有任何题单")
        
        display_menu()
        
        while True:
            choice = input("\n请输入选项编号（输入 q 退出）: ").strip().lower()
            if choice == 'q':
                return
            
            if choice not in ['1', '2', '3', '4', '5', '6', '7', '8']:
                print("无效的选项，请重新输入")
                continue
                
            # 如果没有题单且选择了需要题单的操作
            if not all_favorites and choice in ['2', '3', '4', '5', '6', '7', '8']:
                print("当前没有任何题单，请先创建题单")
                continue
                
            if choice == '1':  # 创建题单
                while True:
                    favorite_name = input("\n请输入新题单名称（输入 q 返回）: ").strip()
                    if favorite_name.lower() == 'q':
                        break
                        
                    if not favorite_name:
                        print("题单名称不能为空，请重新输入")
                        continue
                        
                    is_public = get_yes_no_input("是否公开？")

                    description = input("\n请输入题单描述（输入 q 返回）: ").strip()    
                    if description.lower() == 'q':
                        break
                    
                    favorite_slug = client.create_favorite_list(favorite_name, is_public, description)
                    if favorite_slug:
                        print(f"\n成功创建题单: {favorite_name}")
                        first_problem_slug = ""
                        if get_yes_no_input("\n是否现在添加题目？"):
                            add_questions_to_favorite(client, favorite_slug, favorite_name)
                            # 添加后再读取题单内容，取第一题 slug
                            resp = client.get_favorite_questions(favorite_slug)
                            if resp and resp.get('questions'):
                                first_problem_slug = resp['questions'][0].get('titleSlug', '')

                        # 写出题单名称 + 链接（若题单暂时无题目，则只写名称）
                        generate_favorite_list_file(
                            [{"name": favorite_name, "slug": favorite_slug, "first_problem_slug": first_problem_slug}],
                            category_name="创建题单",
                            merge_mode="upsert",
                        )
                    break
                break

            elif choice == '2':
                # 显示题单列表
                all_favorites = get_all_favorites()
                if all_favorites:
                    display_favorites(all_favorites)

                while True:
                    try:
                        index_input = input("\n请输入要删除的题单编号（输入 q 返回，输入 a 删除所有题单）: ").strip().lower()
                        if index_input == 'q':
                            break
                            
                        if index_input == 'a':  # 批量删除
                            if get_yes_no_input("确认要删除/取消收藏所有题单吗？"):
                                success_count = 0
                                fail_count = 0
                                for fav in all_favorites:
                                    if delete_favorite_list(client, fav, True):
                                        success_count += 1
                                    else:
                                        fail_count += 1
                                print(f"\n批量删除完成，成功：{success_count} 个，失败：{fail_count} 个")
                                break
                            continue
                            
                        # 删除单个题单
                        index = int(index_input) - 1
                        if 0 <= index < len(all_favorites):
                            selected_favorite = all_favorites[index]
                            print(f"\n已选择题单: {selected_favorite['name']}")
                            if delete_favorite_list(client, selected_favorite):
                                break
                        else:
                            print("无效的题单编号，请重新输入")
                    except ValueError:
                        print("请输入有效的数字")
                        continue
                break

            elif choice in ['3', '4', '5']:  # 需要选择题单的操作
                # 显示题单列表
                all_favorites = get_all_favorites()
                if all_favorites:
                    display_favorites(all_favorites)

                # 选 3（查看题单）时，先遍历导出所有题单到 md
                if choice == '3' and all_favorites:
                    print("\n正在导出所有题单到 favorite_list.md（会遍历每个题单取第一题）...")
                    export_all_favorites_to_md(client, all_favorites)
                
                while True:
                    try:
                        index_input = input("\n请选择题单编号（输入 q 返回）: ").strip().lower()
                        if index_input == 'q':
                            break
                            
                        index = int(index_input) - 1
                        if 0 <= index < len(all_favorites):
                            selected_favorite = all_favorites[index]
                            print(f"\n已选择题单: {selected_favorite['name']}")

                            if choice == '3':  # 查看题单
                                while True:
                                    response = client.get_favorite_questions(selected_favorite['slug'])
                                    first_problem_slug = ""
                                    if response and response.get('questions'):
                                        first_problem_slug = response['questions'][0].get('titleSlug', '')

                                    category_name = "我创建的题单" if selected_favorite.get('is_created') else "我收藏的题单"
                                    generate_favorite_list_file(
                                        [{
                                            "name": selected_favorite['name'],
                                            "slug": selected_favorite['slug'],
                                            "first_problem_slug": first_problem_slug,
                                        }],
                                        category_name=category_name,
                                        merge_mode="upsert",
                                    )

                                    if not response or not response['questions']:
                                        print("题单中没有题目")
                                        break
                                        
                                    display_questions(response['questions'], response['totalLength'])
                                    
                                    if response['hasMore']:
                                        if get_yes_no_input("\n还有更多题目，是否继续查看？"):
                                            skip = len(response['questions'])
                                            response = client.get_favorite_questions(selected_favorite['slug'], skip=skip)
                                            if not response:
                                                break
                                        else:
                                            break
                                    else:
                                        input("\n按回车键返回...")
                                        break
                                break
                                    
                            elif choice == '4':  # 新增题目
                                add_questions_to_favorite(client, selected_favorite['slug'], selected_favorite['name'])
                                break
                                
                            elif choice == '5':  # 删除题目
                                while True:
                                    response = client.get_favorite_questions(selected_favorite['slug'])
                                    if not response or not response['questions']:
                                        print("题单中没有题目")
                                        break
                                        
                                    display_questions(response['questions'], response['totalLength'])
                                    
                                    q_input = input("\n请输入要删除的题目编号（输入 q 返回，输入 a 删除所有题目）: ").strip().lower()
                                    if q_input == 'q':
                                        break
                                        
                                    if q_input == 'a':
                                        if get_yes_no_input("确认要删除所有题目吗？"):
                                            success_count = 0
                                            fail_count = 0
                                            for question in response['questions']:
                                                if client.remove_question_from_favorite(selected_favorite['slug'], question['titleSlug']):
                                                    print(f"成功删除题目: {question['translatedTitle']}")
                                                    success_count += 1
                                                else:
                                                    print(f"删除题目失败: {question['translatedTitle']}")
                                                    fail_count += 1
                                            print(f"\n批量删除完成，成功：{success_count} 个，失败：{fail_count} 个")
                                            # 重新获取并显示题目列表
                                            print("\n更新后的题目列表:")
                                            response = client.get_favorite_questions(selected_favorite['slug'])
                                            if response:
                                                display_questions(response['questions'], response['totalLength'])
                                            break
                                        continue
                                        
                                    try:
                                        q_index = int(q_input) - 1
                                        if 0 <= q_index < len(response['questions']):
                                            question = response['questions'][q_index]
                                            if client.remove_question_from_favorite(selected_favorite['slug'], question['titleSlug']):
                                                print(f"成功删除题目: {question['questionFrontendId']} {question['translatedTitle']}")
                                                # 重新获取并显示题目列表
                                                print("\n更新后的题目列表:")
                                                response = client.get_favorite_questions(selected_favorite['slug'])
                                                if response:
                                                    display_questions(response['questions'], response['totalLength'])
                                            else:
                                                print("删除题目失败")
                                        else:
                                            print("无效的题目编号")
                                    except ValueError:
                                        print("请输入有效的数字")
                                        continue
                                        
                                    if not get_yes_no_input("\n是否继续删除题目？"):
                                        break
                                break
                        else:
                            print("无效的题单编号，请重新输入")
                            continue
                    except ValueError:
                        print("请输入有效的数字")
                        continue
                break

            elif choice == '6':  # 收藏他人题单
                user_slug = input("\n请输入用户名: ").strip()
                if not user_slug:
                    print("用户名不能为空")
                    continue
                
                view_and_operate_public_favorites(client, user_slug, 'collect')
                break

            elif choice == '7':  # 复制他人题单
                user_slug = input("\n请输入用户名: ").strip()
                if not user_slug:
                    print("用户名不能为空")
                    continue
                
                view_and_operate_public_favorites(client, user_slug, 'fork')
                break

            elif choice == '8':  # 快速创建题单
                quick_create_favorite(client)
                break

            break

if __name__ == "__main__":
    main() 