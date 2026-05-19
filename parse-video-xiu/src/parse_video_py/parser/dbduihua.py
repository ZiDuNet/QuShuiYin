"""豆包对话图片解析 — 基于 api.bugpk.com 第三方接口

接口地址: https://api.bugpk.com/api/dbduihua
请求方式: GET
请求参数: url (对话分享链接)
功能: 提取豆包 AI 对话中生成的无水印图片
"""

import httpx
from .base import BaseParser, VideoInfo, VideoAuthor, ImgInfo


class DbDuiHua(BaseParser):
    async def parse_share_url(self, share_url: str) -> VideoInfo:
        api_url = f"https://api.bugpk.com/api/dbduihua?url={share_url}"
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(api_url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            })
            resp.raise_for_status()
            data = resp.json()

        image_urls = data.get("images") or []
        video_urls = data.get("videos") or []
        images = [ImgInfo(url=u) for u in image_urls if isinstance(u, str)]
        video_url = video_urls[0] if video_urls and isinstance(video_urls[0], str) else ""

        return VideoInfo(
            video_url=video_url,
            cover_url=image_urls[0] if image_urls else "",
            title="",
            images=images,
        )

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        raise NotImplementedError("豆包对话图片解析请使用分享链接")
