"""抖音解析器 — 基于 media-parser API 方式

核心逻辑：
1. 从 URL 中提取视频 ID
2. 先访问页面获取完整 Cookie（ttwid + 页面产生的其他 cookie）
3. 通过 a_bogus 签名调用抖音 API
4. API: /aweme/v1/web/aweme/detail/?aweme_id={id}&msToken={token}&a_bogus={abogus}
"""

import re

import httpx

from ..douyin_utils.signer import DouyinSigner
from .base import BaseParser, ImgInfo, VideoAuthor, VideoInfo


class DouYin(BaseParser):

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        from urllib.parse import urlparse

        host = urlparse(share_url).netloc

        # 短链接需要先获取重定向地址
        if "v.douyin.com" in host:
            redirect_url = await self._resolve_short_url_raw(share_url)
            if "/user/" in redirect_url:
                return await self._parse_user_profile(redirect_url)
            video_id = self._extract_id(redirect_url)
            if not video_id:
                raise Exception("短链接无法解析视频 ID")
        else:
            if "/user/" in share_url:
                return await self._parse_user_profile(share_url)
            video_id = self._extract_id(share_url)
            if not video_id:
                raise Exception("无法从链接中提取视频 ID")

        return await self._parse_by_id(video_id)

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        return await self._parse_by_id(video_id)

    async def _parse_by_id(self, video_id: str) -> VideoInfo:
        """通过 API 获取视频详情，失败则降级到第三方"""
        detail = None
        for attempt in range(2):
            detail = await self._fetch_detail(video_id)
            if detail:
                break
            DouyinSigner.clear_cache()

        if detail:
            return self._format_detail(detail)

        # 降级: 第三方 API（视频）
        try:
            return await self._fallback_parse(video_id)
        except Exception:
            pass

        # 降级: 第三方 API（实况/图集）
        return await self._fallback_live_parse(video_id)

    async def _fetch_detail(self, video_id: str) -> dict | None:
        """先访问页面获取 Cookie，再调用 API"""
        page_url = f"https://www.douyin.com/video/{video_id}?previous_page=web_code_link"
        headers = {
            "User-Agent": DouyinSigner.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://www.douyin.com/",
            "sec-ch-ua": '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        }

        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            # 步骤1: 访问页面获取 Cookie
            await client.get(page_url, headers=headers, follow_redirects=True)

            # 步骤2: 获取 ttwid（如果没有从页面获得）
            cookies = dict(client.cookies)
            if "ttwid" not in cookies:
                ttwid = DouyinSigner.get_ttwid()
                if ttwid:
                    client.cookies.set("ttwid", ttwid, domain=".douyin.com")

            # 步骤3: 调用 API
            ms_token = DouyinSigner.get_ms_token()
            base_url = (
                f"https://www.douyin.com/aweme/v1/web/aweme/detail/"
                f"?device_platform=webapp&aid=6383&channel=channel_pc_web"
                f"&pc_client_type=1&version_code=170400&version_name=17.4.0"
                f"&cookie_enabled=true&screen_width=1920&screen_height=1080"
                f"&browser_language=zh-CN&browser_platform=Win32"
                f"&browser_name=Chrome&browser_version=123.0.0.0"
                f"&browser_online=true&engine_name=Blink&engine_version=123.0.0.0"
                f"&os_name=Windows&os_version=10&cpu_core_num=12"
                f"&device_memory=8&platform=PC&downlink=10"
                f"&effective_type=4g&round_trip_time=50"
                f"&aweme_id={video_id}&msToken={ms_token}"
            )

            a_bogus = DouyinSigner.get_a_bogus(base_url)
            api_url = f"{base_url}&a_bogus={a_bogus}"

            api_headers = {
                "User-Agent": DouyinSigner.USER_AGENT,
                "Referer": page_url,
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "sec-ch-ua": '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Dest": "empty",
            }

            resp = await client.get(api_url, headers=api_headers)
            if resp.status_code != 200:
                return None
            data = resp.json()
            return data.get("aweme_detail")

    def _extract_id(self, url: str) -> str:
        """从各种 URL 格式中提取视频 ID"""
        patterns = [
            r"/video/(\d+)",
            r"modal_id=(\d+)",
            r"/note/(\d+)",
            r"/share/slides/(\d+)",
            r"/share/video/(\d+)",
        ]
        for pattern in patterns:
            m = re.search(pattern, url)
            if m:
                return m.group(1)
        return ""

    async def _resolve_short_url_raw(self, url: str) -> str:
        """解析 v.douyin.com 短链接，返回重定向后的完整 URL"""
        full_headers = {
            "User-Agent": DouyinSigner.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://www.douyin.com/",
        }

        # 方法1: 跟踪重定向
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
                response = await client.get(url, headers=full_headers)
                final_url = str(response.url)
                if final_url and "www.douyin.com" in final_url:
                    return final_url
        except Exception:
            pass

        # 方法2: 手动获取 Location
        try:
            async with httpx.AsyncClient(follow_redirects=False, timeout=10) as client:
                response = await client.get(url, headers=full_headers)
                location = response.headers.get("location", "")
                if location:
                    return location
        except Exception:
            pass

        # 方法3: 带 cookie
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
                ttwid = DouyinSigner.get_ttwid()
                if ttwid:
                    client.cookies.set("ttwid", ttwid, domain=".douyin.com")
                response = await client.get(url, headers=full_headers)
                return str(response.url)
        except Exception:
            pass

        return ""

    def _format_detail(self, detail: dict) -> VideoInfo:
        """将 aweme_detail 转为 VideoInfo"""
        # 作者
        author_data = detail.get("author") or {}
        avatar_thumb = author_data.get("avatar_thumb") or {}
        avatar_urls = avatar_thumb.get("url_list") or []
        author_name = author_data.get("nickname", "")
        author_uid = author_data.get("unique_id") or author_data.get("short_id", "")
        author_avatar = avatar_urls[0] if avatar_urls else ""

        # 标题
        title = detail.get("desc", "")

        # 封面 — 优先动态封面
        cover_url = ""
        video_data = detail.get("video") or {}
        dynamic_cover = video_data.get("dynamic_cover") or {}
        cover_urls = dynamic_cover.get("url_list") or []
        if cover_urls:
            cover_url = cover_urls[0]
        if not cover_url:
            cover = video_data.get("cover") or {}
            cover_urls = cover.get("url_list") or []
            if cover_urls:
                cover_url = cover_urls[0]

        # 视频
        video_url = ""
        images_raw = detail.get("images") or []
        if not images_raw:
            bit_rate = video_data.get("bit_rate") or []
            if bit_rate:
                play_addr = bit_rate[0].get("play_addr") or {}
                url_list = play_addr.get("url_list") or []
                if len(url_list) >= 3:
                    video_url = url_list[2]
                elif url_list:
                    video_url = url_list[0]
            if not video_url:
                play_addr = video_data.get("play_addr") or {}
                url_list = play_addr.get("url_list") or []
                if url_list:
                    video_url = url_list[0].replace("playwm", "play")

        # 音乐 — 图集时不提取
        music_url = ""
        if not images_raw:
            music = detail.get("music") or {}
            play_url = music.get("play_url") or {}
            music_urls = play_url.get("url_list") or []
            if music_urls:
                music_url = music_urls[0]

        # 图片/实况
        images = []
        for img in images_raw:
            if not img:
                continue
            url_list = img.get("url_list") or []
            img_url = url_list[-1] if url_list else ""

            live_url = ""
            img_video = img.get("video") or {}
            play_addr = img_video.get("play_addr") or {}
            live_urls = play_addr.get("url_list") or []
            if live_urls:
                live_url = live_urls[0].replace("playwm", "play")

            images.append(ImgInfo(url=img_url, live_photo_url=live_url))

        return VideoInfo(
            video_url=video_url,
            cover_url=cover_url,
            title=title,
            music_url=music_url,
            images=images,
            author=VideoAuthor(uid=author_uid, name=author_name, avatar=author_avatar),
        )

    async def _fallback_parse(self, video_id: str) -> VideoInfo:
        """降级: 调用第三方 API 解析"""
        # 构造一个抖音 URL 给第三方 API
        share_url = f"https://www.douyin.com/video/{video_id}"
        api_url = f"https://api.bugpk.com/api/douyin?url={share_url}"

        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                resp = await client.get(api_url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                })
                resp.raise_for_status()
                data = resp.json()
        except Exception:
            raise Exception("抖音视频详情获取失败（第三方降级也失败）")

        # 适配第三方返回格式
        d = data.get("data") or data.get("video_info") or data
        if isinstance(d, str):
            raise Exception("抖音第三方解析返回异常")

        video_url = d.get("video_url") or d.get("nwm_video_url") or d.get("wm_video_url") or ""
        cover_url = d.get("cover") or d.get("cover_url") or ""
        title = d.get("title") or d.get("desc") or ""
        music_url = d.get("music_url") or d.get("audio_url") or ""

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

    async def _fallback_live_parse(self, video_id: str) -> VideoInfo:
        """降级: 调用第三方实况/图集 API"""
        import urllib.parse
        share_url = f"https://www.douyin.com/video/{video_id}"
        api_url = f"https://api.bugpk.com/api/dylive?url={urllib.parse.quote(share_url, safe='')}"

        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(api_url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            })
            resp.raise_for_status()
            data = resp.json()

        d = data.get("data") or data
        if isinstance(d, str):
            raise Exception("抖音视频详情获取失败（所有降级均失败）")

        video_url = d.get("video_url") or d.get("nwm_video_url") or d.get("wm_video_url") or ""
        cover_url = d.get("cover") or d.get("cover_url") or ""
        title = d.get("title") or d.get("desc") or ""

        author = d.get("author") or {}
        if isinstance(author, str):
            author = {"nickname": author}

        images = []
        for img in d.get("images") or d.get("image_list") or []:
            if isinstance(img, str):
                images.append(ImgInfo(url=img))
            elif isinstance(img, dict):
                url = img.get("url") or img.get("origin") or ""
                live = img.get("live_photo_url") or img.get("video_url") or ""
                images.append(ImgInfo(url=url, live_photo_url=live))

        return VideoInfo(
            video_url=video_url,
            cover_url=cover_url,
            title=title,
            images=images,
            author=VideoAuthor(
                name=author.get("nickname") or author.get("name") or "",
                avatar=author.get("avatar") or author.get("avatar_url") or "",
            ),
        )

    async def _parse_user_profile(self, share_url: str) -> VideoInfo:
        """解析抖音主页（通过 bugpk 第三方接口）"""
        import urllib.parse
        api_url = f"https://api.bugpk.com/api/dyzy?url={urllib.parse.quote(share_url, safe='')}&count=1"

        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(api_url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            })
            resp.raise_for_status()
            data = resp.json()

        d = data.get("data") or data
        if isinstance(d, str):
            raise Exception("抖音主页解析失败")

        items = d if isinstance(d, list) else [d]
        if not items:
            raise Exception("抖音主页无作品")

        first = items[0] if isinstance(items[0], dict) else {}
        video_url = first.get("video_url") or first.get("nwm_video_url") or first.get("wm_video_url") or first.get("url") or ""
        cover_url = first.get("cover") or first.get("cover_url") or ""
        title = first.get("title") or first.get("desc") or ""
        author = first.get("author") or {}
        if isinstance(author, str):
            author = {"nickname": author}

        images = []
        for img in first.get("images") or first.get("image_list") or []:
            if isinstance(img, str):
                images.append(ImgInfo(url=img))
            elif isinstance(img, dict):
                images.append(ImgInfo(url=img.get("url") or img.get("origin") or ""))

        return VideoInfo(
            video_url=video_url,
            cover_url=cover_url,
            title=title,
            images=images,
            author=VideoAuthor(
                name=author.get("nickname") or author.get("name") or "",
                avatar=author.get("avatar") or author.get("avatar_url") or "",
            ),
        )
