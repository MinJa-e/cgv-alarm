import firebase_admin
from firebase_admin import credentials, messaging

# ----------------------------------------------------
# 1. Firebase 인증 및 설정
# ----------------------------------------------------
# 1. Firebase 인증
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

# 2. 🔴 여러 개 토큰을 리스트로 등록 (쉼표로 구분)
USER_FCM_TOKENS = [
    "cs_tn9sT-krm5ocHfOzGkL:APA91bFq-JN0NaVeKYHg-Zi4Hjem5K6irdQN5xEsogz7TugJ0kS-lDolcZ5wxaw2aejSKj_mdjmY4ge5mXxa5j-iL6LqrrJEW_9lXc846y1LignEsNHkhMo",
    "fUxaqBzJqMC6ajwbZ-Y664:APA91bEKAU2_4KUZ2_DFm_JP0JYGO13Mng2nhpikdMSvs9LpmUXOK_oFwX8RpXBMvcM1ri8wOzJsII0MPErFH_b5ax7skiYp0uqxhh7QSiFWIU9S4vNeEdY",
    "c9niqt92qVBZrQDHTq-tKi:APA91bGgtO9-50SK3ohGg4_3_O-wGFzRpd5uVyccf6RAYiY4X02QOGb_j29FfmFpLhjUMqK_EpRl_A-yyimrKJvC3ZYAl01wzL2E4939oidBPhlm2JX6OC8"
    # 필요하면 세번째, 네번째 계속 추가 가능
]

def send_push_notification(title, body):
    """여러 기기/사용자에게 동시 푸시 알림 발송"""
    message = messaging.MulticastMessage(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        tokens=USER_FCM_TOKENS,
    )
    # 여러 명에게 발송할 때는 send_each_for_multicast 사용
    response = messaging.send_each_for_multicast(message)
    print(f"✅ 알림 전송 완료! (성공: {response.success_count}건, 실패: {response.failure_count}건)")

if __name__ == "__main__":
    print("🚀 테스트 알림 발송 중...")
    send_push_notification(
        "🎬 CGV 용산 IMAX 예매 오픈!", 
        "지금 바로 CGV 앱을 켜서 예매를 진행하세요!"
    )

    # 터미널 테스트 : python main.py


# ----------------------------------------------------
# 2. CGV 용산 IMAX 예매 감시 함수
# ----------------------------------------------------
def check_cgv_imax(target_date):
    """
    target_date: 'YYYYMMDD' 형식 (예: '20260825')
    """
    url = "http://www.cgv.co.kr/common/showtimes/iframeTheater.aspx"
    
    # CGV 용산아이파크몰 극장 코드: 0013
    params = {
        'areacode': '01',
        'theaterCode': '0013',
        'date': target_date
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        response = requests.get(url, params=params, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 상영관 목록 조회
        hall_list = soup.select('div.sect-showtimes > ul > li')
        
        for hall in hall_list:
            # 상영관 이름 추출 (예: IMAX, 4DX 등)
            hall_title = hall.select_one('div.info-hall > ul > li:nth-child(2)')
            
            if hall_title and 'IMAX' in hall_title.text:
                # IMAX관 내에 상영 시간표(좌석 정보/시간)가 열렸는지 확인
                time_slots = hall.select('div.info-timetable > ul > li')
                if len(time_slots) > 0:
                    return True  # IMAX 상영표 열림!
                    
        return False # 아직 안 열림

    except Exception as e:
        print(f"⚠️ 크롤링 중 오류 발생: {e}")
        return False

# ----------------------------------------------------
# 3. 메인 감시 루프 실행
# ----------------------------------------------------
if __name__ == "__main__":
    # 🔴 모니터링할 날짜 설정 (YYYYMMDD)
    TARGET_DATE = "20261202" 
    
    print(f"🚀 [CGV 용산 IMAX] {TARGET_DATE} 예매 감시를 시작합니다...")
    
    while True:
        is_open = check_cgv_imax(TARGET_DATE)
        
        now_time = time.strftime('%H:%M:%S')
        
        if is_open:
            print(f"[{now_time}] 🎉🎉🎉 IMAX 예매가 오픈되었습니다! 알림을 보냅니다.")
            
            # 알림 발송
            send_push_notification(
                "🎬 CGV 용산 IMAX 예매 오픈!",
                f"{TARGET_DATE} 용산 IMAX 상영표가 열렸습니다. 지금 바로 예매하세요!"
            )
            
            # 알림을 쏜 후 감시 종료 (도배 방지)
            break
        else:
            print(f"[{now_time}] 아직 예매 전입니다. (3초 후 재시도)")
            time.sleep(3)  # 3초 대기 후 다시 확인