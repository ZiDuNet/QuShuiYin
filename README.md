# QuShuiYin - 短视频去水印平台集合

> 多平台短视频去水印解析工具集合，目标是打造一个覆盖所有主流平台的统一解析 API。

## 项目背景

市面上有大量开源的去水印项目，各自支持不同的平台，技术栈各异。本项目的目标是：

1. **收集**：汇聚各开源项目的解析能力
2. **整合**：以 `parse-video-xiu` 为主项目，将其他项目的独有平台解析器移植过来
3. **统一**：提供统一的 API 接口，一个入口解析所有平台

## 项目结构

```
去水印项目/
├── parse-video-xiu/       ← 🔧 主开发项目（基于 parse-video-py 改造）
├── parse-video-py/        ← 📦 上游原版（用于同步更新）
├── media-parser/          ← 📖 参考：28+ 平台，抖音签名绕过
├── parse-video/           ← 📖 参考：Go 版，26 平台
├── short_videos/          ← 📖 参考：PHP 轻量接口，独有豆包/即梦AI
├── cleanmark/             ← 📖 参考：商业版，用户系统+支付
└── douyin-video-decode/   ← 📖 参考：前端增强版
```

## 主项目 parse-video-xiu

基于 [parse-video-py](https://github.com/wujunwei928/parse-video-py) v0.0.3 改造，已新增 10 个平台，覆盖 **35 个平台**。

### 支持平台（35 个）

抖音、快手、小红书、哔哩哔哩、微博、西瓜视频、微视、皮皮虾、皮皮搞笑、最右、梨视频、虎牙、AcFun、逗拍、美拍、全民K歌、六间房、新片场、好看视频、度小视、绿洲、Twitter/X、腾讯视频、央视网、搜狐视频、火山、TikTok、即梦AI、知乎、今日头条、豆包、Instagram、YouTube、抖音主页、网易云音乐

### 快速启动

```bash
cd parse-video-xiu
pip install -e ".[all]"
uvicorn parse_video_py.web:app --reload --port 8000
```

访问 `http://localhost:8000/` 使用 Web 界面，或调用 API：

```
GET /video/share/url/parse?url=<分享链接>
```

### 新增平台来源

| 平台 | 移植自 | 来源文件 |
|------|--------|---------|
| 火山 | parse-video (Go) | `parser/huoshan.go` |
| TikTok | media-parser | `parsers/tiktok_parser.py` |
| 即梦AI | short_videos | `api/jimengai/` |
| 知乎 | media-parser | `parsers/zhihu_parser.py` |
| 今日头条 | short_videos | `api/toutiao.php` |
| 豆包 | short_videos | `api/doubao/` |
| Instagram | media-parser | `parsers/instagram_parser.py` |
| YouTube | media-parser | `parsers/youtube_parser.py` |
| 抖音主页 | short_videos | `api/dyzy/` |
| 网易云音乐 | short_videos | `api/wyy.py` |

## 参考项目地址

| 项目 | GitHub | 语言 | 特点 |
|------|--------|------|------|
| parse-video | [wujunwei928/parse-video](https://github.com/wujunwei928/parse-video) | Go | v0.0.2，高性能 Go 版 |
| parse-video-py | [wujunwei928/parse-video-py](https://github.com/wujunwei928/parse-video-py) | Python | v0.0.3，上游原版 |
| media-parser | [ucmao/media-parser](https://github.com/ucmao/media-parser) | Python | 抖音 a_bogus 签名绕过 |
| short_videos | [jiuhunwl/short_videos](https://github.com/jiuhunwl/short_videos) | PHP | 零依赖，CF Workers |
| cleanmark | [haorantiangang/cleanmark](https://github.com/haorantiangang/cleanmark) | Go | 用户系统+支付+小程序 |
| douyin-video-decode | [zwl568633995/douyin-video-decode](https://github.com/zwl568633995/douyin-video-decode) | Python | 精美前端界面 |

## 开发指南

- **日常开发**：只改 `parse-video-xiu/` 目录
- **上游同步**：对比 `parse-video-py/` 合并上游更新
- **移植功能**：从参考项目中提取解析逻辑，适配到 parse-video-xiu 的 BaseParser 架构
- **推送地址**：主项目 → [ZiDuNet/parse-video-py](https://github.com/ZiDuNet/parse-video-py)，集合 → [ZiDuNet/QuShuiYin](https://github.com/ZiDuNet/QuShuiYin)

## 许可证

各子项目保留各自原始许可证。主项目遵循 MIT License。
