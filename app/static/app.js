const state = {
  materials: [],
  inventory: [],
  hardware: [],
  models: [],
  currentMaterialId: null,
  currentInventoryId: null,
  currentMovementItemId: null,
  currentHardwareId: null,
  currentHardwareMovementId: null,
  currentModelId: null,
  currentModelSaleId: null,
  orderworksJobs: [],
  orderworksError: null,
  orderworksConfigured: true,
  orderworksBaseUrl: "",
  lastInventoryMovements: [],
  lastHardwareMovements: [],
  lastModelSales: [],
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
  color_hex: document.getElementById("material-color-hex"),
  supplier: document.getElementById("material-supplier"),
  brand: document.getElementById("material-brand"),
  price_per_gram: document.getElementById("material-price"),
  spool_weight_grams: document.getElementById("material-spool"),
  barcode: document.getElementById("material-barcode"),
  notes: document.getElementById("material-notes"),
};
const materialColorDot = document.getElementById("material-color-dot");
const materialColorPicker = document.getElementById("material-color-picker");
const materialTableBody = document.querySelector("#materials-table tbody");
const materialSearchInput = document.getElementById("materials-search");
const materialBrandFilter = document.getElementById("materials-brand-filter");
const materialTypeFilter = document.getElementById("materials-type-filter");
const materialCategoryFilter = document.getElementById("materials-category-filter");
const materialColorFilter = document.getElementById("materials-color-filter");
const materialClearBtn = document.getElementById("material-clear");
const materialRefreshBtn = document.getElementById("material-refresh");
const materialDeleteBtn = document.getElementById("material-delete");
const materialBarcodeScanBtn = document.getElementById("material-barcode-scan");
const filamentTypeDatalist = document.getElementById("filament-type-list");

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
const inventoryGrid = document.getElementById("inventory-grid");
const inventorySearchInput = document.getElementById("inventory-search");
const inventoryMaterialFilter = document.getElementById("inventory-material-filter");
const inventoryColorFilter = document.getElementById("inventory-color-filter");
const inventoryLocationFilter = document.getElementById("inventory-location-filter");
const inventoryClearBtn = document.getElementById("inventory-clear");
const inventoryRefreshBtn = document.getElementById("inventory-refresh");
const inventoryDeleteBtn = document.getElementById("inventory-delete");
const inventoryMaterialScanBtn = document.getElementById("inventory-material-scan");

// Pagination references
const materialsPrevBtn = document.getElementById("materials-prev");
const materialsNextBtn = document.getElementById("materials-next");
const materialsPageEl = document.getElementById("materials-page");
const materialsInfoEl = document.getElementById("materials-pagination-info");
const inventoryPrevBtn = document.getElementById("inventory-prev");
const inventoryNextBtn = document.getElementById("inventory-next");
const inventoryPageEl = document.getElementById("inventory-page");
const inventoryInfoEl = document.getElementById("inventory-pagination-info");
const modelsPrevBtn = document.getElementById("models-prev");
const modelsNextBtn = document.getElementById("models-next");
const modelsPageEl = document.getElementById("models-page");
const modelsInfoEl = document.getElementById("models-pagination-info");
const hardwarePrevBtn = document.getElementById("hardware-prev");
const hardwareNextBtn = document.getElementById("hardware-next");
const hardwarePageEl = document.getElementById("hardware-page");
const hardwareInfoEl = document.getElementById("hardware-pagination-info");

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
const hardwareSearchInput = document.getElementById("hardware-search");
const hardwareFilterSelect = document.getElementById("hardware-filter");
const hardwareClearBtn = document.getElementById("hardware-clear");
const hardwareRefreshBtn = document.getElementById("hardware-refresh");
const hardwareDeleteBtn = document.getElementById("hardware-delete");

// Model references
const modelForm = document.getElementById("model-form");
const modelIdInput = document.getElementById("model-id");
const modelFields = {
  name: document.getElementById("model-name"),
  category: document.getElementById("model-category"),
  sku: document.getElementById("model-sku"),
  designer: document.getElementById("model-designer"),
  platform: document.getElementById("model-platform"),
  file_location: document.getElementById("model-file"),
  version: document.getElementById("model-version"),
  unit_price: document.getElementById("model-price"),
  active: document.getElementById("model-active"),
  notes: document.getElementById("model-notes"),
};
const modelsTableBody = document.querySelector("#models-table tbody");
const modelsSearchInput = document.getElementById("models-search");
const modelsFilterSelect = document.getElementById("models-filter");
const modelsClearBtn = document.getElementById("models-clear");
const modelsRefreshBtn = document.getElementById("models-refresh");
const modelDeleteBtn = document.getElementById("model-delete");

const modelSaleForm = document.getElementById("model-sale-form");
const modelSaleSelect = document.getElementById("model-sale-model");
const modelSaleQuantity = document.getElementById("model-sale-quantity");
const modelSalePrice = document.getElementById("model-sale-price");
const modelSaleCurrency = document.getElementById("model-sale-currency");
const modelSaleChannel = document.getElementById("model-sale-channel");
const modelSaleReference = document.getElementById("model-sale-reference");
const modelSaleNote = document.getElementById("model-sale-note");
const modelSaleTableBody = document.querySelector("#model-sale-table tbody");

// Movements
const movementForm = document.getElementById("movement-form");
const movementInventorySelect = document.getElementById("movement-inventory");
const movementTypeSelect = document.getElementById("movement-type");
const movementChangeInput = document.getElementById("movement-change");
const movementReferenceInput = document.getElementById("movement-reference");
const movementNoteInput = document.getElementById("movement-note");
const movementTableBody = document.querySelector("#movement-table tbody");
const movementSearchInput = document.getElementById("movements-search");
const movementFilterSelect = document.getElementById("movements-filter");

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
const reportsRefreshBtn = document.getElementById("reports-refresh");
const reportMetricsEl = document.getElementById("report-metrics");
const reportInventoryChartEl = document.getElementById("report-inventory-chart");
const reportModelsChartEl = document.getElementById("report-models-chart");
const reportLowStockEl = document.getElementById("report-low-stock");
const reportHardwareChartEl = document.getElementById("report-hardware-chart");
const reportUsageEl = document.getElementById("report-usage");
const reportOrderworksMetricsEl = document.getElementById("report-orderworks-metrics");
const reportOrderworksStatusEl = document.getElementById("report-orderworks-status");
const reportOrderworksRevenueEl = document.getElementById("report-orderworks-revenue");
const installButton = document.getElementById("install-app");
let themeToggleBtn = null;
let themeToggleLabelEl = null;
const toastContainer = document.getElementById("toast-container");

const scannerOverlay = document.getElementById("barcode-scanner");
const scannerVideo = document.getElementById("scanner-video");
const scannerCloseBtn = document.getElementById("scanner-close");
const scannerTitleEl = document.getElementById("scanner-title");
const scannerStatusEl = document.getElementById("scanner-status");

const paginationState = {
  materials: { page: 1, perPage: 10 },
  inventory: { page: 1, perPage: 10 },
  models: { page: 1, perPage: 10 },
  hardware: { page: 1, perPage: 10 },
};

const filterState = {
  materials: { search: "", brand: "all", type: "all", category: "all", color: "all" },
  inventory: { search: "", material: "all", color: "all", location: "all" },
  models: { search: "", mode: "all" },
  hardware: { search: "", mode: "all" },
  movements: { search: "", mode: "all" },
};

const DEFAULT_BARCODE_FORMATS = [
  "code_128",
  "code_39",
  "code_93",
  "ean_13",
  "ean_8",
  "upc_a",
  "upc_e",
  "itf",
  "qr_code",
];

const scannerState = {
  active: false,
  detector: null,
  stream: null,
  rafId: null,
  onDetected: null,
};

const THEME_STORAGE_KEY = "stockworks-theme";
const VALID_THEME_CHOICES = new Set(["light", "dark"]);
const prefersDarkScheme = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;
let forcedThemeChoice = loadStoredThemeChoice();
let deferredInstallPrompt = null;
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
  updateMaterialColorRequirement();
  syncMaterialColorInputs({ source: "text" });
  safeAsync(loadFilamentTypes);
  registerServiceWorker();
  refreshAll();
});

window.addEventListener("beforeinstallprompt", (event) => {
  event.preventDefault();
  deferredInstallPrompt = event;
  toggleInstallButton(true);
});

window.addEventListener("appinstalled", () => {
  deferredInstallPrompt = null;
  toggleInstallButton(false);
  setMessage("StockWorks installed.", "success");
});

function normalizeHexValue(value) {
  if (!value) return "";
  let hex = String(value).trim();
  if (hex.toLowerCase().startsWith("0x")) {
    hex = hex.slice(2);
  }
  if (hex.startsWith("#")) {
    hex = hex.slice(1);
  }
  if (hex.length === 3) {
    hex = hex
      .split("")
      .map((char) => char + char)
      .join("");
  }
  if (!/^[0-9a-fA-F]{6}$/.test(hex)) {
    return "";
  }
  return `#${hex.toUpperCase()}`;
}

function resolveSwatchColor(colorName, colorHex) {
  const normalizedHex = normalizeHexValue(colorHex);
  if (normalizedHex) {
    return normalizedHex;
  }
  const nameHex = normalizeHexValue(colorName);
  if (nameHex) {
    return nameHex;
  }
  if (colorName && typeof CSS !== "undefined" && typeof CSS.supports === "function") {
    const trimmed = String(colorName).trim();
    if (trimmed && CSS.supports("color", trimmed)) {
      return trimmed;
    }
  }
  return "";
}

function updateMaterialColorRequirement() {
  if (!materialFields.color_hex) return;
  materialFields.color_hex.required = true;
  materialFields.color_hex.placeholder = "#1A1A1A";
}

function updateMaterialColorPreview(nextHex) {
  if (!materialColorDot) return;
  const hexValue = normalizeHexValue(nextHex);
  materialColorDot.style.setProperty("--swatch-color", hexValue || "transparent");
}

function syncMaterialColorInputs({ source } = {}) {
  if (!materialFields.color_hex || !materialColorPicker) return;
  if (source === "picker") {
    materialFields.color_hex.value = materialColorPicker.value.toUpperCase();
  } else if (source === "text") {
    const normalized = normalizeHexValue(materialFields.color_hex.value);
    if (normalized) {
      materialColorPicker.value = normalized;
    }
  }
  updateMaterialColorPreview(materialFields.color_hex.value);
}

function bindEvents() {
  refreshAllBtn.addEventListener("click", refreshAll);
  materialRefreshBtn.addEventListener("click", () => safeAsync(loadMaterials));
  inventoryRefreshBtn.addEventListener("click", () => safeAsync(loadInventory));
  if (modelsRefreshBtn) {
    modelsRefreshBtn.addEventListener("click", () => safeAsync(loadModels));
  }
  hardwareRefreshBtn.addEventListener("click", () => safeAsync(loadHardware));
  if (orderworksRefreshBtn) {
    orderworksRefreshBtn.addEventListener("click", () => safeAsync(loadOrderWorksJobs));
  }
  if (reportsRefreshBtn) {
    reportsRefreshBtn.addEventListener("click", () => safeAsync(refreshReports));
  }
  materialClearBtn.addEventListener("click", resetMaterialForm);
  inventoryClearBtn.addEventListener("click", resetInventoryForm);
  if (modelsClearBtn) {
    modelsClearBtn.addEventListener("click", resetModelForm);
  }
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
  if (modelDeleteBtn) {
    modelDeleteBtn.addEventListener("click", () => {
      if (state.currentModelId) {
        deleteModel(state.currentModelId);
      } else {
        setMessage("Select a model row first.", "error");
      }
    });
  }

  materialForm.addEventListener("submit", handleMaterialSubmit);
  inventoryForm.addEventListener("submit", handleInventorySubmit);
  hardwareForm.addEventListener("submit", handleHardwareSubmit);
  if (modelForm) {
    modelForm.addEventListener("submit", handleModelSubmit);
  }
  if (materialFields.color_hex) {
    materialFields.color_hex.addEventListener("input", () => syncMaterialColorInputs({ source: "text" }));
  }
  if (materialColorPicker) {
    materialColorPicker.addEventListener("input", () => syncMaterialColorInputs({ source: "picker" }));
  }
  materialTableBody.addEventListener("click", handleMaterialRowClick);
  inventoryGrid.addEventListener("click", handleInventoryRowClick);
  hardwareTableBody.addEventListener("click", handleHardwareRowClick);
  if (modelsTableBody) {
    modelsTableBody.addEventListener("click", handleModelRowClick);
  }
  if (materialSearchInput) {
    materialSearchInput.addEventListener("input", () => {
      filterState.materials.search = normalizeSearchTerm(materialSearchInput.value);
      paginationState.materials.page = 1;
      renderMaterials();
    });
  }
  if (materialBrandFilter) {
    materialBrandFilter.addEventListener("change", () => {
      filterState.materials.brand = normalizeSearchTerm(materialBrandFilter.value) || "all";
      paginationState.materials.page = 1;
      renderMaterials();
    });
  }
  if (materialTypeFilter) {
    materialTypeFilter.addEventListener("change", () => {
      filterState.materials.type = normalizeSearchTerm(materialTypeFilter.value) || "all";
      paginationState.materials.page = 1;
      renderMaterials();
    });
  }
  if (materialCategoryFilter) {
    materialCategoryFilter.addEventListener("change", () => {
      filterState.materials.category = normalizeSearchTerm(materialCategoryFilter.value) || "all";
      paginationState.materials.page = 1;
      renderMaterials();
    });
  }
  if (materialColorFilter) {
    materialColorFilter.addEventListener("change", () => {
      filterState.materials.color = normalizeSearchTerm(materialColorFilter.value) || "all";
      paginationState.materials.page = 1;
      renderMaterials();
    });
  }
  if (inventorySearchInput) {
    inventorySearchInput.addEventListener("input", () => {
      filterState.inventory.search = normalizeSearchTerm(inventorySearchInput.value);
      paginationState.inventory.page = 1;
      renderInventory();
    });
  }
  if (inventoryMaterialFilter) {
    inventoryMaterialFilter.addEventListener("change", () => {
      filterState.inventory.material = normalizeSearchTerm(inventoryMaterialFilter.value) || "all";
      paginationState.inventory.page = 1;
      renderInventory();
    });
  }
  if (inventoryColorFilter) {
    inventoryColorFilter.addEventListener("change", () => {
      filterState.inventory.color = normalizeSearchTerm(inventoryColorFilter.value) || "all";
      paginationState.inventory.page = 1;
      renderInventory();
    });
  }
  if (inventoryLocationFilter) {
    inventoryLocationFilter.addEventListener("change", () => {
      filterState.inventory.location = normalizeSearchTerm(inventoryLocationFilter.value) || "all";
      paginationState.inventory.page = 1;
      renderInventory();
    });
  }
  if (modelsSearchInput) {
    modelsSearchInput.addEventListener("input", () => {
      filterState.models.search = normalizeSearchTerm(modelsSearchInput.value);
      paginationState.models.page = 1;
      renderModels();
    });
  }
  if (modelsFilterSelect) {
    modelsFilterSelect.addEventListener("change", () => {
      filterState.models.mode = modelsFilterSelect.value || "all";
      paginationState.models.page = 1;
      renderModels();
    });
  }
  if (hardwareSearchInput) {
    hardwareSearchInput.addEventListener("input", () => {
      filterState.hardware.search = normalizeSearchTerm(hardwareSearchInput.value);
      paginationState.hardware.page = 1;
      renderHardware();
    });
  }
  if (hardwareFilterSelect) {
    hardwareFilterSelect.addEventListener("change", () => {
      filterState.hardware.mode = hardwareFilterSelect.value || "all";
      paginationState.hardware.page = 1;
      renderHardware();
    });
  }
  if (movementSearchInput) {
    movementSearchInput.addEventListener("input", () => {
      filterState.movements.search = normalizeSearchTerm(movementSearchInput.value);
      renderMovements(state.lastInventoryMovements);
    });
  }
  if (movementFilterSelect) {
    movementFilterSelect.addEventListener("change", () => {
      filterState.movements.mode = movementFilterSelect.value || "all";
      renderMovements(state.lastInventoryMovements);
    });
  }
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
  if (modelSaleSelect) {
    modelSaleSelect.addEventListener("change", () => {
      const id = Number(modelSaleSelect.value);
      state.currentModelSaleId = Number.isFinite(id) ? id : null;
      if (state.currentModelSaleId) {
        const selected = state.models.find((model) => model.id === state.currentModelSaleId);
        if (selected && modelSalePrice && !modelSalePrice.value) {
          modelSalePrice.value = selected.unit_price ?? "";
        }
        safeAsync(() => loadModelSales(state.currentModelSaleId));
      } else {
        renderModelSales([]);
      }
    });
  }
  if (modelSaleForm) {
    modelSaleForm.addEventListener("submit", handleModelSaleSubmit);
  }
  if (installButton) {
    installButton.addEventListener("click", handleInstallButtonClick);
  }
  if (materialBarcodeScanBtn) {
    materialBarcodeScanBtn.addEventListener("click", () => {
      openBarcodeScanner({
        title: "Scan material barcode",
        onDetected: (value) => {
          materialFields.barcode.value = value;
          setMessage(`Scanned barcode: ${value}`, "success");
        },
      });
    });
  }
  if (inventoryMaterialScanBtn) {
    inventoryMaterialScanBtn.addEventListener("click", () => {
      openBarcodeScanner({
        title: "Scan material barcode",
        onDetected: async (value) => {
          if (!state.inventory.length) {
            await loadInventory();
          }
          if (!state.materials.length) {
            await loadMaterials();
          }
          const inventoryMatches = findInventoryByBarcode(value);
          if (inventoryMatches.length) {
            const match = inventoryMatches[0];
            startInventoryEdit(match.id);
            highlightInventoryRow(match.id);
            const hexLabel = normalizeHexValue(match.material?.color_hex);
            const materialLabel = match.material
              ? `${match.material.name} (${match.material.color}${hexLabel ? ` • ${hexLabel}` : ""})`
              : `Item ${match.id}`;
            const extra = inventoryMatches.length > 1 ? " Multiple matches found; showing the first." : "";
            setMessage(`Loaded inventory for ${materialLabel}.${extra}`, "success");
            return;
          }
          const material = findMaterialByBarcode(value);
          if (!material) {
            setMessage(`No inventory or material found for barcode ${value}.`, "error");
            return;
          }
          inventoryFields.material_id.value = String(material.id);
          const hexLabel = normalizeHexValue(material.color_hex);
          const materialLabel = `${material.name} (${material.color}${hexLabel ? ` • ${hexLabel}` : ""})`;
          setMessage(`Material found for ${materialLabel}. No inventory entry yet.`, "info");
        },
      });
    });
  }
  if (scannerCloseBtn) {
    scannerCloseBtn.addEventListener("click", () => closeBarcodeScanner());
  }
  if (scannerOverlay) {
    scannerOverlay.addEventListener("click", (event) => {
      if (event.target === scannerOverlay) {
        closeBarcodeScanner();
      }
    });
  }

  if (materialsPrevBtn && materialsNextBtn) {
    materialsPrevBtn.addEventListener("click", () => changePage("materials", -1));
    materialsNextBtn.addEventListener("click", () => changePage("materials", 1));
  }
  if (inventoryPrevBtn && inventoryNextBtn) {
    inventoryPrevBtn.addEventListener("click", () => changePage("inventory", -1));
    inventoryNextBtn.addEventListener("click", () => changePage("inventory", 1));
  }
  if (hardwarePrevBtn && hardwareNextBtn) {
    hardwarePrevBtn.addEventListener("click", () => changePage("hardware", -1));
    hardwareNextBtn.addEventListener("click", () => changePage("hardware", 1));
  }
  if (modelsPrevBtn && modelsNextBtn) {
    modelsPrevBtn.addEventListener("click", () => changePage("models", -1));
    modelsNextBtn.addEventListener("click", () => changePage("models", 1));
  }
}

function registerServiceWorker() {
  if (!("serviceWorker" in navigator)) {
    return;
  }

  if (!window.isSecureContext) {
    console.warn("Service workers and PWA install prompts require HTTPS (or localhost).");
    return;
  }

  navigator.serviceWorker
    .register("/sw.js")
    .then((registration) => {
      console.info("Service worker registered:", registration.scope);
    })
    .catch((error) => {
      console.error("Service worker registration failed:", error);
    });
}

function toggleInstallButton(visible) {
  if (!installButton) {
    return;
  }
  installButton.hidden = !visible;
}

async function handleInstallButtonClick() {
  if (!deferredInstallPrompt) {
    setMessage("Install prompt not available yet.", "error");
    return;
  }

  toggleInstallButton(false);
  deferredInstallPrompt.prompt();
  try {
    const choice = await deferredInstallPrompt.userChoice;
    if (choice.outcome === "accepted") {
      setMessage("Installation started. Look for StockWorks on your home screen.", "success");
    } else {
      setMessage("Install cancelled. You can install later from the browser menu.", "info");
    }
  } catch (error) {
    console.error("Install prompt failed:", error);
    setMessage("Unable to trigger install prompt.", "error");
  } finally {
    deferredInstallPrompt = null;
  }
}

async function refreshAll() {
  try {
    await Promise.all([
      loadMaterials(),
      loadInventory(),
      loadModels(),
      loadHardware(),
      loadOrderWorksJobs({ silent: true }).catch(() => null),
    ]);
    setMessage("Data refreshed.", "success");
  } catch (error) {
    console.error(error);
    setMessage(error.message, "error");
  }
}

async function refreshReports() {
  await Promise.all([
    loadMaterials(),
    loadInventory(),
    loadModels(),
    loadHardware(),
    loadOrderWorksJobs({ silent: true }).catch(() => null),
  ]);
  renderReports();
  setMessage("Reports updated.", "success");
}

async function loadMaterials() {
  const materials = await api("/materials");
  state.materials = materials;
  populateMaterialFilters();
  renderMaterials();
  populateMaterialOptions();
  if (state.currentMaterialId && !materials.some((m) => m.id === state.currentMaterialId)) {
    resetMaterialForm();
  }
  renderReports();
}

async function loadFilamentTypes() {
  if (!filamentTypeDatalist) {
    return;
  }
  try {
    const payload = await api("/filament-types/bambu-x1c");
    const types = Array.isArray(payload?.filament_types) ? payload.filament_types : [];
    filamentTypeDatalist.innerHTML = types.map((item) => `<option value="${escapeHtml(item)}"></option>`).join("");
  } catch (error) {
    console.warn("Unable to load Bambu filament types.", error);
  }
}

async function loadInventory() {
  const inventory = await api("/inventory");
  state.inventory = inventory;
  populateInventoryFilters();
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
  renderReports();
}

async function loadModels() {
  const models = await api("/models");
  state.models = models;
  renderModels();
  populateModelOptions();
  if (state.currentModelId && !models.some((model) => model.id === state.currentModelId)) {
    resetModelForm();
  }
  if (state.currentModelSaleId) {
    const stillExists = models.some((model) => model.id === state.currentModelSaleId);
    if (stillExists) {
      await loadModelSales(state.currentModelSaleId);
    } else if (modelSaleSelect) {
      modelSaleSelect.value = "";
      state.currentModelSaleId = null;
      renderModelSales([]);
    }
  }
  renderReports();
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
  renderReports();
}

async function loadOrderWorksJobs({ silent = false } = {}) {
  const shouldFetch =
    orderworksTableBody || reportOrderworksMetricsEl || reportOrderworksStatusEl || reportOrderworksRevenueEl;
  if (!shouldFetch) {
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
  if (orderworksTableBody) {
    renderOrderWorks();
  }
  renderReports();
}

async function loadMovements(itemId) {
  const results = await api(`/inventory/${itemId}/movements`);
  state.lastInventoryMovements = Array.isArray(results) ? results : [];
  renderMovements(results);
  renderReports();
}

function formatColorChip(colorName, colorHex) {
  const hex = normalizeHexValue(colorHex);
  const swatchColor = resolveSwatchColor(colorName, colorHex);
  const nameLabel = colorName ? escapeHtml(colorName) : `<span class="muted">Unknown</span>`;
  const hexLabel = hex ? `<span class="color-hex">${hex}</span>` : `<span class="color-hex muted">No hex</span>`;
  const dot = `<span class="color-dot" style="--swatch-color: ${swatchColor || "transparent"}" aria-hidden="true"></span>`;
  return `<span class="color-chip">${dot}<span>${nameLabel}</span>${hexLabel}</span>`;
}

function formatMaterialLabel(material) {
  if (!material) return "Unknown";
  const name = escapeHtml(material.name);
  const colorChip = formatColorChip(material.color, material.color_hex);
  return `<span>${name}</span> ${colorChip}`;
}

function normalizeSearchTerm(value) {
  return String(value || "").trim().toLowerCase();
}

function matchesSearch(needle, values) {
  if (!needle) return true;
  return values.some((value) => String(value || "").toLowerCase().includes(needle));
}

function filterMaterials(items) {
  const search = filterState.materials.search;
  const brand = filterState.materials.brand;
  const type = filterState.materials.type;
  const category = filterState.materials.category;
  const color = filterState.materials.color;
  let filtered = items;
  if (search) {
    filtered = filtered.filter((material) =>
      matchesSearch(search, [
        material.name,
        material.brand,
        material.filament_type,
        material.category,
        material.color,
        material.color_hex,
        material.supplier,
        material.barcode,
        material.notes,
      ])
    );
  }
  if (brand !== "all") {
    filtered = filtered.filter((material) => normalizeSearchTerm(material.brand) === brand);
  }
  if (type !== "all") {
    filtered = filtered.filter((material) => normalizeSearchTerm(material.filament_type) === type);
  }
  if (category !== "all") {
    filtered = filtered.filter((material) => normalizeSearchTerm(material.category) === category);
  }
  if (color !== "all") {
    filtered = filtered.filter((material) => normalizeSearchTerm(material.color) === color);
  }
  return filtered;
}

function filterInventory(items) {
  const search = filterState.inventory.search;
  const material = filterState.inventory.material;
  const color = filterState.inventory.color;
  const location = filterState.inventory.location;
  let filtered = items;
  if (search) {
    filtered = filtered.filter((item) =>
      matchesSearch(search, [
        item.material?.name,
        item.material?.color,
        item.material?.barcode,
        item.location,
        item.spool_serial,
      ])
    );
  }
  if (material !== "all") {
    filtered = filtered.filter((item) => normalizeSearchTerm(item.material?.name) === material);
  }
  if (color !== "all") {
    filtered = filtered.filter((item) => normalizeSearchTerm(item.material?.color) === color);
  }
  if (location !== "all") {
    filtered = filtered.filter((item) => normalizeSearchTerm(item.location) === location);
  }
  return filtered;
}

function filterModels(items) {
  const search = filterState.models.search;
  const mode = filterState.models.mode;
  let filtered = items;
  if (search) {
    filtered = filtered.filter((model) =>
      matchesSearch(search, [
        model.name,
        model.category,
        model.sku,
        model.designer,
        model.platform,
        model.file_location,
        model.version,
        model.notes,
      ])
    );
  }
  if (mode === "active") {
    filtered = filtered.filter((model) => model.active);
  } else if (mode === "inactive") {
    filtered = filtered.filter((model) => !model.active);
  }
  return filtered;
}

function filterHardware(items) {
  const search = filterState.hardware.search;
  const mode = filterState.hardware.mode;
  let filtered = items;
  if (search) {
    filtered = filtered.filter((item) =>
      matchesSearch(search, [
        item.name,
        item.category,
        item.supplier,
        item.manufacturer_part_number,
        item.unit_of_measure,
        item.bin_location,
        item.notes,
      ])
    );
  }
  if (mode === "below-reorder") {
    filtered = filtered.filter((item) => {
      const reorder = Number(item.reorder_level || 0);
      const qty = Number(item.quantity_on_hand || 0);
      return reorder > 0 && Number.isFinite(qty) && qty <= reorder;
    });
  } else if (mode === "no-reorder") {
    filtered = filtered.filter((item) => Number(item.reorder_level || 0) <= 0);
  }
  return filtered;
}

function filterMovements(movements) {
  const search = filterState.movements.search;
  const mode = filterState.movements.mode;
  let filtered = movements;
  if (mode !== "all") {
    filtered = filtered.filter((move) => move.movement_type === mode);
  }
  if (search) {
    filtered = filtered.filter((move) =>
      matchesSearch(search, [move.movement_type, move.reference, move.note, move.change_grams])
    );
  }
  return filtered;
}

function buildFilterOptions(items) {
  const cleaned = items.filter((value) => String(value || "").trim());
  const unique = new Map();
  cleaned.forEach((value) => {
    const label = String(value).trim();
    const normalized = normalizeSearchTerm(label);
    if (!unique.has(normalized)) {
      unique.set(normalized, label);
    }
  });
  return Array.from(unique.entries())
    .map(([value, label]) => ({ value, label }))
    .sort((a, b) => a.label.localeCompare(b.label));
}

function populateMaterialFilters() {
  if (!materialBrandFilter || !materialTypeFilter || !materialCategoryFilter || !materialColorFilter) {
    return;
  }
  const brands = buildFilterOptions(state.materials.map((material) => material.brand));
  const types = buildFilterOptions(state.materials.map((material) => material.filament_type));
  const categories = buildFilterOptions(state.materials.map((material) => material.category));
  const colors = buildFilterOptions(state.materials.map((material) => material.color));

  const setOptions = (select, values, allLabel, currentValue) => {
    const options = [`<option value="all">${allLabel}</option>`]
      .concat(values.map((item) => `<option value="${escapeHtml(item.value)}">${escapeHtml(item.label)}</option>`))
      .join("");
    select.innerHTML = options;
    if (values.some((item) => item.value === currentValue)) {
      select.value = currentValue;
    } else {
      select.value = "all";
    }
  };

  setOptions(materialBrandFilter, brands, "All brands", filterState.materials.brand);
  setOptions(materialTypeFilter, types, "All types", filterState.materials.type);
  setOptions(materialCategoryFilter, categories, "All categories", filterState.materials.category);
  setOptions(materialColorFilter, colors, "All colors", filterState.materials.color);

  filterState.materials.brand = materialBrandFilter.value || "all";
  filterState.materials.type = materialTypeFilter.value || "all";
  filterState.materials.category = materialCategoryFilter.value || "all";
  filterState.materials.color = materialColorFilter.value || "all";
}

function populateInventoryFilters() {
  if (!inventoryMaterialFilter || !inventoryColorFilter || !inventoryLocationFilter) {
    return;
  }
  const materials = buildFilterOptions(state.inventory.map((item) => item.material?.name));
  const colors = buildFilterOptions(state.inventory.map((item) => item.material?.color));
  const locations = buildFilterOptions(state.inventory.map((item) => item.location));

  const setOptions = (select, values, allLabel, currentValue) => {
    const options = [`<option value="all">${allLabel}</option>`]
      .concat(values.map((item) => `<option value="${escapeHtml(item.value)}">${escapeHtml(item.label)}</option>`))
      .join("");
    select.innerHTML = options;
    if (values.some((item) => item.value === currentValue)) {
      select.value = currentValue;
    } else {
      select.value = "all";
    }
  };

  setOptions(inventoryMaterialFilter, materials, "All materials", filterState.inventory.material);
  setOptions(inventoryColorFilter, colors, "All colors", filterState.inventory.color);
  setOptions(inventoryLocationFilter, locations, "All locations", filterState.inventory.location);

  filterState.inventory.material = inventoryMaterialFilter.value || "all";
  filterState.inventory.color = inventoryColorFilter.value || "all";
  filterState.inventory.location = inventoryLocationFilter.value || "all";
}

function renderMaterials() {
  const filtered = filterMaterials(state.materials);
  const { items, total, startIndex, endIndex, maxPage } = paginate(filtered, paginationState.materials);
  updatePaginationControls({
    total,
    startIndex,
    endIndex,
    maxPage,
    pageState: paginationState.materials,
    infoEl: materialsInfoEl,
    pageEl: materialsPageEl,
    prevBtn: materialsPrevBtn,
    nextBtn: materialsNextBtn,
  });
  if (!state.materials.length) {
    materialTableBody.innerHTML = `<tr><td colspan="10" class="muted">No materials yet.</td></tr>`;
    return;
  }
  if (!filtered.length) {
    materialTableBody.innerHTML = `<tr><td colspan="10" class="muted">No matches for the current search or filter.</td></tr>`;
    return;
  }
  materialTableBody.innerHTML = items
    .map(
      (material) => `
        <tr data-id="${material.id}">
          <td>${escapeHtml(material.name)}</td>
          <td>${escapeHtml(material.brand || "")}</td>
          <td>${escapeHtml(material.filament_type)}</td>
          <td>${escapeHtml(material.category || "")}</td>
          <td>${formatColorChip(material.color, material.color_hex)}</td>
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
  const filtered = filterInventory(state.inventory);
  const sorted = filtered
    .slice()
    .sort((a, b) => {
      const aMaterial = a.material || {};
      const bMaterial = b.material || {};
      const keyA = [
        normalizeSearchTerm(aMaterial.brand),
        normalizeSearchTerm(aMaterial.filament_type),
        normalizeSearchTerm(aMaterial.category),
        normalizeSearchTerm(aMaterial.name),
      ];
      const keyB = [
        normalizeSearchTerm(bMaterial.brand),
        normalizeSearchTerm(bMaterial.filament_type),
        normalizeSearchTerm(bMaterial.category),
        normalizeSearchTerm(bMaterial.name),
      ];
      for (let i = 0; i < keyA.length; i += 1) {
        if (keyA[i] === keyB[i]) continue;
        return keyA[i].localeCompare(keyB[i]);
      }
      return 0;
    });
  const { items, total, startIndex, endIndex, maxPage } = paginate(sorted, paginationState.inventory);
  updatePaginationControls({
    total,
    startIndex,
    endIndex,
    maxPage,
    pageState: paginationState.inventory,
    infoEl: inventoryInfoEl,
    pageEl: inventoryPageEl,
    prevBtn: inventoryPrevBtn,
    nextBtn: inventoryNextBtn,
  });
  if (!state.inventory.length) {
    inventoryGrid.innerHTML = `<div class="inventory-empty muted">No inventory tracked yet.</div>`;
    return;
  }
  if (!filtered.length) {
    inventoryGrid.innerHTML = `<div class="inventory-empty muted">No matches for the current search or filter.</div>`;
    return;
  }
  inventoryGrid.innerHTML = items
    .map((item) => {
      const material = item.material || {};
      const swatch = resolveSwatchColor(material.color, material.color_hex);
      const brand = escapeHtml(material.brand || "Unbranded");
      const type = escapeHtml(material.filament_type || "Unknown type");
      const category = escapeHtml(material.category || "Uncategorized");
      const name = escapeHtml(material.name || "Unknown material");
      const colorName = escapeHtml(material.color || "Unknown color");
      const location = escapeHtml(item.location || "-");
      const serial = escapeHtml(item.spool_serial || "-");
      const reorder = formatQuantity(item.reorder_level, "g");
      const remaining = formatQuantity(item.quantity_grams, "g");
      const unitCost = item.unit_cost_override ? formatCurrency(item.unit_cost_override) : "-";
      return `
        <div class="inventory-card" role="listitem" data-id="${item.id}">
          <div class="inventory-card-top">
            <span class="inventory-swatch" style="--swatch-color: ${swatch || "transparent"}" aria-hidden="true"></span>
            <div class="inventory-title-block">
              <p class="inventory-title">${name}</p>
              <p class="inventory-subtitle">${colorName}</p>
            </div>
            <div class="inventory-qty">
              <span class="label">Remaining</span>
              <span class="value">${remaining}</span>
            </div>
          </div>
          <div class="inventory-meta">
            <span class="inventory-pill"><span class="color-dot" style="--swatch-color: ${swatch || "transparent"}"></span>${brand}</span>
            <span class="inventory-pill"><span class="color-dot" style="--swatch-color: ${swatch || "transparent"}"></span>${type}</span>
            <span class="inventory-pill"><span class="color-dot" style="--swatch-color: ${swatch || "transparent"}"></span>${category}</span>
          </div>
          <div class="inventory-stats">
            <div class="inventory-stat">
              <span>Location</span>
              <strong>${location}</strong>
            </div>
            <div class="inventory-stat">
              <span>Reorder</span>
              <strong>${reorder}</strong>
            </div>
            <div class="inventory-stat">
              <span>Serial</span>
              <strong>${serial}</strong>
            </div>
            <div class="inventory-stat">
              <span>Unit cost</span>
              <strong>${unitCost}</strong>
            </div>
          </div>
          <div class="inventory-actions">
            <button class="small-button" data-action="edit" data-id="${item.id}">Edit</button>
            <button class="small-button danger" data-action="delete" data-id="${item.id}">Delete</button>
          </div>
        </div>`;
    })
    .join("");
}

function renderModels() {
  const filtered = filterModels(state.models);
  const { items, total, startIndex, endIndex, maxPage } = paginate(filtered, paginationState.models);
  updatePaginationControls({
    total,
    startIndex,
    endIndex,
    maxPage,
    pageState: paginationState.models,
    infoEl: modelsInfoEl,
    pageEl: modelsPageEl,
    prevBtn: modelsPrevBtn,
    nextBtn: modelsNextBtn,
  });
  if (!state.models.length) {
    modelsTableBody.innerHTML = `<tr><td colspan="8" class="muted">No models tracked yet.</td></tr>`;
    return;
  }
  if (!filtered.length) {
    modelsTableBody.innerHTML = `<tr><td colspan="8" class="muted">No matches for the current search or filter.</td></tr>`;
    return;
  }
  modelsTableBody.innerHTML = items
    .map((model) => {
      const status = model.active ? "Active" : "Inactive";
      return `
        <tr data-id="${model.id}">
          <td>${escapeHtml(model.name)}</td>
          <td>${escapeHtml(model.category || "")}</td>
          <td>${escapeHtml(model.sku || "")}</td>
          <td>${formatCurrency(model.unit_price || 0)}</td>
          <td>${status}</td>
          <td>${formatQuantity(model.total_sold || 0)}</td>
          <td>${formatCurrency(model.total_revenue || 0)}</td>
          <td>
            <button class="small-button" data-action="edit" data-id="${model.id}">Edit</button>
            <button class="small-button danger" data-action="delete" data-id="${model.id}">Delete</button>
          </td>
        </tr>`;
    })
    .join("");
}

function renderHardware() {
  const filtered = filterHardware(state.hardware);
  const { items, total, startIndex, endIndex, maxPage } = paginate(filtered, paginationState.hardware);
  updatePaginationControls({
    total,
    startIndex,
    endIndex,
    maxPage,
    pageState: paginationState.hardware,
    infoEl: hardwareInfoEl,
    pageEl: hardwarePageEl,
    prevBtn: hardwarePrevBtn,
    nextBtn: hardwareNextBtn,
  });
  if (!state.hardware.length) {
    hardwareTableBody.innerHTML = `<tr><td colspan="8" class="muted">No hardware recorded yet.</td></tr>`;
    return;
  }
  if (!filtered.length) {
    hardwareTableBody.innerHTML = `<tr><td colspan="8" class="muted">No matches for the current search or filter.</td></tr>`;
    return;
  }
  hardwareTableBody.innerHTML = items
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

function renderReports() {
  const metricsEl = reportMetricsEl || document.getElementById("report-metrics");
  const inventoryChartEl = reportInventoryChartEl || document.getElementById("report-inventory-chart");
  const modelsChartEl = reportModelsChartEl || document.getElementById("report-models-chart");
  const lowStockEl = reportLowStockEl || document.getElementById("report-low-stock");
  const hardwareChartEl = reportHardwareChartEl || document.getElementById("report-hardware-chart");
  const usageEl = reportUsageEl || document.getElementById("report-usage");
  const hasCoreTargets = metricsEl || inventoryChartEl || modelsChartEl || lowStockEl || hardwareChartEl || usageEl;
  if (!hasCoreTargets) {
    return;
  }
  const materials = Array.isArray(state.materials) ? state.materials : [];
  const inventory = Array.isArray(state.inventory) ? state.inventory : [];
  const models = Array.isArray(state.models) ? state.models : [];
  const hardware = Array.isArray(state.hardware) ? state.hardware : [];

  const totalInventoryGrams = inventory.reduce((sum, item) => sum + Number(item.quantity_grams || 0), 0);
  const totalInventoryValue = inventory.reduce((sum, item) => {
    const qty = Number(item.quantity_grams || 0);
    const price = Number(item.material?.price_per_gram || 0);
    if (!Number.isFinite(qty) || !Number.isFinite(price)) {
      return sum;
    }
    return sum + qty * price;
  }, 0);
  const totalHardwareUnits = hardware.reduce((sum, item) => sum + Number(item.quantity_on_hand || 0), 0);
  const totalModelUnits = models.reduce((sum, model) => sum + Number(model.total_sold || 0), 0);
  const totalModelRevenue = models.reduce((sum, model) => sum + Number(model.total_revenue || 0), 0);

  const inventoryAlerts = inventory.filter((item) => {
    const reorder = Number(item.reorder_level || 0);
    const qty = Number(item.quantity_grams || 0);
    return reorder > 0 && Number.isFinite(qty) && qty <= reorder;
  });
  const hardwareAlerts = hardware.filter((item) => {
    const reorder = Number(item.reorder_level || 0);
    const qty = Number(item.quantity_on_hand || 0);
    return reorder > 0 && Number.isFinite(qty) && qty <= reorder;
  });

  const metrics = [
    { label: "Materials", value: formatQuantity(materials.length) },
    { label: "Inventory items", value: formatQuantity(inventory.length) },
    { label: "Inventory on hand", value: formatQuantity(totalInventoryGrams, "g") },
    { label: "Inventory value", value: formatCurrency(totalInventoryValue) },
    { label: "Model listings", value: formatQuantity(models.length) },
    { label: "Model units sold", value: formatQuantity(totalModelUnits) },
    { label: "Model revenue", value: formatCurrency(totalModelRevenue) },
    { label: "Hardware items", value: formatQuantity(hardware.length) },
    { label: "Hardware units", value: formatQuantity(totalHardwareUnits) },
  ];

  if (metricsEl) {
    metricsEl.innerHTML = metrics
      .map(
        (metric) => `
          <div class="report-metric">
            <span class="label">${escapeHtml(metric.label)}</span>
            <span class="value">${escapeHtml(metric.value)}</span>
          </div>`
      )
      .join("");
  }

  if (inventoryChartEl) {
    renderReportBars(
      inventoryChartEl,
      summarizeInventoryByMaterial(inventory),
      "g",
      "No inventory data yet."
    );
  }
  if (modelsChartEl) {
    renderReportBars(
      modelsChartEl,
      summarizeModelsBySales(models),
      "sales",
      "No model sales yet.",
      (value) => formatQuantity(value)
    );
  }
  if (hardwareChartEl) {
    renderReportBars(
      hardwareChartEl,
      summarizeHardwareByCategory(hardware),
      "units",
      "No hardware data yet."
    );
  }

  if (lowStockEl) {
    if (!inventoryAlerts.length && !hardwareAlerts.length) {
      lowStockEl.innerHTML = `<li class="muted">No items below reorder level.</li>`;
    } else {
      const alertLines = [
        ...inventoryAlerts.map((item) => {
          const name = item.material ? item.material.name : `Material ${item.material_id}`;
          const label = `${name} - ${item.location}`;
          return {
            label,
            detail: `${formatQuantity(item.quantity_grams, "g")} on hand, reorder at ${formatQuantity(
              item.reorder_level,
              "g"
            )}`,
          };
        }),
        ...hardwareAlerts.map((item) => ({
          label: item.name,
          detail: `${formatQuantity(item.quantity_on_hand, item.unit_of_measure || "units")} on hand, reorder at ${formatQuantity(
            item.reorder_level,
            item.unit_of_measure || "units"
          )}`,
        })),
      ];
      lowStockEl.innerHTML = alertLines
        .map(
          (alert) => `
            <li class="report-alert">
              <strong>${escapeHtml(alert.label)}</strong><br />
              <span>${escapeHtml(alert.detail)}</span>
            </li>`
        )
        .join("");
    }
  }

  if (usageEl) {
    usageEl.innerHTML = buildUsageSnapshot();
  }
  renderOrderWorksReports();
}

function summarizeInventoryByMaterial(inventory) {
  const totals = new Map();
  inventory.forEach((item) => {
    const name = item.material ? item.material.name : `Material ${item.material_id}`;
    const color = item.material && item.material.color ? ` (${item.material.color})` : "";
    const label = `${name}${color}`;
    const current = totals.get(label) || 0;
    totals.set(label, current + Number(item.quantity_grams || 0));
  });
  return Array.from(totals.entries())
    .map(([label, value]) => ({ label, value }))
    .filter((item) => Number.isFinite(item.value))
    .sort((a, b) => b.value - a.value)
    .slice(0, 6);
}

function summarizeModelsBySales(models) {
  const totals = new Map();
  models.forEach((model) => {
    const label = model.name || "Unnamed model";
    const current = totals.get(label) || 0;
    totals.set(label, current + Number(model.total_sold || 0));
  });
  return Array.from(totals.entries())
    .map(([label, value]) => ({ label, value }))
    .filter((item) => Number.isFinite(item.value))
    .sort((a, b) => b.value - a.value)
    .slice(0, 6);
}

function summarizeHardwareByCategory(hardware) {
  const totals = new Map();
  hardware.forEach((item) => {
    const category = item.category && item.category.trim() ? item.category.trim() : "Uncategorized";
    const current = totals.get(category) || 0;
    totals.set(category, current + Number(item.quantity_on_hand || 0));
  });
  return Array.from(totals.entries())
    .map(([label, value]) => ({ label, value }))
    .filter((item) => Number.isFinite(item.value))
    .sort((a, b) => b.value - a.value)
    .slice(0, 6);
}

function renderReportBars(targetEl, items, unitLabel, emptyText, formatValue) {
  if (!targetEl) return;
  if (!items.length) {
    targetEl.innerHTML = `<div class="muted">${escapeHtml(emptyText)}</div>`;
    return;
  }
  const maxValue = Math.max(...items.map((item) => item.value));
  targetEl.innerHTML = items
    .map((item) => {
      const width = maxValue > 0 ? Math.max(2, (item.value / maxValue) * 100) : 0;
      const valueLabel = formatValue ? formatValue(item.value) : formatQuantity(item.value, unitLabel);
      return `
        <div class="report-bar">
          <div class="report-bar-label">${escapeHtml(item.label)}</div>
          <div class="report-bar-track">
            <span class="report-bar-fill" style="width: ${width}%"></span>
          </div>
          <div class="report-bar-value">${escapeHtml(valueLabel)}</div>
        </div>`;
    })
    .join("");
}

function normalizeOrderStatus(status) {
  if (!status) return "unknown";
  const normalized = String(status).trim().toLowerCase();
  if (!normalized) return "unknown";
  if (normalized === "cancelled") return "canceled";
  return normalized;
}

function parseJobDate(job) {
  const raw =
    job.makerworksCreatedAt || job.createdAt || job.makerworksUpdatedAt || job.updatedAt || job.fulfilledAt;
  if (!raw) return null;
  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  return date;
}

function formatShortDate(date) {
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function renderOrderWorksReports() {
  if (!reportOrderworksMetricsEl || !reportOrderworksStatusEl || !reportOrderworksRevenueEl) {
    return;
  }

  const setFallback = (message) => {
    const safeMessage = escapeHtml(message);
    reportOrderworksMetricsEl.innerHTML = `<div class="muted">${safeMessage}</div>`;
    reportOrderworksStatusEl.innerHTML = `<div class="muted">${safeMessage}</div>`;
    reportOrderworksRevenueEl.innerHTML = `<div class="muted">${safeMessage}</div>`;
  };

  if (!state.orderworksConfigured) {
    setFallback("OrderWorks integration is not configured.");
    return;
  }
  if (state.orderworksError) {
    setFallback(state.orderworksError);
    return;
  }

  const jobs = Array.isArray(state.orderworksJobs) ? state.orderworksJobs : [];
  if (!jobs.length) {
    setFallback("No OrderWorks jobs available.");
    return;
  }

  const totals = {
    totalCents: 0,
    totalCount: 0,
    openCount: 0,
    completedCount: 0,
    last7DaysCount: 0,
    last30DaysCents: 0,
  };
  const statusCounts = new Map();
  const now = new Date();
  const last7Days = new Date(now);
  last7Days.setDate(now.getDate() - 6);
  const last30Days = new Date(now);
  last30Days.setDate(now.getDate() - 29);
  const currencies = new Set();

  jobs.forEach((job) => {
    const status = normalizeOrderStatus(job.status);
    const current = statusCounts.get(status) || 0;
    statusCounts.set(status, current + 1);
    totals.totalCount += 1;
    if (status === "pending" || status === "printing") {
      totals.openCount += 1;
    }
    if (status === "completed") {
      totals.completedCount += 1;
    }

    if (job.currency) {
      currencies.add(String(job.currency).toUpperCase());
    }
    const cents = Number(job.totalCents);
    const createdAt = parseJobDate(job);
    if (createdAt) {
      if (createdAt >= last7Days) {
        totals.last7DaysCount += 1;
      }
      if (createdAt >= last30Days && Number.isFinite(cents)) {
        totals.last30DaysCents += cents;
      }
    }
    if (Number.isFinite(cents)) {
      totals.totalCents += cents;
    }
  });

  const currency = currencies.size === 1 ? Array.from(currencies)[0] : "USD";
  const averageCents = totals.totalCount ? totals.totalCents / totals.totalCount : 0;
  const metrics = [
    { label: "Jobs total", value: formatQuantity(totals.totalCount) },
    { label: "Open jobs", value: formatQuantity(totals.openCount) },
    { label: "Completed jobs", value: formatQuantity(totals.completedCount) },
    { label: "Jobs last 7 days", value: formatQuantity(totals.last7DaysCount) },
    { label: "Revenue last 30 days", value: formatCurrencyValue(totals.last30DaysCents, currency) },
    { label: "Average job value", value: formatCurrencyValue(averageCents, currency) },
  ];

  reportOrderworksMetricsEl.innerHTML = metrics
    .map(
      (metric) => `
        <div class="report-metric">
          <span class="label">${escapeHtml(metric.label)}</span>
          <span class="value">${escapeHtml(metric.value)}</span>
        </div>`
    )
    .join("");

  const statusOrder = ["pending", "printing", "completed", "canceled", "refunded", "failed", "unknown"];
  const statusItems = [];
  statusOrder.forEach((status) => {
    if (statusCounts.has(status)) {
      statusItems.push({ label: formatOrderStatus(status), value: statusCounts.get(status) });
      statusCounts.delete(status);
    }
  });
  Array.from(statusCounts.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .forEach(([status, count]) => {
      statusItems.push({ label: formatOrderStatus(status), value: count });
    });

  renderReportBars(reportOrderworksStatusEl, statusItems, "jobs", "No job status data yet.");

  const dayBuckets = [];
  for (let i = 13; i >= 0; i -= 1) {
    const day = new Date(now);
    day.setDate(now.getDate() - i);
    day.setHours(0, 0, 0, 0);
    dayBuckets.push({
      key: `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, "0")}-${String(day.getDate()).padStart(
        2,
        "0"
      )}`,
      label: formatShortDate(day),
      value: 0,
    });
  }

  jobs.forEach((job) => {
    const createdAt = parseJobDate(job);
    if (!createdAt) return;
    const dayKey = `${createdAt.getFullYear()}-${String(createdAt.getMonth() + 1).padStart(2, "0")}-${String(
      createdAt.getDate()
    ).padStart(2, "0")}`;
    const bucket = dayBuckets.find((entry) => entry.key === dayKey);
    if (!bucket) return;
    const cents = Number(job.totalCents);
    if (Number.isFinite(cents)) {
      bucket.value += cents;
    }
  });

  const hasRevenue = dayBuckets.some((entry) => entry.value > 0);
  renderReportBars(
    reportOrderworksRevenueEl,
    hasRevenue ? dayBuckets : [],
    "",
    "No revenue recorded in the last 14 days.",
    (value) => formatCurrencyValue(value, currency)
  );
}

function summarizeMovementStats(movements, valueKey) {
  return movements.reduce(
    (acc, move) => {
      const change = Number(move[valueKey] || 0);
      if (!Number.isFinite(change)) {
        return acc;
      }
      if (change >= 0) {
        acc.incoming += change;
      } else {
        acc.outgoing += Math.abs(change);
      }
      acc.net += change;
      acc.count += 1;
      return acc;
    },
    { incoming: 0, outgoing: 0, net: 0, count: 0 }
  );
}

function buildUsageSnapshot() {
  const inventoryMoves = Array.isArray(state.lastInventoryMovements) ? state.lastInventoryMovements : [];
  const hardwareMoves = Array.isArray(state.lastHardwareMovements) ? state.lastHardwareMovements : [];
  if (!inventoryMoves.length && !hardwareMoves.length) {
    return "Select an inventory or hardware item in Stock Movements to load usage history here.";
  }

  const lines = [];
  if (inventoryMoves.length) {
    const stats = summarizeMovementStats(inventoryMoves, "change_grams");
    lines.push(
      `Inventory movements loaded: ${stats.count} entries, ${formatQuantity(
        stats.outgoing,
        "g"
      )} out, ${formatQuantity(stats.incoming, "g")} in.`
    );
  }
  if (hardwareMoves.length) {
    const stats = summarizeMovementStats(hardwareMoves, "change_units");
    lines.push(
      `Hardware movements loaded: ${stats.count} entries, ${formatQuantity(
        stats.outgoing,
        "units"
      )} out, ${formatQuantity(stats.incoming, "units")} in.`
    );
  }
  return lines.map((line) => `<div>${escapeHtml(line)}</div>`).join("");
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
  const filtered = filterMovements(movements);
  if (!filtered.length) {
    movementTableBody.innerHTML = `<tr><td colspan="5" class="muted">No matches for the current search or filter.</td></tr>`;
    return;
  }
  movementTableBody.innerHTML = filtered
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
    .map((material) => {
      const hex = normalizeHexValue(material.color_hex);
      const hexLabel = hex ? ` • ${hex}` : "";
      return `<option value="${material.id}">${escapeHtml(material.name)} (${escapeHtml(material.color)}${hexLabel})</option>`;
    })
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
      if (!item.material) {
        return `<option value="${item.id}">Item ${item.id}</option>`;
      }
      const hex = normalizeHexValue(item.material.color_hex);
      const hexLabel = hex ? ` • ${hex}` : "";
      const label = `${item.material.name} (${item.material.color}${hexLabel}) – ${item.location}`;
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

function populateModelOptions() {
  if (!modelSaleSelect) {
    return;
  }
  const options = state.models
    .map((model) => {
      const label = model.sku ? `${model.name} ƒ?" ${model.sku}` : model.name;
      return `<option value="${model.id}">${escapeHtml(label)}</option>`;
    })
    .join("");
  const currentValue = modelSaleSelect.value;
  modelSaleSelect.innerHTML = `<option value="">Select model...</option>${options}`;
  if (options && currentValue && state.models.some((model) => String(model.id) === currentValue)) {
    modelSaleSelect.value = currentValue;
  }
}

async function handleMaterialSubmit(event) {
  event.preventDefault();
  try {
    const payload = buildMaterialPayload();
    if (!payload) return;
    let saved = null;
    if (state.currentMaterialId) {
      saved = await api(`/materials/${state.currentMaterialId}`, { method: "PUT", body: payload });
    } else {
      saved = await api("/materials", { method: "POST", body: payload });
    }
    await loadMaterials();
    if (!state.currentMaterialId && saved && saved.name && saved.name !== payload.name) {
      setMessage(`Duplicate filament name detected. Saved as "${saved.name}".`, "info");
    } else {
      showToast("Material saved.", "success");
    }
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
    showToast("Inventory saved.", "success");
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
    showToast("Hardware saved.", "success");
  } catch (error) {
    console.error(error);
    setMessage(error.message, "error");
  }
}

async function handleModelSubmit(event) {
  event.preventDefault();
  try {
    const payload = buildModelPayload();
    if (!payload) return;
    if (state.currentModelId) {
      await api(`/models/${state.currentModelId}`, { method: "PUT", body: payload });
    } else {
      await api("/models", { method: "POST", body: payload });
    }
    await loadModels();
    showToast("Model saved.", "success");
  } catch (error) {
    console.error(error);
    setMessage(error.message, "error");
  }
}

async function handleModelSaleSubmit(event) {
  event.preventDefault();
  try {
    const modelId = Number(modelSaleSelect.value);
    if (!Number.isFinite(modelId)) {
      setMessage("Select a model first.", "error");
      return;
    }
    const quantity = Number(modelSaleQuantity.value);
    const unitPrice = Number(modelSalePrice.value);
    if (!Number.isFinite(quantity) || quantity <= 0) {
      setMessage("Quantity must be a positive number.", "error");
      return;
    }
    if (!Number.isFinite(unitPrice) || unitPrice < 0) {
      setMessage("Unit price must be zero or greater.", "error");
      return;
    }
    const payload = {
      model_id: modelId,
      quantity: Math.round(quantity),
      unit_price: unitPrice,
      currency: (modelSaleCurrency.value || "USD").trim() || "USD",
      channel: optionalString(modelSaleChannel.value),
      reference: optionalString(modelSaleReference.value),
      note: optionalString(modelSaleNote.value),
    };
    await api("/models/sales", { method: "POST", body: payload });
    modelSaleQuantity.value = "";
    modelSalePrice.value = "";
    modelSaleChannel.value = "";
    modelSaleReference.value = "";
    modelSaleNote.value = "";
    await loadModels();
    await loadModelSales(modelId);
    showToast("Model sale logged.", "success");
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
    showToast("Movement logged.", "success");
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

function handleModelRowClick(event) {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  const id = Number(button.dataset.id);
  if (button.dataset.action === "edit") {
    startModelEdit(id);
  } else if (button.dataset.action === "delete") {
    deleteModel(id);
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
  if (materialFields.color_hex) {
    materialFields.color_hex.value = normalizeHexValue(material.color_hex) || "";
  }
  materialFields.supplier.value = material.supplier || "";
  materialFields.brand.value = material.brand || "";
  materialFields.price_per_gram.value = material.price_per_gram;
  materialFields.spool_weight_grams.value = material.spool_weight_grams;
  materialFields.barcode.value = material.barcode || "";
  materialFields.notes.value = material.notes || "";
  updateMaterialColorRequirement();
  syncMaterialColorInputs({ source: "text" });
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

function highlightInventoryRow(id) {
  const index = state.inventory.findIndex((item) => item.id === id);
  if (index === -1) return;
  const pageState = paginationState.inventory;
  const targetPage = Math.floor(index / pageState.perPage) + 1;
  if (targetPage !== pageState.page) {
    pageState.page = targetPage;
    renderInventory();
  }
  const card = inventoryGrid.querySelector(`.inventory-card[data-id="${id}"]`);
  if (!card) return;
  inventoryGrid.querySelectorAll(".inventory-card.is-highlighted").forEach((el) => el.classList.remove("is-highlighted"));
  card.classList.add("is-highlighted");
  card.scrollIntoView({ behavior: "smooth", block: "center", inline: "nearest" });
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

function startModelEdit(id) {
  const model = state.models.find((item) => item.id === id);
  if (!model) return;
  state.currentModelId = id;
  modelIdInput.value = id;
  modelFields.name.value = model.name || "";
  modelFields.category.value = model.category || "";
  modelFields.sku.value = model.sku || "";
  modelFields.designer.value = model.designer || "";
  modelFields.platform.value = model.platform || "";
  modelFields.file_location.value = model.file_location || "";
  modelFields.version.value = model.version || "";
  modelFields.unit_price.value = model.unit_price ?? "";
  modelFields.active.value = model.active ? "true" : "false";
  modelFields.notes.value = model.notes || "";
  if (modelSaleSelect) {
    modelSaleSelect.value = String(id);
    state.currentModelSaleId = id;
    safeAsync(() => loadModelSales(id));
  }
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

async function deleteModel(id) {
  if (!confirm("Delete this model and its sales history?")) {
    return;
  }
  try {
    await api(`/models/${id}`, { method: "DELETE" });
    if (state.currentModelId === id) {
      resetModelForm();
    }
    await loadModels();
    setMessage("Model deleted.", "success");
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
  const normalizedHex = normalizeHexValue(materialFields.color_hex ? materialFields.color_hex.value : "");
  if (!normalizedHex) {
    setMessage("Provide a valid hex color for the material.", "error");
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
    color_hex: normalizedHex || null,
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

function buildModelPayload() {
  const name = modelFields.name.value.trim();
  if (!name) {
    setMessage("Model name is required.", "error");
    return null;
  }
  const priceValue = modelFields.unit_price.value;
  const unitPrice = priceValue.trim() === "" ? 0 : Number(priceValue);
  if (!Number.isFinite(unitPrice) || unitPrice < 0) {
    setMessage("Unit price must be a positive number.", "error");
    return null;
  }
  return {
    name,
    category: optionalString(modelFields.category.value),
    sku: optionalString(modelFields.sku.value),
    designer: optionalString(modelFields.designer.value),
    platform: optionalString(modelFields.platform.value),
    file_location: optionalString(modelFields.file_location.value),
    version: optionalString(modelFields.version.value),
    unit_price: unitPrice,
    active: modelFields.active.value === "true",
    notes: optionalString(modelFields.notes.value),
  };
}

function resetMaterialForm() {
  materialForm.reset();
  materialIdInput.value = "";
  state.currentMaterialId = null;
  updateMaterialColorRequirement();
  syncMaterialColorInputs({ source: "text" });
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

function resetModelForm() {
  modelForm.reset();
  modelIdInput.value = "";
  state.currentModelId = null;
}

async function loadModelSales(modelId) {
  const sales = await api(`/models/${modelId}/sales`);
  state.lastModelSales = Array.isArray(sales) ? sales : [];
  renderModelSales(sales);
  renderReports();
}

function renderModelSales(sales) {
  if (!modelSaleTableBody) {
    return;
  }
  if (!sales.length) {
    const text = state.currentModelSaleId ? "No sales logged yet." : "Select a model to view sales history.";
    modelSaleTableBody.innerHTML = `<tr><td colspan="7" class="muted">${text}</td></tr>`;
    return;
  }
  modelSaleTableBody.innerHTML = sales
    .map((sale) => {
      const total = Number(sale.quantity || 0) * Number(sale.unit_price || 0);
      return `
        <tr>
          <td>${new Date(sale.sold_at).toLocaleString()}</td>
          <td>${formatQuantity(sale.quantity)}</td>
          <td>${formatCurrency(sale.unit_price, sale.currency)}</td>
          <td>${formatCurrency(total, sale.currency)}</td>
          <td>${escapeHtml(sale.channel || "")}</td>
          <td>${escapeHtml(sale.reference || "")}</td>
          <td>${escapeHtml(sale.note || "")}</td>
        </tr>`;
    })
    .join("");
}

async function loadHardwareMovements(itemId) {
  const movements = await api(`/hardware/${itemId}/movements`);
  state.lastHardwareMovements = Array.isArray(movements) ? movements : [];
  renderHardwareMovements(movements);
  renderReports();
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
    showToast("Hardware movement logged.", "success");
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

function showToast(text, variant = "success") {
  if (!toastContainer || !text) {
    return;
  }
  const toast = document.createElement("div");
  toast.className = `toast ${variant === "success" ? "toast-success" : ""}`;
  toast.textContent = text;
  toastContainer.appendChild(toast);
  requestAnimationFrame(() => toast.classList.add("is-visible"));
  const timeoutId = setTimeout(() => {
    toast.classList.remove("is-visible");
    setTimeout(() => toast.remove(), 200);
  }, 3200);
  toast.addEventListener("click", () => {
    clearTimeout(timeoutId);
    toast.classList.remove("is-visible");
    setTimeout(() => toast.remove(), 200);
  });
}

function paginate(items, pageState) {
  const total = items.length;
  const maxPage = Math.max(1, Math.ceil(total / pageState.perPage));
  if (pageState.page > maxPage) {
    pageState.page = maxPage;
  } else if (pageState.page < 1) {
    pageState.page = 1;
  }
  const startIndex = total ? (pageState.page - 1) * pageState.perPage : 0;
  const endIndex = total ? Math.min(startIndex + pageState.perPage, total) : 0;
  return {
    items: total ? items.slice(startIndex, endIndex) : [],
    total,
    startIndex,
    endIndex,
    maxPage,
  };
}

function updatePaginationControls({ total, startIndex, endIndex, maxPage, pageState, infoEl, pageEl, prevBtn, nextBtn }) {
  if (infoEl) {
    const startLabel = total ? startIndex + 1 : 0;
    const endLabel = total ? endIndex : 0;
    infoEl.textContent = `Showing ${startLabel}-${endLabel} of ${total}`;
  }
  if (pageEl) {
    pageEl.textContent = `Page ${pageState.page} of ${maxPage}`;
  }
  if (prevBtn) {
    prevBtn.disabled = pageState.page <= 1;
  }
  if (nextBtn) {
    nextBtn.disabled = pageState.page >= maxPage;
  }
}

function changePage(section, delta) {
  const pageState = paginationState[section];
  if (!pageState) return;
  pageState.page += delta;
  if (section === "materials") {
    renderMaterials();
  } else if (section === "inventory") {
    renderInventory();
  } else if (section === "models") {
    renderModels();
  } else if (section === "hardware") {
    renderHardware();
  }
}

function normalizeBarcode(value) {
  return String(value || "").trim();
}

function findMaterialByBarcode(barcode) {
  const normalized = normalizeBarcode(barcode);
  if (!normalized) {
    return null;
  }
  return state.materials.find((material) => normalizeBarcode(material.barcode) === normalized) || null;
}

function findInventoryByBarcode(barcode) {
  const normalized = normalizeBarcode(barcode);
  if (!normalized) {
    return [];
  }
  return state.inventory.filter((item) => {
    if (item.material && normalizeBarcode(item.material.barcode) === normalized) {
      return true;
    }
    return normalizeBarcode(item.spool_serial) === normalized;
  });
}

async function openBarcodeScanner({ title, onDetected }) {
  if (!scannerOverlay || !scannerVideo) {
    setMessage("Scanner UI is not available on this page.", "error");
    return;
  }
  if (scannerState.active) {
    return;
  }
  if (!window.isSecureContext) {
    setMessage("Camera access requires HTTPS (or localhost).", "error");
    return;
  }
  if (!navigator.mediaDevices || typeof navigator.mediaDevices.getUserMedia !== "function") {
    setMessage("Camera access is not supported on this device.", "error");
    return;
  }
  if (typeof BarcodeDetector !== "function" || typeof createImageBitmap !== "function") {
    setMessage("Barcode scanning is not supported in this browser.", "error");
    return;
  }

  let detector = null;
  try {
    detector = new BarcodeDetector({ formats: DEFAULT_BARCODE_FORMATS });
  } catch (error) {
    console.error("Barcode detector initialization failed:", error);
    setMessage("Barcode detector is unavailable.", "error");
    return;
  }

  scannerState.active = true;
  scannerState.detector = detector;
  scannerState.onDetected = onDetected;
  if (scannerTitleEl) {
    scannerTitleEl.textContent = title || "Scan barcode";
  }
  if (scannerStatusEl) {
    scannerStatusEl.textContent = "Point the camera at a barcode.";
  }
  scannerOverlay.hidden = false;

  try {
    scannerState.stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: "environment" } },
      audio: false,
    });
    scannerVideo.srcObject = scannerState.stream;
    await scannerVideo.play();
    startBarcodeScanLoop();
  } catch (error) {
    console.error("Camera access failed:", error);
    setMessage("Unable to access the camera.", "error");
    closeBarcodeScanner({ silent: true });
  }
}

function startBarcodeScanLoop() {
  if (!scannerState.active || !scannerState.detector || !scannerVideo) {
    return;
  }
  let lastScan = 0;
  const scan = async (now) => {
    if (!scannerState.active || !scannerState.detector) {
      return;
    }
    if (scannerVideo.readyState < 2) {
      scannerState.rafId = requestAnimationFrame(scan);
      return;
    }
    if (now - lastScan < 250) {
      scannerState.rafId = requestAnimationFrame(scan);
      return;
    }
    lastScan = now;
    try {
      const frame = await createImageBitmap(scannerVideo);
      const barcodes = await scannerState.detector.detect(frame);
      frame.close();
      if (barcodes && barcodes.length) {
        const value = barcodes[0].rawValue || "";
        if (value) {
          const handler = scannerState.onDetected;
          closeBarcodeScanner({ silent: true });
          if (handler) {
            Promise.resolve(handler(value)).catch((error) => {
              console.error("Barcode handler failed:", error);
              setMessage("Unable to process the scanned barcode.", "error");
            });
          }
          return;
        }
      }
    } catch (error) {
      console.error("Barcode scan failed:", error);
    }
    scannerState.rafId = requestAnimationFrame(scan);
  };
  scannerState.rafId = requestAnimationFrame(scan);
}

function closeBarcodeScanner({ silent = false } = {}) {
  if (!scannerState.active && !scannerOverlay) {
    return;
  }
  scannerState.active = false;
  scannerState.onDetected = null;
  if (scannerState.rafId) {
    cancelAnimationFrame(scannerState.rafId);
    scannerState.rafId = null;
  }
  if (scannerState.stream) {
    scannerState.stream.getTracks().forEach((track) => track.stop());
    scannerState.stream = null;
  }
  if (scannerVideo) {
    scannerVideo.pause();
    scannerVideo.srcObject = null;
  }
  if (scannerOverlay) {
    scannerOverlay.hidden = true;
  }
  scannerState.detector = null;
  if (!silent && scannerStatusEl) {
    scannerStatusEl.textContent = "Scanner closed.";
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

function formatQuantity(value, unit) {
  if (!Number.isFinite(Number(value))) {
    return "-";
  }
  const formatted = Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 });
  return unit ? `${formatted} ${unit}` : formatted;
}

function formatCurrency(amount, currency = "USD") {
  if (!Number.isFinite(Number(amount))) {
    return "-";
  }
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency: currency.toUpperCase(),
      maximumFractionDigits: 2,
    }).format(Number(amount));
  } catch {
    return `$${Number(amount).toFixed(2)}`;
  }
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
