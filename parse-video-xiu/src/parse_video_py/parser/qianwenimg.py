"""千问图片/视频去水印 — 基于 api.bugpk.com 第三方接口

接口地址: https://api.bugpk.com/api/qianwenimg
请求方式: GET
请求参数: url (分享链接)
功能: 解析通义千问生成的图片和视频，提取无水印内容
"""

import httpx
from .base import BaseParser, VideoInfo, VideoAuthor, ImgInfo


class QianWenImg(BaseParser):
    async def parse_share_url(self, share_url: str) -> VideoInfo:
        api_url = f"https://api.bugpk.com/api/qianwenimg?url={share_url}"
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(api_url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            })
            resp.raise_for_status()
            data = resp.json()

        d = data.get("data") or data
        if isinstance(d, str):
            raise Exception("千问解析失败")

        title = d.get("title") or d.get("desc") or ""
        cover_url = d.get("cover") or ""

        author = d.get("author") or {}
        if isinstance(author, str):
            author = {"name": author}

        image_urls = d.get("images") or []
        images = [ImgInfo(url=u) for u in image_urls if isinstance(u, str)]

        video_url = d.get("url") or d.get("video_url") or ""

        return VideoInfo(
            video_url=video_url,
            cover_url=cover_url,
            title=title,
            images=images,
            author=VideoAuthor(
                name=author.get("name") or "",
                avatar=author.get("avatar") or "",
            ),
        )

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        raise NotImplementedError("千问解析请使用分享链接")
