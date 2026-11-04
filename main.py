
import json
import os
import time
from datetime import date, timedelta

import requests
import firebase_admin
from firebase_admin import credentials, messaging


# -----------------------------
# 기본 설정
# -----------------------------

API_URL = "https://cgv.co.kr/api/v1/booking/searchMovScnInfo"

SITE_NO = "0013"
IMAX_SCREEN_NO = "018"

TARGET_MOVIES = {
    "듄",
    "듄:파트2",
}

CHECK_DAYS = 30
CHECK_INTERVAL = 300  # 5분

TOKEN_FILE = "tokens.json"
STATE_FILE = "notified.json"


# -----------------------------
# Firebase 초기화
# -----------------------------

if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)


# -----------------------------
# 로컬 파일 읽기 / 저장
# -----------------------------

def load_json(filename, default):
    if not os.path.exists(filename):
        return default

    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# -----------------------------
# 푸시 알림
# -----------------------------

def send_push_notification(title, body):
    tokens = load_json(TOKEN_FILE, [])

    if not tokens:
        print("⚠️ tokens.json에 FCM 토큰이 없습니다.")
        return

    message = messaging.MulticastMessage(
        notification=messaging.Notification(
            title=title,
            body=body
        ),
        tokens=tokens
    )

    response = messaging.send_each_for_multicast(message)

    print(
        f"📨 푸시 발송 결과: "
        f"성공 {response.success_count}, "
        f"실패 {response.failure_count}"
    )


# -----------------------------
# 영화 제목 판별
# -----------------------------

def normalize_title(title):
    return "".join(title.split()).replace("：", ":")


def is_target_movie(title):
    normalized = "".join(title.upper().split())
    normalized = normalized.replace("：", ":").replace("-", ":")

    # 듄 2편을 먼저 판별
    if "파트2" in normalized or "PART2" in normalized:
        return "듄" in normalized or "DUNE" in normalized

    # 1편은 제목이 듄 또는 DUNE인 경우
    return normalized in {"듄", "DUNE"}


# -----------------------------
# CGV 상영 정보 조회
# -----------------------------

def check_cgv_imax(target_date):
    params = {
        "coCd": "A420",
        "siteNo": SITE_NO,
        "scnYmd": target_date,
        "rtctlScopCd": "08"
    }

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/130.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://cgv.co.kr/",
    }

    response = requests.get(
        API_URL,
        params=params,
        headers=headers,
        timeout=15
    )

    response.raise_for_status()

    result = response.json()

    if result.get("statusCode") != 0:
        print("⚠️ CGV 응답 오류:", result.get("statusMessage"))
        return None

    screenings = []

    for item in result.get("data", []):
        if item.get("scnsNo") != IMAX_SCREEN_NO:
            continue

        movie_name = item.get("movNm", "").strip()

        if not is_target_movie(movie_name):
            continue

        screenings.append(item)

    return screenings


# -----------------------------
# 신규 회차 감시
# -----------------------------

def check_new_screenings():
    notified = load_json(STATE_FILE, [])
    notified_set = set(notified)

    today = date.today()

    for offset in range(CHECK_DAYS):
        target_date = (
            today + timedelta(days=offset)
        ).strftime("%Y%m%d")

        try:
            screenings = check_cgv_imax(target_date)

            if screenings is None:
                continue

            for item in screenings:
                movie_name = item.get("movNm", "").strip()
                screen_name = item.get("scnsNm", "")
                sequence = item.get("scnSseq", "")
                start_time = item.get("scnsrtTm", "")

                # 회차별 고유 식별값
                unique_key = "|".join([
                    target_date,
                    item.get("prodNo", ""),
                    item.get("scnsNo", ""),
                    sequence,
                    start_time
                ])

                if unique_key in notified_set:
                    continue

                formatted_time = (
                    start_time[:2] + ":" + start_time[2:]
                    if len(start_time) == 4
                    else start_time
                )

                title = f"듄 IMAX 예매 알림!"
                body = (
                    f"{movie_name} / {screen_name}\n"
                    f"{target_date} {formatted_time} "
                    f"{sequence}회차"
                )

                print("🎬 신규 회차 발견:", body)

                send_push_notification(title, body)

                notified_set.add(unique_key)
                notified.append(unique_key)

                save_json(STATE_FILE, notified)

        except requests.RequestException as e:
            print(f"⚠️ {target_date} CGV 요청 실패: {e}")

        except Exception as e:
            print(f"⚠️ {target_date} 처리 오류: {e}")


# -----------------------------
# 프로그램 실행
# -----------------------------

if __name__ == "__main__":
    print("🚀 듄 1편 / 2편 용산 IMAX 감시 시작")

    while True:
        print("\n🔎 CGV 상영 정보 확인 중...")

        check_new_screenings()

        print(f"⏳ {CHECK_INTERVAL}초 후 다시 확인합니다.")
        time.sleep(CHECK_INTERVAL)
