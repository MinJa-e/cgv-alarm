import firebase_admin
from firebase_admin import credentials, messaging

# 1. Firebase 인증
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

# 2. 🔴 여러 개 토큰을 리스트로 등록 (쉼표로 구분)
USER_FCM_TOKENS = [
    "cs_tn9sT-krm5ocHfOzGkL:APA91bFq-JN0NaVeKYHg-Zi4Hjem5K6irdQN5xEsogz7TugJ0kS-lDolcZ5wxaw2aejSKj_mdjmY4ge5mXxa5j-iL6LqrrJEW_9lXc846y1LignEsNHkhMo",
    "fUxaqBzJqMC6ajwbZ-Y664:APA91bEKAU2_4KUZ2_DFm_JP0JYGO13Mng2nhpikdMSvs9LpmUXOK_oFwX8RpXBMvcM1ri8wOzJsII0MPErFH_b5ax7skiYp0uqxhh7QSiFWIU9S4vNeEdY",
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