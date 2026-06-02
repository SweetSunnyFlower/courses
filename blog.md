# 如何新建一个教程

下面以新增一个教程目录为例，说明从创建文件到接入 VitePress 的完整步骤。

## 1. 确定教程分类和目录

先决定教程属于哪个分类：

- Go：`courses/go/`
- PHP / Laravel：`courses/php/`
- 掘金小册：`courses/juejin/`
- 其他分类：可以在 `courses/` 下新建目录

例如新增一本掘金小册：

```text
courses/juejin/example-course/
```

## 2. 创建教程目录和文章

每个教程目录建议包含：

```text
courses/juejin/example-course/
  index.md
  01. 第一篇文章.md
  02. 第二篇文章.md
  assets/
```

说明：

- `index.md` 是教程目录页，列出所有文章链接。
- 每篇文章一个 `.md` 文件。
- 图片放在当前教程目录下的 `assets/` 中。
- 文件名可以使用中文，但目录页链接里的空格需要写成 `%20`。

例如：

```md
# 示例教程

- [第一篇文章](./01.%20第一篇文章.md)
- [第二篇文章](./02.%20第二篇文章.md)
```

## 3. 文章 Markdown 格式

文章文件建议格式：

```md
# 第一篇文章

原文链接：https://example.com/article/1

正文内容……

![图片说明](assets/01-01.png)
```

注意：

- 图片路径使用相对路径，例如 `assets/xxx.png`。
- 如果正文里有 Go 模板、Blade、Vue 等 `{{ ... }}` 语法，当前 VitePress 配置会自动转义，避免被 Vue 解析。
- 代码块语言尽量使用 VitePress/Shiki 支持的语言，例如 `go`、`php`、`python`、`javascript`、`typescript`、`dart`、`bash`、`json`、`yaml`、`txt`。

## 4. 更新分类页

如果教程属于已有分类，需要更新对应分类页。

例如掘金小册分类页：

```text
courses/juejin/index.md
```

在 `hero.actions` 和 `features` 中加入新教程入口：

```yaml
    - theme: alt
      text: 示例教程
      link: /courses/juejin/example-course/
```

```yaml
  - title: 示例教程
    details: 示例教程说明
    link: /courses/juejin/example-course/
```

## 5. 更新首页课程数量

如果新增教程后分类课程数变化，需要更新首页：

```text
index.md
```

例如掘金小册从 5 门变成 6 门：

```yaml
  - title: 掘金小册
    details: 6 门课程
    link: /courses/juejin/
```

## 6. 更新 VitePress 导航和侧边栏

需要修改：

```text
.vitepress/config.mts
```

### 6.1 更新顶部导航

例如新增掘金小册，在 `juejinNav` 中添加：

```ts
{ text: '示例教程', link: '/courses/juejin/example-course/' },
```

### 6.2 更新分类侧边栏

在 `courseSidebars['/courses/juejin/']` 中添加：

```ts
{ text: '示例教程', link: '/courses/juejin/example-course/' },
```

### 6.3 新增教程自己的侧边栏

为教程目录新增一个 sidebar key：

```ts
'/courses/juejin/example-course/': [
  { text: '示例教程', link: '/courses/juejin/example-course/' },
  {
    text: '章节',
    collapsed: false,
    items: [
      { text: '第一篇文章', link: '/courses/juejin/example-course/01.%20第一篇文章' },
      { text: '第二篇文章', link: '/courses/juejin/example-course/02.%20第二篇文章' },
    ],
  },
],
```

注意：

- sidebar 里的链接不要带 `.md` 后缀。
- URL 里的空格需要写成 `%20`。
- 中文、标点可以 URL 编码，也可以让脚本生成，避免手写错误。

## 7. 检查本地目录页链接

教程目录页 `index.md` 里的本地 Markdown 链接建议统一为：

```md
- [文章标题](./01.%20文章标题.md)
```

规则：

- 使用 `./` 开头。
- 保留 `.md` 后缀。
- 文件名里的空格写成 `%20`。

## 8. 运行构建验证

完成后运行：

```bash
npm run docs:build
```

如果构建成功，说明 VitePress 配置和 Markdown 渲染基本没有问题。

常见问题：

- `The language 'xxx' is not loaded`：代码块语言不支持，改成 `txt` 或正确语言名。
- `Error parsing JavaScript expression`：通常是 Markdown 里有未转义的 `{{ ... }}`，需要检查 `.vitepress/config.mts` 的 Markdown 转义配置是否存在。
- 页面没有左侧菜单：通常是 `.vitepress/config.mts` 里缺少该教程目录对应的 sidebar key。

## 9. 提交前检查 Git 状态

运行：

```bash
git status --short
```

确认需要提交的文件都出现了。

当前项目需要关注：

- `.vitepress/config.mts` 是否被 Git 跟踪。
- `.vitepress/dist/` 不应该提交。
- `courses/...` 下新增的 Markdown 和图片资源需要提交。

## 10. 掘金小册抓取流程

如果是继续抓取一本掘金小册，通常流程是：

1. 准备小册链接，取出 URL 中的 booklet id。
2. 准备掘金 Cookie，只在命令环境变量中使用，不写入源码。
3. 运行抓取脚本：

```bash
JUEJIN_COOKIE='你的 Cookie' \
JUEJIN_BOOKLET_ID=小册ID \
JUEJIN_OUT_DIR=courses/juejin/example-course \
python3 -u scrape_juejin_book.py
```

4. 修复新生成的 `index.md` 链接格式。
5. 修复不支持或误识别的代码块语言。
6. 更新分类页、首页、`.vitepress/config.mts`。
7. 运行 `npm run docs:build` 验证。
