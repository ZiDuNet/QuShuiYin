import re

import httpx

from .base import BaseParser, VideoAuthor, VideoInfo


class HuoShan(BaseParser):
    async def parse_share_url(self, share_url: str) -> VideoInfo:
        video_id = await self._get_video_id_from_share_url(share_url)
        return await self.parse_video_id(video_id)

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        req_url = f"https://share.huoshan.com/api/item/info?item_id={video_id}"
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(req_url, headers=self.get_default_headers())
            data = response.json()

        item_info = data.get("data", {}).get("item_info", {})
        video_url = item_info.get("url", "")
        cover_url = item_info.get("cover", "")

        return VideoInfo(
            video_url=video_url,
            cover_url=cover_url,
        )

    async def _get_video_id_from_share_url(self, share_url: str) -> str:
        async with httpx.AsyncClient(follow_redirects=False) as client:
            response = await client.get(share_url, headers=self.get_default_headers())

        location = response.headers.get("location", "")
        if not location:
            raise ValueError("火山分享链接重定向失败")

        match = re.search(r"item_id=(\d+)", location)
        if not match:
            raise ValueError("从分享链接中提取视频ID失败")

        return match.group(1)
