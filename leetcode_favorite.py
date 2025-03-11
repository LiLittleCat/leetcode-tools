import requests
import json
import os
import re
from typing import Optional, List, Dict, TypedDict
from dataclasses import dataclass
from datetime import datetime
from prettytable import PrettyTable
from dotenv import load_dotenv

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

    def create_favorite_list(self, name: str, is_public: bool = True, cover_emoji: str = "📚", description: str = "") -> Optional[str]:
        """
        创建新的题单
        :param name: 题单名称
        :param is_public: 是否公开
        :param cover_emoji: 封面表情
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
                slug = create_result.get("favoriteSlug")
                # 如果提供了封面表情，则更新题单的封面表情
                if cover_emoji and slug:
                    self.update_favorite_emoji(slug, cover_emoji)
                return slug
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

    def add_question_to_favorite(self, favorite_slug: str, question_frontend_id: str) -> bool:
        """
        向题单添加题目
        :param favorite_slug: 题单的 slug
        :param question_frontend_id: 题目的前端 ID（如 "102"）
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
            "questionId": question_frontend_id
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
            print(f"添加题目失败: {data.get('data', {}).get('addQuestionToFavorite', {}).get('error')}")
            return False

    def get_favorite_questions(self, favorite_slug: str, skip: int = 0, limit: int = 100) -> Optional[QuestionListResponse]:
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

        data = response.json()
        if data.get("data", {}).get("deleteFavoriteV2", {}).get("ok"):
            return True
        else:
            error = data.get("data", {}).get("deleteFavoriteV2", {}).get("error", "未知错误")
            print(f"删除题单失败: {error}")
            return False

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
    table.field_names = ["编号", "题单类型", "题单名称", "状态", "最后更新"]
    # 设置对齐方式
    table.align["编号"] = "r"  # 右对齐
    table.align["题单类型"] = "c"  # 居中对齐
    table.align["题单名称"] = "l"  # 左对齐
    table.align["状态"] = "c"  # 居中对齐
    table.align["最后更新"] = "l"  # 左对齐
    
    for i, favorite in enumerate(favorites, 1):
        emoji = favorite['coverEmoji'] if favorite.get('coverEmoji') else '📚'
        name = f"{emoji} {favorite['name']}"
        last_added = format_time(favorite.get('lastQuestionAddedAt'))
        status = '🔓 公开' if favorite['isPublicFavorite'] else '🔒 私有'
        favorite_type = "📝 创建" if favorite.get('is_created') else "⭐ 收藏"
        
        table.add_row([i, favorite_type, name, status, last_added])
    
    print(table)

def display_questions(questions: List[Question], total_length: int) -> None:
    """
    显示题目列表
    """
    print(f"\n题目列表 (共 {total_length} 题):")
    
    table = PrettyTable()
    table.field_names = ["编号", "题号", "状态", "难度", "题目", "通过率", "标签"]
    # 设置对齐方式
    table.align["编号"] = "r"  # 右对齐
    table.align["题号"] = "r"  # 右对齐
    table.align["状态"] = "c"  # 居中对齐
    table.align["难度"] = "c"  # 居中对齐
    table.align["题目"] = "l"  # 左对齐
    table.align["通过率"] = "r"  # 右对齐
    table.align["标签"] = "l"  # 左对齐
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
        tags = [tag['nameTranslated'] or tag['name'] for tag in question['topicTags']]
        tags_str = ', '.join(tags) if tags else "无"
        ac_rate = f"{question['acRate']:.1%}"
        
        table.add_row([
            i,
            question['questionFrontendId'],
            status,
            difficulty,
            title,
            ac_rate,
            tags_str
        ])
    
    print(table)

def get_question_ids() -> List[str]:
    """
    获取要添加的题目ID列表
    """
    print("\n请输入要添加的题目编号（如 102，多个编号用逗号分隔）:")
    ids = input().strip()
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

def display_menu() -> None:
    """
    显示操作菜单
    """
    table = PrettyTable()
    table.field_names = ["选项", "功能"]
    table.align = "l"  # 左对齐
    table.border = True  # 显示边框
    table.hrules = False  # 添加每行的分割线
    
    table.add_row(["1", "创建题单"])
    table.add_row(["2", "删除题单"])
    table.add_row(["3", "查看题单"])
    table.add_row(["4", "新增题目"])
    table.add_row(["5", "删除题目"])
    table.add_row(["6", "退出(q)"])
    
    print("\n请选择操作:")
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
        
        question_ids = get_question_ids()
        if not question_ids:
            break
            
        has_changes = False
        for qid in question_ids:
            if client.add_question_to_favorite(favorite_slug, qid):
                print(f"成功添加题目 {qid} 到题单")
                has_changes = True
            else:
                print(f"添加题目 {qid} 失败")
        
        # 如果成功添加了题目，重新获取并显示题目列表
        if has_changes:
            print("\n更新后的题目列表:")
            response = client.get_favorite_questions(favorite_slug)
            if response:
                display_questions(response['questions'], response['totalLength'])
                
        if not get_yes_no_input("\n是否继续添加题目？"):
            break

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
            choice = input("\n请输入选项编号: ").strip().lower()
            if choice == 'q' or choice == '6':
                # print("Bye, see you next time!")
                return
            
            if choice not in ['1', '2', '3', '4', '5']:
                print("无效的选项，请重新输入")
                continue
                
            # 如果没有题单且选择了需要题单的操作
            if not all_favorites and choice in ['2', '3', '4', '5']:
                print("当前没有任何题单，请先创建题单")
                continue
                
            if choice == '1':  # 创建题单
                while True:
                    favorite_name = input("\n请输入新题单名称（输入q返回）: ").strip()
                    if favorite_name.lower() == 'q':
                        break
                        
                    if not favorite_name:
                        print("题单名称不能为空，请重新输入")
                        continue
                        
                    is_public = get_yes_no_input("是否公开？")
                    emoji = input("请输入封面表情（直接回车使用默认 📚）: ").strip() or "📚"
                    
                    favorite_slug = client.create_favorite_list(favorite_name, is_public, emoji)
                    if favorite_slug:
                        print(f"\n成功创建题单: {favorite_name}")
                        if get_yes_no_input("\n是否现在添加题目？"):
                            add_questions_to_favorite(client, favorite_slug, favorite_name)
                    break
                break
                
            elif choice in ['2', '3', '4', '5']:  # 需要选择题单的操作
                # 显示题单列表
                all_favorites = get_all_favorites()
                if all_favorites:
                    display_favorites(all_favorites)
                
                while True:
                    try:
                        index_input = input("\n请选择题单编号（输入q返回）: ").strip().lower()
                        if index_input == 'q':
                            break
                            
                        index = int(index_input) - 1
                        if 0 <= index < len(all_favorites):
                            selected_favorite = all_favorites[index]
                            print(f"\n已选择题单: {selected_favorite['name']}")
                            
                            if choice == '2':  # 删除题单
                                if get_yes_no_input("确认要删除这个题单吗？"):
                                    if client.delete_favorite(selected_favorite['slug']):
                                        print(f"成功删除题单: {selected_favorite['name']}")
                                        break
                                    
                            elif choice == '3':  # 查看题单
                                while True:
                                    response = client.get_favorite_questions(selected_favorite['slug'])
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
                                    
                                    q_input = input("\n请输入要移除的题目编号（输入q返回）: ").strip().lower()
                                    if q_input == 'q':
                                        break
                                        
                                    try:
                                        q_index = int(q_input) - 1
                                        if 0 <= q_index < len(response['questions']):
                                            question = response['questions'][q_index]
                                            if client.remove_question_from_favorite(selected_favorite['slug'], question['titleSlug']):
                                                print(f"成功移除题目: {question['translatedTitle']}")
                                                # 重新获取并显示题目列表
                                                print("\n更新后的题目列表:")
                                                response = client.get_favorite_questions(selected_favorite['slug'])
                                                if response:
                                                    display_questions(response['questions'], response['totalLength'])
                                            else:
                                                print("移除题目失败")
                                        else:
                                            print("无效的题目编号")
                                    except ValueError:
                                        print("请输入有效的数字")
                                        continue
                                        
                                    if not get_yes_no_input("\n是否继续移除题目？"):
                                        break
                                break
                        else:
                            print("无效的题单编号，请重新输入")
                            continue
                    except ValueError:
                        print("请输入有效的数字")
                        continue
                break
            break

if __name__ == "__main__":
    main() 