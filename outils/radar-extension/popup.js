// Popup : bouton "Capturer maintenant", ligne d'état, lien options.

const runBtn = document.getElementById("run");
const statusEl = document.getElementById("status");
const optsLink = document.getElementById("opts");

async function refreshStatus() {
  const d = await chrome.storage.local.get({ lastRun: null, lastResult: null });
  if (d.lastResult) {
    statusEl.textContent = d.lastResult;
  } else {
    statusEl.textContent = "Aucune capture pour l'instant.";
  }
}

runBtn.addEventListener("click", async () => {
  runBtn.disabled = true;
  statusEl.textContent = "Capture en cours…";
  try {
    const res = await chrome.runtime.sendMessage({ type: "run-now" });
    if (res && res.ok) {
      await refreshStatus();
    } else {
      statusEl.textContent = "Erreur : " + (res && res.error ? res.error : "inconnue");
    }
  } catch (e) {
    statusEl.textContent = "Erreur : " + String(e);
  } finally {
    runBtn.disabled = false;
  }
});

optsLink.addEventListener("click", (e) => {
  e.preventDefault();
  chrome.runtime.openOptionsPage();
});

// RADAR-FIX-1 (3) — recette : forcer l'alarme à +2 min et vérifier que la capture part TOUTE SEULE.
const testAlarmLink = document.getElementById("testalarm");
if (testAlarmLink) {
  testAlarmLink.addEventListener("click", async (e) => {
    e.preventDefault();
    try {
      const res = await chrome.runtime.sendMessage({ type: "test-alarm" });
      statusEl.textContent = res && res.ok
        ? "Alarme programmée dans 2 min — laissez Chrome ouvert, la capture partira seule."
        : "Erreur : " + (res && res.error ? res.error : "inconnue");
    } catch (err) {
      statusEl.textContent = "Erreur : " + String(err);
    }
  });
}

refreshStatus();
