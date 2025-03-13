// ==UserScript==
// @name         LeetCode 题目 titleSlug 提取器
// @namespace    http://tampermonkey.net/
// @version      0.1
// @description  在 LeetCode 中国站点显示并提供复制页面中所有题目 titleSlug 的功能
// @author       Yi Liu
// @homepageURL  https://github.com/LiLittleCat/leetcode-tools
// @license      MIT
// @match        https://leetcode.cn/discuss/*
// @grant        none
// ==/UserScript==

(function () {
  "use strict";

  // 创建样式
  const style = document.createElement("style");
  style.textContent = `
        #leetcode-title-slug-extractor {
            position: fixed;
            top: 70px;
            right: 20px;
            width: 300px;
            max-height: 80vh;
            background-color: #fff;
            border: 1px solid #ddd;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            z-index: 9999;
            overflow: hidden;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
            transition: all 0.3s ease;
        }

        #leetcode-title-slug-extractor.collapsed {
            width: 40px;
            height: 40px;
            overflow: hidden;
        }

        #leetcode-title-slug-extractor-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 15px;
            background-color: #f3f4f5;
            border-bottom: 1px solid #ddd;
            cursor: move;
        }

        #leetcode-title-slug-extractor-title-section {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        #leetcode-title-slug-extractor-title {
            font-weight: bold;
            color: #333;
            margin: 0;
        }

        #leetcode-title-slug-extractor-github {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 4px;
            background: #24292e;
            color: #fff;
            border-radius: 4px;
            text-decoration: none;
            transition: background 0.2s;
            width: 24px;
            height: 24px;
        }

        #leetcode-title-slug-extractor-github:hover {
            background: #1a1f23;
        }

        #leetcode-title-slug-extractor-github svg {
            width: 16px;
            height: 16px;
            fill: currentColor;
        }

        #leetcode-title-slug-extractor-toggle {
            background: none;
            border: none;
            cursor: pointer;
            font-size: 18px;
            color: #555;
            padding: 0;
            width: 24px;
            height: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        #leetcode-title-slug-extractor-content {
            padding: 10px 15px;
            max-height: calc(80vh - 50px);
            overflow-y: auto;
        }

        .leetcode-title-slug-extractor-link-item {
            margin-bottom: 12px;
            padding-bottom: 12px;
            border-bottom: 1px solid #eee;
            position: relative;
        }

        .leetcode-title-slug-extractor-link-item:last-child {
            border-bottom: none;
        }

        .leetcode-title-slug-extractor-link-url {
            display: block;
            word-break: break-all;
            margin-bottom: 5px;
            color: #0077cc;
            text-decoration: none;
            font-size: 14px;
        }

        .leetcode-title-slug-extractor-link-url:hover {
            text-decoration: underline;
        }

        .leetcode-title-slug-extractor-link-text {
            display: block;
            color: #666;
            font-size: 12px;
            margin-bottom: 5px;
        }

        .leetcode-title-slug-extractor-link-copy {
            background-color: #f3f4f5;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 3px 8px;
            font-size: 12px;
            cursor: pointer;
            color: #333;
            transition: all 0.2s ease;
        }

        .leetcode-title-slug-extractor-link-copy:hover {
            background-color: #e7e8e9;
        }

        .leetcode-title-slug-extractor-link-copy.copied {
            background-color: #4caf50;
            color: white;
            border-color: #4caf50;
        }

        #leetcode-title-slug-extractor-refresh {
            margin-top: 10px;
            background-color: #f3f4f5;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 5px 10px;
            font-size: 13px;
            cursor: pointer;
            color: #333;
            width: 100%;
            transition: all 0.2s ease;
        }

        #leetcode-title-slug-extractor-refresh:hover {
            background-color: #e7e8e9;
        }

        .leetcode-title-slug-extractor-no-links {
            color: #666;
            font-style: italic;
            text-align: center;
            padding: 20px 0;
        }

        .leetcode-title-slug-extractor-link-inline {
            position: absolute;
            right: 10px;
            top: 50%;
            transform: translateY(-50%);
            background: #f0f0f0;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            color: #666;
        }
    `;
  document.head.appendChild(style);

  // 创建面板
  const panel = document.createElement("div");
  panel.id = "leetcode-title-slug-extractor";
  panel.innerHTML = `
        <div id="leetcode-title-slug-extractor-header">
            <div id="leetcode-title-slug-extractor-title-section">
                <h3 id="leetcode-title-slug-extractor-title">LeetCode 题目 titleSlug 提取器</h3>
                <a href="https://github.com/LiLittleCat/leetcode-tools" target="_blank" id="leetcode-title-slug-extractor-github">
                    <svg viewBox="0 0 16 16">
                        <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
                    </svg>
                </a>
            </div>
            <button id="leetcode-title-slug-extractor-toggle">−</button>
        </div>
        <div id="leetcode-title-slug-extractor-content"></div>
        <div class="leetcode-title-slug-extractor-resizer leetcode-title-slug-extractor-resizer-nw"></div>
        <div class="leetcode-title-slug-extractor-resizer leetcode-title-slug-extractor-resizer-ne"></div>
        <div class="leetcode-title-slug-extractor-resizer leetcode-title-slug-extractor-resizer-sw"></div>
        <div class="leetcode-title-slug-extractor-resizer leetcode-title-slug-extractor-resizer-se"></div>
    `;
  document.body.appendChild(panel);

  // 获取元素
  const toggleBtn = document.getElementById(
    "leetcode-title-slug-extractor-toggle"
  );
  const content = document.getElementById(
    "leetcode-title-slug-extractor-content"
  );
  const header = document.getElementById(
    "leetcode-title-slug-extractor-header"
  );
  const resizers = document.querySelectorAll(
    ".leetcode-title-slug-extractor-resizer"
  );

  // 切换面板显示/隐藏
  toggleBtn.addEventListener("click", () => {
    panel.classList.toggle("collapsed");
    toggleBtn.textContent = panel.classList.contains("collapsed") ? "+" : "−";
  });

  // 提取并显示链接
  function extractLinks() {
    // 直接获取页面中的所有 ul 元素
    const uls = document.body.querySelectorAll("ul");
    const ulGroups = new Map(); // 用于按ul分组存储titleSlug
    let validGroupCount = 0; // 用于跟踪有效分组数量

    if (uls.length === 0) {
      content.innerHTML =
        '<div class="leetcode-title-slug-extractor-no-links">未找到指定区域的 LeetCode 题目链接</div>';
      return;
    }

    uls.forEach((ul) => {
      const slugs = []; // 改用数组以保持顺序
      const links = ul.querySelectorAll("a");

      links.forEach((link) => {
        const href = link.getAttribute("href");
        if (
          href &&
          href !== "#" &&
          !href.startsWith("javascript:") &&
          link.href.startsWith("https://leetcode.cn/problems")
        ) {
          const titleSlug =
            link.href.split("/problems/")[1]?.split("/")[0] || "";
          const title = link.textContent.trim();
          if (titleSlug) {
            slugs.push({ title, titleSlug });
          }
        }
      });

      if (slugs.length > 0) {
        // 使用连续的分组编号
        ulGroups.set(validGroupCount, {
          links: slugs,
          element: ul,
        });
        validGroupCount++;
      }
    });

    if (ulGroups.size === 0) {
      content.innerHTML =
        '<div class="leetcode-title-slug-extractor-no-links">未找到 LeetCode 题目链接</div>';
      return;
    }

    let html = "";
    ulGroups.forEach(({ links, element }, groupIndex) => {
      html += `
        <div class="leetcode-title-slug-extractor-group">
          <div class="leetcode-title-slug-extractor-group-header">
            <div class="leetcode-title-slug-extractor-group-title-section">
              <button class="leetcode-title-slug-extractor-group-toggle" data-group="${groupIndex}">+</button>
              <span class="leetcode-title-slug-extractor-group-title">分组 ${
                groupIndex + 1
              } (${links.length})</span>
            </div>
            <div class="leetcode-title-slug-extractor-group-actions">
              <button class="leetcode-title-slug-extractor-link-locate" data-group="${groupIndex}">定位分组</button>
              <button class="leetcode-title-slug-extractor-link-copy" data-slugs='${JSON.stringify(
                links.map((s) => s.titleSlug)
              )}'>复制全部 titleSlug（空格分隔）</button>
            </div>
          </div>
          <div class="leetcode-title-slug-extractor-slugs collapsed">
            ${links
              .map(
                ({ title, titleSlug }, index) => `
              <div class="leetcode-title-slug-extractor-slug">
                <div class="leetcode-title-slug-extractor-slug-header">
                  <div class="leetcode-title-slug-extractor-title">${title}</div>
                  <button class="leetcode-title-slug-extractor-link-locate-item" data-group="${groupIndex}" data-index="${index}">定位</button>
                </div>
                <div class="leetcode-title-slug-extractor-slug-text">titleSlug: ${titleSlug}</div>
              </div>
            `
              )
              .join("")}
          </div>
        </div>
      `;
    });

    html +=
      '<button id="leetcode-title-slug-extractor-refresh">刷新链接</button>';
    content.innerHTML = html;

    // 更新复制按钮事件监听
    updateCopyButtons();

    // 添加定位按钮事件监听
    updateLocateButtons(ulGroups);

    // 添加折叠/展开按钮事件监听
    updateToggleButtons();

    // 添加刷新功能
    document
      .getElementById("leetcode-title-slug-extractor-refresh")
      .addEventListener("click", extractLinks);
  }

  // 修改样式
  const additionalStyle = document.createElement("style");
  additionalStyle.textContent = `
    #leetcode-title-slug-extractor {
      position: fixed;
      top: 70px;
      right: 20px;
      min-width: 300px;
      min-height: 200px;
      width: 500px;
      height: 600px;
      background-color: #fff;
      border: 1px solid #ddd;
      border-radius: 8px;
      box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
      z-index: 9999;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    #leetcode-title-slug-extractor-content {
      flex: 1;
      overflow-y: auto;
      padding: 10px;
    }

    #leetcode-title-slug-extractor-resizer {
      position: absolute;
      right: 0;
      bottom: 0;
      width: 15px;
      height: 15px;
      cursor: se-resize;
      background: linear-gradient(135deg, transparent 50%, #ccc 50%);
      border-radius: 0 0 8px 0;
    }

    .leetcode-title-slug-extractor-group {
      margin-bottom: 10px;
      border: 1px solid #eee;
      border-radius: 6px;
      overflow: hidden;
    }

    .leetcode-title-slug-extractor-group-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0;
      padding: 8px;
      background: #f0f0f0;
      border-radius: 4px;
      color: #333;
    }

    .leetcode-title-slug-extractor-group-title-section {
      display: flex;
      align-items: center;
      gap: 8px;
      color: #333;
    }

    .leetcode-title-slug-extractor-group-toggle {
      width: 24px;
      height: 24px;
      padding: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #fff;
      border: 1px solid #ddd;
      border-radius: 4px;
      cursor: pointer;
      font-size: 16px;
      line-height: 1;
      color: #333;
    }

    .leetcode-title-slug-extractor-group-title {
      font-weight: bold;
      color: #333;
      font-size: 13px;
    }

    .leetcode-title-slug-extractor-group-toggle:hover {
      background: #f8f8f8;
    }

    .leetcode-title-slug-extractor-slugs {
      display: flex;
      flex-direction: column;
      gap: 8px;
      transition: all 0.3s ease-in-out;
      overflow: hidden;
      padding: 0;
      margin: 0;
    }

    .leetcode-title-slug-extractor-slugs:not(.collapsed) {
      padding: 8px;
      margin-top: 8px;
      max-height: 300px;
      overflow-y: auto;
    }

    .leetcode-title-slug-extractor-slugs.collapsed {
      max-height: 0;
    }

    .leetcode-title-slug-extractor-slug {
      background: #fff;
      padding: 8px;
      border-radius: 4px;
      border: 1px solid #eee;
    }

    .leetcode-title-slug-extractor-slug-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 4px;
    }

    .leetcode-title-slug-extractor-title {
      color: #333;
      font-size: 13px;
      flex: 1;
    }

    .leetcode-title-slug-extractor-slug-text {
      font-family: monospace;
      font-size: 12px;
      color: #666;
      word-break: break-all;
    }

    .leetcode-title-slug-extractor-group-actions {
      display: flex;
      gap: 8px;
    }

    .leetcode-title-slug-extractor-link-locate,
    .leetcode-title-slug-extractor-link-copy {
      padding: 4px 12px;
      background: #f0f0f0;
      border: 1px solid #ddd;
      border-radius: 4px;
      cursor: pointer;
      font-size: 12px;
      color: #333;
    }

    .leetcode-title-slug-extractor-link-locate:hover,
    .leetcode-title-slug-extractor-link-copy:hover {
      background: #e0e0e0;
    }

    .leetcode-title-slug-extractor-link-copy.copied {
      background: #4caf50;
      color: #fff;
      border-color: #4caf50;
    }

    .leetcode-title-slug-extractor-resizer {
      position: absolute;
      width: 15px;
      height: 15px;
      background: linear-gradient(135deg, transparent 50%, #ccc 50%);
      z-index: 10000;
    }

    .leetcode-title-slug-extractor-resizer-nw {
      top: 0;
      left: 0;
      cursor: nw-resize;
      transform: rotate(135deg);
      border-radius: 8px 0 0 0;
    }

    .leetcode-title-slug-extractor-resizer-ne {
      top: 0;
      right: 0;
      cursor: ne-resize;
      transform: rotate(225deg);
      border-radius: 0 8px 0 0;
    }

    .leetcode-title-slug-extractor-resizer-sw {
      bottom: 0;
      left: 0;
      cursor: sw-resize;
      transform: rotate(45deg);
      border-radius: 0 0 0 8px;
    }

    .leetcode-title-slug-extractor-resizer-se {
      bottom: 0;
      right: 0;
      cursor: se-resize;
      transform: rotate(-45deg);
      border-radius: 0 0 8px 0;
    }

    .leetcode-title-slug-extractor-highlight-ul {
      animation: leetcode-title-slug-extractor-highlight-pulse 2s;
      background-color: rgba(255, 255, 0, 0.2);
      border-radius: 4px;
    }

    @keyframes leetcode-title-slug-extractor-highlight-pulse {
      0% {
        background-color: rgba(255, 255, 0, 0.5);
      }
      100% {
        background-color: rgba(255, 255, 0, 0);
      }
    }

    .leetcode-title-slug-extractor-link-locate-item {
      padding: 2px 8px;
      background: #f0f0f0;
      border: 1px solid #ddd;
      border-radius: 4px;
      cursor: pointer;
      font-size: 12px;
      color: #333;
      margin-left: 8px;
    }

    .leetcode-title-slug-extractor-link-locate-item:hover {
      background: #e0e0e0;
    }
  `;
  document.head.appendChild(additionalStyle);

  // 初始提取链接
  setTimeout(extractLinks, 1000); // 延迟1秒，确保页面加载完成

  // 添加拖拽功能
  let isDragging = false;
  let offsetX, offsetY;

  header.addEventListener("mousedown", (e) => {
    isDragging = true;
    offsetX = e.clientX - panel.getBoundingClientRect().left;
    offsetY = e.clientY - panel.getBoundingClientRect().top;
  });

  document.addEventListener("mousemove", (e) => {
    if (!isDragging) return;

    const x = e.clientX - offsetX;
    const y = e.clientY - offsetY;

    panel.style.left = `${x}px`;
    panel.style.top = `${y}px`;
    panel.style.right = "auto";
  });

  document.addEventListener("mouseup", () => {
    isDragging = false;
  });

  // 添加调整大小功能
  let isResizing = false;
  let currentResizer = null;

  resizers.forEach((resizer) => {
    resizer.addEventListener("mousedown", (e) => {
      isResizing = true;
      currentResizer = e.target;
      e.preventDefault();
    });
  });

  document.addEventListener("mousemove", (e) => {
    if (!isResizing) return;

    const rect = panel.getBoundingClientRect();
    let newWidth, newHeight, newLeft, newTop;

    switch (currentResizer.className.split(" ")[1]) {
      case "leetcode-title-slug-extractor-resizer-se":
        newWidth = e.clientX - rect.left;
        newHeight = e.clientY - rect.top;
        break;
      case "leetcode-title-slug-extractor-resizer-sw":
        newWidth = rect.right - e.clientX;
        newHeight = e.clientY - rect.top;
        newLeft = e.clientX;
        break;
      case "leetcode-title-slug-extractor-resizer-ne":
        newWidth = e.clientX - rect.left;
        newHeight = rect.bottom - e.clientY;
        newTop = e.clientY;
        break;
      case "leetcode-title-slug-extractor-resizer-nw":
        newWidth = rect.right - e.clientX;
        newHeight = rect.bottom - e.clientY;
        newLeft = e.clientX;
        newTop = e.clientY;
        break;
    }

    if (newWidth >= 300) {
      panel.style.width = newWidth + "px";
      if (newLeft !== undefined) {
        panel.style.left = newLeft + "px";
        panel.style.right = "auto";
      }
    }

    if (newHeight >= 200) {
      panel.style.height = newHeight + "px";
      if (newTop !== undefined) {
        panel.style.top = newTop + "px";
      }
    }
  });

  document.addEventListener("mouseup", () => {
    isResizing = false;
    currentResizer = null;
  });

  // 修复复制功能
  function updateCopyButtons() {
    document
      .querySelectorAll(".leetcode-title-slug-extractor-link-copy")
      .forEach((button) => {
        button.addEventListener("click", function () {
          const slugs = JSON.parse(this.getAttribute("data-slugs"));
          const textToCopy = slugs.join(" ");
          navigator.clipboard.writeText(textToCopy).then(() => {
            this.textContent = "已复制!";
            this.classList.add("copied");
            setTimeout(() => {
              this.textContent = "复制全部 titleSlug（空格分隔）";
              this.classList.remove("copied");
            }, 2000);
          });
        });
      });
  }

  // 修改定位功能
  function updateLocateButtons(ulGroups) {
    // 分组定位按钮
    document
      .querySelectorAll(".leetcode-title-slug-extractor-link-locate")
      .forEach((button) => {
        button.addEventListener("click", function () {
          const groupIndex = parseInt(this.getAttribute("data-group"));
          const groupData = ulGroups.get(groupIndex);
          if (groupData && groupData.element) {
            // 移除之前的高亮
            document
              .querySelectorAll(".leetcode-title-slug-extractor-highlight-ul")
              .forEach((el) => {
                el.classList.remove(
                  "leetcode-title-slug-extractor-highlight-ul"
                );
              });

            // 添加新的高亮
            groupData.element.classList.add(
              "leetcode-title-slug-extractor-highlight-ul"
            );

            // 滚动到元素位置
            groupData.element.scrollIntoView({
              behavior: "smooth",
              block: "center",
            });

            // 2秒后移除高亮
            setTimeout(() => {
              groupData.element.classList.remove(
                "leetcode-title-slug-extractor-highlight-ul"
              );
            }, 2000);
          }
        });
      });

    // 单个题目定位按钮
    document
      .querySelectorAll(".leetcode-title-slug-extractor-link-locate-item")
      .forEach((button) => {
        button.addEventListener("click", function () {
          const groupIndex = parseInt(this.getAttribute("data-group"));
          const itemIndex = parseInt(this.getAttribute("data-index"));
          const groupData = ulGroups.get(groupIndex);

          if (groupData && groupData.element) {
            const links = groupData.element.querySelectorAll("a");
            if (links[itemIndex]) {
              // 移除之前的高亮
              document
                .querySelectorAll(".leetcode-title-slug-extractor-highlight-ul")
                .forEach((el) => {
                  el.classList.remove(
                    "leetcode-title-slug-extractor-highlight-ul"
                  );
                });

              // 高亮单个链接
              const linkElement = links[itemIndex];
              linkElement.classList.add(
                "leetcode-title-slug-extractor-highlight-ul"
              );

              // 滚动到元素位置
              linkElement.scrollIntoView({
                behavior: "smooth",
                block: "center",
              });

              // 2秒后移除高亮
              setTimeout(() => {
                linkElement.classList.remove(
                  "leetcode-title-slug-extractor-highlight-ul"
                );
              }, 2000);
            }
          }
        });
      });
  }

  // 添加折叠/展开功能
  function updateToggleButtons() {
    document
      .querySelectorAll(".leetcode-title-slug-extractor-group-toggle")
      .forEach((button) => {
        button.addEventListener("click", function () {
          const group = this.closest(".leetcode-title-slug-extractor-group");
          const content = group.querySelector(
            ".leetcode-title-slug-extractor-slugs"
          );
          const isCollapsed = content.classList.contains("collapsed");

          // 更新按钮文本
          this.textContent = isCollapsed ? "−" : "+";

          // 切换内容显示状态
          content.classList.toggle("collapsed");
        });
      });
  }

  // 监听页面变化，动态更新链接
  const observer = new MutationObserver((mutations) => {
    let shouldUpdate = false;

    for (const mutation of mutations) {
      if (
        mutation.type === "childList" &&
        !mutation.target.closest("#leetcode-title-slug-extractor")
      ) {
        shouldUpdate = true;
        break;
      }
    }

    if (shouldUpdate && !panel.classList.contains("collapsed")) {
      extractLinks();
    }
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true,
  });
})();
