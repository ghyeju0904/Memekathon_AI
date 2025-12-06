## 👾 코드 구현
**API 버전**  
파일명 - meme_explainer.py  
실행코드 - python meme_explainer.py userName

**Dummy 버전**
파일명 - dummy_explainer.py  
실행코드 - python dummy_explainer.py userName

**코드 차이점**  
매트릭 호출 부분 - 
`def fetch_creator_metrics(creator_id: str) -> Dict[str, Any]:...`
 - get_user_posts 대신 data/dummy_data.py의 DUMMY_ACTIVITY_7D 사용
- 그 외 점수계산, 구간 라벨링, LLM 설명, 최종 출력 구조, bot_score 계산 부분 동일   


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