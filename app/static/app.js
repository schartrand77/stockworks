const state = {
  materials: [],
  inventory: [],
  hardware: [],
  currentMaterialId: null,
  currentInventoryId: null,
  currentMovementItemId: null,
  currentHardwareId: null,
  currentHardwareMovementId: null,
  orderworksJobs: [],
  orderworksError: null,
  orderworksConfigured: true,
  orderworksBaseUrl: "",
};

const messageEl = document.getElementById("message");
const refreshAllBtn = document.getElementById("refresh-all");
const tabButtons = Array.from(document.querySelectorAll(".tab-button"));
const tabPanels = Array.from(document.querySelectorAll(".tab-panel"));
const TAB_QUERY_PARAM = "tab";

// Material references
const materialForm = document.getElementById("material-form");
const materialIdInput = document.getElementById("material-id");
const materialFields = {
  name: document.getElementById("material-name"),
  filament_type: document.getElementById("material-type"),
  category: document.getElementById("material-category"),
  color: document.getElementById("material-color"),
  supplier: document.getElementById("material-supplier"),
  brand: document.getElementById("material-brand"),
  price_per_gram: document.getElementById("material-price"),
  spool_weight_grams: document.getElementById("material-spool"),
  barcode: document.getElementById("material-barcode"),
  notes: document.getElementById("material-notes"),
};
const materialTableBody = document.querySelector("#materials-table tbody");
const materialClearBtn = document.getElementById("material-clear");
const materialRefreshBtn = document.getElementById("material-refresh");
const materialDeleteBtn = document.getElementById("material-delete");

// Inventory references
const inventoryForm = document.getElementById("inventory-form");
const inventoryIdInput = document.getElementById("inventory-id");
const inventoryFields = {
  material_id: document.getElementById("inventory-material"),
  location: document.getElementById("inventory-location"),
  quantity_grams: document.getElementById("inventory-quantity"),
  reorder_level: document.getElementById("inventory-reorder"),
  spool_serial: document.getElementById("inventory-serial"),
  unit_cost_override: document.getElementById("inventory-cost"),
};
const inventoryTableBody = document.querySelector("#inventory-table tbody");
const inventoryClearBtn = document.getElementById("inventory-clear");
const inventoryRefreshBtn = document.getElementById("inventory-refresh");
const inventoryDeleteBtn = document.getElementById("inventory-delete");

// Hardware references
const hardwareForm = document.getElementById("hardware-form");
const hardwareIdInput = document.getElementById("hardware-id");
const hardwareFields = {
  name: document.getElementById("hardware-name"),
  category: document.getElementById("hardware-category"),
  supplier: document.getElementById("hardware-supplier"),
  manufacturer_part_number: document.getElementById("hardware-mpn"),
  unit_of_measure: document.getElementById("hardware-unit"),
  unit_cost: document.getElementById("hardware-unit-cost"),
  quantity_on_hand: document.getElementById("hardware-quantity"),
  reorder_level: document.getElementById("hardware-reorder"),
  bin_location: document.getElementById("hardware-bin"),
  notes: document.getElementById("hardware-notes"),
};
const hardwareTableBody = document.querySelector("#hardware-table tbody");
const hardwareClearBtn = document.getElementById("hardware-clear");
const hardwareRefreshBtn = document.getElementById("hardware-refresh");
const hardwareDeleteBtn = document.getElementById("hardware-delete");

// Movements
const movementForm = document.getElementById("movement-form");
const movementInventorySelect = document.getElementById("movement-inventory");
const movementTypeSelect = document.getElementById("movement-type");
const movementChangeInput = document.getElementById("movement-change");
const movementReferenceInput = document.getElementById("movement-reference");
const movementNoteInput = document.getElementById("movement-note");
const movementTableBody = document.querySelector("#movement-table tbody");

const hardwareMovementForm = document.getElementById("hardware-movement-form");
const hardwareMovementSelect = document.getElementById("hardware-movement-item");
const hardwareMovementType = document.getElementById("hardware-movement-type");
const hardwareMovementChange = document.getElementById("hardware-movement-change");
const hardwareMovementReference = document.getElementById("hardware-movement-reference");
const hardwareMovementNote = document.getElementById("hardware-movement-note");
const hardwareMovementTableBody = document.querySelector("#hardware-movement-table tbody");

const orderworksTableBody = document.querySelector("#orderworks-table tbody");
const orderworksRefreshBtn = document.getElementById("orderworks-refresh");
const orderworksStatusEl = document.getElementById("orderworks-status");
let themeToggleBtn = null;
let themeToggleLabelEl = null;

const THEME_STORAGE_KEY = "stockworks-theme";
const VALID_THEME_CHOICES = new Set(["light", "dark"]);
const prefersDarkScheme = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;
let forcedThemeChoice = loadStoredThemeChoice();
applyThemePreference(forcedThemeChoice);

if (prefersDarkScheme) {
  const mediaListener = () => {
    if (!forcedThemeChoice) {
      applyThemePreference(null);
    }
  };
  if (typeof prefersDarkScheme.addEventListener === "function") {
    prefersDarkScheme.addEventListener("change", mediaListener);
  } else if (typeof prefersDarkScheme.addListener === "function") {
    prefersDarkScheme.addListener(mediaListener);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  applyThemePreference(forcedThemeChoice);
  initThemeToggle();
  initTabs();
  bindEvents();
  refreshAll();
});

function bindEvents() {
  refreshAllBtn.addEventListener("click", refreshAll);
  materialRefreshBtn.addEventListener("click", () => safeAsync(loadMaterials));
  inventoryRefreshBtn.addEventListener("click", () => safeAsync(loadInventory));
  hardwareRefreshBtn.addEventListener("click", () => safeAsync(loadHardware));
  if (orderworksRefreshBtn) {
    orderworksRefreshBtn.addEventListener("click", () => safeAsync(loadOrderWorksJobs));
  }
  materialClearBtn.addEventListener("click", resetMaterialForm);
  inventoryClearBtn.addEventListener("click", resetInventoryForm);
  hardwareClearBtn.addEventListener("click", resetHardwareForm);
  materialDeleteBtn.addEventListener("click", () => {
    if (state.currentMaterialId) {
      deleteMaterial(state.currentMaterialId);
    } else {
      setMessage("Select a material first.", "error");
    }
  });
  inventoryDeleteBtn.addEventListener("click", () => {
    if (state.currentInventoryId) {
      deleteInventory(state.currentInventoryId);
    } else {
      setMessage("Select an inventory row first.", "error");
    }
  });
  hardwareDeleteBtn.addEventListener("click", () => {
    if (state.currentHardwareId) {
      deleteHardware(state.currentHardwareId);
    } else {
      setMessage("Select a hardware row first.", "error");
    }
  });

  materialForm.addEventListener("submit", handleMaterialSubmit);
  inventoryForm.addEventListener("submit", handleInventorySubmit);
  hardwareForm.addEventListener("submit", handleHardwareSubmit);
  materialTableBody.addEventListener("click", handleMaterialRowClick);
  inventoryTableBody.addEventListener("click", handleInventoryRowClick);
  hardwareTableBody.addEventListener("click", handleHardwareRowClick);
  movementInventorySelect.addEventListener("change", () => {
    const id = Number(movementInventorySelect.value);
    state.currentMovementItemId = Number.isFinite(id) ? id : null;
    if (state.currentMovementItemId) {
      safeAsync(() => loadMovements(state.currentMovementItemId));
    } else {
      renderMovements([]);
    }
  });
  movementForm.addEventListener("submit", handleMovementSubmit);
  hardwareMovementSelect.addEventListener("change", () => {
    const id = Number(hardwareMovementSelect.value);
    state.currentHardwareMovementId = Number.isFinite(id) ? id : null;
    if (state.currentHardwareMovementId) {
      safeAsync(() => loadHardwareMovements(state.currentHardwareMovementId));
    } else {
      renderHardwareMovements([]);
    }
  });
  hardwareMovementForm.addEventListener("submit", handleHardwareMovementSubmit);
}

async function refreshAll() {
  try {
    await Promise.all([
      loadMaterials(),
      loadInventory(),
      loadHardware(),
      loadOrderWorksJobs({ silent: true }).catch(() => null),
    ]);
    setMessage("Data refreshed.", "success");
  } catch (error) {
    console.error(error);
    setMessage(error.message, "error");
  }
}

async function loadMaterials() {
  const materials = await api("/materials");
  state.materials = materials;
  renderMaterials();
  populateMaterialOptions();
  if (state.currentMaterialId && !materials.some((m) => m.id === state.currentMaterialId)) {
    resetMaterialForm();
  }
}

async function loadInventory() {
  const inventory = await api("/inventory");
  state.inventory = inventory;
  renderInventory();
  populateInventoryOptions();
  if (state.currentInventoryId && !inventory.some((i) => i.id === state.currentInventoryId)) {
    resetInventoryForm();
  }
  if (state.currentMovementItemId) {
    const stillExists = inventory.some((i) => i.id === state.currentMovementItemId);
    if (stillExists) {
      await loadMovements(state.currentMovementItemId);
    } else {
      movementInventorySelect.value = "";
      state.currentMovementItemId = null;
      renderMovements([]);
    }
  }
}

async function loadHardware() {
  const hardware = await api("/hardware");
  state.hardware = hardware;
  renderHardware();
  populateHardwareOptions();
  if (state.currentHardwareId && !hardware.some((item) => item.id === state.currentHardwareId)) {
    resetHardwareForm();
  }
  if (state.currentHardwareMovementId) {
    const stillExists = hardware.some((item) => item.id === state.currentHardwareMovementId);
    if (stillExists) {
      await loadHardwareMovements(state.currentHardwareMovementId);
    } else {
      hardwareMovementSelect.value = "";
      state.currentHardwareMovementId = null;
      renderHardwareMovements([]);
    }
  }
}

async function loadOrderWorksJobs({ silent = false } = {}) {
  if (!orderworksTableBody) {
    return;
  }
  try {
    const payload = await api("/orderworks/jobs");
    state.orderworksJobs = Array.isArray(payload.jobs) ? payload.jobs : [];
    state.orderworksError = null;
    state.orderworksConfigured = true;
    state.orderworksBaseUrl = typeof payload.base_url === "string" ? payload.base_url : "";
  } catch (error) {
    console.error(error);
    state.orderworksJobs = [];
    state.orderworksBaseUrl = "";
    state.orderworksError = error && error.message ? error.message : "Unable to sync OrderWorks jobs.";
    state.orderworksConfigured = error && Number(error.status) === 503 ? false : true;
    if (!silent) {
      setMessage(state.orderworksError, "error");
    }
  }
  renderOrderWorks();
}

async function loadMovements(itemId) {
  const results = await api(`/inventory/${itemId}/movements`);
  renderMovements(results);
}

function renderMaterials() {
  if (!state.materials.length) {
    materialTableBody.innerHTML = `<tr><td colspan="10" class="muted">No materials yet.</td></tr>`;
    return;
  }
  materialTableBody.innerHTML = state.materials
    .map(
      (material) => `
        <tr data-id="${material.id}">
          <td>${escapeHtml(material.name)}</td>
          <td>${escapeHtml(material.brand || "")}</td>
          <td>${escapeHtml(material.filament_type)}</td>
          <td>${escapeHtml(material.category || "")}</td>
          <td>${escapeHtml(material.color)}</td>
          <td>$${material.price_per_gram.toFixed(2)}</td>
          <td>${material.spool_weight_grams}</td>
          <td>${escapeHtml(material.supplier || "")}</td>
          <td>${escapeHtml(material.barcode || "")}</td>
          <td>
            <button class="small-button" data-action="edit" data-id="${material.id}">Edit</button>
            <button class="small-button danger" data-action="delete" data-id="${material.id}">Delete</button>
          </td>
        </tr>`
    )
    .join("");
}

function renderInventory() {
  if (!state.inventory.length) {
    inventoryTableBody.innerHTML = `<tr><td colspan="7" class="muted">No inventory tracked yet.</td></tr>`;
    return;
  }
  inventoryTableBody.innerHTML = state.inventory
    .map((item) => {
      const materialLabel = item.material ? `${item.material.name} (${item.material.color})` : "Unknown";
      return `
        <tr data-id="${item.id}">
          <td>${escapeHtml(materialLabel)}</td>
          <td>${escapeHtml(item.location)}</td>
          <td>${Number(item.quantity_grams).toFixed(2)}</td>
          <td>${Number(item.reorder_level).toFixed(2)}</td>
          <td>${escapeHtml(item.spool_serial || "")}</td>
          <td>${item.unit_cost_override ? `$${Number(item.unit_cost_override).toFixed(2)}` : "-"}</td>
          <td>
            <button class="small-button" data-action="edit" data-id="${item.id}">Edit</button>
            <button class="small-button danger" data-action="delete" data-id="${item.id}">Delete</button>
          </td>
        </tr>`;
    })
    .join("");
}

function renderHardware() {
  if (!state.hardware.length) {
    hardwareTableBody.innerHTML = `<tr><td colspan="8" class="muted">No hardware recorded yet.</td></tr>`;
    return;
  }
  hardwareTableBody.innerHTML = state.hardware
    .map(
      (item) => `
        <tr data-id="${item.id}">
          <td>${escapeHtml(item.name)}</td>
          <td>${escapeHtml(item.category || "")}</td>
          <td>${escapeHtml(item.unit_of_measure)}</td>
          <td>${Number(item.quantity_on_hand).toFixed(2)}</td>
          <td>${Number(item.reorder_level).toFixed(2)}</td>
          <td>${item.unit_cost ? `$${Number(item.unit_cost).toFixed(2)}` : "-"}</td>
          <td>${escapeHtml(item.bin_location || "")}</td>
          <td>
            <button class="small-button" data-action="edit" data-id="${item.id}">Edit</button>
            <button class="small-button danger" data-action="delete" data-id="${item.id}">Delete</button>
          </td>
        </tr>`
    )
    .join("");
}

function renderOrderWorks() {
  if (!orderworksTableBody) {
    return;
  }
  if (orderworksStatusEl) {
    if (!state.orderworksConfigured) {
      orderworksStatusEl.textContent =
        "OrderWorks integration is not configured. Connect StockWorks to the MakerWorks database or provide ORDERWORKS_* credentials.";
      orderworksStatusEl.classList.remove("error");
      orderworksStatusEl.classList.add("muted");
    } else if (state.orderworksError) {
      orderworksStatusEl.textContent = state.orderworksError;
      orderworksStatusEl.classList.add("error");
      orderworksStatusEl.classList.remove("muted");
    } else {
      orderworksStatusEl.textContent = state.orderworksJobs.length
        ? `Showing ${state.orderworksJobs.length} job${state.orderworksJobs.length === 1 ? "" : "s"} from OrderWorks.`
        : "No jobs returned from OrderWorks.";
      orderworksStatusEl.classList.remove("error");
      orderworksStatusEl.classList.add("muted");
    }
  }
  if (!state.orderworksConfigured) {
    orderworksTableBody.innerHTML = `<tr><td colspan="7" class="muted">Configure OrderWorks credentials to sync jobs.</td></tr>`;
    return;
  }
  if (state.orderworksError) {
    orderworksTableBody.innerHTML = `<tr><td colspan="7" class="muted">${escapeHtml(state.orderworksError)}</td></tr>`;
    return;
  }
  if (!state.orderworksJobs.length) {
    orderworksTableBody.innerHTML = `<tr><td colspan="7" class="muted">No jobs available.</td></tr>`;
    return;
  }
  const orderworksBase = state.orderworksBaseUrl ? state.orderworksBaseUrl.replace(/\/+$/, "") : "";
  orderworksTableBody.innerHTML = state.orderworksJobs
    .map((job) => {
      const status = formatOrderStatus(job.status);
      const fulfillment = formatOrderStatus(job.fulfillmentStatus);
      const total = formatCurrencyValue(job.totalCents, job.currency);
      const createdAt = job.makerworksCreatedAt || job.createdAt;
      const createdLabel = formatTimestamp(createdAt);
      const lineItemsSummary = summarizeLineItems(job.lineItems);
      const jobLinkId = job.paymentIntentId || job.id;
      const jobLink =
        orderworksBase && jobLinkId ? `${orderworksBase}/jobs/${encodeURIComponent(jobLinkId)}` : null;
      const safeJobLink = jobLink ? escapeHtml(jobLink) : "";
      return `
        <tr>
          <td>${escapeHtml(job.id)}</td>
          <td>${escapeHtml(status)}</td>
          <td>${escapeHtml(fulfillment)}</td>
          <td>${escapeHtml(total)}</td>
          <td>${escapeHtml(createdLabel)}</td>
          <td>${escapeHtml(lineItemsSummary)}</td>
          <td>${
            jobLink
              ? `<a href="${safeJobLink}" target="_blank" rel="noreferrer noopener">Open</a>`
              : ""
          }</td>
        </tr>`;
    })
    .join("");
}

function renderMovements(movements) {
  if (!movements.length) {
    const text = state.currentMovementItemId
      ? "No movements recorded."
      : "Select an inventory item to view history.";
    movementTableBody.innerHTML = `<tr><td colspan="5" class="muted">${text}</td></tr>`;
    return;
  }
  movementTableBody.innerHTML = movements
    .map(
      (move) => `
        <tr>
          <td>${new Date(move.created_at).toLocaleString()}</td>
          <td>${escapeHtml(move.movement_type)}</td>
          <td>${Number(move.change_grams).toFixed(2)}</td>
          <td>${escapeHtml(move.reference || "")}</td>
          <td>${escapeHtml(move.note || "")}</td>
        </tr>`
    )
    .join("");
}

function populateMaterialOptions() {
  const options = state.materials
    .map((material) => `<option value="${material.id}">${escapeHtml(material.name)} (${escapeHtml(material.color)})</option>`)
    .join("");
  const select = document.getElementById("inventory-material");
  const currentValue = select.value;
  select.innerHTML = `<option value="">Select material...</option>${options}`;
  if (options && currentValue && state.materials.some((m) => String(m.id) === currentValue)) {
    select.value = currentValue;
  }
}

function populateInventoryOptions() {
  const options = state.inventory
    .map((item) => {
      const label = item.material ? `${item.material.name} – ${item.location}` : `Item ${item.id}`;
      return `<option value="${item.id}">${escapeHtml(label)}</option>`;
    })
    .join("");
  const currentValue = movementInventorySelect.value;
  movementInventorySelect.innerHTML = `<option value="">Select inventory item...</option>${options}`;
  if (options && currentValue && state.inventory.some((i) => String(i.id) === currentValue)) {
    movementInventorySelect.value = currentValue;
  }
}

function populateHardwareOptions() {
  const options = state.hardware
    .map((item) => {
      const label = item.bin_location ? `${item.name} – ${item.bin_location}` : item.name;
      return `<option value="${item.id}">${escapeHtml(label)}</option>`;
    })
    .join("");
  const currentValue = hardwareMovementSelect.value;
  hardwareMovementSelect.innerHTML = `<option value="">Select hardware item...</option>${options}`;
  if (options && currentValue && state.hardware.some((i) => String(i.id) === currentValue)) {
    hardwareMovementSelect.value = currentValue;
  }
}

async function handleMaterialSubmit(event) {
  event.preventDefault();
  try {
    const payload = buildMaterialPayload();
    if (!payload) return;
    if (state.currentMaterialId) {
      await api(`/materials/${state.currentMaterialId}`, { method: "PUT", body: payload });
    } else {
      await api("/materials", { method: "POST", body: payload });
    }
    await loadMaterials();
    setMessage("Material saved.", "success");
  } catch (error) {
    console.error(error);
    setMessage(error.message, "error");
  }
}

async function handleInventorySubmit(event) {
  event.preventDefault();
  try {
    const payload = buildInventoryPayload();
    if (!payload) return;
    if (state.currentInventoryId) {
      await api(`/inventory/${state.currentInventoryId}`, { method: "PUT", body: payload });
    } else {
      await api("/inventory", { method: "POST", body: payload });
    }
    await loadInventory();
    setMessage("Inventory saved.", "success");
  } catch (error) {
    console.error(error);
    setMessage(error.message, "error");
  }
}

async function handleHardwareSubmit(event) {
  event.preventDefault();
  try {
    const payload = buildHardwarePayload();
    if (!payload) return;
    if (state.currentHardwareId) {
      await api(`/hardware/${state.currentHardwareId}`, { method: "PUT", body: payload });
    } else {
      await api("/hardware", { method: "POST", body: payload });
    }
    await loadHardware();
    setMessage("Hardware saved.", "success");
  } catch (error) {
    console.error(error);
    setMessage(error.message, "error");
  }
}

async function handleMovementSubmit(event) {
  event.preventDefault();
  try {
    if (!movementInventorySelect.value) {
      setMessage("Select an inventory item first.", "error");
      return;
    }
    const baseChange = Number(movementChangeInput.value);
    if (!Number.isFinite(baseChange) || baseChange === 0) {
      setMessage("Change amount must be non-zero.", "error");
      return;
    }
    let changeValue = baseChange;
    if (movementTypeSelect.value === "incoming") {
      changeValue = Math.abs(baseChange);
    } else if (movementTypeSelect.value === "outgoing") {
      changeValue = -Math.abs(baseChange);
    }
    const payload = {
      inventory_item_id: Number(movementInventorySelect.value),
      movement_type: movementTypeSelect.value,
      change_grams: changeValue,
      reference: movementReferenceInput.value.trim() || null,
      note: movementNoteInput.value.trim() || null,
    };
    await api("/movements", { method: "POST", body: payload });
    movementChangeInput.value = "";
    movementReferenceInput.value = "";
    movementNoteInput.value = "";
    await loadInventory();
    if (state.currentMovementItemId) {
      await loadMovements(state.currentMovementItemId);
    }
    setMessage("Movement logged.", "success");
  } catch (error) {
    console.error(error);
    setMessage(error.message, "error");
  }
}

function handleMaterialRowClick(event) {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  const id = Number(button.dataset.id);
  if (button.dataset.action === "edit") {
    startMaterialEdit(id);
  } else if (button.dataset.action === "delete") {
    deleteMaterial(id);
  }
}

function handleInventoryRowClick(event) {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  const id = Number(button.dataset.id);
  if (button.dataset.action === "edit") {
    startInventoryEdit(id);
  } else if (button.dataset.action === "delete") {
    deleteInventory(id);
  }
}

function handleHardwareRowClick(event) {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  const id = Number(button.dataset.id);
  if (button.dataset.action === "edit") {
    startHardwareEdit(id);
  } else if (button.dataset.action === "delete") {
    deleteHardware(id);
  }
}

function startMaterialEdit(id) {
  const material = state.materials.find((m) => m.id === id);
  if (!material) return;
  state.currentMaterialId = id;
  materialIdInput.value = id;
  materialFields.name.value = material.name;
  materialFields.filament_type.value = material.filament_type;
  materialFields.category.value = material.category || "";
  materialFields.color.value = material.color;
  materialFields.supplier.value = material.supplier || "";
  materialFields.brand.value = material.brand || "";
  materialFields.price_per_gram.value = material.price_per_gram;
  materialFields.spool_weight_grams.value = material.spool_weight_grams;
  materialFields.barcode.value = material.barcode || "";
  materialFields.notes.value = material.notes || "";
}

function startInventoryEdit(id) {
  const item = state.inventory.find((i) => i.id === id);
  if (!item) return;
  state.currentInventoryId = id;
  inventoryIdInput.value = id;
  inventoryFields.material_id.value = item.material_id;
  inventoryFields.location.value = item.location;
  inventoryFields.quantity_grams.value = item.quantity_grams;
  inventoryFields.reorder_level.value = item.reorder_level;
  inventoryFields.spool_serial.value = item.spool_serial || "";
  inventoryFields.unit_cost_override.value = item.unit_cost_override ?? "";
  movementInventorySelect.value = String(id);
  state.currentMovementItemId = id;
  safeAsync(() => loadMovements(id));
}

function startHardwareEdit(id) {
  const item = state.hardware.find((hardware) => hardware.id === id);
  if (!item) return;
  state.currentHardwareId = id;
  hardwareIdInput.value = id;
  hardwareFields.name.value = item.name;
  hardwareFields.category.value = item.category || "";
  hardwareFields.supplier.value = item.supplier || "";
  hardwareFields.manufacturer_part_number.value = item.manufacturer_part_number || "";
  hardwareFields.unit_of_measure.value = item.unit_of_measure;
  hardwareFields.unit_cost.value = item.unit_cost ?? "";
  hardwareFields.quantity_on_hand.value = item.quantity_on_hand;
  hardwareFields.reorder_level.value = item.reorder_level;
  hardwareFields.bin_location.value = item.bin_location || "";
  hardwareFields.notes.value = item.notes || "";
  hardwareMovementSelect.value = String(id);
  state.currentHardwareMovementId = id;
  safeAsync(() => loadHardwareMovements(id));
}

async function deleteMaterial(id) {
  if (!confirm("Delete this material? Make sure related inventory entries are removed first.")) {
    return;
  }
  try {
    await api(`/materials/${id}`, { method: "DELETE" });
    if (state.currentMaterialId === id) {
      resetMaterialForm();
    }
    await Promise.all([loadMaterials(), loadInventory()]);
    setMessage("Material deleted.", "success");
  } catch (error) {
    console.error(error);
    setMessage(error.message, "error");
  }
}

async function deleteInventory(id) {
  if (!confirm("Delete this inventory entry and its movements?")) {
    return;
  }
  try {
    await api(`/inventory/${id}`, { method: "DELETE" });
    if (state.currentInventoryId === id) {
      resetInventoryForm();
    }
    await loadInventory();
    setMessage("Inventory deleted.", "success");
  } catch (error) {
    console.error(error);
    setMessage(error.message, "error");
  }
}

async function deleteHardware(id) {
  if (!confirm("Delete this hardware item and its movements?")) {
    return;
  }
  try {
    await api(`/hardware/${id}`, { method: "DELETE" });
    if (state.currentHardwareId === id) {
      resetHardwareForm();
    }
    await loadHardware();
    setMessage("Hardware deleted.", "success");
  } catch (error) {
    console.error(error);
    setMessage(error.message, "error");
  }
}

function buildMaterialPayload() {
  const requiredFields = ["name", "filament_type", "color"];
  if (requiredFields.some((key) => !materialFields[key].value.trim())) {
    setMessage("Fill in all required material fields.", "error");
    return null;
  }
  const price = Number(materialFields.price_per_gram.value);
  const spool = Number(materialFields.spool_weight_grams.value);
  if (!Number.isFinite(price) || price <= 0 || !Number.isFinite(spool) || spool <= 0) {
    setMessage("Price and spool weight must be positive numbers.", "error");
    return null;
  }
  return {
    name: materialFields.name.value.trim(),
    filament_type: materialFields.filament_type.value.trim(),
    category: optionalString(materialFields.category.value),
    color: materialFields.color.value.trim(),
    supplier: optionalString(materialFields.supplier.value),
    brand: optionalString(materialFields.brand.value),
    price_per_gram: price,
    spool_weight_grams: Math.round(spool),
    barcode: optionalString(materialFields.barcode.value),
    notes: optionalString(materialFields.notes.value),
  };
}

function optionalString(value) {
  const trimmed = (value || "").trim();
  return trimmed ? trimmed : null;
}

function buildInventoryPayload() {
  const materialValue = inventoryFields.material_id.value;
  if (!materialValue) {
    setMessage("Select a material for the inventory item.", "error");
    return null;
  }
  const materialId = Number(materialValue);
  const location = inventoryFields.location.value.trim();
  if (!location) {
    setMessage("Location is required.", "error");
    return null;
  }
  const quantity = Number(inventoryFields.quantity_grams.value);
  const reorder = Number(inventoryFields.reorder_level.value);
  if (!Number.isFinite(quantity) || quantity < 0 || !Number.isFinite(reorder) || reorder < 0) {
    setMessage("Quantity and reorder level must be positive numbers.", "error");
    return null;
  }
  const unitCostStr = inventoryFields.unit_cost_override.value;
  let unitCost = null;
  if (unitCostStr.trim() !== "") {
    unitCost = Number(unitCostStr);
    if (!Number.isFinite(unitCost) || unitCost < 0) {
      setMessage("Unit cost override must be a positive number.", "error");
      return null;
    }
  }
  return {
    material_id: materialId,
    location,
    quantity_grams: quantity,
    reorder_level: reorder,
    spool_serial: optionalString(inventoryFields.spool_serial.value),
    unit_cost_override: unitCost,
  };
}

function buildHardwarePayload() {
  const name = hardwareFields.name.value.trim();
  if (!name) {
    setMessage("Name is required for hardware.", "error");
    return null;
  }
  const quantity = Number(hardwareFields.quantity_on_hand.value || 0);
  const reorder = Number(hardwareFields.reorder_level.value || 0);
  if (!Number.isFinite(quantity) || quantity < 0 || !Number.isFinite(reorder) || reorder < 0) {
    setMessage("Quantities must be non-negative numbers.", "error");
    return null;
  }
  const unitCostStr = hardwareFields.unit_cost.value;
  let unitCost = null;
  if (unitCostStr.trim() !== "") {
    unitCost = Number(unitCostStr);
    if (!Number.isFinite(unitCost) || unitCost < 0) {
      setMessage("Unit cost must be a positive number.", "error");
      return null;
    }
  }
  return {
    name,
    category: optionalString(hardwareFields.category.value),
    supplier: optionalString(hardwareFields.supplier.value),
    manufacturer_part_number: optionalString(hardwareFields.manufacturer_part_number.value),
    unit_of_measure: hardwareFields.unit_of_measure.value.trim() || "piece",
    unit_cost: unitCost,
    quantity_on_hand: quantity,
    reorder_level: reorder,
    bin_location: optionalString(hardwareFields.bin_location.value),
    notes: optionalString(hardwareFields.notes.value),
  };
}

function resetMaterialForm() {
  materialForm.reset();
  materialIdInput.value = "";
  state.currentMaterialId = null;
}

function resetInventoryForm() {
  inventoryForm.reset();
  inventoryIdInput.value = "";
  state.currentInventoryId = null;
}

function resetHardwareForm() {
  hardwareForm.reset();
  hardwareIdInput.value = "";
  state.currentHardwareId = null;
}

async function loadHardwareMovements(itemId) {
  const movements = await api(`/hardware/${itemId}/movements`);
  renderHardwareMovements(movements);
}

function renderHardwareMovements(movements) {
  if (!movements.length) {
    const text = state.currentHardwareMovementId
      ? "No hardware movements recorded."
      : "Select a hardware item to view history.";
    hardwareMovementTableBody.innerHTML = `<tr><td colspan="5" class="muted">${text}</td></tr>`;
    return;
  }
  hardwareMovementTableBody.innerHTML = movements
    .map(
      (move) => `
        <tr>
          <td>${new Date(move.created_at).toLocaleString()}</td>
          <td>${escapeHtml(move.movement_type)}</td>
          <td>${Number(move.change_units).toFixed(2)}</td>
          <td>${escapeHtml(move.reference || "")}</td>
          <td>${escapeHtml(move.note || "")}</td>
        </tr>`
    )
    .join("");
}

async function handleHardwareMovementSubmit(event) {
  event.preventDefault();
  try {
    const itemId = Number(hardwareMovementSelect.value);
    if (!Number.isFinite(itemId)) {
      setMessage("Select a hardware item first.", "error");
      return;
    }
    let change = Number(hardwareMovementChange.value);
    if (!Number.isFinite(change) || change === 0) {
      setMessage("Change value must be non-zero.", "error");
      return;
    }
    if (hardwareMovementType.value === "incoming") {
      change = Math.abs(change);
    } else if (hardwareMovementType.value === "outgoing") {
      change = -Math.abs(change);
    }
    const payload = {
      hardware_item_id: itemId,
      movement_type: hardwareMovementType.value,
      change_units: change,
      reference: optionalString(hardwareMovementReference.value),
      note: optionalString(hardwareMovementNote.value),
    };
    await api("/hardware/movements", { method: "POST", body: payload });
    hardwareMovementChange.value = "";
    hardwareMovementReference.value = "";
    hardwareMovementNote.value = "";
    await loadHardware();
    await loadHardwareMovements(itemId);
    setMessage("Hardware movement logged.", "success");
  } catch (error) {
    console.error(error);
    setMessage(error.message, "error");
  }
}

function setMessage(text, variant = "info") {
  messageEl.textContent = text;
  messageEl.className = `message ${variant === "error" ? "error" : variant === "success" ? "success" : ""}`;
  if (!text) {
    setTimeout(() => (messageEl.textContent = ""), 2000);
  }
}

async function api(path, { method = "GET", body, headers } = {}) {
  const config = {
    method,
    headers: {
      ...(headers || {}),
    },
    credentials: "same-origin",
  };
  if (body !== undefined) {
    config.headers["Content-Type"] = "application/json";
    config.body = JSON.stringify(body);
  }
  const response = await fetch(path, config);
  if (response.status === 401) {
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }
  if (response.status === 204) {
    return null;
  }
  const raw = await response.text();
  if (!response.ok) {
    let message = raw || `Request failed (${response.status})`;
    try {
      const data = raw ? JSON.parse(raw) : null;
      if (data && typeof data.detail === "string") {
        message = data.detail;
      } else if (data) {
        message = JSON.stringify(data);
      }
    } catch {
      // ignore JSON parse errors and fall back to raw string
    }
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }
  if (!raw) {
    return null;
  }
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return JSON.parse(raw);
  }
  return raw;
}

function safeAsync(fn) {
  Promise.resolve()
    .then(() => fn())
    .catch((error) => {
      console.error(error);
      setMessage(error.message || "Unexpected error", "error");
    });
}

function escapeHtml(value) {
  if (value === null || value === undefined) return "";
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function formatOrderStatus(value) {
  if (!value) return "-";
  return String(value)
    .toLowerCase()
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatCurrencyValue(cents, currency) {
  if (!Number.isFinite(Number(cents))) {
    return "-";
  }
  const normalizedCurrency = typeof currency === "string" && currency.length >= 3 ? currency : "USD";
  const amount = Number(cents) / 100;
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency: normalizedCurrency.toUpperCase(),
    }).format(amount);
  } catch {
    return `$${amount.toFixed(2)}`;
  }
}

function summarizeLineItems(lineItems) {
  if (!Array.isArray(lineItems) || lineItems.length === 0) {
    return "-";
  }
  const parts = lineItems.slice(0, 3).map((item) => {
    if (!item || typeof item !== "object") {
      return "Line item";
    }
    const description = typeof item.description === "string" ? item.description.trim() : "";
    const material = typeof item.material === "string" ? item.material.trim() : "";
    const color = typeof item.color === "string" ? item.color.trim() : "";
    const details = [description || "Line item"];
    if (material) details.push(material);
    if (color) details.push(color);
    return details.join(" • ");
  });
  if (lineItems.length > 3) {
    parts.push(`+${lineItems.length - 3} more`);
  }
  return parts.join("; ");
}

function formatTimestamp(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "-";
  }
  return date.toLocaleString();
}

function sanitizeTabSlug(value) {
  if (value === null || value === undefined) {
    return "";
  }
  return String(value).trim().toLowerCase().replace(/[^a-z0-9-]/g, "");
}

function getPanelIdFromSlug(rawValue) {
  const slug = sanitizeTabSlug(rawValue);
  if (!slug) return null;
  const directPanel = document.getElementById(slug);
  if (directPanel) {
    return directPanel.id;
  }
  const candidate = slug.endsWith("-panel") ? slug : `${slug}-panel`;
  const candidatePanel = document.getElementById(candidate);
  return candidatePanel ? candidatePanel.id : null;
}

function getPanelIdFromQuery() {
  try {
    const currentUrl = new URL(window.location.href);
    return getPanelIdFromSlug(currentUrl.searchParams.get(TAB_QUERY_PARAM));
  } catch {
    return null;
  }
}

function syncTabQuery(panelId) {
  try {
    const currentUrl = new URL(window.location.href);
    if (panelId) {
      const slug = panelId.replace(/-panel$/i, "");
      currentUrl.searchParams.set(TAB_QUERY_PARAM, slug);
    } else {
      currentUrl.searchParams.delete(TAB_QUERY_PARAM);
    }
    window.history.replaceState({}, "", currentUrl);
  } catch {
    // Ignore history errors (e.g., unsupported browsers)
  }
}

function initTabs() {
  if (!tabButtons.length || !tabPanels.length) {
    return;
  }
  const requestedTab = getPanelIdFromQuery();
  const activeButton = document.querySelector(".tab-button.active") || tabButtons[0];
  const fallbackId =
    (activeButton && activeButton.dataset && activeButton.dataset.tabTarget) || (tabPanels[0] && tabPanels[0].id);
  const targetId = requestedTab || fallbackId;
  if (targetId) {
    setActiveTab(targetId);
  }
  tabButtons.forEach((button) => {
    button.addEventListener("click", () => {
      if (button.dataset.tabTarget) {
        setActiveTab(button.dataset.tabTarget);
      }
    });
  });
}

function setActiveTab(targetId, options = {}) {
  if (!targetId) return;
  const targetPanel = document.getElementById(targetId);
  if (!targetPanel) return;
  tabButtons.forEach((button) => {
    const isActive = button.dataset.tabTarget === targetId;
    button.classList.toggle("active", isActive);
    button.setAttribute("aria-selected", isActive ? "true" : "false");
  });
  tabPanels.forEach((panel) => {
    const isActive = panel.id === targetId;
    panel.classList.toggle("active", isActive);
    panel.hidden = !isActive;
  });
  if (!options.skipUrlSync) {
    syncTabQuery(targetId);
  }
}

function initThemeToggle() {
  themeToggleBtn = document.getElementById("theme-toggle");
  if (!themeToggleBtn) {
    return;
  }
  themeToggleLabelEl = themeToggleBtn.querySelector("[data-theme-toggle-label]");
  updateThemeToggleUi(getCurrentTheme());
  themeToggleBtn.addEventListener("click", () => {
    const current = getCurrentTheme();
    const nextTheme = current === "dark" ? "light" : "dark";
    forcedThemeChoice = nextTheme;
    persistThemeChoice(nextTheme);
    applyThemePreference(nextTheme);
  });
}

function getSystemTheme() {
  if (prefersDarkScheme && prefersDarkScheme.matches) {
    return "dark";
  }
  return "light";
}

function getCurrentTheme() {
  const applied = getAppliedTheme();
  if (applied) {
    return applied;
  }
  if (forcedThemeChoice) {
    return forcedThemeChoice;
  }
  return getSystemTheme();
}

function getAppliedTheme() {
  const rootTheme = document.documentElement.getAttribute("data-theme");
  if (rootTheme === "light" || rootTheme === "dark") {
    return rootTheme;
  }
  return null;
}

function loadStoredThemeChoice() {
  try {
    const stored = localStorage.getItem(THEME_STORAGE_KEY);
    if (stored && VALID_THEME_CHOICES.has(stored)) {
      return stored;
    }
  } catch {
    // Ignore storage access issues
  }
  return null;
}

function persistThemeChoice(value) {
  try {
    if (value && VALID_THEME_CHOICES.has(value)) {
      localStorage.setItem(THEME_STORAGE_KEY, value);
    } else {
      localStorage.removeItem(THEME_STORAGE_KEY);
    }
  } catch {
    // Ignore storage access issues
  }
}

function applyThemePreference(theme) {
  const root = document.documentElement;
  let activeTheme = theme;
  if (theme === "light" || theme === "dark") {
    root.setAttribute("data-theme", theme);
  } else {
    root.removeAttribute("data-theme");
    activeTheme = getSystemTheme();
  }
  if (activeTheme !== "light" && activeTheme !== "dark") {
    activeTheme = "light";
  }
  root.setAttribute("data-active-theme", activeTheme);
  if (document.body) {
    document.body.setAttribute("data-active-theme", activeTheme);
  }
  updateThemeToggleUi(activeTheme);
}

function updateThemeToggleUi(activeTheme = getCurrentTheme()) {
  if (!themeToggleBtn) {
    return;
  }
  const isDark = activeTheme === "dark";
  themeToggleBtn.setAttribute("aria-pressed", isDark ? "true" : "false");
  const label = isDark ? "Switch to light theme" : "Switch to dark theme";
  themeToggleBtn.setAttribute("aria-label", label);
  themeToggleBtn.setAttribute("title", label);
  if (themeToggleLabelEl) {
    themeToggleLabelEl.textContent = label;
  }
}
