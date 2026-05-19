import re
import urllib.parse

import httpx

from .base import BaseParser, VideoAuthor, VideoInfo

# 匹配央视网页面中嵌入的视频 GUID
_cctv_guid_re = re.compile(r'var\s+guid\s*=\s*"([^"]+)"')


class CCTV(BaseParser):
    """央视网解析 — 支持 bugpk 降级"""

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        try:
            guid = await self._extract_guid(share_url)
            return await self.parse_video_id(guid)
        except Exception:
            return await self._fallback_parse(share_url)

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        if not video_id:
            raise ValueError("视频GUID不能为空")

        api_url = f"https://vdn.apps.cntv.cn/api/getHttpVideoInfo.do?pid={video_id}"

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(api_url, headers=self.get_default_headers())
            response.raise_for_status()

        data = response.json()

        status = data.get("status", "")
        if status != "001":
            raise Exception(f"央视网视频API返回错误 (status: {status})")

        video_url = data.get("hls_url", "")
        if not video_url:
            raise Exception("未找到视频播放地址")

        title = data.get("title", "")
        cover_url = data.get("image", "")
        play_channel = data.get("play_channel", "")

        return VideoInfo(
            video_url=video_url,
            cover_url=cover_url,
            title=title,
            author=VideoAuthor(name=play_channel),
        )

    async def _extract_guid(self, page_url: str) -> str:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(page_url, headers=self.get_default_headers())
            response.raise_for_status()

        return self._extract_guid_from_html(response.text)

    @staticmethod
    def _extract_guid_from_html(html: str) -> str:
        match = _cctv_guid_re.search(html)
        if match and match.group(1):
            return match.group(1)
        raise ValueError("页面中未找到视频GUID")

    async def _fallback_parse(self, share_url: str) -> VideoInfo:
        """降级: 调用 bugpk 聚合接口"""
        api_url = f"https://api.bugpk.com/api/short_videos?url={urllib.parse.quote(share_url, safe='')}"
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(api_url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            })
            resp.raise_for_status()
            data = resp.json()

        d = data.get("data") or data
        if isinstance(d, str):
            raise Exception("央视网第三方降级解析失败")

        return VideoInfo(
            video_url=d.get("url") or "",
            cover_url=d.get("cover") or "",
            title=d.get("title") or "",
            author=VideoAuthor(name=str(d.get("author") or ""), avatar=d.get("avatar") or ""),
        )
