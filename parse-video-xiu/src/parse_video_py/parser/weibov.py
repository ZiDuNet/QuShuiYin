"""微博去水印解析 — 基于 api.bugpk.com 第三方接口

接口地址: https://api.bugpk.com/api/weibo_v
请求方式: GET
请求参数: url (分享链接)
功能: 微博短视频无水印解析（备用接口）
"""

import httpx
from .base import BaseParser, VideoInfo, VideoAuthor, ImgInfo


class WeiBoV(BaseParser):
    async def parse_share_url(self, share_url: str) -> VideoInfo:
        api_url = f"https://api.bugpk.com/api/weibo_v?url={share_url}"
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(api_url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            })
            resp.raise_for_status()
            data = resp.json()

        d = data.get("data") or data
        if isinstance(d, str):
            raise Exception("微博去水印解析失败")

        video_url = d.get("url") or ""
        cover_url = d.get("cover") or ""
        title = d.get("title") or ""

        author = d.get("author") or {}
        if isinstance(author, str):
            author = {"name": author}

        return VideoInfo(
            video_url=video_url,
            cover_url=cover_url,
            title=title,
            author=VideoAuthor(
                name=author.get("name") or author.get("nickname") or "",
                avatar=author.get("avatar") or d.get("avatar") or "",
            ),
        )

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        raise NotImplementedError("微博去水印解析请使用分享链接")
