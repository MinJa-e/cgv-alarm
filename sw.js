importScripts('https://www.gstatic.com/firebasejs/10.8.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.8.0/firebase-messaging-compat.js');

// 🔴 [수정 필요] index.html과 동일한 firebaseConfig 정보를 넣으세요.
firebase.initializeApp({
      apiKey: "AIzaSyC57js6l9dVqgxdN1D5gri9kJa-cOzawAA",
      authDomain: "cgv-alarm-ddc5c.firebaseapp.com",
      projectId: "cgv-alarm-ddc5c",
      storageBucket: "cgv-alarm-ddc5c.firebasestorage.app",
      messagingSenderId: "1016931664",
      appId: "1:1016931664:web:75864aa32de8f949cd7855"
});

const messaging = firebase.messaging();

// 핸드폰이 꺼져있을 때 백그라운드에서 푸시 알림을 띄워주는 역할
messaging.onBackgroundMessage((payload) => {
  const notificationTitle = payload.notification.title;
  const notificationOptions = {
    body: payload.notification.body,
    icon: '/icon.png',
    data: { url: payload.data?.url || 'http://m.cgv.co.kr' }
  };

  self.registration.showNotification(notificationTitle, notificationOptions);
});

// 알림을 클릭하면 CGV 페이지로 이동
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil(
    clients.openWindow(event.notification.data.url)
  );
});