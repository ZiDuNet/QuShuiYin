"""皮皮搞笑解析器 — 基于 short_videos/pipigx.php 移植

核心逻辑：
1. 从 URL 中提取 pid 和 mid 参数
2. POST https://h5.pipigx.com/ppapi/share/fetch_content
3. 解析返回的视频/图片数据
"""

import json
from urllib.parse import parse_qs, urlparse

import httpx

from .base import BaseParser, ImgInfo, VideoAuthor, VideoInfo


class PiPiGaoXiao(BaseParser):

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        try:
            parsed = urlparse(share_url)
            params = parse_qs(parsed.query)

            pid = params.get("pid", [None])[0]
            mid = params.get("mid", [None])[0]

            if not pid or not mid:
                # 短链接需要重定向
                async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
                    resp = await client.get(share_url, headers=self._headers())
                    final_url = str(resp.url)
                    parsed = urlparse(final_url)
                    params = parse_qs(parsed.query)
                    pid = params.get("pid", [None])[0]
                    mid = params.get("mid", [None])[0]

            if not pid or not mid:
                raise Exception("无法提取 pid 或 mid 参数")

            api_url = "https://h5.pipigx.com/ppapi/share/fetch_content"
            payload = {"pid": int(pid), "mid": int(mid), "type": "post"}

            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    api_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                resp.raise_for_status()
                data = resp.json()

            post = data.get("data", {}).get("post", {})
            if not post:
                raise Exception("皮皮搞笑数据解析失败")

            title = post.get("content", "")
            videos = post.get("videos", {})
            cover_url = ""

            # 视频
            video_url = ""
            if isinstance(videos, dict):
                for vid, vdata in videos.items():
                    video_url = vdata.get("url", "")
                    thumb = vdata.get("thumb", "")
                    if thumb:
                        cover_url = f"https://file.ippzone.com/img/frame/id/{thumb}"
                    break
            elif isinstance(videos, list) and videos:
                video_url = videos[0].get("url", "")
                thumb = videos[0].get("thumb", "")
                if thumb:
                    cover_url = f"https://file.ippzone.com/img/frame/id/{thumb}"

            return VideoInfo(
                video_url=video_url,
                cover_url=cover_url,
                title=title,
            )
        except Exception:
            return await self._fallback_parse(share_url)

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        raise NotImplementedError("皮皮搞笑暂不支持直接解析视频ID")

    async def _fallback_parse(self, share_url: str) -> VideoInfo:
        """降级: 调用 bugpk 第三方 API"""
        api_url = f"https://api.bugpk.com/api/pipigx?url={share_url}"
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(api_url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            })
            resp.raise_for_status()
            data = resp.json()

        d = data.get("data") or data
        if isinstance(d, str):
            raise Exception("第三方解析返回异常")

        video_url = d.get("url") or d.get("video_url") or d.get("nwm_video_url") or d.get("wm_video_url") or ""
        cover_url = d.get("cover") or d.get("cover_url") or d.get("img") or d.get("pic") or ""
        title = d.get("title") or d.get("desc") or d.get("name") or ""
        music_url = d.get("music_url") or d.get("audio_url") or ""

        if isinstance(d.get("music"), dict):
            music_url = d["music"].get("url", "") or music_url

        author = d.get("author") or {}
        if isinstance(author, str):
            author = {"nickname": author}
        author_name = author.get("nickname") or author.get("name") or ""
        author_avatar = author.get("avatar") or author.get("avatar_url") or ""

        images = []
        for img in d.get("images") or d.get("image_list") or []:
            if isinstance(img, str):
                images.append(ImgInfo(url=img))
            elif isinstance(img, dict):
                images.append(ImgInfo(url=img.get("url") or img.get("origin") or ""))

        return VideoInfo(
            video_url=video_url,
            cover_url=cover_url,
            title=title,
            music_url=music_url,
            images=images,
            author=VideoAuthor(name=author_name, avatar=author_avatar),
        )

    def _headers(self) -> dict:
        return {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15",
        }
