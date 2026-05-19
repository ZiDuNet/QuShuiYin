from .base import BaseParser, VideoAuthor, VideoInfo, ImgInfo


class Instagram(BaseParser):
    async def parse_share_url(self, share_url: str) -> VideoInfo:
        info = self._extract_via_ytdlp(share_url)
        return info

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        raise NotImplementedError("Instagram 暂不支持通过视频ID解析")

    def _extract_via_ytdlp(self, url: str) -> VideoInfo:
        try:
            import yt_dlp
        except ImportError:
            raise ImportError("Instagram 解析需要安装 yt-dlp: pip install yt-dlp")

        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "extract_flat": False,
            "nocheckcertificate": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        if not info:
            raise ValueError("Instagram 解析失败")

        # 视频URL
        video_url = ""
        entries = info.get("entries", [])
        if entries:
            for entry in entries:
                if entry.get("ext") == "mp4" or entry.get(
                    "url", ""
                ).endswith(".mp4"):
                    video_url = entry.get("url", "")
                    break
        elif info.get("url") and info.get("ext") == "mp4":
            video_url = info["url"]

        # 封面
        cover_url = ""
        if entries:
            cover_url = entries[0].get("thumbnail", "")
        cover_url = cover_url or info.get("thumbnail", "")

        # 标题
        title = info.get("title", "")
        desc = info.get("description", "")
        if desc and title not in desc:
            title = f"{title}\n{desc[:200]}".strip()
        elif not title:
            title = desc[:200]

        # 图集
        images = []
        if entries:
            for entry in entries:
                ext = entry.get("ext", "")
                if ext not in ("mp4",) and "video" not in str(
                    entry.get("formats", [])
                ):
                    img_url = entry.get("url", "")
                    if img_url:
                        images.append(ImgInfo(url=img_url))
        elif info.get("ext") not in ("mp4",) and info.get("url"):
            images.append(ImgInfo(url=info["url"]))

        # 作者
        author = VideoAuthor(
            uid=info.get("uploader_id", ""),
            name=info.get("uploader", ""),
        )

        return VideoInfo(
            video_url=video_url,
            cover_url=cover_url,
            title=title,
            images=images,
            author=author,
        )
