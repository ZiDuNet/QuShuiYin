"""小红书解析器 — 基于 short_videos/XiaohongshuParser.php 移植

核心逻辑：
1. 从 URL 中提取笔记 ID（支持 xhslink.com 短链接重定向）
2. 请求页面，提取 __INITIAL_STATE__ JSON
3. 解析视频流（h265/h264 按码率排序）和图片（去水印处理）
"""

import json
import re
from urllib.parse import urlparse

import httpx

from .base import BaseParser, ImgInfo, VideoAuthor, VideoInfo


class RedBook(BaseParser):

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        try:
            return await self._parse_main(share_url)
        except Exception:
            return await self._fallback_parse(share_url)

    async def _parse_main(self, share_url: str) -> VideoInfo:
        # 预处理: xhs.com → xhslink.com
        share_url = share_url.replace("xhs.com", "xhslink.com")

        parsed = urlparse(share_url)
        host = parsed.netloc

        # 提取 ID
        note_id = self._extract_id(share_url)
        if not note_id and host != "www.xiaohongshu.com":
            # 短链接需要重定向
            share_url = await self._get_real_url(share_url)
            note_id = self._extract_id(share_url)

        if not note_id:
            raise Exception("无法从小红书链接中提取笔记 ID")

        # 请求页面
        headers = self._pc_headers()
        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
            resp = await client.get(share_url, headers=headers)
            resp.raise_for_status()
            html = resp.text

        note = self._extract_note(html, note_id)

        # 如果 PC UA 失败，用移动 UA 重试
        if not note:
            headers = self._mobile_headers()
            async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
                resp = await client.get(share_url, headers=headers)
                resp.raise_for_status()
                note = self._extract_note(resp.text, note_id)

        if not note:
            raise Exception("小红书页面解析失败")

        return self._format_note(note)

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        url = f"https://www.xiaohongshu.com/explore/{video_id}"
        return await self.parse_share_url(url)

    async def _fallback_parse(self, share_url: str) -> VideoInfo:
        """降级: 调用 bugpk 第三方 API"""
        api_url = f"https://api.bugpk.com/api/xhs?url={share_url}"
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

    def _pc_headers(self) -> dict:
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }

    def _mobile_headers(self) -> dict:
        return {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Mobile Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }

    def _extract_id(self, url: str) -> str:
        patterns = [
            r"/discovery/item/([a-zA-Z0-9]+)",
            r"/explore/([a-zA-Z0-9]+)",
            r"/item/([a-zA-Z0-9]+)",
            r"/note/([a-zA-Z0-9]+)",
        ]
        for p in patterns:
            m = re.search(p, url)
            if m:
                return m.group(1)
        return ""

    async def _get_real_url(self, url: str) -> str:
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
                resp = await client.get(url, headers=self._pc_headers())
                return str(resp.url)
        except Exception:
            return url

    def _extract_note(self, html: str, note_id: str) -> dict | None:
        """从 __INITIAL_STATE__ 中提取笔记数据"""
        pattern = r"<script>\s*window\.__INITIAL_STATE__\s*=\s*({[\s\S]*?})</script>"
        m = re.search(pattern, html)
        if not m:
            return None

        json_str = m.group(1).replace("undefined", "null")
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            return None

        # 路径1: note.noteDetailMap.id.note
        note_detail = data.get("note", {}).get("noteDetailMap", {}).get(note_id, {})
        note = note_detail.get("note")

        # 路径2: noteData.data.noteData
        if not note:
            note = data.get("noteData", {}).get("data", {}).get("noteData")

        return note

    def _format_note(self, note: dict) -> VideoInfo:
        """格式化笔记数据"""
        note_type = note.get("type", "unknown")
        if note_type == "normal":
            note_type = "image"

        title = note.get("title", "")
        desc = note.get("desc", "")
        display_title = title or desc

        user = note.get("user", {})
        author_name = user.get("nickname", user.get("nickName", ""))
        author_avatar = user.get("avatar", "")

        # 封面
        cover_url = self._extract_cover(note)

        # 视频流
        video_url = ""
        if note_type == "video":
            video_url = self._extract_video_url(note)

        # 图片和实况
        images = []
        live_photos = []
        image_list = note.get("imageList", [])
        for img in image_list:
            img_url = img.get("url") or img.get("urlDefault") or img.get("urlPre") or ""
            img_url = self._process_image_url(img_url)
            if img_url:
                images.append(ImgInfo(url=img_url))

            # 实况视频
            live_url = ""
            for codec in ("h264", "h265"):
                streams = img.get("stream", {}).get(codec, [])
                if streams and streams[0].get("masterUrl"):
                    live_url = streams[0]["masterUrl"]
                    break
            if live_url:
                images[-1] = ImgInfo(url=img_url, live_photo_url=live_url)

        return VideoInfo(
            video_url=video_url,
            cover_url=cover_url,
            title=display_title,
            images=images,
            author=VideoAuthor(
                uid=user.get("userId", ""),
                name=author_name,
                avatar=author_avatar,
            ),
        )

    def _extract_cover(self, note: dict) -> str:
        """提取封面 URL"""
        image_list = note.get("imageList", [])
        if image_list:
            first = image_list[0]
            for key in ("urlPre", "urlDefault", "url"):
                url = first.get(key, "")
                if url:
                    return self._process_image_url(url)

        # video.image.thumbnailFileid
        thumb = note.get("video", {}).get("image", {}).get("thumbnailFileid", "")
        if thumb:
            return f"https://sns-img-hw.xhscdn.com/{thumb}"

        cover = note.get("cover", {})
        if isinstance(cover, dict):
            url = cover.get("url", "")
            if url:
                return url
            file_id = cover.get("fileId", "")
            if file_id:
                return f"https://sns-img-hw.xhscdn.com/{file_id}?imageView2/2/w/0/format/jpg"

        return ""

    def _extract_video_url(self, note: dict) -> str:
        """提取最高画质视频 URL"""
        streams = []
        video = note.get("video", {})
        media = video.get("media", {}).get("stream", {})

        for codec in ("h265", "h264"):
            for s in media.get(codec, []):
                s["_codec"] = codec
                streams.append(s)

        if streams:
            # 优先 h265，其次按码率降序
            streams.sort(key=lambda x: (
                0 if x.get("_codec") == "h265" else 1,
                -(x.get("avgBitrate") or x.get("videoBitrate") or 0),
            ))
            return streams[0].get("masterUrl", "")

        # 兜底: originVideoKey
        key = video.get("consumer", {}).get("originVideoKey", "")
        if key:
            return f"http://sns-video-bd.xhscdn.com/{key}"

        return ""

    def _process_image_url(self, url: str) -> str:
        """处理图片链接，去水印"""
        if not url:
            return ""

        # 处理 oss-sg 路径
        m = re.search(r"/oss-sg/([a-zA-Z0-9_]+)/([a-zA-Z0-9]+)!", url)
        if m:
            return f"https://sns-img-hw.xhscdn.com/oss-sg/{m.group(1)}/{m.group(2)}?imageView2/2/w/0/format/jpg"

        # 处理 notes_pre_post / spectrum
        m = re.search(r"/([a-zA-Z0-9_]+)/([a-zA-Z0-9]+)!", url)
        if m:
            dir_name = m.group(1)
            if not re.match(r"^[a-f0-9]{32}$", dir_name) and not dir_name.isdigit():
                return f"https://sns-img-hw.xhscdn.com/{dir_name}/{m.group(2)}?imageView2/2/w/0/format/jpg"

        # 不带 ! 的短链接
        m = re.search(r"(notes_pre_post|spectrum|notes_uhdr)/([a-zA-Z0-9]+)", url)
        if m:
            return f"https://sns-img-hw.xhscdn.com/{m.group(1)}/{m.group(2)}?imageView2/2/w/0/format/jpg"

        return url
