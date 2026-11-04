
import time
import requests
from bs4 import BeautifulSoup

import firebase_admin
from firebase_admin import credentials, messaging


# ----------------------------------------------------
# 1. Firebase 인증 및 설정
# ----------------------------------------------------

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

# 실제 새로 발급받은 FCM 토큰으로 교체
USER_FCM_TOKENS = [
    "여기에_FCM_토큰_입력",
]


def send_push_notification(title, body):
    """등록된 기기들에 푸시 알림 발송"""

    if not USER_FCM_TOKENS or USER_FCM_TOKENS[0] == "여기에_FCM_토큰_입력":
        print("⚠️ FCM 토큰을 등록해주세요.")
        return

    message = messaging.MulticastMessage(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        tokens=USER_FCM_TOKENS,
    )

    response = messaging.send_each_for_multicast(message)

    print(
        f"✅ 알림 발송 결과: "
        f"성공 {response.success_count}건, "
        f"실패 {response.failure_count}건"
    )


# ----------------------------------------------------
# 2. CGV 용산 IMAX 예매 감시 함수
# ----------------------------------------------------


def check_cgv_imax(target_date):

    url = "https://www.cgv.co.kr/common/showtimes/iframeTheater.aspx"

    params = {
        "areacode": "01",
        "theaterCode": "0013",
        "date": target_date
    }

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=15
        )

        response.raise_for_status()

        # CGV 원본 HTML 저장
        with open("cgv_debug.html", "w", encoding="utf-8") as f:
            f.write(response.text)

        soup = BeautifulSoup(response.text, "html.parser")

        print("응답 HTML 길이:", len(response.text))
        print(
            "IMAX 상영관 목록:",
            len(soup.select("div.sect-showtimes > ul > li"))
        )
        print("듄 1편 포함 여부:", "듄" in response.text)
        print("듄 2편 포함 여부:", "듄: 파트 2" in response.text)

        hall_list = soup.select("div.sect-showtimes > ul > li")

        for hall in hall_list:

            hall_title = hall.select_one(
                "div.info-hall > ul > li:nth-child(2)"
            )

            if hall_title and "IMAX" in hall_title.get_text():

                time_slots = hall.select(
                    "div.info-timetable > ul > li"
                )

                if len(time_slots) > 0:
                    return True

        return False

    except requests.RequestException as e:
        print(f"⚠️ CGV 접속 오류: {e}")
        return None

    except Exception as e:
        print(f"⚠️ 데이터 확인 오류: {e}")
        return None



# ----------------------------------------------------
# 3. 메인 감시 루프
# ----------------------------------------------------

def main():

    TARGET_DATE = "20261202"

    CHECK_INTERVAL = 30

    print(
        f"🚀 [CGV 용산 IMAX] "
        f"{TARGET_DATE} 예매 감시를 시작합니다."
    )

    while True:

        now_time = time.strftime("%H:%M:%S")

        is_open = check_cgv_imax(TARGET_DATE)

        if is_open is True:

            print(
                f"[{now_time}] 🎉 "
                "IMAX 상영 정보가 발견되었습니다!"
            )

            send_push_notification(
                "🎬 CGV 용산 IMAX 상영 정보 발견!",
                f"{TARGET_DATE} 용산 IMAX 상영 정보가 확인됐습니다."
            )

            break

        elif is_open is False:

            print(
                f"[{now_time}] 아직 상영 정보가 없습니다. "
                f"({CHECK_INTERVAL}초 후 재확인)"
            )

        else:

            print(
                f"[{now_time}] 확인 실패. "
                "다음 주기에 다시 시도합니다."
            )

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
