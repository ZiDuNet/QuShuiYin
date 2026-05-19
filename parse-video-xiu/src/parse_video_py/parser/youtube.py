import json
import re

import httpx

from .base import BaseParser, VideoAuthor, VideoInfo


class YouTube(BaseParser):
    async def parse_share_url(self, share_url: str) -> VideoInfo:
        video_id = self._extract_video_id(share_url)
        return await self.parse_video_id(video_id)

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        url = f"https://www.youtube.com/watch?v={video_id}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }

        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            html = response.text

        # 尝试从 ytInitialPlayerResponse 提取
        match = re.search(r"ytInitialPlayerResponse\s*=\s*({.+?});", html)
        if match:
            try:
                player_data = json.loads(match.group(1))
                return self._parse_player_data(player_data, url)
            except Exception:
                pass

        # 降级到 yt-dlp
        return self._fallback_ytdlp(url)

    def _parse_player_data(self, data: dict, original_url: str) -> VideoInfo:
        streaming = data.get("streamingData", {})
        formats = streaming.get("formats", [])

        video_url = ""
        for fmt in formats:
            url = fmt.get("url")
            if url:
                video_url = url
                break

        # 如果有 signatureCipher 说明需要解密，降级 yt-dlp
        if not video_url:
            for fmt in formats:
                if fmt.get("signatureCipher"):
                    return self._fallback_ytdlp(original_url)

        # 音频URL
        music_url = ""
        adaptive = streaming.get("adaptiveFormats", [])
        for fmt in adaptive:
            if "audio/" in fmt.get("mimeType", ""):
                url = fmt.get("url")
                if url:
                    music_url = url
                    break

        # 视频详情
        details = data.get("videoDetails", {})
        title = details.get("title", "")
        cover_url = ""
        thumbnails = details.get("thumbnail", {}).get("thumbnails", [])
        if thumbnails:
            cover_url = thumbnails[-1].get("url", "")

        author = VideoAuthor(
            uid=details.get("channelId", ""),
            name=details.get("author", ""),
        )

        return VideoInfo(
            video_url=video_url,
            cover_url=cover_url,
            title=title,
            music_url=music_url,
            author=author,
        )

    def _fallback_ytdlp(self, url: str) -> VideoInfo:
        try:
            import yt_dlp
        except ImportError:
            raise ImportError("YouTube 解析需要安装 yt-dlp: pip install yt-dlp")

        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "extract_flat": False,
            "nocheckcertificate": True,
            "format": "best[ext=mp4]",
            "extractor_args": {
                "youtube": {"player_client": ["web_creator", "web"]}
            },
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        if not info:
            raise ValueError("YouTube 解析失败")

        video_url = info.get("url", "")
        if not video_url:
            formats = info.get("formats", [])
            for fmt in formats:
                if fmt.get("ext") == "mp4" and fmt.get("url"):
                    video_url = fmt["url"]
                    break

        return VideoInfo(
            video_url=video_url,
            cover_url=info.get("thumbnail", ""),
            title=info.get("title", ""),
            author=VideoAuthor(
                uid=info.get("channel_id", ""),
                name=info.get("uploader", "") or info.get("channel", ""),
            ),
        )

    @staticmethod
    def _extract_video_id(url: str) -> str:
        # youtu.be 短链接
        match = re.search(r"youtu\.be/([a-zA-Z0-9_-]+)", url)
        if match:
            return match.group(1)

        # 标准 watch?v= 链接
        match = re.search(r"[?&]v=([a-zA-Z0-9_-]+)", url)
        if match:
            return match.group(1)

        # embed 链接
        match = re.search(r"/embed/([a-zA-Z0-9_-]+)", url)
        if match:
            return match.group(1)

        raise ValueError("从YouTube链接中提取视频ID失败")
