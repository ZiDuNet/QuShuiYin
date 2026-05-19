# CLAUDE.md

本项目是一个去水印工具集合，目标是将多个开源去水印项目的解析能力整合到统一 API 中。

## 项目定位

- **主开发项目**：`parse-video-xiu/` — 基于 parse-video-py v0.0.3 改造，当前支持 35 个平台
- **其他目录**：参考项目，不直接修改，仅用于移植解析逻辑和对比测试

## 核心架构（parse-video-xiu）

```
parse-video-xiu/src/parse_video_py/
├── parser/          # 各平台解析器
│   ├── base.py      # BaseParser 抽象基类、VideoSource 枚举、VideoInfo 数据结构
│   ├── __init__.py  # video_source_info_mapping 域名路由映射
│   └── [平台].py    # 每个平台独立一个文件
├── web.py           # FastAPI 入口（3 个接口：/、/video/share/url/parse、/video/id/parse）
├── utils.py         # URL 提取工具
└── templates/       # 前端页面
```

## 添加新平台的流程

1. 在 `parser/base.py` 的 `VideoSource` 枚举中新增值
2. 创建 `parser/[平台名].py`，继承 `BaseParser`，实现 `parse_share_url` 和 `parse_video_id`
3. 在 `parser/__init__.py` 中注册域名映射
4. 如有新依赖，更新 `pyproject.toml`

## 开发命令

```bash
cd parse-video-xiu
pip install -e ".[all]"          # 安装依赖
uvicorn parse_video_py.web:app --reload --port 8000  # 启动开发服务
pytest                            # 运行测试
```

## 参考项目用途

| 项目 | 主要参考价值 |
|------|------------|
| media-parser | 抖音 a_bogus 签名绕过（`douyin_utils/`）、小红书重试、Instagram/YouTube（yt-dlp） |
| parse-video (Go) | Go 版解析逻辑对照、火山平台 |
| short_videos | 豆包/即梦AI/今日头条/网易云的 PHP 解析逻辑、CF Workers 部署方案 |
| cleanmark | 用户系统、VIP 等级、微信/支付宝支付、管理后台、微信小程序 |
| douyin-video-decode | 精美前端界面（深色毛玻璃主题）、小程序端 |

## 当前已知问题

- 抖音解析器（HTML 方式）失效，短链接重定向到首页而非视频页，需要移植 media-parser 的 API 直调方式（ttwid + a_bogus 签名）
- 小红书图片有防盗链，已在 HTML 模板添加 `<meta name="referrer" content="no-referrer"/>`
- 抖音主页和网易云音乐依赖 Cookie/登录凭证，稳定性较差

## Git 仓库

- 集合仓库：https://github.com/ZiDuNet/QuShuiYin
- 主项目：https://github.com/ZiDuNet/parse-video-py
- 上游：https://github.com/wujunwei928/parse-video-py
