"""抖音实况/图集解析 — 基于 api.bugpk.com 第三方接口

接口地址: https://api.bugpk.com/api/dylive
请求方式: GET
请求参数: url (分享链接)
功能: 解析抖音实况照片和图集内容，提取每张图片的静态图和实况视频
"""

import httpx
from .base import BaseParser, VideoInfo, VideoAuthor, ImgInfo


class DyLive(BaseParser):
    async def parse_share_url(self, share_url: str) -> VideoInfo:
        api_url = f"https://api.bugpk.com/api/dylive?url={share_url}"
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(api_url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            })
            resp.raise_for_status()
            data = resp.json()

        d = data.get("data") or data
        if isinstance(d, str):
            raise Exception("抖音实况解析失败")

        title = d.get("title", "")
        cover_url = d.get("cover", "")

        # 作者
        author_name = d.get("auther") or d.get("author", "")
        author_avatar = d.get("avatar", "")
        author_uid = str(d.get("uid", ""))

        # 图片 — images 是图片列表，url 是实况视频列表
        image_urls = d.get("images") or []
        live_urls = d.get("url") or []
        images = []
        for i, img_url in enumerate(image_urls):
            if isinstance(img_url, str):
                live = live_urls[i] if i < len(live_urls) and isinstance(live_urls[i], str) else ""
                images.append(ImgInfo(url=img_url, live_photo_url=live))

        # 音乐
        music_url = ""
        music = d.get("music") or {}
        if isinstance(music, dict):
            music_url = music.get("url", "")

        return VideoInfo(
            video_url="",
            cover_url=cover_url,
            title=title,
            music_url=music_url,
            images=images,
            author=VideoAuthor(uid=author_uid, name=author_name, avatar=author_avatar),
        )

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        raise NotImplementedError("抖音实况解析请使用分享链接")
