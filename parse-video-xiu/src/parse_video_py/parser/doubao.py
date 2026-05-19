import json
import re
from html import unescape
from urllib.parse import urlparse, parse_qs

import httpx

from .base import BaseParser, VideoAuthor, VideoInfo, ImgInfo


class Doubao(BaseParser):
    async def parse_share_url(self, share_url: str) -> VideoInfo:
        try:
            parsed = urlparse(share_url)
            params = parse_qs(parsed.query)

            share_id = params.get("share_id", [None])[0]
            video_id = params.get("video_id", [None])[0]

            if share_id and video_id:
                return await self._parse_video_share(share_id, video_id)

            return await self._parse_creation_page(share_url)
        except Exception:
            return await self._fallback_parse(share_url)

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        raise NotImplementedError("豆包暂不支持通过视频ID解析")

    async def _parse_video_share(
        self, share_id: str, video_id: str
    ) -> VideoInfo:
        api_url = "https://www.doubao.com/creativity/share/get_video_share_info"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Content-Type": "application/json",
            "Origin": "https://www.doubao.com",
            "Referer": f"https://www.doubao.com/video-sharing?share_id={share_id}&video_id={video_id}",
        }
        payload = {"share_id": share_id, "vid": video_id, "creation_id": ""}
        params = {
            "version_code": "20800",
            "aid": "497858",
            "device_platform": "web",
        }

        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.post(
                api_url, headers=headers, json=payload, params=params
            )
            data = response.json()

        if data.get("code") != 0:
            raise ValueError(f"豆包解析失败: {data.get('msg', '未知错误')}")

        result = data.get("data", {})
        video_url = result.get("video_url", "")
        cover_url = result.get("cover_url", "")
        title = result.get("title", "")

        author_data = result.get("author", {})
        return VideoInfo(
            video_url=video_url,
            cover_url=cover_url,
            title=title,
            author=VideoAuthor(
                uid=str(author_data.get("uid", "")),
                name=author_data.get("name", ""),
                avatar=author_data.get("avatar_url", ""),
            ),
        )

    async def _parse_creation_page(self, share_url: str) -> VideoInfo:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(share_url, headers=headers)
            html = response.text

        # 提取 data-fn-args
        match = re.search(r'data-fn-args="([^"]+)"', html)
        if not match:
            raise ValueError("豆包页面解析失败")

        raw_args = unescape(match.group(1))
        args = json.loads(raw_args)

        # 递归查找 creations 列表
        creations = self._find_creations(args)
        if not creations:
            raise ValueError("豆包未找到创作内容")

        # 提取第一个创作的内容
        first = creations[0]
        video_url = ""
        cover_url = ""
        images = []

        # 视频内容
        if "video" in first and isinstance(first["video"], dict):
            download_url = first["video"].get("download_url", "")
            if download_url and "watermark" not in download_url:
                video_url = download_url
            else:
                video_list = first.get("video_model", {}).get("video_list", [])
                for v in video_list:
                    v_url = v.get("main_url", "")
                    if v_url and "watermark" not in v_url:
                        import base64

                        video_url = base64.b64decode(v_url).decode("utf-8")
                        break

        # 图片内容
        if "image" in first and isinstance(first["image"], dict):
            img_url = first["image"].get("image_ori_raw", {}).get("url", "")
            if img_url:
                cover_url = img_url

        # 遍历所有 creations 提取图片
        for creation in creations:
            if "image" in creation and isinstance(creation["image"], dict):
                img_url = (
                    creation["image"]
                    .get("image_ori_raw", {})
                    .get("url", "")
                )
                if img_url:
                    images.append(ImgInfo(url=img_url))

        return VideoInfo(
            video_url=video_url,
            cover_url=cover_url,
            images=images,
        )

    def _find_creations(self, data) -> list:
        """递归查找 creations 数组"""
        if isinstance(data, dict):
            for key in ["creations", "creation_block"]:
                if key in data:
                    if key == "creations" and isinstance(data[key], list):
                        return data[key]
                    if key == "creation_block" and isinstance(data[key], dict):
                        if "creations" in data[key]:
                            return data[key]["creations"]
            for value in data.values():
                result = self._find_creations(value)
                if result:
                    return result
        elif isinstance(data, list):
            for item in data:
                result = self._find_creations(item)
                if result:
                    return result
        return []

    async def _fallback_parse(self, share_url: str) -> VideoInfo:
        """降级: 调用 bugpk 第三方 API"""
        api_url = f"https://api.bugpk.com/api/dbvideos?url={share_url}"
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
