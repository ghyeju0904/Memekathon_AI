# dummy_data.py
"""
해커톤 데모용 더미 7일 활동 데이터셋.

- 실제 API에서 posts가 비어 있을 때
- meme_explainer.fetch_creator_metrics() 에서 fallback 용으로 사용.

key = MemeX userName (예: "zIfjpicANr")
"""

DUMMY_ACTIVITY_7D = {
    # 1) Vesta.Crona (zIfjpicANr) - 상위 크리에이터 느낌
    "zIfjpicANr": {
        "likes_7d": 950,       # 좋아요 950개
        "comments_7d": 310,    # 댓글 310개
        "reposts_7d": 180,     # 리포스트 180회
        "quotes_7d": 72,       # 인용 72회
        "views_7d": 190_000,   # 조회수 19만 회
        "followers": 7_500,    # 팔로워 7,500명
        "tip_count_7d": 26,    # Tip 26번
        "tip_amount_7d": 15.3, # Tip 총 15.3 토큰 (테스트넷)
    },

    # 2) Jarod47 (YTLb8s9) - 중위권, 꾸준한 활동
    "YTLb8s9": {
        "likes_7d": 180,
        "comments_7d": 45,
        "reposts_7d": 22,
        "quotes_7d": 8,
        "views_7d": 14_500,
        "followers": 520,
        "tip_count_7d": 4,
        "tip_amount_7d": 1.2,
    },

    # 3) Jonathan.Reynolds (CWar5xLFJW) - 성장 단계의 작은 크리에이터
    "CWar5xLFJW": {
        "likes_7d": 40,
        "comments_7d": 8,
        "reposts_7d": 3,
        "quotes_7d": 1,
        "views_7d": 2_500,
        "followers": 120,
        "tip_count_7d": 0,
        "tip_amount_7d": 0.0,
    },

    # 4) Margaret.Wiza39 (cQECd) - 조회수 대비 반응이 적은, 살짝 수상한 패턴
    "cQECd": {
        "likes_7d": 60,
        "comments_7d": 3,
        "reposts_7d": 1,
        "quotes_7d": 0,
        "views_7d": 90_000,
        "followers": 300,
        "tip_count_7d": 0,
        "tip_amount_7d": 0.0,
    },
}