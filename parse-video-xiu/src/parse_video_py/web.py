import dataclasses
import os
import secrets
from pathlib import Path
from urllib.parse import urlparse

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from fastapi_mcp import FastApiMCP

from parse_video_py import VideoSource, parse_video_id, parse_video_share_url
from parse_video_py.parser import video_source_info_mapping, detect_source
from parse_video_py.utils import extract_url


def _get_templates_dir() -> str:
    # 模板已移入 src/parse_video_py/templates/，与 web.py 同级
    templates_dir = Path(__file__).parent / "templates"
    if templates_dir.is_dir():
        return str(templates_dir)
    raise FileNotFoundError("templates 目录未找到")


app = FastAPI(
    title="去水印解析 API",
    description="短视频/图集去水印解析服务，支持 51 个平台",
    version="1.0.0",
    docs_url="/swagger",
)

mcp = FastApiMCP(app)
mcp.mount_http()

templates = Jinja2Templates(directory=_get_templates_dir())


def _build_auth_dependency() -> list[Depends]:
    """根据环境变量动态构建 Basic Auth 依赖项"""
    basic_auth_username = os.getenv("PARSE_VIDEO_USERNAME")
    basic_auth_password = os.getenv("PARSE_VIDEO_PASSWORD")

    if not (basic_auth_username and basic_auth_password):
        return []

    security = HTTPBasic()

    def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
        correct_username = secrets.compare_digest(
            credentials.username, basic_auth_username
        )
        correct_password = secrets.compare_digest(
            credentials.password, basic_auth_password
        )
        if not (correct_username and correct_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Basic"},
            )
        return credentials

    return [Depends(verify_credentials)]


# 模块加载时构建一次，避免每个路由装饰器重复调用
_auth_dependency = _build_auth_dependency()


@app.get("/", response_class=HTMLResponse, dependencies=_auth_dependency)
async def read_item(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "title": "github.com/wujunwei928/parse-video-py Demo",
        },
    )


@app.get("/docs", response_class=HTMLResponse, dependencies=_auth_dependency)
async def docs_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="docs.html",
        context={
            "title": "API 接口文档",
        },
    )


@app.get("/video/share/url/parse", dependencies=_auth_dependency)
async def share_url_parse(url: str):
    video_share_url = extract_url(url)
    if video_share_url is None:
        return {
            "code": 400,
            "msg": "未检测到有效的分享链接",
        }

    try:
        video_info = await parse_video_share_url(video_share_url)
        return {
            "code": 200,
            "msg": "解析成功",
            "data": dataclasses.asdict(video_info),
        }
    except Exception as err:
        return {
            "code": 500,
            "msg": str(err),
        }


@app.get("/video/id/parse", dependencies=_auth_dependency)
async def video_id_parse(source: VideoSource, video_id: str):
    try:
        video_info = await parse_video_id(source, video_id)
        return {
            "code": 200,
            "msg": "解析成功",
            "data": dataclasses.asdict(video_info),
        }
    except Exception as err:
        return {
            "code": 500,
            "msg": str(err),
        }


@app.get("/api/list", dependencies=_auth_dependency)
async def api_list():
    """返回所有可用接口列表"""
    result = []
    for source, info in video_source_info_mapping.items():
        parser_cls = info["parser"]
        desc = info.get("label") or info.get("description", "")
        if not desc:
            doc = parser_cls.__doc__ or ""
            desc = doc.strip().split("\n")[0] if doc else source.value

        # 分类
        categories = {
            "视频平台": [
                VideoSource.DouYin, VideoSource.DyLive,
                VideoSource.KuaiShou, VideoSource.KsImg,
                VideoSource.RedBook, VideoSource.XhsImg,
                VideoSource.WeiBo, VideoSource.WeiBoV,
                VideoSource.BiliBili, VideoSource.PiPiXia, VideoSource.PiPiGaoXiao,
                VideoSource.ZuiYou, VideoSource.Toutiao,
                VideoSource.XiGua, VideoSource.HaoKan, VideoSource.WeiShi,
                VideoSource.HuoShan, VideoSource.AcFun, VideoSource.SixRoom,
                VideoSource.Sohu, VideoSource.CCTV, VideoSource.QQVideo,
                VideoSource.DouPai, VideoSource.MeiPai, VideoSource.QuanMin,
                VideoSource.QuanMinKGe, VideoSource.LiShiPin, VideoSource.XinPianChang,
                VideoSource.HuYa, VideoSource.LvZhou,
                VideoSource.Doubao, VideoSource.DbDuiHua,
                VideoSource.JimengAI, VideoSource.QianWenImg,
                VideoSource.TikTok, VideoSource.Twitter,
                VideoSource.Instagram, VideoSource.YouTube,
                VideoSource.Zhihu,
                VideoSource.VideoSjx, VideoSource.XyDetail,
                VideoSource.NetEase,
            ],
            "音乐平台": [
                VideoSource.KuWo, VideoSource.QQMusic,
                VideoSource.QsMusic,
            ],
        }
        category = "其他"
        for cat, sources in categories.items():
            if source in sources:
                category = cat
                break

        result.append({
            "source": source.value,
            "name": source.name,
            "description": desc,
            "domains": info["domain_list"],
            "category": category,
        })

    return {"code": 200, "data": result}


# === 自动生成平台独立路由 ===

def _create_platform_route(parser_cls):
    """为每个平台生成独立路由处理函数"""
    async def platform_parse(url: str = ""):
        if not url:
            return {"code": 400, "msg": "缺少 url 参数"}
        video_share_url = extract_url(url)
        if video_share_url is None:
            video_share_url = url
        try:
            _obj = parser_cls()
            video_info = await _obj.parse_share_url(video_share_url)
            return {
                "code": 200,
                "msg": "解析成功",
                "data": dataclasses.asdict(video_info),
            }
        except Exception as err:
            return {
                "code": 500,
                "msg": str(err),
            }
    return platform_parse


for _source, _info in video_source_info_mapping.items():
    _route_path = f"/api/{_source.value}/parse"
    _handler = _create_platform_route(_info["parser"])
    app.add_api_route(
        _route_path,
        _handler,
        methods=["GET"],
        dependencies=_auth_dependency,
        tags=[_source.name],
        summary=f"{_source.value} 解析",
    )


@app.get("/proxy", dependencies=_auth_dependency)
async def proxy_media(url: str):
    """服务端代理转发媒体资源（降级方案，绕过防盗链）"""
    if not url:
        raise HTTPException(status_code=400, detail="url 参数不能为空")

    parsed = urlparse(url)
    referer = f"{parsed.scheme}://{parsed.netloc}/"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": referer,
        "Origin": referer.rstrip("/"),
    }

    async def stream():
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            async with client.stream("GET", url, headers=headers) as resp:
                if resp.status_code != 200:
                    return
                async for chunk in resp.aiter_bytes(chunk_size=65536):
                    yield chunk

    content_type = "video/mp4"
    if any(ext in url.lower() for ext in (".jpg", ".jpeg", ".png", ".webp")):
        content_type = "image/jpeg"
    elif ".mp3" in url.lower():
        content_type = "audio/mpeg"

    return StreamingResponse(stream(), media_type=content_type)


mcp.setup_server()
