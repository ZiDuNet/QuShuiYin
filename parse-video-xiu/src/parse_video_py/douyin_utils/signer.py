"""抖音签名工具 — 基于 media-parser/douyin_utils 移植

提供 ttwid 获取、a_bogus 签名、ms_token 生成等功能。
"""

import json
import os
import random
import urllib.parse

from py_mini_racer import MiniRacer

_JS_DIR = os.path.dirname(os.path.abspath(__file__))


class DouyinSigner:
    _a_bogus_ctx: MiniRacer | None = None
    _ttwid_cache: str | None = None

    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    )

    @classmethod
    def _get_a_bogus_ctx(cls) -> MiniRacer:
        if cls._a_bogus_ctx is None:
            js_path = os.path.join(_JS_DIR, "a_bogus.js")
            with open(js_path, "r", encoding="utf-8") as f:
                js_code = f.read()
            cls._a_bogus_ctx = MiniRacer()
            cls._a_bogus_ctx.eval(js_code)
        return cls._a_bogus_ctx

    @classmethod
    def get_a_bogus(cls, url: str) -> str:
        """对请求 URL 生成 a_bogus 签名"""
        query = urllib.parse.urlparse(url).query
        ctx = cls._get_a_bogus_ctx()
        return ctx.call("generate_a_bogus", query, cls.USER_AGENT)

    @classmethod
    def get_ms_token(cls, length: int = 107) -> str:
        """生成随机 msToken"""
        chars = "ABCDEFGHIGKLMNOPQRSTUVWXYZabcdefghigklmnopqrstuvwxyz0123456789="
        return "".join(random.choice(chars) for _ in range(length))

    @classmethod
    def get_ttwid(cls) -> str | None:
        """从字节跳动注册接口获取 ttwid Cookie（带缓存）"""
        if cls._ttwid_cache:
            return cls._ttwid_cache

        import httpx

        url = "https://ttwid.bytedance.com/ttwid/union/register/"
        data = {
            "region": "cn",
            "aid": 6383,
            "need_t": 1,
            "service": "www.douyin.com",
            "migrate_priority": 0,
            "cb_url_protocol": "https",
            "domain": ".douyin.com",
        }
        try:
            resp = httpx.post(url, json=data, timeout=5)
            ttwid = resp.cookies.get("ttwid")
            if ttwid:
                cls._ttwid_cache = ttwid
            return ttwid
        except Exception:
            return None

    @classmethod
    def clear_cache(cls):
        """清除缓存（ttwid 失效时调用）"""
        cls._ttwid_cache = None
