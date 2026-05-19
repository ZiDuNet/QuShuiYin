"""影视解析 — 基于 api.bugpk.com 第三方接口

接口地址: https://api.bugpk.com/api/videosjx
请求方式: GET
请求参数: url (视频链接)
功能: 影视解析，去广告，支持非凡等平台
"""

import httpx
from .base import BaseParser, VideoInfo, VideoAuthor, ImgInfo


class VideoSjx(BaseParser):
    async def parse_share_url(self, share_url: str) -> VideoInfo:
        api_url = f"https://api.bugpk.com/api/videosjx?url={share_url}"
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(api_url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            })
            resp.raise_for_status()
            data = resp.json()

        d = data.get("data") or data
        if isinstance(d, str):
            raise Exception("影视解析失败")

        video_url = d.get("url") or d.get("video_url") or ""
        cover_url = d.get("cover") or d.get("cover_url") or ""
        title = d.get("title") or d.get("name") or ""

        return VideoInfo(
            video_url=video_url,
            cover_url=cover_url,
            title=title,
        )

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        raise NotImplementedError("影视解析请使用分享链接")
