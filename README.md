# 我要看图 (栗次元)

fork 自 [ImNotBird/astrbot_plugin_Pic](https://github.com/ImNotBird/astrbot_plugin_Pic),图源改为 17 个栗次元全分类,增加 LLM 工具、配置开关、中文别名指令。

## 安装

WebUI → 插件管理 → 从 GitHub 安装 → 贴:

```
https://github.com/publieople/astrbot_plugin_Pic
```

## 用法

| 方式 | 说明 |
|---|---|
| `/help` | 显示帮助 |
| `/看图分类` | 列出当前已启用的图源 |
| `/来点 [分类]` | 发送指定分类的随机图,留空随机 |
| 发 "我要看图" | 关键词触发随机(可在配置中改 `trigger_words`) |
| LLM 自动调用 | AI 主动调 `send_random_pic` |

### 分类别名 (`/来点` 支持)

| key | 标签 | 支持别名 |
|---|---|---|
| `ycy` | 二次元自适应 | 二次元, 二次元自适应 |
| `moez` | 萌版自适应 | 萌版, 萌 |
| `ai` | AI 自适应 | ai, ai自适应, ai图 |
| `ysz` | 原神自适应 | 原神自适应 |
| `pc` | PC 横图 | pc, pc横图, 电脑, 横图 |
| `moe` | 萌版横图 | 萌版横图, 萌横 |
| `fj` | 风景横图 | 风景, 风景横图 |
| `bd` | 白底横图 | 白底, 白底横图 |
| `ys` | 原神横图 | 原神, 原神横图 |
| `acg` | ACG 动图 | acg, 动图 *(返 mp4,被白名单过滤)** |
| `mp` | 移动竖图 | 手机, 竖图, 移动竖图 |
| `moemp` | 萌版竖图 | 萌版竖图, 萌竖 |
| `ysmp` | 原神竖图 | 原神竖图 |
| `aimp` | AI 竖图 | ai竖图 |
| `tx` | 头像方图 | 头像, 头像方图 |
| `lai` | 七濑胡桃 | 七濑胡桃, 胡桃 |
| `xhl` | 小狐狸 | 小狐狸, 狐狸 |

## 配置

`_conf_schema.json` 支持 WebUI 配置:

| 字段 | 默认 | 说明 |
|---|---|---|
| `max_retries` | `2` | 图源失败时最大重试次数(继续换下一个) |
| `trigger_words` | `我要看图` | 关键词触发列表(逗号分隔) |
| `enabled_categories` | `[]` (全启用) | 勾选要启用的分类;取消勾选后 `/来点` 会提示"已被禁用" |
