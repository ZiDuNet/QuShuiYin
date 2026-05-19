"""今日头条解析器 — 基于 short_videos/toutiao.php 移植

核心逻辑：
1. 跟踪重定向获取视频 ID
2. 请求 https://www.toutiao.com/video/{id} 页面
3. 提取 RENDER_DATA JSON（URL 解码后解析）
4. 从中提取视频播放地址
"""

import json
import re
from urllib.parse import unquote

import httpx

from .base import BaseParser, ImgInfo, VideoAuthor, VideoInfo


class Toutiao(BaseParser):

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        try:
            return await self._parse_main(share_url)
        except Exception:
            return await self._fallback_parse(share_url)

    async def _parse_main(self, share_url: str) -> VideoInfo:
        # 跟踪重定向获取视频 ID
        video_id = await self._extract_id(share_url)
        if not video_id:
            raise Exception("无法从今日头条链接中提取视频 ID")

        page_url = f"https://www.toutiao.com/video/{video_id}"
        headers = self._headers()

        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
            resp = await client.get(page_url, headers=headers)
            resp.raise_for_status()
            html = resp.text

        # 提取 RENDER_DATA
        start_tag = '<script id="RENDER_DATA" type="application/json">'
        pos = html.find(start_tag)
        if pos == -1:
            raise Exception("今日头条页面中未找到 RENDER_DATA")

        json_str = html[pos + len(start_tag):]
        end_pos = json_str.find("</script>")
        if end_pos == -1:
            raise Exception("今日头条 RENDER_DATA 解析失败")

        json_str = unquote(json_str[:end_pos])
        try:
            render_data = json.loads(json_str)
        except json.JSONDecodeError:
            raise Exception("今日头条 RENDER_DATA JSON 解析失败")

        data = render_data.get("data", {})
        if not data or not data.get("itemId"):
            raise Exception("今日头条分享链接已失效")

        # 提取视频信息
        initial_video = data.get("initialVideo", {})
        user_info = initial_video.get("itemCell", {}).get("userInfo", {})

        title = initial_video.get("title", "")
        cover = initial_video.get("coverUrl", "")

        # 视频地址: 优先索引2（最高画质），其次索引1
        video_list = initial_video.get("videoPlayInfo", {}).get("video_list", [])
        video_url = ""
        if len(video_list) > 2:
            video_url = video_list[2].get("main_url", "")
        if not video_url and len(video_list) > 1:
            video_url = video_list[1].get("main_url", "")
        if not video_url and video_list:
            video_url = video_list[0].get("main_url", "")

        return VideoInfo(
            video_url=video_url,
            cover_url=cover,
            title=title,
            author=VideoAuthor(
                uid=user_info.get("userID", ""),
                name=user_info.get("name", ""),
                avatar=user_info.get("avatarURL", ""),
            ),
        )

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        url = f"https://www.toutiao.com/video/{video_id}"
        return await self.parse_share_url(url)

    async def _fallback_parse(self, share_url: str) -> VideoInfo:
        """降级: 调用 bugpk 第三方 API"""
        api_url = f"https://api.bugpk.com/api/toutiao?url={share_url}"
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

    async def _extract_id(self, url: str) -> str:
        """跟踪重定向并提取视频 ID"""
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
                resp = await client.get(url, headers=self._headers())
                final_url = str(resp.url)
                m = re.search(r"/video/(\d+)", final_url)
                if m:
                    return m.group(1)
        except Exception:
            pass

        # 备用: 直接从 URL 中匹配
        m = re.search(r"(\d{15,})", url)
        return m.group(1) if m else ""

    def _headers(self) -> dict:
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
