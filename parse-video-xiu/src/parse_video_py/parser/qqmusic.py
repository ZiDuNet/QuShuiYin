"""QQ音乐解析 — 基于 api.bugpk.com 第三方接口

接口地址: https://api.bugpk.com/api/qqmusic
请求方式: GET
请求参数: url (音乐链接) / type (song/mv/search)
功能: QQ音乐解析，提取音乐直链
"""

import httpx
from .base import BaseParser, VideoInfo, VideoAuthor, ImgInfo


class QQMusic(BaseParser):
    async def parse_share_url(self, share_url: str) -> VideoInfo:
        api_url = f"https://api.bugpk.com/api/qqmusic?url={share_url}"
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(api_url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            })
            resp.raise_for_status()
            data = resp.json()

        d = data.get("data") or data
        if isinstance(d, str):
            raise Exception("QQ音乐解析失败")

        music_url = d.get("url") or d.get("music_url") or ""
        cover_url = d.get("cover") or d.get("pic") or d.get("cover_url") or ""
        title = d.get("name") or d.get("title") or d.get("song") or ""
        author_name = d.get("singer") or d.get("artist") or d.get("author") or ""
        author_avatar = d.get("avatar") or ""

        return VideoInfo(
            video_url="",
            cover_url=cover_url,
            title=title,
            music_url=music_url,
            author=VideoAuthor(name=author_name, avatar=author_avatar),
        )

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        raise NotImplementedError("QQ音乐解析请使用分享链接")
