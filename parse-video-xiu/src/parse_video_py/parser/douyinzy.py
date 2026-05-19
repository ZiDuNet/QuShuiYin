import re
from urllib.parse import urlparse, parse_qs

import httpx

from .base import BaseParser, VideoAuthor, VideoInfo, ImgInfo


class DouyinZY(BaseParser):
    async def parse_share_url(self, share_url: str) -> VideoInfo:
        sec_uid = self._extract_sec_uid(share_url)
        return await self._fetch_user_posts(sec_uid)

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        raise NotImplementedError("抖音主页暂不支持通过视频ID解析，请使用分享链接")

    async def _fetch_user_posts(self, sec_uid: str) -> VideoInfo:
        api_url = "https://www.douyin.com/aweme/v1/web/aweme/post/"
        params = {
            "device_platform": "webapp",
            "aid": "6383",
            "channel": "channel_pc_web",
            "sec_user_id": sec_uid,
            "max_cursor": 0,
            "count": 18,
            "publish_video_strategy_type": "2",
            "pc_client_type": "1",
            "version_code": "170400",
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": f"https://www.douyin.com/user/{sec_uid}",
        }

        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
            response = await client.get(api_url, params=params, headers=headers)
            data = response.json()

        aweme_list = data.get("aweme_list", [])
        if not aweme_list:
            raise ValueError("抖音主页解析失败，未获取到作品列表（可能需要Cookie）")

        # 返回第一个视频的信息（主页模式）
        first = aweme_list[0]
        return self._parse_aweme(first)

    def _parse_aweme(self, item: dict) -> VideoInfo:
        video_url = ""
        video_data = item.get("video", {})
        play_addr = video_data.get("play_addr", {})
        url_list = play_addr.get("url_list", [])
        if url_list:
            video_url = url_list[0].replace("playwm", "play")

        cover_url = ""
        cover_data = video_data.get("cover", {})
        cover_urls = cover_data.get("url_list", [])
        if cover_urls:
            cover_url = cover_urls[0]

        # 图集
        images = []
        raw_images = item.get("images", [])
        if isinstance(raw_images, list):
            for img in raw_images:
                img_urls = img.get("url_list", [])
                if img_urls:
                    images.append(ImgInfo(url=img_urls[0]))

        # 音乐
        music_url = ""
        music_data = item.get("music", {})
        play_url = music_data.get("play_url", {})
        music_urls = play_url.get("url_list", [])
        if music_urls:
            music_url = music_urls[0]

        # 作者
        author_data = item.get("author", {})
        avatar_urls = author_data.get("avatar_larger", {}).get("url_list", [])

        return VideoInfo(
            video_url=video_url,
            cover_url=cover_url,
            title=item.get("desc", ""),
            music_url=music_url,
            images=images,
            author=VideoAuthor(
                uid=author_data.get("sec_uid", ""),
                name=author_data.get("nickname", ""),
                avatar=avatar_urls[0] if avatar_urls else "",
            ),
        )

    @staticmethod
    def _extract_sec_uid(url: str) -> str:
        parsed = urlparse(url)
        # /user/SEC_UID
        match = re.search(r"/user/([a-zA-Z0-9_-]+)", parsed.path)
        if match:
            return match.group(1)

        # 查询参数
        params = parse_qs(parsed.query)
        if "sec_uid" in params:
            return params["sec_uid"][0]

        raise ValueError("从抖音主页链接中提取 sec_uid 失败")
