import re
from urllib.parse import urlparse

import httpx

from .base import BaseParser, VideoAuthor, VideoInfo, ImgInfo


class Zhihu(BaseParser):
    async def parse_share_url(self, share_url: str) -> VideoInfo:
        ids = self._extract_ids(share_url)
        return await self._fetch_and_parse(ids, share_url)

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        return await self._fetch_and_parse(
            {"zvideo_id": video_id},
            f"https://www.zhihu.com/zvideo/{video_id}",
        )

    def _extract_ids(self, url: str) -> dict:
        ids = {
            "question_id": None,
            "answer_id": None,
            "zvideo_id": None,
            "pin_id": None,
            "article_id": None,
        }
        # 回答
        m = re.search(r"question/(\d+)/answer/(\d+)", url)
        if m:
            ids["question_id"] = m.group(1)
            ids["answer_id"] = m.group(2)
            return ids

        m = re.search(r"/answer/(\d+)", url)
        if m:
            ids["answer_id"] = m.group(1)

        # 视频
        m = re.search(r"/zvideo/(\d+)", url)
        if m:
            ids["zvideo_id"] = m.group(1)

        # 想法
        m = re.search(r"/pin/(\d+)", url)
        if m:
            ids["pin_id"] = m.group(1)

        # 文章
        m = re.search(r"(?:zhuanlan\.zhihu\.com/p/|/article/)(\d+)", url)
        if m:
            ids["article_id"] = m.group(1)

        return ids

    async def _fetch_and_parse(self, ids: dict, original_url: str) -> VideoInfo:
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
            "Accept": "application/json, text/plain, */*",
        }

        data = {}
        async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
            if ids["answer_id"]:
                resp = await client.get(
                    f"https://api.zhihu.com/answers/{ids['answer_id']}", headers=headers
                )
                if resp.status_code == 200:
                    data = resp.json()
            elif ids["zvideo_id"]:
                resp = await client.get(
                    f"https://api.zhihu.com/videos/{ids['zvideo_id']}", headers=headers
                )
                if resp.status_code == 200:
                    data = resp.json()
            elif ids["pin_id"]:
                resp = await client.get(
                    f"https://api.zhihu.com/pins/{ids['pin_id']}", headers=headers
                )
                if resp.status_code == 200:
                    data = resp.json()
            elif ids["article_id"]:
                resp = await client.get(
                    f"https://api.zhihu.com/articles/{ids['article_id']}",
                    headers=headers,
                )
                if resp.status_code == 200:
                    data = resp.json()

        # 视频URL
        video_url = ""
        if "playlist" in data:
            playlist = data["playlist"]
            for quality in ["HD", "SD", "LD"]:
                if quality in playlist and playlist[quality].get("play_url"):
                    video_url = playlist[quality]["play_url"]
                    break

        # 从HTML内容中提取Lens视频
        if not video_url:
            content = data.get("content", "")
            if isinstance(content, str):
                lens_match = re.search(r'data-lens-id="(\d+)"', content)
                if lens_match:
                    video_url = await self._get_lens_video(lens_match.group(1), client if 'client' in dir() else None)

        # 标题
        title = ""
        if "question" in data and "title" in data.get("question", {}):
            title = data["question"]["title"]
        elif "title" in data:
            title = data["title"]
        elif "content" in data and isinstance(data["content"], list):
            parts = []
            for item in data["content"]:
                if item.get("type") == "text" and item.get("content"):
                    parts.append(re.sub(r"<[^>]+>", "", item["content"]))
            title = "\n".join(parts)
        if not title:
            excerpt = data.get("excerpt", "")
            if isinstance(excerpt, str):
                title = re.sub(r"<[^>]+>", "", excerpt)[:100]

        # 封面
        cover_url = ""
        if data.get("thumbnail"):
            cover_url = data["thumbnail"]
        elif data.get("image_url"):
            cover_url = data["image_url"]
        elif isinstance(data.get("content"), str):
            img_match = re.search(r'<img[^>]+src="([^"]+)"', data["content"])
            if img_match and img_match.group(1).startswith("http"):
                cover_url = img_match.group(1)

        # 图集
        images = []
        # Pin 想法中的图片
        if "content" in data and isinstance(data["content"], list):
            for item in data["content"]:
                if item.get("type") == "image" and item.get("url"):
                    images.append(ImgInfo(url=item["url"]))
        # HTML内容中的图片
        elif isinstance(data.get("content"), str):
            for match in re.finditer(
                r'<img[^>]+(?:data-original|data-actualsrc|src)="([^"]+)"',
                data["content"],
            ):
                src = match.group(1)
                if src.startswith("http"):
                    src = src.replace("_hd", "_r").replace("_hq", "_r")
                    images.append(ImgInfo(url=src))
            # 去重
            seen = set()
            unique = []
            for img in images:
                if img.url not in seen:
                    seen.add(img.url)
                    unique.append(img)
            images = unique

        # 作者
        author_data = data.get("author", {})
        author = VideoAuthor()
        if isinstance(author_data, dict):
            author = VideoAuthor(
                uid=str(author_data.get("id", "")),
                name=author_data.get("name", ""),
                avatar=author_data.get("avatar_url", ""),
            )

        return VideoInfo(
            video_url=video_url,
            cover_url=cover_url,
            title=title,
            images=images,
            author=author,
        )

    async def _get_lens_video(self, lens_id: str, client=None) -> str:
        url = f"https://lens.zhihu.com/api/v4/videos/{lens_id}"
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15",
            "Referer": "https://v.vzuu.com/",
            "Origin": "https://v.vzuu.com",
        }
        close_client = False
        if client is None:
            client = httpx.AsyncClient(follow_redirects=True, timeout=10)
            close_client = True
        try:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                playlist = data.get("playlist", {})
                for quality in ["HD", "SD", "LD"]:
                    if quality in playlist and playlist[quality].get("play_url"):
                        return playlist[quality]["play_url"]
        finally:
            if close_client:
                await client.aclose()
        return ""
