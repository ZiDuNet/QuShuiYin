"""微博解析器 — 基于 short_videos/weibo_v.php 移植

核心逻辑：
1. 从 URL 中提取视频 ID（支持 show?fid=、/tv/show/、layerid= 等多种格式）
2. POST h5.video.weibo.com/api/component 获取视频信息
3. 解析 stream_url / urls 中的视频地址
4. 通过第三方代理解决 CDN 防盗链 403
"""

import base64
import re
from urllib.parse import parse_qs, urlparse

import fake_useragent
import httpx

from .base import BaseParser, ImgInfo, VideoAuthor, VideoInfo

# 第三方代理（主用）
PROXY_URL = "https://svproxy.168299.xyz/?type=weibo&proxyurl="
# 备用代理
PROXY_URL_BACKUP = "https://api.bugpk.com/api/weibo?proxyurl="


def _proxy(url: str) -> str:
    """通过第三方代理包装 URL，绕过防盗链"""
    if not url:
        return url
    if not url.startswith("http"):
        url = f"https:{url}"
    return PROXY_URL + base64.b64encode(url.encode()).decode()


class WeiBo(BaseParser):

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        try:
            return await self._parse_main(share_url)
        except Exception:
            return await self._fallback_parse(share_url)

    async def _parse_main(self, share_url: str) -> VideoInfo:
        video_id = self._extract_video_id(share_url)
        if video_id:
            return await self.parse_video_id(video_id)

        # 非视频链接，尝试解析图集
        parsed = urlparse(share_url)
        path_parts = parsed.path.strip("/").split("/")
        if len(path_parts) >= 2:
            post_id = path_parts[-1]
            return await self._parse_post(post_id, share_url)

        raise Exception("unsupported weibo url format")

    def _extract_video_id(self, url: str) -> str:
        """从各种 URL 格式中提取视频 ID"""
        parsed = urlparse(url)
        query = parse_qs(parsed.query)

        # show?fid=xxx
        if "fid" in query:
            return query["fid"][0]

        # /tv/show/xxx
        if "/tv/show/" in parsed.path:
            return parsed.path.replace("/tv/show/", "").strip("/")

        # layerid=xxx (新版视频页)
        if "layerid" in query:
            return query["layerid"][0]

        # mid=xxx (另一种格式)
        if "mid" in query:
            return query["mid"][0]

        # video.weibo.com/show?fid=xxx
        if "show" in parsed.path and "fid" in query:
            return query["fid"][0]

        return ""

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        """通过视频 ID 解析，使用 h5.video.weibo.com API"""
        req_url = f"https://h5.video.weibo.com/api/component?page=/show/{video_id}"
        headers = {
            "User-Agent": fake_useragent.UserAgent(os=["ios"]).random,
            "Referer": f"https://h5.video.weibo.com/show/{video_id}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        post_data = f'data={{"Component_Play_Playinfo":{{"oid":"{video_id}"}}}}'

        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
            response = await client.post(req_url, headers=headers, content=post_data)
            response.raise_for_status()

        json_data = response.json()
        play_info = json_data.get("data", {}).get("Component_Play_Playinfo", {})

        if not play_info:
            raise Exception("微博视频信息获取失败")

        # 视频地址: urls 中第一条画质最高
        video_url = play_info.get("stream_url", "")
        urls = play_info.get("urls", {})
        if urls:
            _, first_url = next(iter(urls.items()))
            if first_url:
                video_url = first_url

        # 封面
        cover = play_info.get("cover_image", "")

        # 头像
        avatar = play_info.get("avatar", "")

        return VideoInfo(
            video_url=_proxy(video_url),
            cover_url=_proxy(cover),
            title=play_info.get("title", ""),
            author=VideoAuthor(
                uid=str(play_info.get("user", {}).get("id", "")),
                name=play_info.get("author", ""),
                avatar=_proxy(avatar),
            ),
        )

    async def _parse_post(self, post_id: str, original_url: str) -> VideoInfo:
        """解析微博图文帖子"""
        headers = {
            "User-Agent": fake_useragent.UserAgent(os=["ios"]).random,
            "Referer": "https://m.weibo.cn/",
            "X-Requested-With": "XMLHttpRequest",
        }

        try:
            api_url = f"https://m.weibo.cn/statuses/show?id={post_id}"
            async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
                resp = await client.get(api_url, headers=headers)
                resp.raise_for_status()
                data = resp.json().get("data", {})
                if data:
                    return self._format_post_data(data)
        except Exception:
            pass

        # 备用: 解析桌面版 HTML
        async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
            resp = await client.get(original_url, headers={"User-Agent": headers["User-Agent"]})
            resp.raise_for_status()
            text = resp.content.decode(resp.encoding or "utf-8", errors="replace")
            return self._parse_html(text)

    def _format_post_data(self, data: dict) -> VideoInfo:
        """格式化移动 API 返回的帖子数据"""
        title = re.sub(r"<[^>]*>", "", data.get("text", ""))
        user = data.get("user", {})
        images = []
        for pic in data.get("pics", []):
            for size in ("large", "original", "bmiddle", "url"):
                pic_data = pic.get(size, {})
                if isinstance(pic_data, dict) and pic_data.get("url"):
                    images.append(ImgInfo(url=pic_data["url"]))
                    break

        return VideoInfo(
            video_url="",
            cover_url="",
            title=title,
            images=images,
            author=VideoAuthor(
                name=user.get("screen_name", ""),
                avatar=user.get("avatar_large", ""),
            ),
        )

    async def _fallback_parse(self, share_url: str) -> VideoInfo:
        """降级: 调用 bugpk 第三方 API"""
        api_url = f"https://api.bugpk.com/api/weibo?url={share_url}"
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

    def _parse_html(self, html: str) -> VideoInfo:
        """从桌面版 HTML 中提取数据"""
        pattern = r"\$render_data\s*=\s*(.*?)\[0\]"
        m = re.search(pattern, html)
        if not m:
            raise Exception("parse weibo html page fail")

        import json
        data = json.loads(m.group(1) + "[0]")
        status = data.get("status", {})
        title = re.sub(r"<[^>]*>", "", status.get("text", ""))
        user = status.get("user", {})
        images = []
        for pic in status.get("pics", []):
            for size in ("large", "original", "bmiddle", "url"):
                pic_data = pic.get(size, {})
                if isinstance(pic_data, dict) and pic_data.get("url"):
                    images.append(ImgInfo(url=pic_data["url"]))
                    break

        return VideoInfo(
            video_url="",
            cover_url="",
            title=title,
            images=images,
            author=VideoAuthor(
                name=user.get("screen_name", ""),
                avatar=user.get("avatar_large", ""),
            ),
        )
