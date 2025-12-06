# bug_feedback.py

from __future__ import annotations

import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# 로그 파일 위치 설정
BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
BUG_LOG_FILE = LOG_DIR / "bug_reports.jsonl"


def _write_jsonl(entry: Dict[str, Any]) -> None:
    """JSONL 형식으로 한 줄씩 기록"""
    with BUG_LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def report_bug(
    title: str,
    message: str,
    context: Optional[Dict[str, Any]] = None,
    exc: Optional[BaseException] = None,
) -> None:
    """
    백엔드에서 이상한 상황/버그를 감지했을 때 호출하는 함수.

    - title: "Creator metrics anomaly" 같은 간단한 제목
    - message: 사람이 볼 수 있는 설명
    - context: creator_id, metrics 등 추가 정보
    - exc: 실제 Exception 객체 (있으면 스택트레이스 기록)
    """
    entry: Dict[str, Any] = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "title": title,
        "message": message,
        "context": context or {},
    }

    if exc is not None:
        entry["exception_type"] = type(exc).__name__
        entry["exception_message"] = str(exc)
        entry["traceback"] = traceback.format_exc()

    _write_jsonl(entry)


def validate_creator_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    크리에이터 메트릭에서 자주 터질만한 이상 패턴을 미리 체크해서
    경고 메시지 리스트로 반환.

    → 경고가 하나라도 있으면 meme_explainer 쪽에서 report_bug() 호출.
    """
    warnings: List[str] = []

    required_keys = [
        "likes_7d",
        "comments_7d",
        "reposts_7d",
        "quotes_7d",
        "views_7d",
        "followers",
        "tip_count_7d",
        "tip_amount_7d",
        "memescore_v1_1",
    ]

    for key in required_keys:
        if key not in metrics:
            warnings.append(f"missing key: {key}")

    # 기본적인 타입/값 체크 (필요하면 더 추가)
    try:
        likes = float(metrics.get("likes_7d", 0) or 0)
        views = float(metrics.get("views_7d", 0) or 0)
        comments = float(metrics.get("comments_7d", 0) or 0)
        reposts = float(metrics.get("reposts_7d", 0) or 0)
        quotes = float(metrics.get("quotes_7d", 0) or 0)
        score = float(metrics.get("memescore_v1_1", 0) or 0)
    except Exception as e:
        warnings.append(f"metric cast error: {e}")
        return warnings

    # 조회수는 있는데 좋아요/코멘트/리포스트가 전혀 없는 경우 (데이터 파이프 문제 의심)
    if views > 0 and likes == comments == reposts == quotes == 0:
        warnings.append(
            "views_7d > 0 인데 likes/comments/reposts/quotes 가 모두 0 입니다 (수집 파이프 확인 필요)."
        )

    # 점수가 음수로 내려간 경우 (수식 버그 가능)
    if score < 0:
        warnings.append("MemeScore_v1_1 이 음수입니다. 점수 계산 로직 확인 필요.")

    # 비정상적으로 큰 값 (대충 임계치, 해커톤용이니까 하드코딩)
    if likes > 1_000_000 or views > 10_000_000:
        warnings.append("likes_7d 또는 views_7d 값이 너무 큽니다. (1e6/1e7 초과)")

    return warnings