window.APPGLOBALS = {};

const SCAN_INTERVAL = 60000; // ms
const API_URL = "http://localhost:8888";

async function attemptRegistration(registrationId) {
  await fetch(`${API_URL}/register/${registrationId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
}

async function poll(synchronous=false) {
  const targetDate = document.getElementById("target-date").value;
  const targetClass = document.getElementById("target-class").value;
  const autoSubscribeTime = document.getElementById(
    "auto-subscribe-time"
  ).value;
  const response = await fetch(`${API_URL}/search/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      target_date: targetDate,
      target_class: targetClass,
    }),
  });

  if (response.ok) {
    const payload = await response.json();
    const template = document.createElement("template");

    template.innerHTML = payload.rawHTML.trim();
    const outputElem = document.getElementById("output-box");

    for (var i = 0; i < outputElem.children.length; i++) {
      const e = outputElem.children[i];
      outputElem.removeChild(e);
    }

    const content = template.content;
    for (x of Array.from(content.querySelectorAll("a.reserve"))) {
      if (x.innerHTML.includes("Inschrijven")) {
        new Notification("Class available");
        const registrationId = x.id.split("_")[1];
        const startTime =
          x.parentElement.parentElement.previousElementSibling.firstElementChild.firstElementChild.textContent
            .slice(0, 6)
            .trim();

        if (autoSubscribeTime && startTime && startTime === autoSubscribeTime) {
          const confirmed = synchronous && confirm(`Do you want to register at ${startTime}?`);

          if (!synchronous || confirmed) {
            await attemptRegistration(registrationId);
            stopScanning();
            new Notification(
                `Attempted registration at ${startTime}. Scan stopped.`
            );
          }
        }
      }
    }

    outputElem.appendChild(content);

    if (window.APPGLOBALS.isScanning) {
      window.APPGLOBALS.curScanID = setTimeout(poll, SCAN_INTERVAL);
    }
  } else {
    stopScanning();
    alert(
      "Something went wrong while polling server. Scanning has been stopped."
    );
  }
}

function stopScanning() {
  window.APPGLOBALS.isScanning = false;
  document.getElementById("scan-indicator").classList.remove("lds-ellipsis");
  if (window.APPGLOBALS.curScanID) {
    clearTimeout(window.APPGLOBALS.curScanID);
  }
}

function startScanning() {
  if (!window.APPGLOBALS.isScanning) {
    window.APPGLOBALS.isScanning = true;
    document.getElementById("scan-indicator").classList.add("lds-ellipsis");
    window.APPGLOBALS.curScanID = setTimeout(poll, SCAN_INTERVAL);
  }
}

async function checkNotificationPermissions() {
  if (Notification.permission === "granted") {
    return true;
  } else {
    const r = await Notification.requestPermission();
    if (r === "granted") {
      return true;
    }
    return false;
  }
}

window.addEventListener("load", (event) => {
  document.getElementById("start-btn").addEventListener("click", function () {
    if (checkNotificationPermissions()) {
      startScanning();
    }
  });
  document.getElementById("stop-btn").addEventListener("click", function () {
    stopScanning();
  });
  document
    .getElementById("sync-scan-btn")
    .addEventListener("click", async function () {
      if (checkNotificationPermissions()) {
        await poll(true);
      }
    });
});
