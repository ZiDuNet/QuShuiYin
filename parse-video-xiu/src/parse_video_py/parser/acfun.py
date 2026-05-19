import json
import re
import urllib.parse

import httpx
from parsel import Selector

from .base import BaseParser, VideoAuthor, VideoInfo, ImgInfo


class AcFun(BaseParser):
    """A站解析 — 支持视频和图集，降级到 bugpk 聚合接口"""

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        try:
            return await self._parse_main(share_url)
        except Exception:
            return await self._fallback_parse(share_url)

    async def _parse_main(self, share_url: str) -> VideoInfo:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
            response = await client.get(share_url, headers=self.get_default_headers())
            response.raise_for_status()

        # 尝试新版页面结构：window.pageInfo
        re_pattern = r"window\.pageInfo\s*=\s*({.*?});"
        re_result = re.search(re_pattern, response.text, re.DOTALL)
        if re_result:
            try:
                page_data = json.loads(re_result.group(1))
                return self._parse_page_info(page_data)
            except (json.JSONDecodeError, KeyError):
                pass

        # 旧版：var videoInfo
        re_video_pattern = r"var videoInfo =\s(.*?);"
        re_video_result = re.search(re_video_pattern, response.text)
        if re_video_result and len(re_video_result.groups()) >= 1:
            video_data = json.loads(re_video_result.group(1).strip())

            re_play_pattern = r"var playInfo =\s(.*?);"
            re_play_result = re.search(re_play_pattern, response.text)
            if re_play_result and len(re_play_result.groups()) >= 1:
                play_data = json.loads(re_play_result.group(1).strip())

                sel = Selector(response.text)
                uid = (
                    sel.css("div.up-info > a.info-item1::attr(href)")
                    .get(default="")
                    .replace("/upPage/", "")
                )
                name = sel.css("div.up-info span.up-name::text").get(default="")
                avatar = sel.css("div.up-info span.up-avatar > img::attr(src)").get(default="")

                return VideoInfo(
                    video_url=play_data["streams"][0]["playUrls"][0],
                    cover_url=video_data["cover"],
                    title=video_data["title"],
                    author=VideoAuthor(uid=uid, name=name, avatar=avatar),
                )

        raise Exception("AcFun 页面解析失败")

    def _parse_page_info(self, page_data: dict) -> VideoInfo:
        """解析新版 pageInfo 结构"""
        video_data = page_data.get("video") or page_data
        cover_url = video_data.get("coverUrl") or video_data.get("cover") or ""
        title = video_data.get("title") or ""
        video_url = ""

        # 视频流
        play_info = video_data.get("playInfo") or video_data.get("currentVideoInfo") or {}
        ks_play = play_info.get("ksPlay") or ""
        if ks_play:
            # m3u8 链接
            video_url = ks_play

        # 作者
        user = page_data.get("user") or video_data.get("user") or {}
        author_name = user.get("name") or user.get("userName") or ""
        author_avatar = user.get("headUrl") or user.get("avatar") or ""
        author_uid = str(user.get("id") or user.get("userId") or "")

        return VideoInfo(
            video_url=video_url,
            cover_url=cover_url,
            title=title,
            author=VideoAuthor(uid=author_uid, name=author_name, avatar=author_avatar),
        )

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
            raise Exception("AcFun 第三方降级解析失败")

        video_url = d.get("url") or ""
        cover_url = d.get("cover") or ""
        title = d.get("title") or ""
        author_name = str(d.get("author") or "")
        author_avatar = d.get("avatar") or ""

        return VideoInfo(
            video_url=video_url,
            cover_url=cover_url,
            title=title,
            author=VideoAuthor(name=author_name, avatar=author_avatar),
        )

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        req_url = f"https://www.acfun.cn/v/{video_id}"
        return await self.parse_share_url(req_url)
