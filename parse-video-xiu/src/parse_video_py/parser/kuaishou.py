"""快手解析器 — 基于 short_videos/KuaishouSpider.php 移植

核心逻辑：
1. 短链接获取重定向 URL，直接 URL 保留
2. 请求页面，提取 INIT_STATE JSON（优先）或 APOLLO_STATE（备用）
3. 从 JSON 中解析视频/图集数据
"""

import json
import re
from urllib.parse import urlparse

import httpx

from .base import BaseParser, ImgInfo, VideoAuthor, VideoInfo


class KuaiShou(BaseParser):

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        try:
            return await self._parse_main(share_url)
        except Exception:
            return await self._fallback_parse(share_url)

    async def _parse_main(self, share_url: str) -> VideoInfo:
        parsed = urlparse(share_url)
        host = parsed.netloc

        # 短链接需要重定向
        if host == "v.kuaishou.com":
            async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
                resp = await client.get(share_url, headers=self._headers())
                redirect_url = str(resp.url)
        else:
            redirect_url = share_url

        # 提取内容类型和 ID
        content_type, content_id = self._extract_content_info(redirect_url)
        if not content_id:
            raise Exception("无法从链接中提取视频/图集 ID")

        # 请求页面
        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
            resp = await client.get(redirect_url, headers=self._page_headers())
            resp.raise_for_status()
            page_content = resp.text

        # 优先 INIT_STATE，备用 APOLLO_STATE
        result = self._extract_from_init_state(page_content)
        if result:
            return result

        result = self._extract_from_apollo_state(page_content, content_id, content_type)
        if result:
            return result

        raise Exception("failed to parse video JSON info from HTML")

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        raise NotImplementedError("快手暂不支持直接解析视频ID")

    async def _fallback_parse(self, share_url: str) -> VideoInfo:
        """降级: 调用 bugpk 第三方 API"""
        api_url = f"https://api.bugpk.com/api/kuaishou?url={share_url}"
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

    def _headers(self) -> dict:
        return {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        }

    def _page_headers(self) -> dict:
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }

    def _extract_content_info(self, url: str) -> tuple[str, str]:
        """从 URL 中提取内容类型和 ID"""
        patterns = {
            "short-video": r"/short-video/([^?/&]+)",
            "long-video": r"/long-video/([^?/&]+)",
            "photo": r"/photo/([^?/&]+)",
            "fw-photo": r"/fw/photo/([^?/&]+)",
            "fw-long-video": r"/fw/long-video/([^?/&]+)",
        }
        for ctype, pattern in patterns.items():
            m = re.search(pattern, url)
            if m:
                return ctype, m.group(1)
        return "", ""

    def _extract_from_init_state(self, page_content: str) -> VideoInfo | None:
        """从 INIT_STATE 中提取数据"""
        pattern = r"window\.INIT_STATE\s*=\s*(.*?)</script>"
        m = re.search(pattern, page_content, re.DOTALL)
        if not m:
            return None

        json_str = m.group(1).strip().rstrip(";")

        # 容错: 清理异常 JSON 值
        json_str = json_str.replace(
            '"{"err_msg":"launchApplication:fail"}"',
            '"err_msg","launchApplication:fail"',
        ).replace(
            '"{"err_msg":"system:access_denied"}"',
            '"err_msg","system:access_denied"',
        )

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            # 尝试 stripslashes
            try:
                data = json.loads(json_str.replace('\\"', '"'))
            except json.JSONDecodeError:
                return None

        # 过滤有效数据（tusjoh 开头的 key）
        photo = {}
        for key, value in data.items():
            if isinstance(key, str) and key.startswith("tusjoh"):
                if isinstance(value, dict) and ("photo" in value or "fid" in value):
                    photo = value.get("photo", {})
                    break

        if not photo:
            return None

        return self._format_photo(photo)

    def _extract_from_apollo_state(
        self, page_content: str, content_id: str, content_type: str
    ) -> VideoInfo | None:
        """从 APOLLO_STATE 中提取数据（备用方案）"""
        pattern = r"window\.__APOLLO_STATE__\s*=\s*(.*?)</script>"
        m = re.search(pattern, page_content, re.DOTALL)
        if not m:
            return None

        # 清理 JS 函数等非 JSON 内容
        raw = m.group(1)
        raw = re.sub(r"function\s*\([^)]*\)\s*\{[^}]*\}", ":", raw)
        raw = raw.replace(";(:());", "")

        try:
            apollo = json.loads(raw)
        except json.JSONDecodeError:
            return None

        default_client = apollo.get("defaultClient", {})
        key = f"VisionVideoDetailPhoto:{content_id}"
        video_data = default_client.get(key)
        if not video_data:
            return None

        # 找作者数据
        author_name = ""
        author_avatar = ""
        for k, v in default_client.items():
            if k.startswith("VisionVideoDetailAuthor:"):
                author_name = v.get("name", "")
                author_avatar = v.get("headerUrl", "")
                break

        video_url = ""
        if content_type in ("long-video", "fw-long-video"):
            try:
                video_url = video_data["manifestH265"]["json"]["adaptationSet"][0][
                    "representation"
                ][0]["backupUrl"][0]
            except (KeyError, IndexError):
                video_url = video_data.get("photoUrl", "")
        else:
            video_url = video_data.get("photoUrl", "")

        if not video_url:
            return None

        return VideoInfo(
            video_url=video_url,
            cover_url=video_data.get("coverUrl", ""),
            title=video_data.get("caption", ""),
            author=VideoAuthor(name=author_name, avatar=author_avatar),
        )

    def _format_photo(self, photo: dict) -> VideoInfo:
        """从 photo 数据格式化输出"""
        title = photo.get("caption", "")
        author_name = photo.get("userName", "")
        author_avatar = photo.get("headUrl", "")
        cover_urls = photo.get("coverUrls", [])
        cover_url = cover_urls[0].get("url", "") if cover_urls else ""

        # 音乐信息
        music_source = photo.get("music", photo.get("soundTrack", {}))
        music_url = ""
        if music_source:
            audio_urls = music_source.get("audioUrls", [])
            music_url = audio_urls[0].get("url", "") if audio_urls else ""

        # 图集
        images = []
        atlas = photo.get("ext_params", {}).get("atlas", {})
        atlas_list = atlas.get("list", [])
        atlas_cdn = atlas.get("cdn", [])
        if atlas_list:
            cdn = atlas_cdn[0] if atlas_cdn else "tx2.a.yximgs.com"
            for path in atlas_list:
                images.append(ImgInfo(url=f"https://{cdn}/{path}"))

        # 单张图片
        if not images and photo.get("photoType") == "SINGLE_PICTURE":
            if cover_url:
                images.append(ImgInfo(url=cover_url))

        # 视频
        video_url = ""
        if not images:
            main_mv = photo.get("mainMvUrls", [])
            if main_mv:
                video_url = main_mv[0].get("url", "")
            if not video_url:
                try:
                    video_url = photo["manifest"]["adaptationSet"][0]["representation"][
                        0
                    ]["url"]
                except (KeyError, IndexError):
                    pass

        return VideoInfo(
            video_url=video_url,
            cover_url=cover_url,
            title=title,
            music_url=music_url,
            images=images,
            author=VideoAuthor(name=author_name, avatar=author_avatar),
        )
