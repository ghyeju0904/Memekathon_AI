"""
meme_explainer.py

역할 정리:
- MemeX Public API로 7일치 활동지표 가져오기 (fetch_creator_metrics)
- MemeScore v1.1 계산 + 구성요소 분해 (compute_memescore_parts)
- 간단한 룰 기반 bot_score 계산 (calc_bot_score)
- 각 지표별 구간 라벨 + 세부 점수 출력 블록 생성
- LLM으로 자연어 설명 생성 (call_llm_explainer)
- 외부에서 explain_meme_score(creator_id) 한 번만 호출해서 전체 결과 사용
"""

from __future__ import annotations

import os
import math
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from dotenv import load_dotenv
from openai import OpenAI

from bug_feedback import validate_creator_metrics, report_bug
from api import get_mock_user_data, get_user_basic, get_user_posts

# ============================================================
# 0. 공통 설정
# ============================================================

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY 가 설정되어 있지 않습니다 (.env 확인).")

client = OpenAI(api_key=OPENAI_API_KEY)
DEFAULT_MODEL = os.getenv("MEME_EXPLAINER_MODEL", "gpt-4.1-mini")


# ============================================================
# 1. 간단한 bot_score 계산
# ============================================================

def calc_bot_score(metrics: Dict[str, Any]) -> float:
    """0~1 사이의 간단한 이상치 점수. 1에 가까울수록 수상한 패턴."""
    likes = float(metrics.get("likes_7d", 0) or 0)
    comments = float(metrics.get("comments_7d", 0) or 0)
    reposts = float(metrics.get("reposts_7d", 0) or 0)
    quotes = float(metrics.get("quotes_7d", 0) or 0)
    views = float(metrics.get("views_7d", 0) or 0)

    like_view = likes / views if views > 0 else 0.0
    comment_like = comments / likes if likes > 0 else 0.0
    repost_like = reposts / likes if likes > 0 else 0.0

    score = 0.0

    if like_view > 0.3:
        score += 0.4
    if like_view > 0.5:
        score += 0.2

    if likes > 100 and comment_like < 0.01:
        score += 0.2
    if likes > 100 and repost_like < 0.01:
        score += 0.2

    return max(0.0, min(score, 1.0))


# ============================================================
# 2. creator_id → (username, userNameTag)
# ============================================================

def resolve_username_and_tag(creator_id: str) -> Tuple[str, str]:
    """
    - "username#tag" 형식이면 그대로 분리
    - 아니면 mock-user-data에서 userName == creator_id 인 유저를 찾아 tag 사용
    """
    if "#" in creator_id:
        username, tag = creator_id.split("#", 1)
        return username, tag

    users = get_mock_user_data()
    for u in users:
        if u.get("userName") == creator_id:
            return u["userName"], u["userNameTag"]

    raise ValueError(
        f"creator_id '{creator_id}' 에 해당하는 유저를 찾지 못했습니다. "
        "username 또는 'username#tag' 형식으로 전달해 주세요."
    )


# ============================================================
# 3. MemeScore v1.1 계산 헬퍼
# ============================================================

def compute_memescore_parts(
    likes: float,
    comments: float,
    reposts: float,
    quotes: float,
    views: float,
    followers: float,
    tip_count: float,
    tip_amount: float,
) -> Dict[str, float]:
    """
    MemeScore v1.1 전체 점수 + 구성요소(반응/조회/팔로워/Tip)를 한 번에 계산.
    - 반환값:
      {
        "score": 최종 점수,
        "engage_component": 반응 부분 점수 (0~35),
        "view_component": 조회수 부분 점수 (0~25),
        "follow_component": 팔로워 부분 점수 (0~25),
        "tip_component": Tip 부분 점수 (0~15),
        "engage_raw": 1*L + 4*C + 3*R + 5*Q
      }
    """
    # 반응 합산
    engage_raw = 1 * likes + 4 * comments + 3 * reposts + 5 * quotes
    engage_score = math.log10(1 + engage_raw) if engage_raw > 0 else 0.0
    engage_component = 35 * engage_score

    # 조회수
    view_score = math.log10(1 + views / 100.0) if views > 0 else 0.0
    view_component = 25 * view_score

    # 팔로워
    follow_score = math.log10(1 + followers) if followers > 0 else 0.0
    follow_component = 25 * follow_score

    # Tip
    tip_raw = tip_count + 10 * tip_amount
    tip_score = math.log10(1 + tip_raw) if tip_raw > 0 else 0.0
    tip_component = 15 * tip_score

    score = engage_component + view_component + follow_component + tip_component

    return {
        "score": score,
        "engage_component": engage_component,
        "view_component": view_component,
        "follow_component": follow_component,
        "tip_component": tip_component,
        "engage_raw": engage_raw,
    }


# ============================================================
# 4. MemeX 메트릭 가져오기
# ============================================================

def fetch_creator_metrics(creator_id: str) -> Dict[str, Any]:
    """MemeX Public API로 기본 정보 + 활동 요약 + MemeScore 계산."""
    username, tag = resolve_username_and_tag(creator_id)

    # 1) 유저 기본 정보
    user_info = get_user_basic(username, tag)
    followers = (
        user_info.get("followersCount")
        or user_info.get("followerCount")  # 혹시 이런 이름일 수도 있어서 추가
        or user_info.get("followers")
        or 0
    )

    # 2) 유저 게시물 (최근 100개 정도만 사용)
    posts, _ = get_user_posts(username, tag, limit=100)

    print(f"[DEBUG] posts count for {username}#{tag}: {len(posts)}")

    likes_7d = 0
    comments_7d = 0
    reposts_7d = 0
    quotes_7d = 0
    views_7d = 0

    # 🔥 핵심: socialMeta 안에서 카운트 꺼내기
    for post in posts:
        sm = post.get("socialMeta") or {}

        likes_7d += (
            sm.get("likeCount", 0)  # ← 여기!
        )
        comments_7d += (
            sm.get("replyCount", 0)  # ← 댓글은 replyCount로 보임
        )
        reposts_7d += (
            sm.get("repostCount", 0)
        )
        quotes_7d += (
            sm.get("quoteCount", 0)   # 없으면 그냥 0으로 둘 거라 문제 없음
        )
        views_7d += (
            sm.get("viewCount", 0)
        )

    # Tip은 아직 온체인 연동 전이라 0으로 두는 상태
    tip_count_7d = 0.0
    tip_amount_7d = 0.0

    parts = compute_memescore_parts(
        likes_7d,
        comments_7d,
        reposts_7d,
        quotes_7d,
        views_7d,
        float(followers),
        tip_count_7d,
        tip_amount_7d,
    )

    return {
        "creator_id": creator_id,
        "username": username,
        "display_name": user_info.get("displayName") or username,
        "likes_7d": likes_7d,
        "comments_7d": comments_7d,
        "reposts_7d": reposts_7d,
        "quotes_7d": quotes_7d,
        "views_7d": views_7d,
        "followers": followers,
        "tip_count_7d": tip_count_7d,
        "tip_amount_7d": tip_amount_7d,
        "memescore_v1_1": parts["score"],
        "memescore_7d_ago": None,
        "rank_now": None,
        "rank_7d_ago": None,
        "engage_component": parts["engage_component"],
        "view_component": parts["view_component"],
        "follow_component": parts["follow_component"],
        "tip_component": parts["tip_component"],
        "engage_raw": parts["engage_raw"],
    }


# ============================================================
# 5. 구간 라벨 함수들 (표현용)
# ============================================================

def like_range_label(value: float) -> str:
    v = int(value)
    if v == 0:
        return "0개"
    if v <= 10:
        return "0~10개"
    if v <= 50:
        return "11~50개"
    if v <= 200:
        return "51~200개"
    return "200개 이상"


def comment_range_label(value: float) -> str:
    v = int(value)
    if v == 0:
        return "0개"
    if v <= 5:
        return "0~5개"
    if v <= 20:
        return "6~20개"
    if v <= 50:
        return "21~50개"
    return "50개 이상"


def repost_range_label(value: float) -> str:
    v = int(value)
    if v == 0:
        return "0회"
    if v <= 3:
        return "1~3회"
    if v <= 10:
        return "4~10회"
    if v <= 30:
        return "11~30회"
    return "30회 이상"


def quote_range_label(value: float) -> str:
    v = int(value)
    if v == 0:
        return "0회"
    if v <= 3:
        return "1~3회"
    if v <= 10:
        return "4~10회"
    if v <= 30:
        return "11~30회"
    return "30회 이상"


def view_range_label(value: float) -> str:
    v = int(value)
    if v == 0:
        return "0회"
    if v < 1_000:
        return "0~1천회"
    if v < 10_000:
        return "1천~1만회"
    if v < 50_000:
        return "1만~5만회"
    return "5만회 이상"


def follower_range_label(value: float) -> str:
    v = int(value)
    if v == 0:
        return "0명"
    if v < 100:
        return "0~100명"
    if v < 500:
        return "100~500명"
    if v < 2_000:
        return "500~2천명"
    return "2천명 이상"


def tip_range_label(value: float) -> str:
    v = int(value)
    if v == 0:
        return "0회"
    if v == 1:
        return "1회"
    if v <= 4:
        return "2~4회"
    if v <= 9:
        return "5~9회"
    return "10회 이상"


# ============================================================
# 6. LLM 컨텍스트 & 호출
# ============================================================

def build_creator_context(metrics: Dict[str, Any], bot_score: float) -> str:
    """LLM에게 넘길 텍스트 컨텍스트 구성."""
    username = metrics.get("username") or metrics.get("creator_id") or "unknown"
    display_name = metrics.get("display_name") or username

    lines = [
        f"크리에이터: {display_name} (@{username})",
        f"- 오늘 MemeScore: {metrics.get('memescore_v1_1', 0.0)}",
        "",
        "최근 7일 활동 요약:",
        f"- 좋아요 합 (L): {metrics.get('likes_7d', 0)}",
        f"- 댓글 합 (C): {metrics.get('comments_7d', 0)}",
        f"- 리포스트 합 (R): {metrics.get('reposts_7d', 0)}",
        f"- 인용 합 (Q): {metrics.get('quotes_7d', 0)}",
        f"- 조회수 합 (V): {metrics.get('views_7d', 0)}",
        f"- 현재 팔로워 수 (F): {metrics.get('followers', 0)}",
        f"- Tip 횟수 (Tn): {metrics.get('tip_count_7d', 0)}",
        f"- Tip 총액 (Ta): {metrics.get('tip_amount_7d', 0.0)}",
        "",
        f"bot_score: {bot_score:.2f} (0에 가까울수록 정상, 1에 가까울수록 이상 패턴)",
    ]
    return "\n".join(lines)


def call_llm_explainer(context_text: str, model: Optional[str] = None) -> str:
    """LLM으로 섹션 구조화된 자연어 설명 생성."""
    model_name = model or DEFAULT_MODEL

    system_prompt = (
        "당신은 소셜/온체인 활동 데이터를 쉽게 설명해주는 분석 어시스턴트입니다. "
        "숫자를 그대로 나열하지 말고, 크리에이터 관점에서 이해하기 쉽게 요약하고, "
        "앞으로 무엇을 하면 좋을지 짧게 제안하세요."
    )

    user_prompt = (
        context_text
        + "\n\n"
        + "위 데이터를 바탕으로 아래 형식을 엄격하게 지켜서 한국어로 답변해주세요.\n"
        + "\n"
        + "📊 점수 & 랭킹 요약\n"
        + "- 지난 7일간 MemeScore와 현재 상태를 2~3문장으로 요약\n"
        + "\n"
        + "⚠️ 활동 패턴 / 리스크 평가\n"
        + "- bot_score를 참고해 활동 패턴이 자연스러운지, "
          "이상 패턴 가능성이 있는지 1~2문장으로 설명\n"
        + "\n"
        + "✅ 다음 행동 가이드\n"
        + "- 앞으로 MemeScore를 올리기 위한 행동 가이드를 2~3개, 불릿 포인트로 제안\n"
        + "\n"
        + "⭐ 핵심 한줄 요약\n"
        + "- 이 크리에이터에게 가장 중요한 메시지를 한 문장으로 정리\n"
    )

    resp = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.4,
        max_tokens=600,
    )

    content = resp.choices[0].message.content
    return content.strip() if content else ""


# ============================================================
# 7. 외부에서 쓸 메인 함수
# ============================================================

def explain_meme_score(creator_id: str) -> str:
    """
    한 번 호출로:
    - 인사 + 사용자 브리핑
    - 세부 점수/구간 블록
    - LLM 자연어 설명
    을 합친 텍스트를 반환.
    """
    metrics = fetch_creator_metrics(creator_id)

    # 기본 이상치 검증
    warnings = validate_creator_metrics(metrics)
    if warnings:
        report_bug(
            title="Creator metrics anomaly",
            message=f"creator_id={creator_id} metrics anomaly detected",
            context={"creator_id": creator_id, "warnings": warnings, "metrics": metrics},
        )

    bot_score = calc_bot_score(metrics)

    # ---------- 사용자 기본 정보 ----------
    display_name = metrics.get("display_name") or metrics.get("username") or creator_id

    header_lines = [
        f"안녕하세요, {display_name}님👾",
        f"다음은 {display_name}님의 MemeScore 분석입니다.",
        "",
    ]
    header_block = "\n".join(header_lines)

    # ---------- 점수 분해용 숫자 ----------
    likes = float(metrics["likes_7d"])
    comments = float(metrics["comments_7d"])
    reposts = float(metrics["reposts_7d"])
    quotes = float(metrics["quotes_7d"])
    views = float(metrics["views_7d"])
    followers = float(metrics["followers"])
    tip_count = float(metrics["tip_count_7d"])
    tip_amount = float(metrics["tip_amount_7d"])

    engage_component = float(metrics.get("engage_component", 0.0))
    engage_raw = float(metrics.get("engage_raw", 0.0))

    like_points = comment_points = repost_points = quote_points = 0.0
    if engage_component > 0 and engage_raw > 0:
        like_points   = engage_component * (1 * likes    / engage_raw)
        comment_points = engage_component * (4 * comments / engage_raw)
        repost_points  = engage_component * (3 * reposts  / engage_raw)
        quote_points   = engage_component * (5 * quotes   / engage_raw)

    view_points   = float(metrics.get("view_component", 0.0))
    follow_points = float(metrics.get("follow_component", 0.0))
    tip_points    = float(metrics.get("tip_component", 0.0))

    # 반올림
    like_p   = int(round(like_points))
    comment_p = int(round(comment_points))
    repost_p  = int(round(repost_points))
    quote_p   = int(round(quote_points))
    view_p    = int(round(view_points))
    follow_p  = int(round(follow_points))
    tip_p     = int(round(tip_points))

    total_p = like_p + comment_p + repost_p + quote_p + view_p + follow_p + tip_p

    if total_p == 0:
        summary_line = "- 요약 : 최근 7일간 활동이 거의 없어 모든 지표가 0점에 가깝습니다."
    else:
        pairs = [
            ("좋아요", like_p),
            ("댓글", comment_p),
            ("리포스트", repost_p),
            ("인용", quote_p),
            ("조회수", view_p),
            ("팔로워", follow_p),
            ("Tip", tip_p),
        ]
        top_metric, _ = max(pairs, key=lambda x: x[1])
        summary_line = f"- 요약 : 현재 점수에 가장 크게 기여한 항목은 '{top_metric}'입니다."

    breakdown_lines = [
        "📈 점수에 기여한 주요 요소 (세부 점수)",
        f"- 좋아요 : {like_p}점 ({like_range_label(likes)})",
        f"- 댓글   : {comment_p}점 ({comment_range_label(comments)})",
        f"- 리포스트: {repost_p}점 ({repost_range_label(reposts)})",
        f"- 인용   : {quote_p}점 ({quote_range_label(quotes)})",
        f"- 조회수 : {view_p}점 ({view_range_label(views)})",
        f"- 팔로워 : {follow_p}점 ({follower_range_label(followers)})",
        f"- Tip    : {tip_p}점 ({tip_range_label(tip_count)} / 총 {tip_amount:.2f})",
        summary_line,
        "",
    ]
    breakdown_block = "\n".join(breakdown_lines)

    # LLM 설명
    context_text = build_creator_context(metrics, bot_score)
    explanation = call_llm_explainer(context_text)

    # 최종 합치기
    return f"{header_block}\n{breakdown_block}\n{explanation}"


# ============================================================
# 8. CLI 실행용
# ============================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("사용법: python meme_explainer.py <creator_id 또는 username#tag>")
        raise SystemExit(1)

    cid = sys.argv[1]
    try:
        result = explain_meme_score(cid)
        print("\n===== MemeScore 설명 =====\n")
        print(result)
    except Exception as e:
        report_bug(
            title="meme_explainer CLI error",
            message="explain_meme_score 실행 중 에러 발생",
            context={"creator_id": cid},
            exc=e,
        )
        raise