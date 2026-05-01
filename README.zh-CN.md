# douban-scraper

🇺🇸 [English](README.md)

[![Python](https://img.shields.io/badge/python-%E2%89%A53.10-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

导出你的豆瓣电影、图书、音乐和广播数据为 JSON。直接调用 Frodo 移动端 API 和 Rexxar API，无需浏览器自动化，无需 Selenium，大部分数据无需登录。

## 功能

- 导出电影、图书、音乐、广播为 JSON
- 支持断点续传，中断后可从上次位置继续
- 使用 `to-csv` 将导出数据转为 CSV
- 电影、图书、音乐无需认证
- 内置请求限速，避免触发 API 阈值

## 安装

```bash
git clone https://github.com/lizh3/douban-scraper.git
cd douban-scraper
pip install -e .
```

开发环境（包含 pytest、ruff）：

```bash
pip install -e ".[dev]"
```

需要 Python 3.10+。

## 快速开始

```bash
# Export your Douban collection
douban-scraper export --user 123456789 --types movie,book --output ./my-data

# Convert to CSV
douban-scraper to-csv --input ./my-data
```

## 命令

### `export`

导出用户的豆瓣收藏数据，将 JSON 文件写入输出目录。

```bash
douban-scraper export --user 123456789 --types movie,book,music --output ./my-data
```

### `to-csv`

将导出的 JSON 文件合并为单个 `douban_export.csv`。仅处理 `movies.json` 和 `books.json`（不支持 `music.json` 和 `broadcasts.json`）。

```bash
douban-scraper to-csv --input ./my-data
```

输出列：title、type、my_rating、comment、create_time、year、genres、douban_rating、card_subtitle、url、tags。

## 认证方式

### 电影 / 图书 / 音乐（无需认证）

这些数据通过 Frodo 移动端 API 获取。工具内置了 API key 和 HMAC-SHA1 签名，公开个人资料数据无需登录或凭证。

### 广播（需要 Cookie）

广播使用 Rexxar API，需要从已认证的浏览器会话中获取有效的 `ck` Cookie。

```bash
douban-scraper export --user 123456789 --types broadcast --cookie "YOUR_CK_VALUE" --output ./my-data
```

只需传入 `ck` 的原始值，代码会自动添加 `ck=` 前缀。

获取 `ck` Cookie 的方法：

1. 在浏览器中登录豆瓣
2. 打开开发者工具 (F12 或 Ctrl+Shift+I)
3. 进入 Chrome 的 **Application**（应用）标签页或 Firefox 的 **Storage**（存储）标签页
4. 在 **Cookies** 下选择 `m.douban.com`
5. 复制名为 `ck` 的 Cookie 值

## 输出格式

工具按内容类型在输出目录中生成对应的 JSON 文件：

| 文件 | 内容 |
|------|------|
| `movies.json` | 电影评分和评论 |
| `books.json` | 图书评分和评论 |
| `music.json` | 音乐评分和评论 |
| `broadcasts.json` | 广播/日记帖子 |

注意：文件名是 `music.json`（单数），不是 `musics.json`。

`.progress.json` 文件用于跟踪抓取状态，支持断点续传。

电影条目示例：

```json
{
  "comment": "Rewatched this again, still holds up.",
  "rating": {
    "value": 5,
    "max": 5
  },
  "create_time": "2024-08-12 22:31:17",
  "subject": {
    "id": "35290178",
    "title": "奥本海默",
    "url": "https://movie.douban.com/subject/35290178/",
    "cover": "https://img2.doubanio.com/view/photo/s_ratio_poster/public/p2895451952.jpg",
    "rating": {
      "value": 8.9
    },
    "type": "movie",
    "year": "2023",
    "genres": ["剧情", "传记", "历史"],
    "card_subtitle": "2023 / 美国 英国 / 剧情 传记 历史 / 克里斯托弗·诺兰 / 基里安·墨菲 艾米莉·布朗特"
  },
  "status": "done",
  "tags": ["诺兰", "历史", "2023"]
}
```

广播条目示例：

```json
{
  "id": "abc123",
  "text": "Just finished reading this. Highly recommended.",
  "created_at": "2024-07-20 14:05:00",
  "comments_count": 3,
  "likes_count": 12,
  "subject": null,
  "reshared_status": null
}
```

## 配置

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `--user` / `-u` | 是 | | 豆瓣用户 ID（数字） |
| `--types` / `-t` | 否 | `movie,book,music` | 逗号分隔：`movie`、`book`、`music`、`broadcast` |
| `--status` / `-s` | 否 | `done` | 逗号分隔的状态：`done`、`doing`、`mark` 或 `all` |
| `--output` / `-o` | 否 | `./output` | 输出目录 |
| `--cookie` / `-c` | 广播必填 | | `ck` Cookie 原始值（不是 `ck=值`） |
| `--delay` / `-d` | 否 | `1.5` | 请求间隔（秒） |
| `--max-items` / `-m` | 否 | `0` | 每种类型/状态的最大条目数（0 = 不限） |
| `--api-key` | 否 | 内置 | 覆盖 Frodo API key |
| `--api-secret` | 否 | 内置 | 覆盖 Frodo HMAC 密钥 |
| `--force` / `-f` | 否 | `false` | 重新抓取并覆盖已有输出（⚠️ 会删除输出目录中的所有 `.json` 文件） |

## 已知限制

- 长评（评论/影评）不支持导出。没有对应的 API 接口，且豆瓣网页受工作量证明（proof-of-work）机制保护
- v1 不支持游戏收藏
- 不支持私密个人资料数据
- `to-csv` 仅处理 `movies.json` 和 `books.json`（不支持音乐和广播）
- `--force` 会删除输出目录中的**所有** `.json` 文件，包括你可能添加的自定义文件

## 查找你的用户 ID

你的豆瓣用户 ID 是个人主页 URL 中的数字部分。打开你的个人主页，查看 URL：

```
https://www.douban.com/people/123456789/
```

其中的数字 `123456789` 就是你的用户 ID。使用 `--user 123456789` 传入。

## 贡献

如有改动建议，请先提交 Issue 讨论。Fork 仓库后提交 Pull Request。提交前请运行 `pytest`。代码风格使用 `ruff` 检查。

## 免责声明

本项目与豆瓣无关。请合理使用，尊重 API 速率限制。

## 许可证

MIT &copy; 2026 ritetsu. 详见 [LICENSE](LICENSE)。
