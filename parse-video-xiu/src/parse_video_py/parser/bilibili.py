"""哔哩哔哩解析器 — 基于 short_videos/BilibiliParser.php 移植

核心逻辑：
1. 提取 BV 号（支持 b23.tv 短链接重定向）
2. 调用 bilibili API: /x/web-interface/view 获取视频信息
3. 调用 /x/player/playurl 获取播放地址，替换 CDN 域名解决防盗链
"""

import re
from urllib.parse import urlparse

import httpx

from .base import BaseParser, ImgInfo, VideoAuthor, VideoInfo


class BiliBili(BaseParser):

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        try:
            bvid = await self._extract_bvid(share_url)
            if not bvid:
                raise Exception("无法提取 BV 号")
            return await self._parse_bvid(bvid)
        except Exception:
            return await self._fallback_parse(share_url)

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        return await self._parse_bvid(video_id)

    async def _extract_bvid(self, url: str) -> str:
        parsed = urlparse(url)
        host = parsed.netloc

        if host == "b23.tv":
            async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
                resp = await client.get(url, headers=self._headers())
                return self._bvid_from_path(str(resp.url))
        elif host in ("www.bilibili.com", "m.bilibili.com"):
            return self._bvid_from_path(url)
        return ""

    def _bvid_from_path(self, url: str) -> str:
        m = re.search(r"/video/(BV\w+)", url)
        return m.group(1) if m else ""

    async def _parse_bvid(self, bvid: str) -> VideoInfo:
        headers = self._headers()

        view_url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(view_url, headers=headers)
            resp.raise_for_status()
            view_data = resp.json()

        if view_data.get("code") != 0:
            raise Exception(f"bilibili API error: {view_data.get('message', '')}")

        info = view_data["data"]
        pages = info.get("pages", [])
        cid = pages[0]["cid"] if pages else 0

        play_url = (
            f"https://api.bilibili.com/x/player/playurl"
            f"?otype=json&fnver=0&fnval=3&player=3&qn=112"
            f"&bvid={bvid}&cid={cid}&platform=html5&high_quality=1"
        )
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(play_url, headers=headers)
            resp.raise_for_status()
            play_data = resp.json()

        video_url = ""
        durl = play_data.get("data", {}).get("durl", [])
        if durl:
            raw_url = durl[0].get("url", "")
            parts = raw_url.split(".bilivideo.com/")
            if len(parts) > 1:
                video_url = f"https://upos-sz-mirrorhw.bilivideo.com/{parts[1]}"
            else:
                video_url = raw_url

        return VideoInfo(
            video_url=video_url,
            cover_url=info.get("pic", ""),
            title=info.get("title", ""),
            author=VideoAuthor(
                name=info.get("owner", {}).get("name", ""),
                avatar=info.get("owner", {}).get("face", ""),
            ),
        )

    async def _fallback_parse(self, share_url: str) -> VideoInfo:
        """降级: 调用 bugpk 第三方 API"""
        api_url = f"https://api.bugpk.com/api/bilibili?url={share_url}"
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

        # 处理音乐字段可能是 dict 的情况
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
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36",
            "Referer": "https://www.bilibili.com/",
            "Content-Type": "application/json;charset=UTF-8",
        }
