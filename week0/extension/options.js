const el = document.getElementById("server");
chrome.storage.sync.get("server").then(({ server }) => { el.value = server || ""; });
document.getElementById("save").onclick = async () => {
  const v = el.value.trim();
  if (v && !/^https?:\/\//.test(v)) { document.getElementById("msg").textContent = "Must start with http:// or https://"; return; }
  await chrome.storage.sync.set({ server: v });
  document.getElementById("msg").textContent = "Saved. If it's not localhost:8765, grant access when Chrome asks, or edit host_permissions.";
};
