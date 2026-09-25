// Options : formulaire → chrome.storage.local. Reprogramme l'alarme au save.

const fields = ["searchUrl", "labuseUrl", "token", "hour", "jitterMaxMin"];

async function load() {
  const d = await chrome.storage.local.get({
    searchUrl: "",
    labuseUrl: "http://localhost:8205",
    token: "",
    hour: 21,
    jitterMaxMin: 180
  });
  for (const f of fields) document.getElementById(f).value = d[f];
}

document.getElementById("save").addEventListener("click", async () => {
  const patch = {
    searchUrl: document.getElementById("searchUrl").value.trim(),
    labuseUrl: document.getElementById("labuseUrl").value.trim() || "http://localhost:8205",
    token: document.getElementById("token").value.trim(),
    hour: Math.max(0, Math.min(23, parseInt(document.getElementById("hour").value, 10) || 21)),
    jitterMaxMin: Math.max(0, Math.min(600, parseInt(document.getElementById("jitterMaxMin").value, 10) || 180))
  };
  await chrome.storage.local.set(patch);
  try { await chrome.runtime.sendMessage({ type: "reschedule" }); } catch (_) {}
  const s = document.getElementById("saved");
  s.textContent = "Enregistré.";
  setTimeout(() => { s.textContent = ""; }, 2000);
});

load();
