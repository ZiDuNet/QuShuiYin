"""最右解析器 — 基于 short_videos/zuiyou.php 移植

核心逻辑：
1. 从 URL（或重定向后）提取 pid 和 vid 参数
2. POST https://share.xiaochuankeji.cn/planck/share/post/detail_h5
3. 解析视频/图片数据
"""

import json
from urllib.parse import parse_qs, urlparse

import httpx

from .base import BaseParser, ImgInfo, VideoAuthor, VideoInfo


class ZuiYou(BaseParser):

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        try:
            return await self._parse_main(share_url)
        except Exception:
            return await self._fallback_parse(share_url)

    async def _parse_main(self, share_url: str) -> VideoInfo:
        # 提取 pid 和 vid，可能需要重定向
        pid = self._get_param(share_url, "pid")
        vid = self._get_param(share_url, "vid")

        if not pid:
            # 短链接重定向
            try:
                async with httpx.AsyncClient(follow_redirects=False, timeout=10) as client:
                    resp = await client.get(share_url, headers=self._headers())
                    location = resp.headers.get("location", "")
                    if location:
                        pid = self._get_param(location, "pid")
                        vid = self._get_param(location, "vid")
            except Exception:
                pass

        if not pid:
            # 全程跟踪重定向
            try:
                async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
                    resp = await client.get(share_url, headers=self._headers())
                    final_url = str(resp.url)
                    pid = self._get_param(final_url, "pid")
                    if not vid:
                        vid = self._get_param(final_url, "vid")
            except Exception:
                pass

        if not pid:
            raise Exception("无法从最右链接中提取 pid")

        # 调用 API
        api_url = "https://share.xiaochuankeji.cn/planck/share/post/detail_h5"
        payload = {"pid": int(pid), "h_av": "5.2.13.011"}

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                api_url,
                json=payload,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()

        post = data.get("data", {}).get("post", {})
        if not post:
            raise Exception("最右数据解析失败")

        member = post.get("member", {})
        author_name = member.get("name", "")
        author_avatar = ""
        avatar_urls = member.get("avatar_urls", {}).get("origin", {}).get("urls", [])
        if avatar_urls:
            author_avatar = avatar_urls[0]

        title = post.get("content", "")

        # 封面
        imgs = post.get("imgs", [])
        cover_url = ""
        img_vid = ""
        if imgs:
            first_img = imgs[0]
            cover_urls = first_img.get("urls", {}).get("540_webp", {}).get("urls", [])
            cover_url = cover_urls[0] if cover_urls else ""
            img_vid = first_img.get("id", "")

        # 视频
        video_url = ""
        videos = post.get("videos", {})
        # 优先用 URL 中的 vid，其次用 img 的 id
        target_vid = vid or img_vid
        if isinstance(videos, dict) and target_vid:
            video_data = videos.get(target_vid, {})
            video_url = video_data.get("url", "")

        return VideoInfo(
            video_url=video_url,
            cover_url=cover_url,
            title=title,
            author=VideoAuthor(name=author_name, avatar=author_avatar),
        )

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        raise NotImplementedError("最右暂不支持直接解析视频ID")

    async def _fallback_parse(self, share_url: str) -> VideoInfo:
        """降级: 调用 bugpk 第三方 API"""
        api_url = f"https://api.bugpk.com/api/zuiyou?url={share_url}"
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

    def _get_param(self, url: str, key: str) -> str:
        """从 URL query 中提取参数"""
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        return params.get(key, [None])[0] or ""

    def _headers(self) -> dict:
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        }
