"""모델 — enums + dataclasses"""
from dataclasses import dataclass, field, asdict
from enum import Enum


class PostType(str, Enum):
    VIDEO = "GraphVideo"
    IMAGE = "GraphImage"
    CAROUSEL = "GraphSidecar"
    UNKNOWN = ""


class MediaKind(str, Enum):
    VIDEO = "mp4"
    IMAGE = "jpg"


class Endpoint(str, Enum):
    POSTS_V2 = "/api/v1/instagram/postsV2"
    POSTS = "/api/v1/instagram/posts"
    USER_INFO = "/api/v1/instagram/userInfo"
    PROFILE = "/api/v1/instagram/profile"
    CONVERT = "/api/convert"


def _count(v):
    if isinstance(v, dict):
        return v.get("count")
    return v


def _first_count(*vals):
    for v in vals:
        c = _count(v)
        if c is not None:
            return c
    return None


@dataclass(slots=True)
class Post:
    shortcode: str = ""
    type: PostType = PostType.UNKNOWN
    caption: str = ""
    likes: int | None = None
    comments: int | None = None
    views: int | None = None
    taken_at: int | None = None
    display_url: str = ""
    video_url: str = ""
    owner: str = ""

    @classmethod
    def from_raw(cls, n: dict) -> "Post":
        cap = n.get("caption")
        if not cap and isinstance(n.get("edge_media_to_caption"), dict):
            edges = n["edge_media_to_caption"].get("edges") or []
            cap = edges[0]["node"]["text"] if edges else ""
        return cls(
            shortcode=n.get("shortcode", ""),
            type=PostType(n.get("__typename", "")) if n.get("__typename") in PostType._value2member_map_ else PostType.UNKNOWN,
            caption=cap or "",
            likes=_first_count(n.get("like_count"), n.get("edge_liked_by"), n.get("edge_media_preview_like")),
            comments=_first_count(n.get("comment_count"), n.get("edge_media_to_comment")),
            views=n.get("video_view_count"),
            taken_at=n.get("taken_at_timestamp") or n.get("taken_at"),
            display_url=n.get("display_url", ""),
            video_url=n.get("video_url", ""),
            owner=(n.get("owner") or {}).get("username", ""),
        )

    def media_url(self) -> tuple[str, MediaKind] | None:
        if self.video_url:
            return self.video_url, MediaKind.VIDEO
        if self.display_url:
            return self.display_url, MediaKind.IMAGE
        return None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["type"] = self.type.value
        return d


@dataclass(slots=True)
class UserProfile:
    id: str = ""
    username: str = ""
    full_name: str = ""
    biography: str = ""
    followers: int | None = None
    following: int | None = None
    posts: int | None = None
    profile_pic_url: str = ""
    external_url: str = ""
    category: str = ""
    is_private: bool = False
    is_verified: bool = False

    @classmethod
    def from_raw(cls, raw: dict) -> "UserProfile":
        """userInfo와 profile 엔드포인트의 서로 다른 응답 모양을 모두 처리한다."""
        result = raw.get("result", raw)
        if isinstance(result, list):
            result = result[0] if result else {}
        if isinstance(result, dict) and isinstance(result.get("user"), dict):
            result = result["user"]
        if not isinstance(result, dict):
            result = {}

        hd_pic = result.get("hd_profile_pic_url_info") or {}
        return cls(
            id=str(result.get("id") or result.get("pk") or ""),
            username=result.get("username") or "",
            full_name=result.get("full_name") or "",
            biography=result.get("biography") or "",
            followers=_first_count(result.get("follower_count"), result.get("edge_followed_by")),
            following=_first_count(result.get("following_count"), result.get("edge_follow")),
            posts=_first_count(result.get("media_count"), result.get("edge_owner_to_timeline_media")),
            profile_pic_url=(
                result.get("profile_pic_url_hd")
                or hd_pic.get("url")
                or result.get("profile_pic_url")
                or ""
            ),
            external_url=result.get("external_url") or "",
            category=result.get("category") or "",
            is_private=bool(result.get("is_private")),
            is_verified=bool(result.get("is_verified")),
        )

    def to_dict(self) -> dict:
        return asdict(self)
