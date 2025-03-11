# LeetCode 题单管理工具

这是一个用于管理 LeetCode（力扣）题单的命令行工具。通过这个工具，你可以方便地创建、查看、编辑和删除你的 LeetCode 题单。

## 功能特点

- 📝 创建新的题单（支持公开/私有设置）
- 👀 查看所有题单列表（包括自己创建的和收藏的）
- ➕ 向题单添加题目（支持单个/批量添加）
- ➖ 从题单移除题目（支持单个/批量删除）
- 🗑️ 删除题单（支持批量操作，带成功/失败统计）
- ⭐ 收藏他人题单（支持查看内容和二次确认）
- 📋 复制他人题单（支持查看内容和二次确认）
- 📊 以表格形式展示题目信息（包括难度、状态、题号等）

## 安装步骤

1. 克隆仓库：

```bash
git clone https://github.com/LiLittleCat/leetcode-tools.git
cd leetcode-tools
```

2. (可选) 创建并激活虚拟环境：

```bash
# 创建虚拟环境
python -m venv .venv

# 在 Linux/macOS 上激活虚拟环境
source .venv/bin/activate

# 在 Windows 上激活虚拟环境
# .venv\Scripts\activate
```

3. 安装依赖：

```bash
pip install -r requirements.txt
```

4. 配置环境变量：

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

   - 1️⃣ 📝 创建题单
   - 2️⃣ 🗑️ 删除题单
   - 3️⃣ 👀 查看题单
   - 4️⃣ ➕ 新增题目
   - 5️⃣ ➖ 删除题目
   - 6️⃣ ⭐ 收藏他人题单
   - 7️⃣ 📋 复制他人题单

## 获取 Cookie 信息

1. 登录 [LeetCode 中文站](https://leetcode.cn)
2. 打开浏览器开发者工具（F12）
3. 切换到 Application 标签页
4. 在左侧边栏找到 Storage -> Cookies -> https://leetcode.cn
5. 在右侧列表中找到并复制以下值：
   - `csrftoken`
   - `LEETCODE_SESSION`

## 注意事项

- ❗⚠️ 页面上的题号和题目的 id 可能不一致，建议使用 title-slug 来添加题目。

  如果是从讨论里获取的题单，如 [分享丨【题单】滑动窗口与双指针（定长/不定长/单序列/双序列/三指针/分组循环）- 讨论 - 力扣（LeetCode）](https://leetcode.cn/discuss/post/3578981/ti-dan-hua-dong-chuang-kou-ding-chang-bu-rzz7)，推荐使用浏览器脚本 [leetcode_title_slug_extractor.user.js](https://github.com/LiLittleCat/leetcode-tools/blob/main/leetcode_title_slug_extractor.user.js) 来快速获取题目的 title-slug：

  1. 安装 Tampermonkey 浏览器扩展
  2. 将 `leetcode_title_slug_extractor.user.js` 导入到 Tampermonkey
  3. 访问 LeetCode 中文站的题单讨论页面
  4. 页面右上角会出现一个浮动面板，显示当前页面所有题目的 title-slug
  5. 可以通过面板快速复制单个或整组题目的 title-slug
  6. 支持定位功能，点击"定位"按钮可以快速找到对应的题目位置

- 请妥善保管你的 Cookie 信息，不要分享给他人
- Cookie 可能会定期失效，需要重新获取
- 建议定期备份重要的题单信息

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License
