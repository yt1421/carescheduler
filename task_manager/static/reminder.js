// 今日やることページで、期限超過・本日期限のタスクがある場合にブラウザ通知でリマインドする。
(function () {
  const banner = document.getElementById("reminder-banner");
  if (!banner || typeof Notification === "undefined") return;

  const message = banner.textContent.trim();

  function notify() {
    new Notification("看護管理タスク リマインド", { body: message });
  }

  if (Notification.permission === "granted") {
    notify();
  } else if (Notification.permission !== "denied") {
    Notification.requestPermission().then((permission) => {
      if (permission === "granted") notify();
    });
  }
})();
