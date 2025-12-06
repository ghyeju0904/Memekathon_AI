## 🧮 MemeScore 입력 데이터 예시

`compute_memescore_parts()` 함수는 **최근 7일간의 활동 데이터 + 현재 팔로워 수 + Tip 정보**를 입력으로 받아 MemeScore를 구성하는 세부 점수들을 계산

```python
# 필요한 데이터
parts = compute_memescore_parts(
    likes_7d,        # 최근 7일 좋아요 총합
    comments_7d,     # 최근 7일 댓글 총합
    reposts_7d,      # 최근 7일 리포스트 총합
    quotes_7d,       # 최근 7일 인용(Quote) 총합
    views_7d,        # 최근 7일 조회수 총합
    float(followers),# 현재 팔로워 수
    tip_count_7d,    # 최근 7일 Tip(후원) 횟수
    tip_amount_7d,   # 최근 7일 Tip(후원) 금액 총액
)

# 예시 데이터
likes_7d      = 180
comments_7d   = 45
reposts_7d    = 22
quotes_7d     = 8
views_7d      = 14_500
followers     = 520
tip_count_7d  = 4
tip_amount_7d = 1.2   # 예: 1.2 ETH 또는 1.2 BASE 등, 서비스 기준 화폐 단위