import json

import httpx

from .base import BaseParser, ImgInfo, VideoAuthor, VideoInfo


class JimengAI(BaseParser):
    async def parse_share_url(self, share_url: str) -> VideoInfo:
        try:
            item_id = self._extract_item_id(share_url)
            return await self.parse_video_id(item_id)
        except Exception:
            return await self._fallback_parse(share_url)

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        api_url = "https://jimeng.jianying.com/mweb/v1/get_item_info"
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
            "Content-Type": "application/json",
        }
        payload = {"published_item_id": video_id}

        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.post(api_url, headers=headers, json=payload)
            data = response.json()

        if data.get("ret") != "0":
            raise ValueError(f"即梦AI 解析失败: {data.get('msg', '未知错误')}")

        result = data.get("data", {})
        common = result.get("common_attr", {})
        author_data = result.get("author", {})
        video_data = result.get("video", {})

        # 视频URL优先级：转码原画 > 原始视频 > 其他清晰度
        video_url = ""
        transcoded = video_data.get("transcoded_video", {})
        if "origin" in transcoded:
            video_url = transcoded["origin"].get("video_url", "")
        if not video_url:
            video_url = video_data.get("origin_video", {}).get("video_url", "")

        # 封面
        cover_map = common.get("cover_url_map", {})
        cover_url = cover_map.get("original", "") or cover_map.get("1080", "") or cover_map.get("720", "")

        # 备选视频列表
        backup_urls = []
        for key in ["1080p", "720p", "480p"]:
            if key in transcoded and transcoded[key].get("video_url"):
                backup_urls.append(transcoded[key]["video_url"])

        return VideoInfo(
            video_url=video_url,
            cover_url=cover_url,
            title=common.get("description", ""),
            author=VideoAuthor(
                uid=author_data.get("uid", ""),
                name=author_data.get("name", ""),
                avatar=author_data.get("avatar_url", ""),
            ),
        )

    @staticmethod
    def _extract_item_id(share_url: str) -> str:
        # 从分享链接中提取 published_item_id
        import re

        match = re.search(r"/(\d{15,})", share_url)
        if match:
            return match.group(1)

        match = re.search(r"published_item_id=(\d+)", share_url)
        if match:
            return match.group(1)

        raise ValueError("从即梦AI分享链接中提取ID失败")

    async def _fallback_parse(self, share_url: str) -> VideoInfo:
        """降级: 调用 bugpk 第三方 API"""
        api_url = f"https://api.bugpk.com/api/jimengai?url={share_url}"
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
