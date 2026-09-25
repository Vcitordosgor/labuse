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

refreshStatus();
