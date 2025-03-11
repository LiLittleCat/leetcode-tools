# LeetCode 题单管理工具

这是一个用于管理 LeetCode（力扣）题单的命令行工具。通过这个工具，你可以方便地创建、查看、编辑和删除你的 LeetCode 题单。

## 功能特点

- 📝 创建新的题单（支持公开/私有设置）
- 👀 查看所有题单列表（包括自己创建的和收藏的）
- ➕ 向题单添加题目
- ➖ 从题单移除题目
- 🗑️ 删除题单
- 📊 以表格形式展示题目信息（包括难度、通过率、标签等）

## 安装步骤

1. 克隆仓库：

```bash
git clone https://github.com/LiLittleCat/leetcode-tools.git
cd leetcode-tools
```

2. 安装依赖：

```bash
pip install -r requirements.txt
```

3. 配置环境变量：

   - 复制 `.env.example` 文件并重命名为 `.env`

   ```bash
   cp .env.example .env
   ```

   - 从浏览器中获取 LeetCode 的 Cookie 信息
   - 在 `.env` 文件中填入你的 `csrftoken` 和 `LEETCODE_SESSION`

## 使用说明

1. 运行程序：

```bash
python leetcode_favorite.py
```

2. 主菜单选项：
   - 1️ 📝 创建题单
   - 2️ 🗑️ 删除题单
   - 3️ 👀 查看题单
   - 4️ ➕ 新增题目
   - 5️ ➖ 删除题目
   - 6️ ❌ 退出(q)

## 获取 Cookie 信息

1. 登录 [LeetCode 中文站](https://leetcode.cn)
2. 打开浏览器开发者工具（F12）
3. 切换到 Application 标签页
4. 在左侧边栏找到 Storage -> Cookies -> https://leetcode.cn
5. 在右侧列表中找到并复制以下值：
   - `csrftoken`
   - `LEETCODE_SESSION`

## 注意事项

- 请妥善保管你的 Cookie 信息，不要分享给他人
- Cookie 可能会定期失效，需要重新获取
- 建议定期备份重要的题单信息

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License
