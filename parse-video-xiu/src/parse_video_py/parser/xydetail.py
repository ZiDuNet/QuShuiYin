"""闲鱼商品信息解析 — 基于 api.bugpk.com 第三方接口

接口地址: https://api.bugpk.com/api/xydetail
请求方式: GET
请求参数: url (商品链接，需带 id)
功能: 解析闲鱼商品信息，提取图片和描述
"""

import httpx
from .base import BaseParser, VideoInfo, VideoAuthor, ImgInfo


class XyDetail(BaseParser):
    async def parse_share_url(self, share_url: str) -> VideoInfo:
        api_url = f"https://api.bugpk.com/api/xydetail?url={share_url}"
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(api_url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            })
            resp.raise_for_status()
            data = resp.json()

        d = data.get("data") or data
        if isinstance(d, str):
            raise Exception("闲鱼商品解析失败")

        title = d.get("desc") or d.get("title") or ""
        video_url = d.get("playUrl") or ""

        author_name = d.get("nick") or ""
        author_avatar = d.get("portraitUrl") or ""

        image_urls = d.get("images") or []
        images = [ImgInfo(url=u) for u in image_urls if isinstance(u, str)]

        return VideoInfo(
            video_url=video_url,
            cover_url=image_urls[0] if image_urls else "",
            title=title,
            images=images,
            author=VideoAuthor(name=author_name, avatar=author_avatar),
        )

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        raise NotImplementedError("闲鱼商品解析请使用分享链接")
