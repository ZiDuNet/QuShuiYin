# 去水印项目集合

> 更新时间：2026-05-20

## 项目结构

| 目录 | 说明 | 语言 | 来源 |
|------|------|------|------|
| **parse-video-xiu** | 主开发项目（基于 parse-video-py 改造，35 平台） | Python | 改造版 |
| parse-video-py | 上游原版（关联 wujunwei928/parse-video-py） | Python | [GitHub](https://github.com/wujunwei928/parse-video-py) |
| media-parser | 多平台解析服务（28+ 平台，抖音签名绕过） | Python | [GitHub](https://github.com/ucmao/media-parser) |
| parse-video | Go 版解析工具（26 平台） | Go | [GitHub](https://github.com/wujunwei928/parse-video) |
| short_videos | PHP 轻量接口集（11 平台） | PHP | [GitHub](https://github.com/jiuhunwl/short_videos) |
| cleanmark | 商业级方案（用户系统+支付+小程序） | Go | [GitHub](https://github.com/haorantiangang/cleanmark) |
| douyin-video-decode | parse-video-py 克隆版（有前端界面） | Python | [GitHub](https://github.com/zwl568633995/douyin-video-decode) |

## 开发指南

- **开发目录**：`parse-video-xiu/`
- **上游同步**：从 `parse-video-py/` 对比合并上游更新
- **功能参考**：从其他子项目中移植解析逻辑

## 参考地址

| 项目 | GitHub |
|------|--------|
| parse-video | https://github.com/wujunwei928/parse-video |
| parse-video-py | https://github.com/wujunwei928/parse-video-py |
| media-parser | https://github.com/ucmao/media-parser |
| short_videos | https://github.com/jiuhunwl/short_videos |
| cleanmark | https://github.com/haorantiangang/cleanmark |
| douyin-video-decode | https://github.com/zwl568633995/douyin-video-decode |
| **parse-video-xiu (主项目)** | https://github.com/ZiDuNet/parse-video-py |
