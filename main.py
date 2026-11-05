
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

TOKEN_FILE = "tokens.json"
STATE_FILE = "notified.json"
CONFIG_FILE = "config.json"


# -----------------------------
# 설정 파일 읽기
# -----------------------------

def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


config = load_config()

THEATERS = config["theaters"]
TARGET_MOVIES = config["movies"]
CHECK_DAYS = config.get("check_days", 30)
CHECK_INTERVAL = config.get("check_interval", 300)


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
# 디스코드 알림
# -----------------------------

def send_discord_notification(title, body):
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")

    if not webhook_url:
        print("⚠️ 디스코드 웹훅 URL이 설정되지 않았습니다.")
        return

    payload = {
        "username": "CGV 알림봇",
        "content": f"🎬 **{title}**\n{body}"
    }

    try:
        response = requests.post(
            webhook_url,
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        print("💬 디스코드 알림 발송 성공!")

    except requests.RequestException as e:
        print(f"⚠️ 디스코드 알림 발송 실패: {e}")


# -----------------------------
# 영화 제목 판별
# -----------------------------

def normalize_title(title):
    return (
        "".join(str(title).upper().split())
        .replace("：", "")
        .replace(":", "")
        .replace("-", "")
    )


def is_target_movie(title):
    normalized = normalize_title(title)

    return any(
        normalized == normalize_title(target)
        for target in TARGET_MOVIES
    )


# -----------------------------
# CGV 상영 정보 조회
# -----------------------------

def check_cgv_theater(theater, target_date):
    params = {
        "coCd": "A420",
        "siteNo": theater["site_no"],
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
        timeout=(5, 15)
    )

    response.raise_for_status()
    result = response.json()

    if result.get("statusCode") != 0:
        print("⚠️ CGV 응답 오류:", result.get("statusMessage"))
        return None

    screenings = []

    # 빈 배열이면 모든 상영관 허용
    screen_nos = [
        str(no) for no in theater.get("screen_nos", [])
    ]

    for item in result.get("data", []):
        screen_no = str(item.get("scnsNo", ""))

        if screen_nos and screen_no not in screen_nos:
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

    for theater in THEATERS:
        theater_name = theater["name"]
        site_no = str(theater["site_no"])

        print(f"\n🏢 {theater_name} 확인 시작")

        for offset in range(CHECK_DAYS):
            target_date = (
                today + timedelta(days=offset)
            ).strftime("%Y%m%d")

            try:
                screenings = check_cgv_theater(
                    theater,
                    target_date
                )

                if screenings is None:
                    continue

                for item in screenings:
                    movie_name = item.get("movNm", "").strip()
                    screen_name = item.get("scnsNm", "")
                    sequence = item.get("scnSseq", "")
                    start_time = item.get("scnsrtTm", "")

                    # 지점까지 포함한 회차별 고유 식별값
                    unique_key = "|".join([
                        site_no,
                        target_date,
                        item.get("prodNo", ""),
                        str(item.get("scnsNo", "")),
                        str(sequence),
                        str(start_time)
                    ])

                    # 기존 용산 IMAX 알림 기록도 확인
                    legacy_key = "|".join([
                        target_date,
                        item.get("prodNo", ""),
                        str(item.get("scnsNo", "")),
                        str(sequence),
                        str(start_time)
                    ])

                    if (
                        unique_key in notified_set
                        or (
                            site_no == "0013"
                            and legacy_key in notified_set
                        )
                    ):
                        continue

                    formatted_time = (
                        start_time[:2] + ":" + start_time[2:]
                        if len(start_time) == 4
                        else start_time
                    )

                    title = f"{movie_name} 상영 알림!"
                    body = (
                        f"{theater_name} / {screen_name}\n"
                        f"{target_date} {formatted_time} "
                        f"{sequence}회차"
                    )

                    print("🎬 신규 회차 발견:", body)

                    send_push_notification(title, body)
                    send_discord_notification(title, body)

                    notified_set.add(unique_key)
                    notified.append(unique_key)

                    save_json(STATE_FILE, notified)

            except requests.RequestException as e:
                print(f"⚠️ {theater_name} {target_date} 요청 실패: {e}")

            except Exception as e:
                print(f"⚠️ {theater_name} {target_date} 처리 오류: {e}")


# -----------------------------
# 프로그램 실행
# -----------------------------

if __name__ == "__main__":
    print("🚀 CGV 전체 상영관 감시 시작")

    print("감시 지점:")
    for theater in THEATERS:
        print(f"- {theater['name']}")

    print("감시 영화:", ", ".join(TARGET_MOVIES))
    print(f"확인 기간: {CHECK_DAYS}일")
    print(f"확인 간격: {CHECK_INTERVAL}초")

    while True:
        print("\n🔎 CGV 상영 정보 확인 중...")

        check_new_screenings()

        print(
            f"⏳ {CHECK_INTERVAL}초 후 다시 확인합니다."
        )

        time.sleep(CHECK_INTERVAL)
