import hashlib
import json
import re
from base64 import b64decode

import httpx

from .base import BaseParser, VideoAuthor, VideoInfo


class NetEase(BaseParser):
    AES_KEY = b"e82ckenh8dichen8"
    EAPI_BASE = "https://interface3.music.163.com/eapi"
    API_BASE = "https://interface3.music.163.com/api"

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        song_id = self._extract_song_id(share_url)
        return await self.parse_video_id(song_id)

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        song_id = video_id

        # 获取歌曲详情
        detail = await self._get_song_detail(song_id)
        # 获取播放地址
        play_url = await self._get_song_url(song_id)
        # 获取歌词
        lyric = await self._get_lyric(song_id)

        song_data = {}
        songs = detail.get("songs", [])
        if songs:
            song_data = songs[0]

        title = song_data.get("name", "")
        artists = [ar.get("name", "") for ar in song_data.get("ar", [])]
        if artists:
            title = f"{title} - {'/'.join(artists)}"

        cover_url = song_data.get("al", {}).get("picUrl", "")

        return VideoInfo(
            video_url=play_url,
            cover_url=cover_url,
            title=title,
            music_url=play_url,
        )

    async def _get_song_detail(self, song_id: str) -> dict:
        url = f"{self.API_BASE}/v3/song/detail"
        data = {"c": json.dumps([{"id": int(song_id), "v": 0}])}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.post(url, data=data, headers=headers)
            return response.json()

    async def _get_song_url(self, song_id: str) -> str:
        url = f"{self.EAPI_BASE}/song/enhance/player/url/v1"
        path = "/api/song/enhance/player/url/v1"

        payload = json.dumps(
            {
                "ids": [f"{song_id}"],
                "level": "exhigh",
                "encodeType": "flac",
                "header": {},
            }
        )

        encrypted = self._eapi_encrypt(path, payload)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.post(
                url, data=f"params={encrypted}", headers=headers
            )
            data = response.json()

        url_data = data.get("data", [])
        if url_data:
            return url_data[0].get("url", "") or url_data[0].get("http_url_", "")
        return ""

    async def _get_lyric(self, song_id: str) -> str:
        url = f"{self.API_BASE}/song/lyric"
        data = {"id": song_id, "cp": "false", "tv": "0", "lv": "0", "rv": "0", "kv": "0"}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.post(url, data=data, headers=headers)
                result = response.json()
                return result.get("lrc", {}).get("lyric", "")
        except Exception:
            return ""

    def _eapi_encrypt(self, url_path: str, payload: str) -> str:
        """网易云 EAPI 加密（AES-ECB）"""
        try:
            from Crypto.Cipher import AES
            from Crypto.Util.Padding import pad
        except ImportError:
            raise ImportError(
                "网易云音乐解析需要安装 pycryptodome: pip install pycryptodome"
            )

        digest = hashlib.md5(
            f"nobody{url_path}use{payload}md5forencrypt".encode()
        ).hexdigest()

        message = f"{url_path}-36cd479b6b5-{payload}-36cd479b6b5-{digest}"

        cipher = AES.new(self.AES_KEY, AES.MODE_ECB)
        encrypted = cipher.encrypt(pad(message.encode(), AES.block_size))
        return encrypted.hex().upper()

    @staticmethod
    def _extract_song_id(url: str) -> str:
        match = re.search(r"id=(\d+)", url)
        if match:
            return match.group(1)

        match = re.search(r"/song/(\d+)", url)
        if match:
            return match.group(1)

        raise ValueError("从网易云音乐链接中提取歌曲ID失败")
