import { FloorplanViewer } from "./viewer3d.js";

const fileInput = document.getElementById("fileInput");
const dropZone = document.getElementById("dropZone");
const browseBtn = document.getElementById("browseBtn");
const preview = document.getElementById("preview");
const hints = document.getElementById("hints");
const analyzeBtn = document.getElementById("analyzeBtn");
const planBtn = document.getElementById("planBtn");
const status = document.getElementById("status");
const sceneMeta = document.getElementById("sceneMeta");
const viewerEmpty = document.querySelector(".viewer-empty");
const planOutput = document.getElementById("planOutput");
const renoRequest = document.getElementById("renoRequest");
const settingsBtn = document.getElementById("settingsBtn");
const connectionDialog = document.getElementById("connectionDialog");
const connectionForm = document.getElementById("connectionForm");
const credentialMode = document.getElementById("credentialMode");
const servicePrincipalFields = document.getElementById("servicePrincipalFields");
const settingsFeedback = document.getElementById("settingsFeedback");

let selectedFile = null;
let currentScene = null;
const viewer = new FloorplanViewer(document.getElementById("viewer"));

function setStatus(msg, type = "") {
  status.textContent = msg;
  status.className = `status ${type}`;
}

function syncCredentialFields() {
  servicePrincipalFields.hidden = credentialMode.value !== "service_principal";
}

credentialMode.addEventListener("change", syncCredentialFields);

settingsBtn.addEventListener("click", async () => {
  connectionDialog.showModal();
  settingsFeedback.textContent = "Loading connection settings…";
  try {
    const res = await fetch("/api/settings");
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || res.statusText);
    document.getElementById("foundryEndpoint").value = data.foundry_project_endpoint;
    document.getElementById("foundryModel").value = data.foundry_model;
    document.getElementById("azureTenantId").value = data.azure_tenant_id;
    document.getElementById("azureClientId").value = data.azure_client_id;
    document.getElementById("azureClientSecret").value = "";
    document.getElementById("clearClientSecret").checked = false;
    document.getElementById("secretStatus").textContent = data.has_client_secret ? "SAVED" : "NOT SET";
    credentialMode.value = data.azure_credential_mode;
    syncCredentialFields();
    settingsFeedback.textContent = "";
  } catch (err) {
    settingsFeedback.textContent = `Could not load settings: ${err.message}`;
  }
});

document.getElementById("closeSettingsBtn").addEventListener("click", () => connectionDialog.close());
document.getElementById("cancelSettingsBtn").addEventListener("click", () => connectionDialog.close());

connectionForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = {
    foundry_project_endpoint: document.getElementById("foundryEndpoint").value.trim(),
    foundry_model: document.getElementById("foundryModel").value.trim(),
    azure_credential_mode: credentialMode.value,
    azure_tenant_id: document.getElementById("azureTenantId").value.trim(),
    azure_client_id: document.getElementById("azureClientId").value.trim(),
  };
  const secret = document.getElementById("azureClientSecret").value;
  if (secret) payload.azure_client_secret = secret;
  if (document.getElementById("clearClientSecret").checked) payload.clear_client_secret = true;

  settingsFeedback.textContent = "Saving settings…";
  try {
    const res = await fetch("/api/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const body = await res.json();
    if (!res.ok) throw new Error(body.detail || res.statusText);
    document.getElementById("azureClientSecret").value = "";
    document.getElementById("clearClientSecret").checked = false;
    document.getElementById("secretStatus").textContent = body.has_client_secret ? "SAVED" : "NOT SET";
    settingsFeedback.textContent = "Saved. New settings will be used for the next Azure request.";
  } catch (err) {
    settingsFeedback.textContent = `Could not save settings: ${err.message}`;
  }
});

function onFile(file) {
  if (!file?.type.startsWith("image/")) {
    setStatus("Please select an image file.", "error");
    return;
  }
  selectedFile = file;
  preview.src = URL.createObjectURL(file);
  preview.hidden = false;
  analyzeBtn.disabled = false;
  setStatus(`Ready: ${file.name}`, "ok");
}

browseBtn.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", (e) => onFile(e.target.files[0]));
dropZone.addEventListener("click", (e) => {
  if (e.target !== browseBtn) fileInput.click();
});
dropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropZone.classList.add("dragover");
});
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragover"));
dropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropZone.classList.remove("dragover");
  onFile(e.dataTransfer.files[0]);
});

analyzeBtn.addEventListener("click", async () => {
  if (!selectedFile) return;
  analyzeBtn.disabled = true;
  setStatus("Sending to Azure AI Foundry…", "loading");

  const form = new FormData();
  form.append("file", selectedFile);
  form.append("hints", hints.value);

  try {
    const res = await fetch("/api/analyze-floorplan", { method: "POST", body: form });
    const body = await res.json();
    if (!res.ok) throw new Error(body.detail || res.statusText);

    currentScene = body;
    viewer.loadScene(body);
    viewerEmpty?.remove();
    planBtn.disabled = false;

    const sqft = body.total_sqft ? `${body.total_sqft.toFixed(0)} sq ft` : "sq ft n/a";
    sceneMeta.textContent = `${body.rooms.length} rooms · ${body.walls.length} walls · ${sqft} · ${body.unit}`;
    setStatus("Floorplan analyzed — 3D scene ready.", "ok");
  } catch (err) {
    setStatus(err.message, "error");
  } finally {
    analyzeBtn.disabled = false;
  }
});

planBtn.addEventListener("click", async () => {
  if (!currentScene || !renoRequest.value.trim()) return;
  planBtn.disabled = true;
  planOutput.textContent = "Generating renovation plan…";

  const form = new FormData();
  form.append("request", renoRequest.value.trim());

  try {
    const res = await fetch("/api/plan-renovation", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scene: currentScene, request: renoRequest.value.trim() }),
    });
    const body = await res.json();
    if (!res.ok) throw new Error(body.detail || res.statusText);
    planOutput.textContent = body.plan;
  } catch (err) {
    planOutput.textContent = `Error: ${err.message}`;
  } finally {
    planBtn.disabled = false;
  }
});
