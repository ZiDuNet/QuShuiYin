"""小红书图文解析 — 基于 api.bugpk.com 第三方接口

接口地址: https://api.bugpk.com/api/xhsimg
请求方式: GET
请求参数: url (分享链接)
功能: 无水印解析小红书图文内容，提取图片列表
"""

import httpx
from .base import BaseParser, VideoInfo, VideoAuthor, ImgInfo


class XhsImg(BaseParser):
    async def parse_share_url(self, share_url: str) -> VideoInfo:
        api_url = f"https://api.bugpk.com/api/xhsimg?url={share_url}"
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(api_url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            })
            resp.raise_for_status()
            data = resp.json()

        d = data.get("data") or data
        if isinstance(d, str):
            raise Exception("小红书图文解析失败")

        title = d.get("title") or d.get("desc") or ""
        cover_url = d.get("cover") or ""

        author = d.get("author") or d.get("authorID") or ""
        if isinstance(author, str):
            author_name = author
            author_avatar = d.get("avatar") or ""
        else:
            author_name = author.get("nickname") or author.get("name") or str(d.get("author", ""))
            author_avatar = author.get("avatar") or d.get("avatar") or ""

        image_urls = d.get("images") or []
        images = [ImgInfo(url=u) for u in image_urls if isinstance(u, str)]

        return VideoInfo(
            video_url="",
            cover_url=cover_url,
            title=title,
            images=images,
            author=VideoAuthor(name=author_name, avatar=author_avatar),
        )

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        raise NotImplementedError("小红书图文解析请使用分享链接")
