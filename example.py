"""Graman 사용 예시 — 게시물 목록/메타데이터를 보기 좋게 출력

상단 상수만 바꿔서 python example.py
"""
import asyncio
import json
import sys
from datetime import datetime

from graman import Graman, Post, PostType

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined] — cp949 콘솔에서 이모지 캡션 출력 시 크래시 방지

USERNAME = "muse"      # 대상 계정 (@ 제외)
TARGET_URL = ""             # 단건 변환 테스트용 인스타 URL (비우면 목록 수집)

TYPE_LABEL = {PostType.VIDEO: "영상", PostType.IMAGE: "사진", PostType.CAROUSEL: "캐러셀"}
LINE = "─" * 64


def fmt_num(n: int | None) -> str:
    return "-" if n is None else f"{n:,}"


def fmt_time(ts: int | None) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") if ts else "-"


def fmt_caption(text: str, width: int = 70) -> str:
    one_line = " ".join(text.split())
    if not one_line:
        return "(캡션 없음)"
    return one_line if len(one_line) <= width else one_line[:width - 1] + "…"


def print_post(i: int, p: Post):
    print(LINE)
    print(f"[{i:>3}] {p.shortcode}  ·  {TYPE_LABEL.get(p.type, '기타')}  ·  {fmt_time(p.taken_at)}")
    print(f"      좋아요 {fmt_num(p.likes):>9}   댓글 {fmt_num(p.comments):>6}   조회 {fmt_num(p.views):>9}")
    print(f"      {fmt_caption(p.caption)}")
    print(f"      https://www.instagram.com/p/{p.shortcode}/")


def print_summary(posts: list[Post]):
    print(LINE)
    if not posts:
        print(f"@{USERNAME}: 수집된 게시물 없음")
        return
    likes = [p.likes for p in posts if p.likes is not None]
    comments = [p.comments for p in posts if p.comments is not None]
    by_type = {}
    for p in posts:
        label = TYPE_LABEL.get(p.type, "기타")
        by_type[label] = by_type.get(label, 0) + 1
    top = max(posts, key=lambda p: p.likes or 0)

    print(f"@{USERNAME}  게시물 {len(posts)}개  ({', '.join(f'{k} {v}' for k, v in by_type.items())})")
    if likes:
        print(f"  평균 좋아요 {sum(likes) // len(likes):,}   최고 {top.likes:,} ({top.shortcode})")
    if comments:
        print(f"  평균 댓글   {sum(comments) // len(comments):,}")
    print(f"  기간 {fmt_time(min(p.taken_at or 0 for p in posts))} ~ {fmt_time(max(p.taken_at or 0 for p in posts))}")


async def example_posts(g: Graman):
    """프로필 + 전체 게시물 메타데이터 수집 → 출력"""
    profile = await g.user_info(USERNAME)
    if profile:
        print(LINE)
        print(f"@{profile.username}  {profile.full_name}")
        print(f"  팔로워 {fmt_num(profile.followers)}   팔로잉 {fmt_num(profile.following)}   게시물 {fmt_num(profile.posts)}")
        print(f"  소개: {profile.biography or '-'}")
        if profile.external_url:
            print(f"  링크: {profile.external_url}")
        print(f"  비공개: {'예' if profile.is_private else '아니오'}   인증: {'예' if profile.is_verified else '아니오'}")

    print(f"\n@{USERNAME} 전체 게시물 수집 중...\n")
    posts = []
    async for p in g.posts(USERNAME):
        posts.append(p)
        print_post(len(posts), p)
    print_summary(posts)


async def example_convert(g: Graman):
    """단건 URL → 미디어 해석"""
    res = await g.convert(TARGET_URL)
    print(json.dumps(res, ensure_ascii=False, indent=2)[:3000])


async def main():
    async with Graman() as g:
        if TARGET_URL:
            await example_convert(g)
        else:
            await example_posts(g)


if __name__ == "__main__":
    asyncio.run(main())
