import httpx

from .base import BaseParser, VideoAuthor, VideoInfo, ImgInfo

_TIKWM_BASE = "https://www.tikwm.com"


class TikTok(BaseParser):
    async def parse_share_url(self, share_url: str) -> VideoInfo:
        return await self._parse_via_tikwm(share_url)

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        url = f"https://www.tiktok.com/@x/video/{video_id}"
        return await self._parse_via_tikwm(url)

    async def _parse_via_tikwm(self, url: str) -> VideoInfo:
        api_url = f"{_TIKWM_BASE}/api/"
        params = {"url": url, "count": 12, "cursor": 0, "web": 1, "hd": 1}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(api_url, params=params, headers=headers)
            data = response.json()

        if data.get("code") != 0:
            raise ValueError(f"TikTok 解析失败: {data.get('msg', '未知错误')}")

        post_data = data.get("data", {})

        # 视频地址
        play_addr = post_data.get("hdplay") or post_data.get("play", "")
        if play_addr and play_addr.startswith("/"):
            play_addr = f"{_TIKWM_BASE}{play_addr}"

        # 封面
        cover = post_data.get("cover", "")
        if cover and cover.startswith("/"):
            cover = f"{_TIKWM_BASE}{cover}"

        # 音乐
        music = post_data.get("music", "")
        if not music:
            music = post_data.get("music_info", {}).get("play", "")
        if music and music.startswith("/"):
            music = f"{_TIKWM_BASE}{music}"

        # 图集
        images = []
        raw_images = post_data.get("images", [])
        if isinstance(raw_images, list):
            for img_url in raw_images:
                images.append(ImgInfo(url=img_url))

        # 作者
        author_data = post_data.get("author", {})
        avatar = author_data.get("avatar", "")
        if avatar and avatar.startswith("/"):
            avatar = f"{_TIKWM_BASE}{avatar}"

        return VideoInfo(
            video_url=play_addr,
            cover_url=cover,
            title=post_data.get("title", ""),
            music_url=music,
            images=images,
            author=VideoAuthor(
                uid=author_data.get("unique_id", "") or str(author_data.get("id", "")),
                name=author_data.get("nickname", ""),
                avatar=avatar,
            ),
        )
