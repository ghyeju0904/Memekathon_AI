# 필요한 데이터
parts = compute_memescore_parts(
    likes_7d,            # 최근 7일 좋아요 총합
    comments_7d,         # 최근 7일 댓글 총합
    reposts_7d,          # 최근 7일 리포스트 총합
    quotes_7d,           # 최근 7일 인용 총합
    views_7d,            # 최근 7일 조회수 총합
    float(followers),    # 현재 팔로워 수
    tip_count_7d,        # 최근 7일 Tip 횟수 총합
    tip_amount_7d,       # 최근 7일 Tip 금액 총액
)

## 예시
likes_7d = 180
comments_7d = 45
reposts_7d = 22
quotes_7d = 8
views_7d = 14500
followers = 520
tip_count_7d = 4
tip_amount_7d = 1.2
