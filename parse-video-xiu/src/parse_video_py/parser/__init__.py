from .acfun import AcFun
from .base import VideoInfo, VideoSource
from .bilibili import BiliBili
from .cctv import CCTV
from .doubao import Doubao
from .doupai import DouPai
from .douyin import DouYin

from .haokan import HaoKan
from .huoshan import HuoShan
from .huya import HuYa
from .instagram import Instagram
from .jimengai import JimengAI
from .kuaishou import KuaiShou
from .lishipin import LiShiPin
from .lvzhou import LvZhou
from .meipai import MeiPai
from .netease import NetEase
from .pipigaoxiao import PiPiGaoXiao
from .pipixia import PiPiXia
from .qqvideo import QQVideo
from .quanmin import QuanMin
from .quanminkge import QuanMinKGe
from .redbook import RedBook
from .sixroom import SixRoom
from .sohu import Sohu
from .tiktok import TikTok
from .toutiao import Toutiao
from .twitter import Twitter
from .weibo import WeiBo
from .weishi import WeiShi
from .xigua import XiGua
from .xinpianchang import XinPianChang
from .youtube import YouTube
from .zhihu import Zhihu
from .zuiyou import ZuiYou
# 新增：多接口拆分
from .dylive import DyLive
from .ksimg import KsImg
from .xhsimg import XhsImg
from .weibov import WeiBoV
# 新增：bugpk 第三方接口
from .dbduihua import DbDuiHua
from .qianwenimg import QianWenImg
from .videosjx import VideoSjx
from .xydetail import XyDetail
# 新增：音乐类
from .kuwo import KuWo
from .qqmusic import QQMusic
from .qsmusic import QsMusic

# 视频来源与解析器的映射关系
video_source_info_mapping = {
    VideoSource.AcFun: {
        "label": "A站",
        "domain_list": ["www.acfun.cn"],
        "parser": AcFun,
    },
    VideoSource.CCTV: {
        "label": "央视网",
        "domain_list": ["tv.cctv.cn", "tv.cctv.com"],
        "parser": CCTV,
    },
    VideoSource.DouPai: {
        "label": "逗拍",
        "domain_list": ["doupai.cc"],
        "parser": DouPai,
    },
    VideoSource.DouYin: {
        "label": "抖音",
        "domain_list": ["v.douyin.com", "www.iesdouyin.com", "www.douyin.com/video"],
        "parser": DouYin,
    },
    VideoSource.HaoKan: {
        "label": "好看视频",
        "domain_list": [
            "haokan.baidu.com",
            "haokan.hao123.com",
        ],
        "parser": HaoKan,
    },
    VideoSource.BiliBili: {
        "label": "哔哩哔哩",
        "domain_list": [
            "www.bilibili.com",
            "b23.tv",
            "m.bilibili.com",
        ],
        "parser": BiliBili,
    },
    VideoSource.HuYa: {
        "label": "虎牙",
        "domain_list": ["v.huya.com"],
        "parser": HuYa,
    },
    VideoSource.KuaiShou: {
        "label": "快手",
        "domain_list": ["v.kuaishou.com", "www.kuaishou.com"],
        "parser": KuaiShou,
    },
    VideoSource.LiShiPin: {
        "label": "梨视频",
        "domain_list": ["www.pearvideo.com"],
        "parser": LiShiPin,
    },
    VideoSource.LvZhou: {
        "label": "绿洲",
        "domain_list": ["weibo.cn"],
        "parser": LvZhou,
    },
    VideoSource.MeiPai: {
        "label": "美拍",
        "domain_list": ["meipai.com"],
        "parser": MeiPai,
    },
    VideoSource.PiPiGaoXiao: {
        "label": "皮皮搞笑",
        "domain_list": ["h5.pipigx.com"],
        "parser": PiPiGaoXiao,
    },
    VideoSource.PiPiXia: {
        "label": "皮皮虾",
        "domain_list": ["h5.pipix.com"],
        "parser": PiPiXia,
    },
    VideoSource.QuanMin: {
        "label": "度小视",
        "domain_list": ["xspshare.baidu.com"],
        "parser": QuanMin,
    },
    VideoSource.QuanMinKGe: {
        "label": "全民K歌",
        "domain_list": ["kg.qq.com"],
        "parser": QuanMinKGe,
    },
    VideoSource.SixRoom: {
        "label": "六间房",
        "domain_list": ["6.cn"],
        "parser": SixRoom,
    },
    VideoSource.Sohu: {
        "label": "搜狐视频",
        "domain_list": ["tv.sohu.com", "my.tv.sohu.com"],
        "parser": Sohu,
    },
    VideoSource.WeiBo: {
        "label": "微博",
        "domain_list": ["weibo.com"],
        "parser": WeiBo,
    },
    VideoSource.WeiShi: {
        "label": "微视",
        "domain_list": ["isee.weishi.qq.com"],
        "parser": WeiShi,
    },
    VideoSource.XiGua: {
        "label": "西瓜视频",
        "domain_list": ["v.ixigua.com", "www.ixigua.com"],
        "parser": XiGua,
    },
    VideoSource.XinPianChang: {
        "label": "新片场",
        "domain_list": ["xinpianchang.com"],
        "parser": XinPianChang,
    },
    VideoSource.ZuiYou: {
        "label": "最右",
        "domain_list": ["share.xiaochuankeji.cn"],
        "parser": ZuiYou,
    },
    VideoSource.RedBook: {
        "label": "小红书",
        "domain_list": [
            "www.xiaohongshu.com",
            "xhslink.com",
        ],
        "parser": RedBook,
    },
    VideoSource.Twitter: {
        "label": "Twitter/X",
        "domain_list": [
            "twitter.com",
            "x.com",
            "t.co",
            "mobile.twitter.com",
        ],
        "parser": Twitter,
    },
    VideoSource.QQVideo: {
        "label": "腾讯视频",
        "domain_list": ["v.qq.com", "m.v.qq.com"],
        "parser": QQVideo,
    },
    VideoSource.HuoShan: {
        "label": "火山",
        "domain_list": ["share.huoshan.com"],
        "parser": HuoShan,
    },
    VideoSource.TikTok: {
        "label": "TikTok",
        "domain_list": [
            "www.tiktok.com",
            "vt.tiktok.com",
            "vm.tiktok.com",
        ],
        "parser": TikTok,
    },
    VideoSource.JimengAI: {
        "label": "即梦AI",
        "domain_list": ["jimeng.jianying.com"],
        "parser": JimengAI,
    },
    VideoSource.Zhihu: {
        "label": "知乎",
        "domain_list": ["www.zhihu.com", "zhuanlan.zhihu.com"],
        "parser": Zhihu,
    },
    VideoSource.Toutiao: {
        "label": "今日头条",
        "domain_list": ["www.toutiao.com", "m.toutiao.com", "m.toutiao.cn"],
        "parser": Toutiao,
    },
    VideoSource.Doubao: {
        "label": "豆包",
        "domain_list": ["www.doubao.com"],
        "parser": Doubao,
    },
    VideoSource.Instagram: {
        "label": "Instagram",
        "domain_list": ["www.instagram.com", "instagram.com"],
        "parser": Instagram,
    },
    VideoSource.YouTube: {
        "label": "YouTube",
        "domain_list": ["www.youtube.com", "youtu.be", "m.youtube.com"],
        "parser": YouTube,
    },

    VideoSource.NetEase: {
        "label": "网易云音乐",
        "domain_list": ["music.163.com"],
        "parser": NetEase,
    },
    # === 多接口拆分 ===
    VideoSource.DyLive: {
        "label": "抖音实况",
        "domain_list": ["www.douyin.com/note"],
        "parser": DyLive,
    },
    VideoSource.KsImg: {
        "label": "快手图集",
        "domain_list": ["www.kuaishou.com/photo"],
        "parser": KsImg,
    },
    VideoSource.XhsImg: {
        "label": "小红书图文",
        "domain_list": [],
        "parser": XhsImg,
        "description": "小红书图文解析",
    },
    VideoSource.WeiBoV: {
        "label": "微博去水印",
        "domain_list": [],
        "parser": WeiBoV,
        "description": "微博去水印解析",
    },
    # === bugpk 第三方接口 ===
    VideoSource.DbDuiHua: {
        "label": "豆包对话",
        "domain_list": ["www.doubao.com/chat"],
        "parser": DbDuiHua,
    },
    VideoSource.QianWenImg: {
        "label": "通义千问",
        "domain_list": ["www.qianwen.com", "tongyi.aliyun.com"],
        "parser": QianWenImg,
    },
    VideoSource.VideoSjx: {
        "label": "影视解析",
        "domain_list": [],
        "parser": VideoSjx,
        "description": "影视解析",
    },
    VideoSource.XyDetail: {
        "label": "闲鱼",
        "domain_list": ["www.goofish.com", "idle.taobao.com", "2.taobao.com"],
        "parser": XyDetail,
    },
    # === 音乐类 ===
    VideoSource.KuWo: {
        "label": "酷我音乐",
        "domain_list": ["www.kuwo.cn", "kuwo.cn"],
        "parser": KuWo,
    },
    VideoSource.QQMusic: {
        "label": "QQ音乐",
        "domain_list": ["y.qq.com"],
        "parser": QQMusic,
    },
    VideoSource.QsMusic: {
        "label": "汽水音乐",
        "domain_list": [],
        "parser": QsMusic,
        "description": "汽水音乐",
    },
}


def detect_source(url: str) -> VideoSource | None:
    """从 URL 中检测视频来源"""
    for source, info in video_source_info_mapping.items():
        for domain in info["domain_list"]:
            if domain and domain in url:
                return source
    return None


async def parse_video_share_url(share_url: str) -> VideoInfo:
    """
    解析分享链接, 获取视频信息
    :param share_url: 视频分享链接
    :return:
    """
    source = ""
    for item_source, item_source_info in video_source_info_mapping.items():
        for item_url_domain in item_source_info["domain_list"]:
            if item_url_domain and item_url_domain in share_url:
                source = item_source
                break
        if source:
            break

    if not source:
        raise ValueError(f"share url [{share_url}] does not have source config")

    url_parser = video_source_info_mapping[source]["parser"]
    if not url_parser:
        raise ValueError(f"source {source} has no video parser")

    _obj = url_parser()
    video_info = await _obj.parse_share_url(share_url)

    return video_info


async def parse_video_id(source: VideoSource, video_id: str) -> VideoInfo:
    """
    解析视频ID, 获取视频信息
    :param source: 视频来源
    :param video_id: 视频id
    :return:
    """
    if not video_id or not source:
        raise ValueError("video_id or source is empty")

    id_parser = video_source_info_mapping[source]["parser"]
    if not id_parser:
        raise ValueError(f"source {source} has no video parser")

    _obj = id_parser()
    video_info = await _obj.parse_video_id(video_id)

    return video_info
