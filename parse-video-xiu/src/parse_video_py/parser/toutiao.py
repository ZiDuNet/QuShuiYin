import json
import re
from urllib.parse import urlparse, parse_qs

import httpx

from .base import BaseParser, VideoAuthor, VideoInfo


class Toutiao(BaseParser):
    async def parse_share_url(self, share_url: str) -> VideoInfo:
        video_id = await self._get_video_id(share_url)
        return await self.parse_video_id(video_id)

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        page_url = f"https://www.toutiao.com/video/{video_id}/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(page_url, headers=headers)
            html = response.text

        # 提取 RENDER_DATA
        match = re.search(
            r'<script id="RENDER_DATA" type="application/json">(.+?)</script>', html
        )
        if not match:
            raise ValueError("今日头条页面解析失败，未找到RENDER_DATA")

        render_data = json.loads(match.group(1))

        # 遍历找到视频数据
        video_data = None
        for key, value in render_data.items():
            if isinstance(value, dict) and "initialVideo" in str(value):
                video_data = self._find_video_data(value)
                if video_data:
                    break

        if not video_data:
            raise ValueError("今日头条解析失败，未找到视频数据")

        # 视频URL
        video_url = ""
        play_info = video_data.get("videoPlayInfo", {})
        if isinstance(play_info, str):
            play_info = json.loads(play_info)
        video_list = play_info.get("video_list", [])
        if video_list:
            # 优先选择最后一个（通常最高清）
            video_url = video_list[-1].get("main_url", "")
            if video_url:
                import base64

                video_url = base64.b64decode(video_url).decode("utf-8")

        # 标题
        title = video_data.get("title", "")

        # 封面
        cover_url = video_data.get("coverUrl", "") or video_data.get(
            "poster_url", ""
        )

        # 作者
        author_data = {}
        item_cell = video_data.get("itemCell", {})
        if "userInfo" in item_cell:
            author_data = item_cell["userInfo"]

        # 音乐
        music_url = ""
        video_ability = item_cell.get("videoAbility", {})
        if isinstance(video_ability, dict) and video_ability.get("music"):
            music_url = video_ability["music"]

        return VideoInfo(
            video_url=video_url,
            cover_url=cover_url,
            title=title,
            music_url=music_url,
            author=VideoAuthor(
                uid=author_data.get("userID", ""),
                name=author_data.get("name", ""),
                avatar=author_data.get("avatarURL", ""),
            ),
        )

    def _find_video_data(self, data: dict) -> dict:
        """递归查找包含 initialVideo 的数据"""
        if isinstance(data, dict):
            if "initialVideo" in data:
                return data["initialVideo"]
            for value in data.values():
                result = self._find_video_data(value)
                if result:
                    return result
        elif isinstance(data, list):
            for item in data:
                result = self._find_video_data(item)
                if result:
                    return result
        return None

    async def _get_video_id(self, share_url: str) -> str:
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15",
        }
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(share_url, headers=headers)
            final_url = str(response.url)

        # 从URL中提取ID
        match = re.search(r"/video/(\d+)", final_url)
        if match:
            return match.group(1)

        match = re.search(r"/item/(\d+)", final_url)
        if match:
            return match.group(1)

        parsed = urlparse(final_url)
        params = parse_qs(parsed.query)
        if "item_id" in params:
            return params["item_id"][0]

        raise ValueError("从今日头条分享链接中提取视频ID失败")
