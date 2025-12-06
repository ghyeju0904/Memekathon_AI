import os
import requests
import pandas as pd

# =========================
# 기본 설정
# =========================
BASE_URL = "https://insectarium-public-api.memex.xyz"
API_PREFIX = "/public/v1"

# 토큰이 필요하면 환경변수에 MEMEX_API_TOKEN 넣어두고 사용
AUTH_TOKEN = os.getenv("MEMEX_API_TOKEN")

def make_headers() -> dict:
    headers = {"Accept": "application/json"}
    if AUTH_TOKEN:
        headers["authorization"] = AUTH_TOKEN
    return headers

# CSV 저장 폴더
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)


# =========================
# 0) 모의 3000 유저 목록
#    GET /public/v1/memekathon/mock-user-data
# =========================
def get_mock_user_data():
    url = f"{BASE_URL}{API_PREFIX}/memekathon/mock-user-data"
    resp = requests.get(url, headers=make_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()


# =========================
# 1) 유저 기본 정보
#    GET /public/v1/user/{username}/{usernametag}
# =========================
def get_user_basic(username: str, usernametag: str):
    url = f"{BASE_URL}{API_PREFIX}/user/{username}/{usernametag}"
    resp = requests.get(url, headers=make_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()


# =========================
# 2) 유저 게시물
#    GET /public/v1/user/{username}/{usernametag}/posts
#
# 응답 예시 형태:
# {
#   "pinPost": {...} | null,
#   "contents": [ {...}, {...}, ... ],
#   "nextCursor": 123 | null,
#   "repostCursor": 0 | null
# }
# =========================
def get_user_posts(
    username: str,
    usernametag: str,
    limit: int = 50,
    cursor: int | None = None,
    repost_cursor: int | None = None,
):
    """
    특정 유저의 게시물 목록 가져오기 + RAW 응답 디버깅 출력
    """
    url = f"{BASE_URL}{API_PREFIX}/user/{username}/{usernametag}/posts"
    params: dict = {"limit": limit}
    if cursor is not None:
        params["cursor"] = cursor
    if repost_cursor is not None:
        params["rePostCursor"] = repost_cursor

    # ✅ 실제 요청 보내는 부분
    resp = requests.get(url, headers=make_headers(), params=params, timeout=10)

    # ✅ 여기서 RAW 응답 상태코드 + 앞 500글자 출력해서 뭐가 오는지 확인
    print("RAW posts response status:", resp.status_code)
    print("RAW posts response body:", resp.text[:500], "\n")

    # 에러면 예외 발생
    resp.raise_for_status()

    # JSON 파싱
    data = resp.json()

    # 아래부터는 기존 로직 그대로
    if isinstance(data, dict):
        posts = data.get("contents", [])  # 실제 게시물 리스트
        meta = {
            "pinPost": data.get("pinPost"),
            "nextCursor": data.get("nextCursor"),
            "repostCursor": data.get("repostCursor"),
        }
    elif isinstance(data, list):
        posts = data
        meta = {}
    else:
        posts, meta = [], {}

    return posts, meta



# =========================
# 3) 유저 거래 내역
#    GET /public/v1/user/{username}/{usernametag}/trade-history
# =========================
def get_user_trade_history(username: str, usernametag: str):
    url = f"{BASE_URL}{API_PREFIX}/user/{username}/{usernametag}/trade-history"
    resp = requests.get(url, headers=make_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()


# =========================
# 4) 유저 보유 토큰
#    GET /public/v1/user/{username}/{usernametag}/hold-tokens
# =========================
def get_user_hold_tokens(
    username: str,
    usernametag: str,
    sort_order: str | None = "desc",
    sort_by: str | None = "totalUsdValue",
):
    url = f"{BASE_URL}{API_PREFIX}/user/{username}/{usernametag}/hold-tokens"
    params: dict = {}
    if sort_order:
        params["sortOrder"] = sort_order
    if sort_by:
        params["sortBy"] = sort_by

    resp = requests.get(url, headers=make_headers(), params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


# =========================
# 5) 유저 스폰서
#    GET /public/v1/user/{username}/{usernametag}/sponsors
# =========================
def get_user_sponsors(username: str, usernametag: str):
    url = f"{BASE_URL}{API_PREFIX}/user/{username}/{usernametag}/sponsors"
    resp = requests.get(url, headers=make_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()


# =========================
# 6) 토큰 최신 가격 (필요하면 사용)
#    GET /public/v1/price/latest/{chainId}/{tokenAddress}
# =========================
def get_token_latest_price(chain_id: int, token_address: str):
    url = f"{BASE_URL}{API_PREFIX}/price/latest/{chain_id}/{token_address}"
    resp = requests.get(url, headers=make_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()


# =========================
# 7) 토큰 가격 차트 (필요하면 사용)
#    GET /public/v1/price/chart/{chainId}/{tokenAddress}/{interval}/{startTime}/{endTime}
# =========================
def get_token_price_chart(
    chain_id: int,
    token_address: str,
    interval: str,
    start_time: str,
    end_time: str,
):
    url = (
        f"{BASE_URL}{API_PREFIX}/price/chart/"
        f"{chain_id}/{token_address}/{interval}/{start_time}/{end_time}"
    )
    resp = requests.get(url, headers=make_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()


# =========================
# 8) 유저 홀더 목록 (필요하면 사용)
#    GET /public/v1/user/{username}/{usernametag}/holders/{count}
# =========================
def get_user_holders(username: str, usernametag: str, count: int = 50):
    url = f"{BASE_URL}{API_PREFIX}/user/{username}/{usernametag}/holders/{count}"
    resp = requests.get(url, headers=make_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()


# =========================
# 메인: 활동 있는 유저 찾아서 CSV 저장
# =========================
if __name__ == "__main__":
    # 0. mock user 전체 가져와서 CSV 저장
    mock_users = get_mock_user_data()
    print(f"🔹 mock users: {len(mock_users)}명")

    mock_df = pd.DataFrame(mock_users)
    mock_csv_path = os.path.join(DATA_DIR, "mock_users.csv")
    mock_df.to_csv(mock_csv_path, index=False, encoding="utf-8-sig")
    print(f"💾 mock_users.csv 저장 완료: {mock_csv_path}")

    # 1. 활동 있는 유저 찾기 (게시물/보유토큰/스폰서/거래 중 하나라도 있으면 OK)
    active = None

    for u in mock_users:
        username = u["userName"]
        usernametag = u["userNameTag"]

        print(f"🔎 후보 유저 확인 중: {username} #{usernametag}")

        posts, _ = get_user_posts(username, usernametag, limit=20)
        hold_tokens = get_user_hold_tokens(username, usernametag)
        sponsors = get_user_sponsors(username, usernametag)
        trade_history = get_user_trade_history(username, usernametag)

        if posts or hold_tokens or sponsors or trade_history:
            active = {
                "user": u,
                "posts": posts,
                "hold_tokens": hold_tokens,
                "sponsors": sponsors,
                "trade_history": trade_history,
            }
            print("✅ 활동 있는 유저 발견!")
            break

    if active is None:
        print("😥 활동 기록 있는 mock 유저를 찾지 못했습니다.")
        raise SystemExit(1)

    # 2. 선택된 유저 정보
    u = active["user"]
    username = u["userName"]
    usernametag = u["userNameTag"]
    print("🎯 최종 선택 유저:", username, usernametag)

    # 3. 유저 기본 정보 CSV
    user_info = get_user_basic(username, usernametag)
    print("🔹 User basic:", user_info)

    user_df = pd.DataFrame([user_info])
    user_basic_path = os.path.join(
        DATA_DIR, f"user_basic_{username}_{usernametag}.csv"
    )
    user_df.to_csv(user_basic_path, index=False, encoding="utf-8-sig")
    print(f"💾 user_basic CSV 저장 완료: {user_basic_path}")

    # 4. 게시물 CSV
    posts = active["posts"]
    print("🔹 Posts count:", len(posts))
    if posts:
        posts_df = pd.DataFrame(posts)
        posts_path = os.path.join(
            DATA_DIR, f"user_posts_{username}_{usernametag}.csv"
        )
        posts_df.to_csv(posts_path, index=False, encoding="utf-8-sig")
        print(f"💾 user_posts CSV 저장 완료: {posts_path}")
    else:
        print("⚠️ 이 유저는 posts 데이터가 없어서 CSV는 생략합니다.")

    # 5. 보유 토큰 CSV
    hold_tokens = active["hold_tokens"]
    print("🔹 Hold tokens count:", len(hold_tokens))
    if hold_tokens:
        hold_df = pd.DataFrame(hold_tokens)
        hold_path = os.path.join(
            DATA_DIR, f"user_hold_tokens_{username}_{usernametag}.csv"
        )
        hold_df.to_csv(hold_path, index=False, encoding="utf-8-sig")
        print(f"💾 user_hold_tokens CSV 저장 완료: {hold_path}")
    else:
        print("⚠️ 이 유저는 hold-tokens 데이터가 없어서 CSV는 생략합니다.")

    # 6. 스폰서 CSV
    sponsors = active["sponsors"]
    print("🔹 Sponsors count:", len(sponsors))
    if sponsors:
        sponsors_df = pd.DataFrame(sponsors)
        sponsors_path = os.path.join(
            DATA_DIR, f"user_sponsors_{username}_{usernametag}.csv"
        )
        sponsors_df.to_csv(sponsors_path, index=False, encoding="utf-8-sig")
        print(f"💾 user_sponsors CSV 저장 완료: {sponsors_path}")
    else:
        print("⚠️ 이 유저는 sponsors 데이터가 없어서 CSV는 생략합니다.")

    # 7. 거래 내역 CSV
    trade_history = active["trade_history"]
    print("🔹 Trade history count:", len(trade_history))
    if trade_history:
        trade_df = pd.DataFrame(trade_history)
        trade_path = os.path.join(
            DATA_DIR, f"user_trade_history_{username}_{usernametag}.csv"
        )
        trade_df.to_csv(trade_path, index=False, encoding="utf-8-sig")
        print(f"💾 user_trade_history CSV 저장 완료: {trade_path}")
    else:
        print("⚠️ 이 유저는 trade-history 데이터가 없어서 CSV는 생략합니다.")