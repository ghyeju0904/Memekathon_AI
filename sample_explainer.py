"""
meme_explainer.py

MemeGaging용 MemeScore 설명 AI 코파일럿 모듈.
"""

import os
import json
from dotenv import load_dotenv
from openai import OpenAI

# =========================
# .env 로드 + API 키 확인
# =========================

# 이 파일이 있는 폴더 기준으로 .env 경로 계산
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")

# .env 로드
load_dotenv(ENV_PATH)

api_key = os.getenv("OPENAI_API_KEY")

# 디버그용: 앞 몇 글자만 찍어보기 (키 전체는 절대 출력 X)
print("DEBUG OPENAI_API_KEY prefix:", api_key[:8] if api_key else None)

if not api_key:
    # 여기서 한 번 더 명확하게 에러를 띄워줌
    raise RuntimeError(
        f"OPENAI_API_KEY not found. "
        f"Checked .env at: {ENV_PATH}\n"
        f"현재 작업 디렉토리: {os.getcwd()}"
    )

client = OpenAI(api_key=api_key)

# =========================
# 프롬프트 정의
# =========================

SYSTEM_PROMPT = """
당신은 Web3 SocialFi 서비스 'MemeGaging'의 AI 코파일럿입니다.

역할:
- 주어진 숫자 데이터를 기반으로 특정 크리에이터의 MemeScore를 설명합니다.
- 지난 7일간 점수 변화와 랭킹 변화를 요약합니다.
- 점수에 많이 기여한 요소(좋아요, 댓글, 리포스트, 인용, 조회수, 팔로워, Tip)를 설명합니다.
- 마지막에 크리에이터가 해볼 만한 전략을 2~3가지 제안합니다.
- 데이터에 없는 내용은 추측하지 않습니다.
- 한국어 요청이면 한국어, 그 외에는 영어로 답변합니다.

답변 형식:
1) 한 문단 요약
2) Bullet 3~5개로 점수 구성 설명
3) Bullet 2~3개로 다음 행동 제안
"""

USER_PROMPT_TEMPLATE = """
아래는 한 MemeX 크리에이터의 최근 7일간 데이터입니다.

- 이 데이터를 기반으로 사람이 이해하기 쉬운 자연어로 설명해 주세요.
- 데이터 나열보다, 변화와 패턴을 위주로 설명해 주세요.
- 점수에 가장 많이 기여한 요소를 설명해 주세요.
- Tip 관련 데이터(tips_count_7d, tips_amount_7d, tip_tx_count_7d)가
  어느 정도 기여했는지도 언급해 주세요.
- 출력 언어: {lang}  (ko면 한국어, 그 외에는 영어)

크리에이터 데이터(JSON):
{context_json}
"""

# =========================
# 컨텍스트 생성 함수
# =========================

def build_creator_context(
    username: str,
    user_tag: str,
    display_name: str,
    profile_image_url: str,
    followers: int,
    country: str,
    score_current: float,
    score_prev: float,
    rank_current: int,
    rank_prev: int,
    likes_7d: int,
    comments_7d: int,
    reposts_7d: int,
    quotes_7d: int,
    views_7d: int,
    tips_count_7d: int,
    tips_amount_7d: float,
    daily_scores: list,
    tip_tx_count_7d: int,
    net_buy_volume_7d: float,
) -> dict:
    """
    크리에이터 한 명에 대한 숫자 데이터를 받아서
    LLM에 던질 context dict로 만들어주는 함수.
    """

    score_diff = score_current - score_prev

    creator_context = {
        "creator_profile": {
            "username": username,
            "user_tag": user_tag,
            "display_name": display_name,
            "profile_image_url": profile_image_url,
            "followers": followers,
            "country": country,
        },
        "score": {
            "meme_score": score_current,
            "meme_score_prev": score_prev,
            "meme_score_diff": score_diff,
            "rank_current": rank_current,
            "rank_prev": rank_prev,
        },
        "metrics_7d": {
            "likes_7d": likes_7d,
            "comments_7d": comments_7d,
            "reposts_7d": reposts_7d,
            "quotes_7d": quotes_7d,
            "views_7d": views_7d,
            "followers_now": followers,
            "tips_count_7d": tips_count_7d,
            "tips_amount_7d": tips_amount_7d,
        },
        "trend": {
            "daily_scores": daily_scores,
        },
        "onchain": {
            "tip_tx_count_7d": tip_tx_count_7d,
            "net_buy_volume_7d": net_buy_volume_7d,
        },
    }

    return creator_context

# =========================
# LLM 호출 함수
# =========================

def generate_meme_score_explanation(creator_context: dict, lang: str = "ko") -> str:
    """
    creator_context(dict)를 LLM에 넘겨서
    MemeScore 설명 문장을 생성하는 함수.
    """

    user_prompt = USER_PROMPT_TEMPLATE.format(
        lang=lang,
        context_json=json.dumps(creator_context, ensure_ascii=False, indent=2),
    )

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT.strip()},
            {"role": "user", "content": user_prompt.strip()},
        ],
        temperature=0.7,
        max_tokens=800,
    )

    return response.choices[0].message.content

# =========================
# 테스트 실행 예시
# =========================

if __name__ == "__main__":
    demo_context = build_creator_context(
        username="demoUser",
        user_tag="ABC123",
        display_name="Demo User",
        profile_image_url="https://example.com/profile.png",
        followers=1234,
        country="South Korea",
        score_current=78.4,
        score_prev=65.1,
        rank_current=12,
        rank_prev=27,
        likes_7d=420,
        comments_7d=123,
        reposts_7d=88,
        quotes_7d=42,
        views_7d=58230,
        tips_count_7d=5,
        tips_amount_7d=0.42,
        daily_scores=[
            {"date": "2025-11-27", "score": 64.3},
            {"date": "2025-11-28", "score": 66.1},
            {"date": "2025-11-29", "score": 70.5},
            {"date": "2025-11-30", "score": 72.0},
            {"date": "2025-12-01", "score": 75.8},
            {"date": "2025-12-02", "score": 78.4},
        ],
        tip_tx_count_7d=5,
        net_buy_volume_7d=12345.6,
    )

    explanation_ko = generate_meme_score_explanation(demo_context, lang="ko")
    print("=== AI 설명 (한국어) ===")
    print(explanation_ko)