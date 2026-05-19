"""皮皮虾解析器 — 基于 short_videos/ppxia.php 移植

核心逻辑：
1. 跟踪重定向获取真实 URL
2. 从 URL 中提取 item ID
3. 调用 https://h5.pipix.com/bds/cell/cell_h5_comment/ API
4. 解析视频/图集数据
"""

import re
from urllib.parse import urlparse

import httpx

from .base import BaseParser, ImgInfo, VideoAuthor, VideoInfo


class PiPiXia(BaseParser):

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        try:
            # 重定向获取真实 URL
            async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
                resp = await client.get(share_url, headers=self._headers())
                real_url = str(resp.url)

            # 提取 ID
            m = re.search(r"/item/([^?/&]+)", real_url)
            if not m:
                raise Exception("无法从皮皮虾链接中提取视频 ID")
            item_id = m.group(1)

            # 调用 API
            api_url = f"https://h5.pipix.com/bds/cell/cell_h5_comment/?count=5&aid=1319&app_name=super&cell_id={item_id}"
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(api_url, headers=self._headers())
                resp.raise_for_status()
                data = resp.json()

            comments = data.get("data", {}).get("cell_comments", [])
            if len(comments) < 2:
                raise Exception("皮皮虾数据解析失败")

            item = comments[1].get("comment_info", {}).get("item", {})
            if not item:
                raise Exception("皮皮虾数据解析失败")

            # 作者
            author_data = item.get("author", {})
            author_name = author_data.get("name", "")
            author_avatar = ""
            avatar_list = author_data.get("avatar", {}).get("download_list", [])
            if avatar_list:
                author_avatar = avatar_list[0].get("url", "")

            # 标题
            title = item.get("content", "")

            # 封面
            cover_list = item.get("cover", {}).get("url_list", [])
            cover_url = cover_list[0].get("url", "") if cover_list else ""

            # 视频
            video_url = ""
            video_high = item.get("video", {}).get("video_high", {})
            url_list = video_high.get("url_list", [])
            if url_list:
                video_url = url_list[0].get("url", "")

            # 图集
            images = []
            note = item.get("note", {})
            multi_image = note.get("multi_image", [])
            for img in multi_image:
                img_urls = img.get("url_list", [])
                if img_urls:
                    images.append(ImgInfo(url=img_urls[0].get("url", "")))

            return VideoInfo(
                video_url=video_url,
                cover_url=cover_url,
                title=title,
                images=images,
                author=VideoAuthor(name=author_name, avatar=author_avatar),
            )
        except Exception:
            return await self._fallback_parse(share_url)

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        raise NotImplementedError("皮皮虾暂不支持直接解析视频ID")

    async def _fallback_parse(self, share_url: str) -> VideoInfo:
        """降级: 调用 bugpk 第三方 API"""
        api_url = f"https://api.bugpk.com/api/pipixia?url={share_url}"
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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        }
