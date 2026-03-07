const state = {
  materials: [],
  inventory: [],
  hardware: [],
  models: [],
  currentMaterialId: null,
  currentInventoryId: null,
  currentMovementItemId: null,
  currentHardwareId: null,
  currentMerchId: null,
  currentHardwareMovementId: null,
  currentModelId: null,
  currentModelSaleId: null,
  currentModelMovementId: null,
  orderworksJobs: [],
  orderworksError: null,
  orderworksConfigured: true,
  orderworksBaseUrl: "",
  bambuViewPrinters: [],
  bambuViewLoadedCount: 0,
  bambuViewError: null,
  bambuViewConfigured: true,
  bambuViewBaseUrl: "",
  lastInventoryMovements: [],
  lastHardwareMovements: [],
  lastModelSales: [],
  lastModelMovements: [],
};

const messageEl = document.getElementById("message");
const csrfMeta = document.querySelector('meta[name="csrf-token"]');
const csrfToken = csrfMeta ? String(csrfMeta.content || "").trim() : "";
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
  refill_barcode: document.getElementById("material-refill-barcode"),
  notes: document.getElementById("material-notes"),
};
const materialColorDot = document.getElementById("material-color-dot");
const materialColorDropdown = document.getElementById("material-color-dropdown");
const materialColorDropdownTrigger = document.getElementById("material-color-dropdown-trigger");
const materialColorDropdownMenu = document.getElementById("material-color-dropdown-menu");
const materialColorDropdownLabel = document.getElementById("material-color-dropdown-label");
const materialColorSlots = Array.from(document.querySelectorAll(".material-color-slot"));
const materialColorEnabledInputs = Array.from(document.querySelectorAll(".material-color-slot input[type='checkbox']"));
const materialColorHexInputs = Array.from(document.querySelectorAll(".material-color-slot input[type='text']"));
const materialColorPickers = Array.from(document.querySelectorAll(".material-color-slot input[type='color']"));
const materialTableBody = document.querySelector("#materials-table tbody");
const materialsTableWrapper = document.getElementById("materials-table-wrapper");
const materialsGallery = document.getElementById("materials-gallery");
const materialSearchInput = document.getElementById("materials-search");
const materialsFilamentViewSelect = document.getElementById("materials-filament-view");
let materialSortHeaders = [];
const materialClearBtn = document.getElementById("material-clear");
const materialRefreshBtn = document.getElementById("material-refresh");
const materialDeleteBtn = document.getElementById("material-delete");
const materialBarcodeScanBtn = document.getElementById("material-barcode-scan");
const materialRefillBarcodeScanBtn = document.getElementById("material-refill-barcode-scan");
const materialBarcodePrintBtn = document.getElementById("material-barcode-print");
const materialCostHistoryList = document.getElementById("material-cost-history-list");
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
const inventoryTableBody = document.querySelector("#inventory-table tbody");
const inventoryTableWrapper = document.getElementById("inventory-table-wrapper");
const inventoryGallery = document.getElementById("inventory-gallery");
const inventoryMaterialFilter = document.getElementById("inventory-material-filter");
const inventoryColorFilter = document.getElementById("inventory-color-filter");
const inventoryLocationFilter = document.getElementById("inventory-location-filter");
const inventoryFilamentViewSelect = document.getElementById("inventory-filament-view");
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
  merch_color: document.getElementById("hardware-merch-color"),
  merch_size: document.getElementById("hardware-merch-size"),
  merch_style: document.getElementById("hardware-merch-style"),
  merch_sku: document.getElementById("hardware-merch-sku"),
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
const hardwareFilterSelect = document.getElementById("hardware-filter");
const hardwareClearBtn = document.getElementById("hardware-clear");
const hardwareRefreshBtn = document.getElementById("hardware-refresh");
const hardwareSyncMerchBtn = document.getElementById("hardware-sync-merch");
const hardwareDeleteBtn = document.getElementById("hardware-delete");
const merchTableBody = document.querySelector("#merch-table tbody");
const merchForm = document.getElementById("merch-form");
const merchIdInput = document.getElementById("merch-id");
const merchFields = {
  name: document.getElementById("merch-name"),
  category: document.getElementById("merch-category"),
  merch_color: document.getElementById("merch-color"),
  merch_size: document.getElementById("merch-size"),
  merch_style: document.getElementById("merch-style"),
  merch_sku: document.getElementById("merch-sku"),
  unit_of_measure: document.getElementById("merch-unit"),
  quantity_on_hand: document.getElementById("merch-quantity"),
  reorder_level: document.getElementById("merch-reorder"),
  bin_location: document.getElementById("merch-bin"),
  notes: document.getElementById("merch-notes"),
};
const merchClearBtn = document.getElementById("merch-clear");
const merchDeleteBtn = document.getElementById("merch-delete");
const merchSearchInput = document.getElementById("merch-search");
const merchNewBtn = document.getElementById("merch-new");
const merchRefreshBtn = document.getElementById("merch-refresh");
const merchSyncBtn = document.getElementById("merch-sync");

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
  quantity_on_hand: document.getElementById("model-quantity"),
  active: document.getElementById("model-active"),
  notes: document.getElementById("model-notes"),
};
const modelsTableBody = document.querySelector("#models-table tbody");
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
const modelMovementForm = document.getElementById("model-movement-form");
const modelMovementSelect = document.getElementById("model-movement-model");
const modelMovementType = document.getElementById("model-movement-type");
const modelMovementChange = document.getElementById("model-movement-change");
const modelMovementReference = document.getElementById("model-movement-reference");
const modelMovementNote = document.getElementById("model-movement-note");
const modelMovementTableBody = document.querySelector("#model-movement-table tbody");

// Movements
const movementForm = document.getElementById("movement-form");
const movementInventorySelect = document.getElementById("movement-inventory");
const movementTypeSelect = document.getElementById("movement-type");
const movementChangeInput = document.getElementById("movement-change");
const movementReferenceInput = document.getElementById("movement-reference");
const movementNoteInput = document.getElementById("movement-note");
const movementTableBody = document.querySelector("#movement-table tbody");
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
const bambuViewRefreshBtn = document.getElementById("bambu-view-refresh");
const bambuViewStatusEl = document.getElementById("bambu-view-status");
const bambuViewTableBody = document.querySelector("#bambu-view-table tbody");
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
  materials: { search: "" },
  inventory: { material: "all", color: "all", location: "all" },
  models: { mode: "all" },
  hardware: { mode: "all" },
  merch: { search: "" },
  movements: { mode: "all" },
};

const sortState = {
  materials: { key: "name", direction: "asc" },
};

const derivedViewCache = {
  materialsFilter: null,
  materialsSort: null,
  inventoryFilter: null,
  modelsFilter: null,
  hardwareFilter: null,
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
const FILAMENT_VIEW_STORAGE_KEY_PREFIX = "stockworks-filament-view-";
const FILAMENT_VIEW_MODES = new Set(["list", "gallery"]);
const VALID_THEME_CHOICES = new Set(["light", "dark"]);
const NON_FILAMENT_INVENTORY_LOCATIONS = new Set(["model", "models", "merch", "hardware"]);
const prefersDarkScheme = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;
let forcedThemeChoice = loadStoredThemeChoice();
let deferredInstallPrompt = null;
const filamentViewState = {
  materials: loadStoredFilamentViewMode("materials"),
  inventory: loadStoredFilamentViewMode("inventory"),
};
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
  resetMerchForm();
  updateMaterialColorRequirement();
  materialColorHexInputs.forEach((_, index) => syncMaterialColorInputs({ source: "text", index }));
  syncMaterialColorModeUi();
  syncFilamentViewControls();
  setMaterialColorDropdownOpen(false);
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

const COLOR_NAME_FALLBACKS = {
  black: "#111111",
  white: "#F5F5F5",
  ivory: "#FFFFF0",
  gray: "#6B7280",
  grey: "#6B7280",
  charcoal: "#364152",
  silver: "#BFC7D5",
  red: "#DC2626",
  orange: "#F97316",
  yellow: "#FACC15",
  gold: "#D4AF37",
  green: "#16A34A",
  lime: "#84CC16",
  teal: "#0D9488",
  cyan: "#06B6D4",
  blue: "#2563EB",
  navy: "#1E3A8A",
  purple: "#7C3AED",
  magenta: "#DB2777",
  pink: "#EC4899",
  brown: "#8B5A2B",
  tan: "#D2B48C",
  beige: "#D6C3A5",
};

function resolveColorFromWords(value) {
  const text = String(value || "").trim().toLowerCase();
  if (!text) {
    return "";
  }
  if (COLOR_NAME_FALLBACKS[text]) {
    return COLOR_NAME_FALLBACKS[text];
  }
  const words = text.split(/[\s/_-]+/g).filter(Boolean);
  for (const word of words) {
    if (COLOR_NAME_FALLBACKS[word]) {
      return COLOR_NAME_FALLBACKS[word];
    }
    if (typeof CSS !== "undefined" && typeof CSS.supports === "function" && CSS.supports("color", word)) {
      return word;
    }
  }
  return "";
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
  const resolvedByWords = resolveColorFromWords(colorName);
  if (resolvedByWords) {
    return resolvedByWords;
  }
  return "";
}

function normalizeHexList(values) {
  if (!Array.isArray(values)) {
    return [];
  }
  const normalized = [];
  values.forEach((value) => {
    const hex = normalizeHexValue(value);
    if (!hex || normalized.includes(hex) || normalized.length >= 4) {
      return;
    }
    normalized.push(hex);
  });
  return normalized;
}

function extractHexesFromString(value) {
  if (!value) {
    return [];
  }
  const matches = String(value).match(/(?:#|0x)?[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?\b/g) || [];
  return normalizeHexList(matches);
}

function resolveColorHexes(colorHexes = [], ...fallbackValues) {
  const normalized = normalizeHexList(colorHexes);
  if (normalized.length) {
    return normalized;
  }
  for (const value of fallbackValues) {
    const parsed = extractHexesFromString(value);
    if (parsed.length) {
      return parsed;
    }
  }
  return [];
}

function materialGradientHexes() {
  const values = materialColorHexInputs.map((input, index) => {
    const enabled = index === 0 || materialColorEnabledInputs[index]?.checked;
    return enabled ? input.value : "";
  });
  return normalizeHexList(values);
}

function materialHexesForDisplay(material) {
  const gradientHexes = resolveColorHexes(material?.color_hexes, material?.color_hex);
  if (gradientHexes.length) {
    return gradientHexes;
  }
  const primaryHex = normalizeHexValue(material?.color_hex);
  return primaryHex ? [primaryHex] : [];
}

function buildSwatchFill(hexes, colorName, colorHex) {
  const normalizedHexes = normalizeHexList(hexes);
  if (normalizedHexes.length > 1) {
    const slice = 100 / normalizedHexes.length;
    const stops = normalizedHexes.map((hex, index) => {
      const start = (index * slice).toFixed(4);
      const end = ((index + 1) * slice).toFixed(4);
      return `${hex} ${start}% ${end}%`;
    });
    return `conic-gradient(${stops.join(", ")})`;
  }
  return resolveSwatchColor(colorName, colorHex) || "transparent";
}

function updateMaterialColorRequirement() {
  if (!materialFields.color_hex) return;
  materialFields.color_hex.required = true;
  materialFields.color_hex.placeholder = "#1A1A1A";
}

function updateMaterialColorPreview() {
  if (!materialColorDot) return;
  const hexes = materialGradientHexes();
  const fill = buildSwatchFill(hexes, materialFields.color.value, materialFields.color_hex.value);
  materialColorDot.style.setProperty("--swatch-fill", fill || "transparent");
  materialColorDot.style.setProperty("--swatch-color", hexes[0] || "transparent");
}

function updateMaterialColorDropdownLabel() {
  if (!materialColorDropdownLabel) return;
  const hexes = materialGradientHexes();
  if (!hexes.length) {
    materialColorDropdownLabel.textContent = "Choose hex colors";
    return;
  }
  materialColorDropdownLabel.textContent = hexes.length > 1 ? hexes.join(" / ") : hexes[0];
}

function setMaterialColorDropdownOpen(isOpen) {
  if (!materialColorDropdown || !materialColorDropdownTrigger || !materialColorDropdownMenu) {
    return;
  }
  materialColorDropdown.classList.toggle("is-open", isOpen);
  materialColorDropdownTrigger.setAttribute("aria-expanded", isOpen ? "true" : "false");
  materialColorDropdownMenu.hidden = !isOpen;
}

function collapseMaterialColorDropdownAfterInteraction() {
  window.setTimeout(() => {
    if (!materialColorDropdown || !materialColorDropdown.classList.contains("is-open")) {
      return;
    }
    const activeElement = document.activeElement;
    if (!activeElement || !materialColorDropdown.contains(activeElement)) {
      setMaterialColorDropdownOpen(false);
    }
  }, 0);
}

function syncMaterialColorModeUi() {
  materialColorSlots.forEach((slot, index) => {
    if (index === 0) {
      materialColorHexInputs[index].disabled = false;
      materialColorPickers[index].disabled = false;
      slot.classList.remove("is-disabled");
      return;
    }
    const enabled = Boolean(materialColorEnabledInputs[index]?.checked);
    materialColorHexInputs[index].disabled = !enabled;
    materialColorPickers[index].disabled = !enabled;
    slot.classList.toggle("is-disabled", !enabled);
  });
  updateMaterialColorPreview();
  updateMaterialColorDropdownLabel();
}

function syncMaterialColorInputs({ source, index } = {}) {
  const textInput = materialColorHexInputs[index];
  const pickerInput = materialColorPickers[index];
  if (!textInput || !pickerInput) return;
  if (source === "picker") {
    textInput.value = pickerInput.value.toUpperCase();
  } else if (source === "text") {
    const normalized = normalizeHexValue(textInput.value);
    if (normalized) {
      pickerInput.value = normalized;
    }
  }
  updateMaterialColorPreview();
  updateMaterialColorDropdownLabel();
}

function bindTap(button, handler) {
  if (!button || typeof handler !== "function") {
    return;
  }
  let lastTouchTime = 0;
  button.addEventListener(
    "touchend",
    (event) => {
      event.preventDefault();
      lastTouchTime = Date.now();
      handler(event);
    },
    { passive: false }
  );
  button.addEventListener("click", (event) => {
    if (Date.now() - lastTouchTime < 700) {
      event.preventDefault();
      return;
    }
    handler(event);
  });
}

function bindEvents() {
  refreshAllBtn.addEventListener("click", refreshAll);
  materialRefreshBtn.addEventListener("click", () => safeAsync(loadMaterials));
  inventoryRefreshBtn.addEventListener("click", () => safeAsync(loadInventory));
  if (modelsRefreshBtn) {
    modelsRefreshBtn.addEventListener("click", () => safeAsync(loadModels));
  }
  hardwareRefreshBtn.addEventListener("click", () => safeAsync(loadHardware));
  if (hardwareSyncMerchBtn) {
    hardwareSyncMerchBtn.addEventListener("click", () => safeAsync(syncMakerWorksMerch));
  }
  if (merchRefreshBtn) {
    merchRefreshBtn.addEventListener("click", () => safeAsync(loadHardware));
  }
  if (merchNewBtn) {
    merchNewBtn.addEventListener("click", startNewMerchEntry);
  }
  if (merchSyncBtn) {
    merchSyncBtn.addEventListener("click", () => safeAsync(syncMakerWorksMerch));
  }
  if (orderworksRefreshBtn) {
    orderworksRefreshBtn.addEventListener("click", () => safeAsync(loadOrderWorksJobs));
  }
  if (bambuViewRefreshBtn) {
    bambuViewRefreshBtn.addEventListener("click", () => safeAsync(loadBambuViewFilaments));
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
  if (merchForm) {
    merchForm.addEventListener("submit", handleMerchSubmit);
  }
  if (modelForm) {
    modelForm.addEventListener("submit", handleModelSubmit);
  }
  if (merchClearBtn) {
    merchClearBtn.addEventListener("click", resetMerchForm);
  }
  if (merchDeleteBtn) {
    merchDeleteBtn.addEventListener("click", () => {
      if (state.currentMerchId) {
        safeAsync(() => deleteMerch(state.currentMerchId));
      } else {
        setMessage("Select a merch row first.", "error");
      }
    });
  }
  materialColorHexInputs.forEach((input, index) => {
    input.addEventListener("input", () => syncMaterialColorInputs({ source: "text", index }));
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        setMaterialColorDropdownOpen(false);
      }
    });
  });
  materialColorPickers.forEach((input, index) => {
    input.addEventListener("input", () => syncMaterialColorInputs({ source: "picker", index }));
    input.addEventListener("change", collapseMaterialColorDropdownAfterInteraction);
  });
  materialColorEnabledInputs.forEach((input, index) => {
    if (index === 0) return;
    input.addEventListener("change", () => {
      syncMaterialColorModeUi();
      collapseMaterialColorDropdownAfterInteraction();
    });
  });
  if (materialColorDropdownTrigger) {
    materialColorDropdownTrigger.addEventListener("click", () => {
      const isOpen = materialColorDropdown?.classList.contains("is-open");
      setMaterialColorDropdownOpen(!isOpen);
    });
  }
  if (materialFields.color) {
    materialFields.color.addEventListener("input", updateMaterialColorPreview);
  }
  document.addEventListener("pointerdown", (event) => {
    if (!materialColorDropdown || !materialColorDropdown.classList.contains("is-open")) {
      return;
    }
    if (materialColorDropdown.contains(event.target)) {
      return;
    }
    setMaterialColorDropdownOpen(false);
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      setMaterialColorDropdownOpen(false);
    }
  });
  if (materialColorDropdown) {
    materialColorDropdown.addEventListener("focusout", collapseMaterialColorDropdownAfterInteraction);
  }
  materialTableBody.addEventListener("click", handleMaterialRowClick);
  if (materialsGallery) {
    materialsGallery.addEventListener("click", handleMaterialRowClick);
  }
  inventoryTableBody.addEventListener("click", handleInventoryRowClick);
  if (inventoryGallery) {
    inventoryGallery.addEventListener("click", handleInventoryRowClick);
  }
  hardwareTableBody.addEventListener("click", handleHardwareRowClick);
  if (merchTableBody) {
    merchTableBody.addEventListener("click", handleMerchRowClick);
  }
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
  if (materialsFilamentViewSelect) {
    materialsFilamentViewSelect.addEventListener("change", () => {
      filamentViewState.materials = normalizeFilamentViewMode(materialsFilamentViewSelect.value);
      storeFilamentViewMode("materials", filamentViewState.materials);
      renderMaterials();
      scrollFilamentSectionIntoView("materials");
    });
  }
  materialSortHeaders = Array.from(
    document.querySelectorAll("#materials-table thead th[data-sort-key]")
  );
  if (materialSortHeaders.length) {
    const handleMaterialSort = (key) => {
      if (!key) {
        return;
      }
      if (sortState.materials.key !== key) {
        sortState.materials.key = key;
        sortState.materials.direction = "asc";
      } else {
        sortState.materials.direction = sortState.materials.direction === "asc" ? "desc" : "asc";
      }
      paginationState.materials.page = 1;
      updateMaterialSortHeaders();
      renderMaterials();
    };
    materialSortHeaders.forEach((header) => {
      const key = header.dataset.sortKey;
      header.addEventListener("click", () => handleMaterialSort(key));
      header.addEventListener(
        "touchend",
        (event) => {
          event.preventDefault();
          handleMaterialSort(key);
        },
        { passive: false }
      );
    });
    updateMaterialSortHeaders();
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
  if (inventoryFilamentViewSelect) {
    inventoryFilamentViewSelect.addEventListener("change", () => {
      filamentViewState.inventory = normalizeFilamentViewMode(inventoryFilamentViewSelect.value);
      storeFilamentViewMode("inventory", filamentViewState.inventory);
      renderInventory();
      scrollFilamentSectionIntoView("inventory");
    });
  }
  if (modelsFilterSelect) {
    modelsFilterSelect.addEventListener("change", () => {
      filterState.models.mode = modelsFilterSelect.value || "all";
      paginationState.models.page = 1;
      renderModels();
    });
  }
  if (hardwareFilterSelect) {
    hardwareFilterSelect.addEventListener("change", () => {
      filterState.hardware.mode = hardwareFilterSelect.value || "all";
      paginationState.hardware.page = 1;
      renderHardware();
    });
  }
  if (merchSearchInput) {
    merchSearchInput.addEventListener("input", () => {
      filterState.merch.search = normalizeSearchTerm(merchSearchInput.value);
      renderMerch();
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
  if (modelMovementSelect) {
    modelMovementSelect.addEventListener("change", () => {
      const id = Number(modelMovementSelect.value);
      state.currentModelMovementId = Number.isFinite(id) ? id : null;
      if (state.currentModelMovementId) {
        safeAsync(() => loadModelMovements(state.currentModelMovementId));
      } else {
        renderModelMovements([]);
      }
    });
  }
  if (modelMovementForm) {
    modelMovementForm.addEventListener("submit", handleModelMovementSubmit);
  }
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
    bindTap(materialBarcodeScanBtn, () => {
      openBarcodeScanner({
        title: "Scan spool barcode",
        onDetected: (value) => {
          materialFields.barcode.value = value;
          setMessage(`Scanned spool barcode: ${value}`, "success");
        },
      });
    });
  }
  if (materialRefillBarcodeScanBtn) {
    bindTap(materialRefillBarcodeScanBtn, () => {
      openBarcodeScanner({
        title: "Scan refill barcode",
        onDetected: (value) => {
          materialFields.refill_barcode.value = value;
          setMessage(`Scanned refill barcode: ${value}`, "success");
        },
      });
    });
  }
  if (materialBarcodePrintBtn) {
    materialBarcodePrintBtn.addEventListener("click", () => {
      safeAsync(() => printMaterialBarcode(state.currentMaterialId));
    });
  }
  if (inventoryMaterialScanBtn) {
    bindTap(inventoryMaterialScanBtn, () => {
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
            const materialHexes = materialHexesForDisplay(match.material);
            const hexLabel = materialHexes.length ? materialHexes.join(" / ") : "";
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
          const materialHexes = materialHexesForDisplay(material);
          const hexLabel = materialHexes.length ? materialHexes.join(" / ") : "";
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

  let hasRefreshedForNewWorker = false;
  navigator.serviceWorker.addEventListener("controllerchange", () => {
    if (hasRefreshedForNewWorker) {
      return;
    }
    hasRefreshedForNewWorker = true;
    window.location.reload();
  });

  navigator.serviceWorker
    .register("/sw.js")
    .then((registration) => {
      console.info("Service worker registered:", registration.scope);
      registration.update().catch(() => null);
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
      loadMaterials({ suppressReports: true }),
      loadInventory({ suppressReports: true }),
      loadModels({ suppressReports: true }),
      loadHardware({ suppressReports: true }),
      loadOrderWorksJobs({ silent: true, suppressReports: true }).catch(() => null),
      loadBambuViewFilaments({ silent: true }).catch(() => null),
    ]);
    renderReports();
    setMessage("Data refreshed.", "success");
  } catch (error) {
    console.error(error);
    setMessage(error.message, "error");
  }
}

async function refreshReports() {
  await Promise.all([
    loadMaterials({ suppressReports: true }),
    loadInventory({ suppressReports: true }),
    loadModels({ suppressReports: true }),
    loadHardware({ suppressReports: true }),
    loadOrderWorksJobs({ silent: true, suppressReports: true }).catch(() => null),
    loadBambuViewFilaments({ silent: true }).catch(() => null),
  ]);
  renderReports();
  setMessage("Reports updated.", "success");
}

async function loadMaterials({ suppressReports = false } = {}) {
  const materials = await fetchAllPages("/materials");
  state.materials = asArray(materials);
  renderMaterials();
  populateMaterialOptions();
  if (state.currentMaterialId && !state.materials.some((m) => m.id === state.currentMaterialId)) {
    resetMaterialForm();
  }
  if (!suppressReports) {
    renderReports();
  }
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

async function loadInventory({ suppressReports = false } = {}) {
  const inventory = await fetchAllPages("/inventory");
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
      await loadMovements(state.currentMovementItemId, { suppressReports: true });
    } else {
      movementInventorySelect.value = "";
      state.currentMovementItemId = null;
      renderMovements([]);
    }
  }
  if (!suppressReports) {
    renderReports();
  }
}

async function loadModels({ suppressReports = false } = {}) {
  const models = await fetchAllPages("/models");
  state.models = models;
  renderModels();
  populateModelOptions();
  if (state.currentModelId && !models.some((model) => model.id === state.currentModelId)) {
    resetModelForm();
  }
  if (state.currentModelSaleId) {
    const stillExists = models.some((model) => model.id === state.currentModelSaleId);
    if (stillExists) {
      await loadModelSales(state.currentModelSaleId, { suppressReports: true });
    } else if (modelSaleSelect) {
      modelSaleSelect.value = "";
      state.currentModelSaleId = null;
      renderModelSales([]);
    }
  }
  if (state.currentModelMovementId) {
    const stillExists = models.some((model) => model.id === state.currentModelMovementId);
    if (stillExists) {
      await loadModelMovements(state.currentModelMovementId, { suppressReports: true });
    } else if (modelMovementSelect) {
      modelMovementSelect.value = "";
      state.currentModelMovementId = null;
      renderModelMovements([]);
    }
  }
  if (!suppressReports) {
    renderReports();
  }
}

async function loadHardware({ suppressReports = false } = {}) {
  const hardware = await fetchAllPages("/hardware");
  state.hardware = hardware;
  renderHardware();
  renderMerch();
  populateHardwareOptions();
  if (state.currentHardwareId && !hardware.some((item) => item.id === state.currentHardwareId)) {
    resetHardwareForm();
  }
  if (state.currentMerchId && !hardware.some((item) => item.id === state.currentMerchId)) {
    resetMerchForm();
  }
  if (state.currentHardwareMovementId) {
    const stillExists = hardware.some((item) => item.id === state.currentHardwareMovementId);
    if (stillExists) {
      await loadHardwareMovements(state.currentHardwareMovementId, { suppressReports: true });
    } else {
      hardwareMovementSelect.value = "";
      state.currentHardwareMovementId = null;
      renderHardwareMovements([]);
    }
  }
  if (!suppressReports) {
    renderReports();
  }
}

async function loadOrderWorksJobs({ silent = false, suppressReports = false } = {}) {
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
  if (!suppressReports) {
    renderReports();
  }
}

async function syncMakerWorksMerch() {
  const payload = await api("/makerworks/merch/sync", { method: "POST" });
  await loadHardware();
  const created = Number(payload?.created || 0);
  const updated = Number(payload?.updated || 0);
  const skipped = Number(payload?.skipped || 0);
  setMessage(
    `MakerWorks merch sync complete. Created: ${created}, updated: ${updated}, skipped: ${skipped}.`,
    "success"
  );
}

async function loadBambuViewFilaments({ silent = false } = {}) {
  const shouldFetch = bambuViewTableBody || bambuViewStatusEl;
  if (!shouldFetch) {
    return;
  }
  try {
    const payload = await api("/printlab/filaments");
    state.bambuViewPrinters = Array.isArray(payload.printers) ? payload.printers : [];
    state.bambuViewLoadedCount = Number(payload.loaded_count || 0);
    state.bambuViewError = null;
    state.bambuViewConfigured = true;
    state.bambuViewBaseUrl = typeof payload.base_url === "string" ? payload.base_url : "";
  } catch (error) {
    console.error(error);
    state.bambuViewPrinters = [];
    state.bambuViewLoadedCount = 0;
    state.bambuViewBaseUrl = "";
    state.bambuViewError = error && error.message ? error.message : "Unable to sync PrintLab filament data.";
    state.bambuViewConfigured = error && Number(error.status) === 503 ? false : true;
    if (!silent) {
      setMessage(state.bambuViewError, "error");
    }
  }
  renderBambuView();
}

async function loadMovements(itemId, { suppressReports = false } = {}) {
  const results = await api(`/inventory/${itemId}/movements`);
  state.lastInventoryMovements = Array.isArray(results) ? results : [];
  renderMovements(results);
  if (!suppressReports) {
    renderReports();
  }
}

function formatColorChip(colorName, colorHex, colorHexes = []) {
  const normalizedHexes = resolveColorHexes(colorHexes, colorHex, colorName);
  const hex = normalizeHexValue(colorHex) || normalizedHexes[0] || "";
  const hexLabelValue = normalizedHexes.length > 1 ? normalizedHexes.join(" / ") : hex;
  const swatchFill = buildSwatchFill(normalizedHexes, colorName, colorHex);
  const nameLabel = colorName ? `<span>${escapeHtml(colorName)}</span>` : "";
  const hexLabel = hexLabelValue
    ? `<span class="color-hex">${escapeHtml(hexLabelValue)}</span>`
    : `<span class="color-hex muted">No hex</span>`;
  const dot = `<span class="color-dot" style="--swatch-fill: ${swatchFill}; --swatch-color: ${
    normalizedHexes[0] || hex || "transparent"
  }" aria-hidden="true"></span>`;
  return `<span class="color-chip">${dot}${nameLabel}${hexLabel}</span>`;
}

function formatColorDots(colorName, colorHex, colorHexes = []) {
  const normalizedHexes = resolveColorHexes(colorHexes, colorHex, colorName);
  const swatches = normalizedHexes.length
    ? normalizedHexes
    : [resolveSwatchColor(colorName, colorHex)].filter((value) => Boolean(value));
  if (!swatches.length) {
    return `<span class="muted">No color</span>`;
  }
  const dots = swatches
    .map(
      (hex) =>
        `<span class="color-dot" style="--swatch-fill: ${hex}; --swatch-color: ${hex}" aria-hidden="true"></span>`
    )
    .join("");
  return `<span class="color-dot-list">${dots}</span>`;
}

function formatFilamentHero(colorName, colorHex, colorHexes = [], fallbackLabel = "No color") {
  const normalizedHexes = resolveColorHexes(colorHexes, colorHex, colorName);
  const primary = normalizedHexes[0] || resolveSwatchColor(colorName, colorHex) || "";
  const fill = buildSwatchFill(normalizedHexes, colorName, colorHex);
  const hasColor = Boolean(primary || fill);
  const label = colorName ? escapeHtml(colorName) : escapeHtml(fallbackLabel);
  const noColorClass = hasColor ? "" : " is-empty";
  return `
    <div class="filament-hero${noColorClass}">
      <div class="filament-roll" style="--swatch-fill: ${fill || primary || "transparent"}; --swatch-color: ${primary || "transparent"}" aria-hidden="true">
        <span class="filament-roll-core"></span>
      </div>
      <div class="filament-hero-label">${label}</div>
    </div>`;
}

function formatFilamentColorDisplay(colorName, colorHex, colorHexes, mode = "chip") {
  return mode === "dots"
    ? formatColorDots(colorName, colorHex, colorHexes)
    : formatColorChip(colorName, colorHex, colorHexes);
}

function formatMaterialLabel(material, mode = "chip") {
  if (!material) return "Unknown";
  const name = escapeHtml(material.name);
  const colorDisplay = formatFilamentColorDisplay(
    material.color,
    material.color_hex,
    materialHexesForDisplay(material),
    mode
  );
  return `<span>${name}</span> ${colorDisplay}`;
}

function materialInventorySummary(materialId) {
  const matching = state.inventory.filter((item) => Number(item.material_id) === Number(materialId));
  const quantity = matching.reduce((sum, item) => sum + Number(item.quantity_grams || 0), 0);
  return {
    count: matching.length,
    quantity,
  };
}

function materialSpoolPrice(material) {
  const pricePerGram = Number(material?.price_per_gram || 0);
  const spoolWeight = Number(material?.spool_weight_grams || 0);
  if (!Number.isFinite(pricePerGram) || !Number.isFinite(spoolWeight) || spoolWeight <= 0) {
    return 0;
  }
  return pricePerGram * spoolWeight;
}

function setElementHiddenState(element, hidden) {
  if (!element) {
    return;
  }
  element.hidden = hidden;
  element.setAttribute("aria-hidden", hidden ? "true" : "false");
}

function syncFilamentSectionView(section, mode) {
  const isGallery = mode === "gallery";
  if (section === "materials") {
    setElementHiddenState(materialsTableWrapper, isGallery);
    setElementHiddenState(materialsGallery, !isGallery);
    return;
  }
  if (section === "inventory") {
    setElementHiddenState(inventoryTableWrapper, isGallery);
    setElementHiddenState(inventoryGallery, !isGallery);
  }
}

function scrollFilamentSectionIntoView(section) {
  const target = section === "materials"
    ? document.getElementById("materials-controls")
    : section === "inventory"
      ? document.getElementById("inventory-controls")
      : null;
  if (!target) {
    return;
  }
  requestAnimationFrame(() => {
    target.scrollIntoView({ block: "start", behavior: "auto" });
  });
}

function normalizeSearchTerm(value) {
  return String(value || "").trim().toLowerCase();
}

function matchesSearch(needle, values) {
  if (!needle) return true;
  return values.some((value) => String(value || "").toLowerCase().includes(needle));
}

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function memoizedArray(cacheKey, sourceItems, signature, compute) {
  const cached = derivedViewCache[cacheKey];
  if (cached && cached.sourceItems === sourceItems && cached.signature === signature) {
    return cached.result;
  }
  const result = compute();
  derivedViewCache[cacheKey] = { sourceItems, signature, result };
  return result;
}

function filterMaterials(items) {
  const materialItems = asArray(items);
  const search = filterState.materials.search;
  return memoizedArray("materialsFilter", materialItems, search || "", () => {
    if (!search) {
      return materialItems;
    }
    return materialItems.filter((material) =>
      matchesSearch(search, [
        material.name,
        material.brand,
        material.filament_type,
        material.category,
        material.color,
        material.color_hex,
        materialHexesForDisplay(material).join(" "),
        material.supplier,
        material.barcode,
        material.notes,
      ])
    );
  });
}

function compareText(a, b) {
  return String(a || "").localeCompare(String(b || ""), undefined, {
    numeric: true,
    sensitivity: "base",
  });
}

function getMaterialSortValue(material, key) {
  switch (key) {
    case "price_per_gram":
      return Number(material.price_per_gram || 0);
    case "spool_price":
      return materialSpoolPrice(material);
    case "spool_weight_grams":
      return Number(material.spool_weight_grams || 0);
    case "filament_type":
      return material.filament_type;
    case "name":
      return material.name;
    case "brand":
      return material.brand;
    case "category":
      return material.category;
    case "color":
      return material.color;
    case "supplier":
      return material.supplier;
    case "barcode":
      return material.barcode;
    default:
      return material[key];
  }
}

function sortMaterials(items) {
  const materialItems = asArray(items);
  const { key, direction } = sortState.materials;
  const signature = `${key || ""}:${direction || "asc"}`;
  return memoizedArray("materialsSort", materialItems, signature, () => {
    if (!key) {
      return materialItems;
    }
    const directionFactor = direction === "desc" ? -1 : 1;
    const sorted = [...materialItems];
    sorted.sort((a, b) => {
      const aValue = getMaterialSortValue(a, key);
      const bValue = getMaterialSortValue(b, key);
      let comparison = 0;
      if (typeof aValue === "number" && typeof bValue === "number") {
        comparison = aValue - bValue;
      } else {
        comparison = compareText(aValue, bValue);
      }
      if (comparison !== 0) {
        return comparison * directionFactor;
      }
      return compareText(a.name, b.name) * directionFactor;
    });
    return sorted;
  });
}

function updateMaterialSortHeaders() {
  if (!materialSortHeaders.length) {
    return;
  }
  materialSortHeaders.forEach((header) => {
    header.classList.remove("sort-asc", "sort-desc");
    header.setAttribute("aria-sort", "none");
    const key = header.dataset.sortKey;
    if (!key || key !== sortState.materials.key) {
      return;
    }
    if (sortState.materials.direction === "desc") {
      header.classList.add("sort-desc");
      header.setAttribute("aria-sort", "descending");
    } else {
      header.classList.add("sort-asc");
      header.setAttribute("aria-sort", "ascending");
    }
  });
}

function filterInventory(items) {
  const material = filterState.inventory.material;
  const color = filterState.inventory.color;
  const location = filterState.inventory.location;
  const signature = `${material}|${color}|${location}`;
  return memoizedArray("inventoryFilter", items, signature, () => {
    let filtered = items.filter((item) => isFilamentInventoryItem(item));
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
  });
}

function isFilamentInventoryItem(item) {
  if (!item || typeof item !== "object") {
    return false;
  }
  const location = normalizeSearchTerm(item.location);
  return !NON_FILAMENT_INVENTORY_LOCATIONS.has(location);
}

function filterModels(items) {
  const mode = filterState.models.mode;
  return memoizedArray("modelsFilter", items, mode || "all", () => {
    let filtered = items;
    if (mode === "active") {
      filtered = filtered.filter((model) => model.active);
    } else if (mode === "inactive") {
      filtered = filtered.filter((model) => !model.active);
    }
    return filtered;
  });
}

function filterHardware(items) {
  const mode = filterState.hardware.mode;
  return memoizedArray("hardwareFilter", items, mode || "all", () => {
    let filtered = items;
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
  });
}

function filterMovements(movements) {
  const mode = filterState.movements.mode;
  let filtered = movements;
  if (mode !== "all") {
    filtered = filtered.filter((move) => move.movement_type === mode);
  }
  return filtered;
}

function isMerchItem(item) {
  if (!item || typeof item !== "object") {
    return false;
  }
  const category = normalizeSearchTerm(item.category);
  if (category === "merch") {
    return true;
  }
  return Boolean(item.makerworks_product_template_id);
}

function filterMerch(items) {
  const search = filterState.merch.search;
  const merchItems = items.filter((item) => isMerchItem(item));
  if (!search) {
    return merchItems;
  }
  return merchItems.filter((item) =>
    matchesSearch(search, [
      item.name,
      item.category,
      item.merch_color,
      item.merch_size,
      item.merch_style,
      item.merch_sku,
      item.bin_location,
      item.notes,
      item.supplier,
      item.manufacturer_part_number,
      item.makerworks_product_template_id,
    ])
  );
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

function populateInventoryFilters() {
  if (!inventoryMaterialFilter || !inventoryColorFilter || !inventoryLocationFilter) {
    return;
  }
  const inventoryItems = state.inventory.filter((item) => isFilamentInventoryItem(item));
  const materials = buildFilterOptions(inventoryItems.map((item) => item.material?.name));
  const colors = buildFilterOptions(inventoryItems.map((item) => item.material?.color));
  const locations = buildFilterOptions(inventoryItems.map((item) => item.location));

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
  const sorted = sortMaterials(filtered);
  const { items, total, startIndex, endIndex, maxPage } = paginate(sorted, paginationState.materials);
  const viewMode = normalizeFilamentViewMode(filamentViewState.materials);
  syncFilamentSectionView("materials", viewMode);
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
  if (viewMode === "gallery") {
    if (!materialsGallery) {
      return;
    }
    if (!state.materials.length) {
      materialsGallery.innerHTML = `<div class="muted">No materials yet.</div>`;
      return;
    }
    if (!filtered.length) {
      materialsGallery.innerHTML = `<div class="muted">No matches for the current search or filter.</div>`;
      return;
    }
    materialsGallery.innerHTML = items
      .map((material) => {
        const summary = materialInventorySummary(material.id);
        const spoolWeight = Math.max(Number(material.spool_weight_grams || 0), 1);
        const slotCount = Math.max(summary.count, 1);
        const maxCapacity = Math.max(spoolWeight * slotCount, summary.quantity, 1);
        const value = Math.max(0, summary.quantity);
        const lowThreshold = Math.min(maxCapacity, spoolWeight);
        const barcodeAction = material.barcode || material.refill_barcode
          ? `<button class="small-button" data-action="print-barcode" data-id="${material.id}">Print</button>`
          : "";
        return `
          <article class="filament-card" data-id="${material.id}">
            <div class="filament-card-swatch">${formatFilamentHero(
              material.color,
              material.color_hex,
              materialHexesForDisplay(material),
              "No color"
            )}</div>
            <div class="filament-card-title">${escapeHtml(material.name)}</div>
            <div class="filament-card-meta">
              <span>${escapeHtml(material.brand || "Unknown brand")}</span>
              <span>${escapeHtml(material.filament_type || "-")}</span>
              <span>${escapeHtml(material.category || "-")}</span>
            </div>
            <div class="filament-card-meter-wrap">
              <meter min="0" max="${maxCapacity.toFixed(2)}" value="${value.toFixed(2)}" low="${lowThreshold.toFixed(2)}"></meter>
              <div class="filament-card-meter-label">${value.toFixed(2)} g in inventory across ${slotCount} spool(s)</div>
            </div>
            <div class="filament-card-actions">
              <button class="small-button" data-action="edit" data-id="${material.id}">Edit</button>
              ${barcodeAction}
              <button class="small-button danger" data-action="delete" data-id="${material.id}">Delete</button>
            </div>
          </article>`;
      })
      .join("");
    return;
  }

  if (!state.materials.length) {
    materialTableBody.innerHTML = `<tr><td colspan="10" class="muted">No materials yet.</td></tr>`;
    return;
  }
  if (!filtered.length) {
    materialTableBody.innerHTML = `<tr><td colspan="10" class="muted">No matches for the current search or filter.</td></tr>`;
    return;
  }
  materialTableBody.innerHTML = items
    .map((material) => {
      const hasRefillBarcode = Boolean(optionalString(material.refill_barcode || ""));
      const barcodeValues = [];
      const seenBarcodes = new Set();
      [material.barcode, material.refill_barcode].forEach((value) => {
        const raw = optionalString(value || "");
        if (!raw) return;
        const normalized = normalizeBarcode(raw);
        if (!normalized || seenBarcodes.has(normalized)) return;
        seenBarcodes.add(normalized);
        barcodeValues.push(raw);
      });
      const barcodeDisplay = barcodeValues.length
        ? barcodeValues.map((value) => `<span class="barcode-value">${escapeHtml(value)}</span>`).join("")
        : `<span class="muted">-</span>`;
      const barcodeAction = material.barcode || hasRefillBarcode
        ? `<button class="small-button" data-action="print-barcode" data-id="${material.id}">Print</button>`
        : "";
      return `
        <tr data-id="${material.id}">
          <td>${escapeHtml(material.name)}</td>
          <td>${escapeHtml(material.brand || "")}</td>
          <td>${escapeHtml(material.filament_type)}</td>
          <td>${escapeHtml(material.category || "")}</td>
          <td>${formatColorChip(material.color, material.color_hex, materialHexesForDisplay(material))}</td>
          <td>${formatCurrency(materialSpoolPrice(material))}</td>
          <td>${material.spool_weight_grams}</td>
          <td>${escapeHtml(material.supplier || "")}</td>
          <td>
            <div class="barcode-cell">
              ${barcodeDisplay}
              ${barcodeAction}
            </div>
          </td>
          <td>
            <button class="small-button" data-action="edit" data-id="${material.id}">Edit</button>
            <button class="small-button danger" data-action="delete" data-id="${material.id}">Delete</button>
          </td>
        </tr>`;
    })
    .join("");
}

function renderInventory() {
  const filtered = filterInventory(state.inventory);
  const { items, total, startIndex, endIndex, maxPage } = paginate(filtered, paginationState.inventory);
  const viewMode = normalizeFilamentViewMode(filamentViewState.inventory);
  syncFilamentSectionView("inventory", viewMode);
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
  if (viewMode === "gallery") {
    if (!inventoryGallery) {
      return;
    }
    if (!state.inventory.length) {
      inventoryGallery.innerHTML = `<div class="muted">No inventory tracked yet.</div>`;
      return;
    }
    if (!filtered.length) {
      inventoryGallery.innerHTML = `<div class="muted">No matches for the current search or filter.</div>`;
      return;
    }
    inventoryGallery.innerHTML = items
      .map((item) => {
        const quantity = Math.max(0, Number(item.quantity_grams || 0));
        const reorder = Math.max(0, Number(item.reorder_level || 0));
        const spoolWeight = Math.max(0, Number(item.material?.spool_weight_grams || 0));
        const maxGauge = Math.max(quantity, spoolWeight, reorder * 2, 1);
        const lowThreshold = Math.min(maxGauge, reorder);
        const optimum = Math.min(maxGauge, Math.max(spoolWeight, reorder));
        return `
          <article class="filament-card" data-id="${item.id}">
            <div class="filament-card-swatch">${formatFilamentHero(
              item.material?.color,
              item.material?.color_hex,
              materialHexesForDisplay(item.material),
              "No color"
            )}</div>
            <div class="filament-card-title">${escapeHtml(item.material?.name || "Unknown material")}</div>
            <div class="filament-card-meta">
              <span>${escapeHtml(item.location || "-")}</span>
              <span>${escapeHtml(item.material?.filament_type || "-")}</span>
              <span>${item.spool_serial ? escapeHtml(item.spool_serial) : "No serial"}</span>
            </div>
            <div class="filament-card-meter-wrap">
              <meter
                min="0"
                max="${maxGauge.toFixed(2)}"
                value="${quantity.toFixed(2)}"
                low="${lowThreshold.toFixed(2)}"
                optimum="${optimum.toFixed(2)}"
              ></meter>
              <div class="filament-card-meter-label">${quantity.toFixed(2)} g available - Reorder ${reorder.toFixed(2)} g</div>
            </div>
            <div class="filament-card-actions">
              <button class="small-button" data-action="edit" data-id="${item.id}">Edit</button>
              <button class="small-button danger" data-action="delete" data-id="${item.id}">Delete</button>
            </div>
          </article>`;
      })
      .join("");
    return;
  }

  if (!state.inventory.length) {
    inventoryTableBody.innerHTML = `<tr><td colspan="7" class="muted">No inventory tracked yet.</td></tr>`;
    return;
  }
  if (!filtered.length) {
    inventoryTableBody.innerHTML = `<tr><td colspan="7" class="muted">No matches for the current search or filter.</td></tr>`;
    return;
  }
  inventoryTableBody.innerHTML = items
    .map((item) => {
      const materialLabel = formatMaterialLabel(item.material);
      return `
        <tr data-id="${item.id}">
          <td>${materialLabel}</td>
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
    modelsTableBody.innerHTML = `<tr><td colspan="9" class="muted">No models tracked yet.</td></tr>`;
    return;
  }
  if (!filtered.length) {
    modelsTableBody.innerHTML = `<tr><td colspan="9" class="muted">No matches for the current search or filter.</td></tr>`;
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
          <td>${Number(model.quantity_on_hand || 0).toFixed(2)}</td>
          <td>${status}</td>
          <td>${formatQuantity(model.total_sold || 0)}</td>
          <td>${formatCurrency(model.total_revenue || 0)}</td>
          <td>
            <button class="small-button" data-action="edit" data-id="${model.id}">Edit</button>
            <button class="small-button" data-action="move" data-id="${model.id}">Move</button>
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

function renderMerch() {
  if (!merchTableBody) {
    return;
  }
  const filtered = filterMerch(state.hardware);
  if (!state.hardware.some((item) => isMerchItem(item))) {
    merchTableBody.innerHTML = `<tr><td colspan="10" class="muted">No merch inventory recorded yet. Run MakerWorks merch sync first.</td></tr>`;
    return;
  }
  if (!filtered.length) {
    merchTableBody.innerHTML = `<tr><td colspan="10" class="muted">No merch matches your search.</td></tr>`;
    return;
  }
  merchTableBody.innerHTML = filtered
    .map(
      (item) => `
        <tr data-id="${item.id}">
          <td>${escapeHtml(item.name)}</td>
          <td>${escapeHtml(item.category || "")}</td>
          <td>${item.merch_color ? formatColorChip(item.merch_color, item.merch_color) : ""}</td>
          <td>${escapeHtml(item.merch_size || "")}</td>
          <td>${Number(item.quantity_on_hand || 0).toFixed(2)}</td>
          <td>${Number(item.reorder_level || 0).toFixed(2)}</td>
          <td>${escapeHtml(item.unit_of_measure || "piece")}</td>
          <td>${escapeHtml(item.bin_location || "")}</td>
          <td>${escapeHtml(item.notes || "")}</td>
          <td>
            <button class="small-button" data-action="edit" data-id="${item.id}">Edit</button>
            <button class="small-button" data-action="move" data-id="${item.id}">Move</button>
            <button class="small-button danger" data-action="delete" data-id="${item.id}">Delete</button>
          </td>
        </tr>`
    )
    .join("");
}

function renderBambuView() {
  if (bambuViewStatusEl) {
    if (!state.bambuViewConfigured) {
      bambuViewStatusEl.textContent =
        "PrintLab integration is not configured. Set PRINTLAB_BASE_URL to load active filaments.";
      bambuViewStatusEl.classList.remove("error");
      bambuViewStatusEl.classList.add("muted");
    } else if (state.bambuViewError) {
      bambuViewStatusEl.textContent = state.bambuViewError;
      bambuViewStatusEl.classList.add("error");
      bambuViewStatusEl.classList.remove("muted");
    } else {
      const printerCount = state.bambuViewPrinters.length;
      const trayCount = state.bambuViewLoadedCount;
      const source = state.bambuViewBaseUrl ? ` from ${state.bambuViewBaseUrl}` : "";
      bambuViewStatusEl.textContent = `Loaded trays: ${trayCount} across ${printerCount} printer${
        printerCount === 1 ? "" : "s"
      }${source}.`;
      bambuViewStatusEl.classList.remove("error");
      bambuViewStatusEl.classList.add("muted");
    }
  }

  if (!bambuViewTableBody) {
    return;
  }
  if (!state.bambuViewConfigured) {
    bambuViewTableBody.innerHTML = `<tr><td colspan="6" class="muted">Configure PRINTLAB_* settings to sync loaded filaments.</td></tr>`;
    return;
  }
  if (state.bambuViewError) {
    bambuViewTableBody.innerHTML = `<tr><td colspan="6" class="muted">${escapeHtml(state.bambuViewError)}</td></tr>`;
    return;
  }

  const rows = [];
  for (const printer of state.bambuViewPrinters) {
    const loaded = Array.isArray(printer.loaded_trays) ? printer.loaded_trays : [];
    if (!loaded.length) {
      const slotCount = Number(printer.ams_slots);
      const unitCount = Number(printer.ams_units);
      const hints = [];
      if (Number.isFinite(slotCount)) {
        hints.push(`slots: ${slotCount}`);
      }
      if (Number.isFinite(unitCount)) {
        hints.push(`units: ${unitCount}`);
      }
      const stateLabel = hints.length ? `No loaded trays (${hints.join(", ")})` : "No loaded trays";
      rows.push(`
        <tr>
          <td>${escapeHtml(printer.printer_name || printer.printer_id || "Printer")}</td>
          <td><span class="muted">-</span></td>
          <td><span class="muted">-</span></td>
          <td><span class="muted">-</span></td>
          <td><span class="muted">-</span></td>
          <td><span class="muted">${escapeHtml(stateLabel)}</span></td>
        </tr>
      `);
      continue;
    }
    for (const tray of loaded) {
      const position =
        Number.isFinite(Number(tray.unit)) && Number.isFinite(Number(tray.slot)) ? `U${tray.unit} S${tray.slot}` : "-";
      const trayHexes = resolveColorHexes(tray.colors, tray.color);
      const colorLabel = trayHexes.length
        ? formatColorChip("", tray.color, trayHexes)
        : `<span class="muted">-</span>`;
      rows.push(`
        <tr>
          <td>${escapeHtml(printer.printer_name || printer.printer_id || "Printer")}</td>
          <td>${escapeHtml(position)}</td>
          <td>${escapeHtml(tray.material || "-")}</td>
          <td>${escapeHtml(tray.name || "-")}</td>
          <td>${colorLabel}</td>
          <td>${escapeHtml(tray.state || "-")}</td>
        </tr>
      `);
    }
  }
  if (!rows.length && state.bambuViewPrinters.length) {
    bambuViewTableBody.innerHTML = `<tr><td colspan="6" class="muted">No printer details reported by PrintLab.</td></tr>`;
    return;
  }
  if (!rows.length) {
    bambuViewTableBody.innerHTML = `<tr><td colspan="6" class="muted">No PrintLab data loaded yet.</td></tr>`;
    return;
  }
  bambuViewTableBody.innerHTML = rows.join("");
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
      const hexes = materialHexesForDisplay(material);
      const hexLabel = hexes.length ? ` • ${hexes.join(" / ")}` : "";
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
  const inventoryItems = state.inventory.filter((item) => isFilamentInventoryItem(item));
  const options = inventoryItems
    .map((item) => {
      if (!item.material) {
        return `<option value="${item.id}">Item ${item.id}</option>`;
      }
      const hexes = materialHexesForDisplay(item.material);
      const hexLabel = hexes.length ? ` • ${hexes.join(" / ")}` : "";
      const label = `${item.material.name} (${item.material.color}${hexLabel}) – ${item.location}`;
      return `<option value="${item.id}">${escapeHtml(label)}</option>`;
    })
    .join("");
  const currentValue = movementInventorySelect.value;
  movementInventorySelect.innerHTML = `<option value="">Select inventory item...</option>${options}`;
  if (options && currentValue && inventoryItems.some((i) => String(i.id) === currentValue)) {
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
  if (!modelSaleSelect && !modelMovementSelect) {
    return;
  }
  const options = state.models
    .map((model) => {
      const label = model.sku ? `${model.name} ƒ?" ${model.sku}` : model.name;
      return `<option value="${model.id}">${escapeHtml(label)}</option>`;
    })
    .join("");
  if (modelSaleSelect) {
    const currentValue = modelSaleSelect.value;
    modelSaleSelect.innerHTML = `<option value="">Select model...</option>${options}`;
    if (options && currentValue && state.models.some((model) => String(model.id) === currentValue)) {
      modelSaleSelect.value = currentValue;
    }
  }
  if (modelMovementSelect) {
    const currentValue = modelMovementSelect.value;
    modelMovementSelect.innerHTML = `<option value="">Select model...</option>${options}`;
    if (options && currentValue && state.models.some((model) => String(model.id) === currentValue)) {
      modelMovementSelect.value = currentValue;
    }
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
      if (state.currentMaterialId) {
        loadMaterialCostHistory(state.currentMaterialId);
      }
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
    if (state.currentModelMovementId === modelId || modelMovementSelect?.value === String(modelId)) {
      await loadModelMovements(modelId);
    }
    showToast("Model sale logged.", "success");
  } catch (error) {
    console.error(error);
    setMessage(error.message, "error");
  }
}

async function handleModelMovementSubmit(event) {
  event.preventDefault();
  try {
    const modelId = Number(modelMovementSelect.value);
    if (!Number.isFinite(modelId)) {
      setMessage("Select a model first.", "error");
      return;
    }
    let change = Number(modelMovementChange.value);
    if (!Number.isFinite(change) || change === 0) {
      setMessage("Change value must be non-zero.", "error");
      return;
    }
    if (modelMovementType.value === "incoming") {
      change = Math.abs(change);
    } else if (modelMovementType.value === "outgoing") {
      change = -Math.abs(change);
    }
    const payload = {
      model_id: modelId,
      movement_type: modelMovementType.value,
      change_units: change,
      reference: optionalString(modelMovementReference.value),
      note: optionalString(modelMovementNote.value),
    };
    await api("/models/movements", { method: "POST", body: payload });
    modelMovementChange.value = "";
    modelMovementReference.value = "";
    modelMovementNote.value = "";
    await loadModels();
    await loadModelMovements(modelId);
    showToast("Model movement logged.", "success");
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
  } else if (button.dataset.action === "print-barcode") {
    safeAsync(() => printMaterialBarcode(id));
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
  } else if (button.dataset.action === "move") {
    startModelMovementEntry(id);
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
  const materialHexes = materialHexesForDisplay(material);
  materialColorEnabledInputs.forEach((input, index) => {
    if (index === 0) return;
    input.checked = index < materialHexes.length;
  });
  materialColorHexInputs.forEach((input, index) => {
    input.value = materialHexes[index] || "";
  });
  materialFields.supplier.value = material.supplier || "";
  materialFields.brand.value = material.brand || "";
  materialFields.price_per_gram.value = materialSpoolPrice(material).toFixed(2);
  materialFields.spool_weight_grams.value = material.spool_weight_grams;
  materialFields.barcode.value = material.barcode || "";
  materialFields.refill_barcode.value = material.refill_barcode || "";
  materialFields.notes.value = material.notes || "";
  updateMaterialColorRequirement();
  syncMaterialColorModeUi();
  materialColorHexInputs.forEach((_, index) => syncMaterialColorInputs({ source: "text", index }));
  setMaterialColorDropdownOpen(false);
  loadMaterialCostHistory(id);
}

async function handleMerchSubmit(event) {
  event.preventDefault();
  try {
    const payload = buildMerchPayload();
    if (!payload) return;
    if (state.currentMerchId) {
      await api(`/hardware/${state.currentMerchId}`, { method: "PUT", body: payload });
    } else {
      const created = await api("/hardware", { method: "POST", body: payload });
      if (created && Number.isFinite(Number(created.id))) {
        state.currentMerchId = Number(created.id);
        merchIdInput.value = String(created.id);
      }
    }
    await loadHardware();
    showToast("Merch saved.", "success");
  } catch (error) {
    console.error(error);
    setMessage(error.message, "error");
  }
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
  const row = inventoryTableBody.querySelector(`tr[data-id="${id}"]`);
  if (!row) return;
  inventoryTableBody.querySelectorAll("tr.is-highlighted").forEach((el) => el.classList.remove("is-highlighted"));
  row.classList.add("is-highlighted");
  row.scrollIntoView({ behavior: "smooth", block: "center", inline: "nearest" });
}

function startHardwareEdit(id) {
  const item = state.hardware.find((hardware) => hardware.id === id);
  if (!item) return;
  state.currentHardwareId = id;
  hardwareIdInput.value = id;
  hardwareFields.name.value = item.name;
  hardwareFields.category.value = item.category || "";
  hardwareFields.merch_color.value = item.merch_color || "";
  hardwareFields.merch_size.value = item.merch_size || "";
  hardwareFields.merch_style.value = item.merch_style || "";
  hardwareFields.merch_sku.value = item.merch_sku || "";
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
  modelFields.quantity_on_hand.value = model.quantity_on_hand ?? 0;
  modelFields.active.value = model.active ? "true" : "false";
  modelFields.notes.value = model.notes || "";
  if (modelMovementSelect) {
    modelMovementSelect.value = String(id);
    state.currentModelMovementId = id;
    safeAsync(() => loadModelMovements(id));
  }
  if (modelSaleSelect) {
    modelSaleSelect.value = String(id);
    state.currentModelSaleId = id;
    safeAsync(() => loadModelSales(id));
  }
}

function startModelMovementEntry(id) {
  const model = state.models.find((item) => item.id === id);
  if (!model || !modelMovementSelect) return;
  modelMovementSelect.value = String(id);
  state.currentModelMovementId = id;
  safeAsync(() => loadModelMovements(id));
  if (modelMovementChange) {
    modelMovementChange.focus();
    modelMovementChange.select();
  }
}

async function deleteMaterial(id) {
  if (!confirm("Delete this material and all related records?")) {
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
  const normalizedHexes = materialGradientHexes();
  if (!normalizedHexes.length) {
    setMessage("Provide at least one valid hex color for the material.", "error");
    return null;
  }
  const spoolPrice = Number(materialFields.price_per_gram.value);
  const spool = Number(materialFields.spool_weight_grams.value);
  if (!Number.isFinite(spoolPrice) || spoolPrice <= 0 || !Number.isFinite(spool) || spool <= 0) {
    setMessage("Spool price and spool weight must be positive numbers.", "error");
    return null;
  }
  const pricePerGram = spoolPrice / spool;
  return {
    name: materialFields.name.value.trim(),
    filament_type: materialFields.filament_type.value.trim(),
    category: optionalString(materialFields.category.value),
    color: materialFields.color.value.trim(),
    color_hex: normalizedHexes[0] || null,
    color_hexes: normalizedHexes.length > 1 ? normalizedHexes : null,
    supplier: optionalString(materialFields.supplier.value),
    brand: optionalString(materialFields.brand.value),
    price_per_gram: pricePerGram,
    spool_weight_grams: Math.round(spool),
    barcode: optionalString(normalizeBarcode(materialFields.barcode.value)),
    refill_barcode: optionalString(normalizeBarcode(materialFields.refill_barcode.value)),
    notes: optionalString(materialFields.notes.value),
  };
}

async function deleteMerch(id) {
  if (!confirm("Delete this merch item and its movements?")) {
    return;
  }
  try {
    await api(`/hardware/${id}`, { method: "DELETE" });
    if (state.currentMerchId === id) {
      resetMerchForm();
    }
    if (state.currentHardwareId === id) {
      resetHardwareForm();
    }
    await loadHardware();
    setMessage("Merch deleted.", "success");
  } catch (error) {
    console.error(error);
    setMessage(error.message, "error");
  }
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
    spool_serial: optionalString(normalizeBarcode(inventoryFields.spool_serial.value)),
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
    merch_color: optionalString(hardwareFields.merch_color.value),
    merch_size: optionalString(hardwareFields.merch_size.value),
    merch_style: optionalString(hardwareFields.merch_style.value),
    merch_sku: optionalString(hardwareFields.merch_sku.value),
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
  const quantityValue = modelFields.quantity_on_hand.value;
  const quantityOnHand = quantityValue.trim() === "" ? 0 : Number(quantityValue);
  if (!Number.isFinite(unitPrice) || unitPrice < 0) {
    setMessage("Unit price must be a positive number.", "error");
    return null;
  }
  if (!Number.isFinite(quantityOnHand) || quantityOnHand < 0) {
    setMessage("Quantity on hand must be zero or greater.", "error");
    return null;
  }
  return {
    name,
    category: optionalString(modelFields.category.value),
    sku: optionalString(normalizeSku(modelFields.sku.value)),
    designer: optionalString(modelFields.designer.value),
    platform: optionalString(modelFields.platform.value),
    file_location: optionalString(modelFields.file_location.value),
    version: optionalString(modelFields.version.value),
    unit_price: unitPrice,
    quantity_on_hand: quantityOnHand,
    active: modelFields.active.value === "true",
    notes: optionalString(modelFields.notes.value),
  };
}

function resetMaterialForm() {
  materialForm.reset();
  materialIdInput.value = "";
  state.currentMaterialId = null;
  materialColorEnabledInputs.forEach((input, index) => {
    if (index === 0) return;
    input.checked = false;
  });
  updateMaterialColorRequirement();
  syncMaterialColorModeUi();
  materialColorHexInputs.forEach((_, index) => syncMaterialColorInputs({ source: "text", index }));
  setMaterialColorDropdownOpen(false);
  loadMaterialCostHistory(null);
}

function buildMerchPayload() {
  const name = merchFields.name.value.trim();
  if (!name) {
    setMessage("Name is required for merch.", "error");
    return null;
  }
  const quantity = Number(merchFields.quantity_on_hand.value || 0);
  const reorder = Number(merchFields.reorder_level.value || 0);
  if (!Number.isFinite(quantity) || quantity < 0 || !Number.isFinite(reorder) || reorder < 0) {
    setMessage("Quantities must be non-negative numbers.", "error");
    return null;
  }
  return {
    name,
    category: optionalString(merchFields.category.value) || "merch",
    merch_color: optionalString(merchFields.merch_color.value),
    merch_size: optionalString(merchFields.merch_size.value),
    merch_style: optionalString(merchFields.merch_style.value),
    merch_sku: optionalString(merchFields.merch_sku.value),
    unit_of_measure: merchFields.unit_of_measure.value.trim() || "piece",
    quantity_on_hand: quantity,
    reorder_level: reorder,
    bin_location: optionalString(merchFields.bin_location.value),
    notes: optionalString(merchFields.notes.value),
  };
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
  if (modelFields.quantity_on_hand) {
    modelFields.quantity_on_hand.value = "0";
  }
}

async function loadModelSales(modelId, { suppressReports = false } = {}) {
  const sales = await api(`/models/${modelId}/sales`);
  state.lastModelSales = Array.isArray(sales) ? sales : [];
  renderModelSales(sales);
  if (!suppressReports) {
    renderReports();
  }
}

async function loadModelMovements(modelId, { suppressReports = false } = {}) {
  const movements = await api(`/models/${modelId}/movements`);
  state.lastModelMovements = Array.isArray(movements) ? movements : [];
  renderModelMovements(movements);
  if (!suppressReports) {
    renderReports();
  }
}

function resetMerchForm() {
  if (!merchForm) return;
  merchForm.reset();
  merchIdInput.value = "";
  state.currentMerchId = null;
  if (merchFields.category) merchFields.category.value = "merch";
  if (merchFields.unit_of_measure) merchFields.unit_of_measure.value = "piece";
  if (merchFields.quantity_on_hand) merchFields.quantity_on_hand.value = "0";
  if (merchFields.reorder_level) merchFields.reorder_level.value = "0";
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

function renderModelMovements(movements) {
  if (!modelMovementTableBody) {
    return;
  }
  if (!movements.length) {
    const text = state.currentModelMovementId
      ? "No model movements recorded."
      : "Select a model to view movement history.";
    modelMovementTableBody.innerHTML = `<tr><td colspan="5" class="muted">${text}</td></tr>`;
    return;
  }
  modelMovementTableBody.innerHTML = movements
    .map(
      (movement) => `
        <tr>
          <td>${new Date(movement.created_at).toLocaleString()}</td>
          <td>${escapeHtml(movement.movement_type)}</td>
          <td>${Number(movement.change_units).toFixed(2)}</td>
          <td>${escapeHtml(movement.reference || "")}</td>
          <td>${escapeHtml(movement.note || "")}</td>
        </tr>`
    )
    .join("");
}

async function loadHardwareMovements(itemId, { suppressReports = false } = {}) {
  const movements = await api(`/hardware/${itemId}/movements`);
  state.lastHardwareMovements = Array.isArray(movements) ? movements : [];
  renderHardwareMovements(movements);
  if (!suppressReports) {
    renderReports();
  }
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
  const raw = String(value || "").trim();
  if (!raw) return "";
  return raw.replace(/[\s-]+/g, "").toUpperCase();
}

async function loadMaterialCostHistory(materialId) {
  if (!materialCostHistoryList) return;
  if (!materialId) {
    materialCostHistoryList.textContent = "Select a material to view history.";
    return;
  }
  try {
    const entries = await api(`/materials/${materialId}/cost-history`);
    if (!Array.isArray(entries) || entries.length === 0) {
      materialCostHistoryList.textContent = "No cost history recorded yet.";
      return;
    }
    materialCostHistoryList.innerHTML = entries
      .slice(0, 8)
      .map((entry) => {
        const when = entry.recorded_at ? new Date(entry.recorded_at).toLocaleString() : "Unknown date";
        const vendor = entry.vendor ? ` · ${escapeHtml(entry.vendor)}` : "";
        const ref = entry.reference ? ` (${escapeHtml(entry.reference)})` : "";
        return `<div>${when} · $${Number(entry.unit_cost_per_gram).toFixed(4)}/g${vendor}${ref}</div>`;
      })
      .join("");
  } catch (err) {
    materialCostHistoryList.textContent = "Unable to load cost history.";
  }
}

function handleMerchRowClick(event) {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  const id = Number(button.dataset.id);
  if (button.dataset.action === "edit") {
    startMerchEdit(id);
    return;
  }
  if (button.dataset.action === "move") {
    setActiveTab("hardware-panel");
    startHardwareMovementEntry(id);
    return;
  }
  if (button.dataset.action === "delete") {
    safeAsync(() => deleteMerch(id));
  }
}

function startNewMerchEntry() {
  resetMerchForm();
  if (merchFields.name) {
    merchFields.name.focus();
  }
}

function startMerchEdit(id) {
  const item = state.hardware.find((hardware) => hardware.id === id);
  if (!item) return;
  state.currentMerchId = id;
  merchIdInput.value = String(id);
  merchFields.name.value = item.name || "";
  merchFields.category.value = item.category || "merch";
  merchFields.merch_color.value = item.merch_color || "";
  merchFields.merch_size.value = item.merch_size || "";
  merchFields.merch_style.value = item.merch_style || "";
  merchFields.merch_sku.value = item.merch_sku || "";
  merchFields.unit_of_measure.value = item.unit_of_measure || "piece";
  merchFields.quantity_on_hand.value = String(item.quantity_on_hand ?? 0);
  merchFields.reorder_level.value = String(item.reorder_level ?? 0);
  merchFields.bin_location.value = item.bin_location || "";
  merchFields.notes.value = item.notes || "";
  if (merchFields.name) {
    merchFields.name.focus();
  }
}

function startHardwareMovementEntry(id) {
  const item = state.hardware.find((hardware) => hardware.id === id);
  if (!item) return;
  hardwareMovementSelect.value = String(id);
  state.currentHardwareMovementId = id;
  safeAsync(() => loadHardwareMovements(id));
  if (hardwareMovementChange) {
    hardwareMovementChange.focus();
    hardwareMovementChange.select();
  }
}

function normalizeSku(value) {
  const raw = String(value || "").trim();
  if (!raw) return "";
  return raw
    .replace(/\s+/g, "-")
    .toUpperCase()
    .replace(/[^A-Z0-9._-]+/g, "")
    .replace(/-{2,}/g, "-")
    .replace(/^-+|-+$/g, "");
}

function findMaterialByBarcode(barcode) {
  const normalized = normalizeBarcode(barcode);
  if (!normalized) {
    return null;
  }
  return (
    state.materials.find(
      (material) =>
        normalizeBarcode(material.barcode) === normalized || normalizeBarcode(material.refill_barcode) === normalized
    ) || null
  );
}

function findInventoryByBarcode(barcode) {
  const normalized = normalizeBarcode(barcode);
  if (!normalized) {
    return [];
  }
  return state.inventory.filter((item) => {
    if (
      item.material &&
      (normalizeBarcode(item.material.barcode) === normalized ||
        normalizeBarcode(item.material.refill_barcode) === normalized)
    ) {
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

async function printMaterialBarcode(materialId) {
  if (!materialId) {
    setMessage("Select a material to print its barcode.", "error");
    return;
  }
  let material = state.materials.find((item) => item.id === materialId);
  if (!material) {
    await loadMaterials();
    material = state.materials.find((item) => item.id === materialId);
  }
  const barcodeValue = normalizeBarcode(material?.barcode) || normalizeBarcode(material?.refill_barcode);
  if (!material || !barcodeValue) {
    setMessage("Material barcode is missing. Set a barcode first.", "error");
    return;
  }
  const labelLines = buildBarcodeLabelLines(material);
  const barcodeUrl = `/materials/${material.id}/barcode?value=${encodeURIComponent(barcodeValue)}&ts=${Date.now()}`;
  openBarcodePrintWindow({
    title: material.name,
    barcodeUrl,
    labelLines,
    barcodeValue,
  });
}

function buildBarcodeLabelLines(material) {
  if (!material) return [];
  const lines = [];
  if (material.name) {
    lines.push(material.name);
  }
  const detailParts = [];
  if (material.filament_type) {
    detailParts.push(material.filament_type);
  }
  if (material.color) {
    detailParts.push(material.color);
  }
  const detail = detailParts.join(" / ");
  if (detail) {
    lines.push(detail);
  }
  return lines;
}

function openBarcodePrintWindow({ title, barcodeUrl, labelLines, barcodeValue }) {
  const printWindow = window.open("", "_blank", "width=520,height=420");
  if (!printWindow) {
    setMessage("Allow popups to print barcode labels.", "error");
    return;
  }
  const safeTitle = escapeHtml(title || "Barcode label");
  const safeBarcode = escapeHtml(barcodeValue || "");
  const safeLines = (labelLines || [])
    .filter((line) => String(line || "").trim())
    .map((line) => `<div class="label-line">${escapeHtml(line)}</div>`)
    .join("");
  const labelWidth = "2.25in";
  const labelHeight = "1.25in";
  const labelPadding = "0.08in";
  const html = `<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>${safeTitle}</title>
    <style>
      * {
        box-sizing: border-box;
      }
      body {
        margin: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        width: 100vw;
        height: 100vh;
        font-family: Arial, Helvetica, sans-serif;
        color: #111;
        background: #fff;
      }
      .label {
        width: ${labelWidth};
        height: ${labelHeight};
        padding: ${labelPadding};
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: space-between;
        gap: 0.08in;
      }
      .label-text {
        width: 100%;
        text-align: center;
        font-size: 0.12in;
        font-weight: 600;
        line-height: 1.1;
      }
      .label-line {
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      .label-barcode {
        width: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
      }
      .label-barcode img {
        max-width: 100%;
        max-height: 0.55in;
      }
      .label-code {
        font-size: 0.11in;
        letter-spacing: 0.04em;
      }
      @media print {
        @page {
          size: ${labelWidth} ${labelHeight};
          margin: 0;
        }
        body {
          width: ${labelWidth};
          height: ${labelHeight};
        }
      }
    </style>
  </head>
  <body>
    <div class="label">
      <div class="label-text">${safeLines}</div>
      <div class="label-barcode">
        <img id="barcode-image" src="${barcodeUrl}" alt="Barcode ${safeBarcode}" />
      </div>
      <div class="label-code">${safeBarcode}</div>
    </div>
    <script>
      const img = document.getElementById("barcode-image");
      const triggerPrint = () => setTimeout(() => window.print(), 50);
      if (img && !img.complete) {
        img.addEventListener("load", triggerPrint);
        img.addEventListener("error", triggerPrint);
      } else {
        triggerPrint();
      }
    </script>
  </body>
</html>`;
  printWindow.document.open();
  printWindow.document.write(html);
  printWindow.document.close();
}

async function api(path, { method = "GET", body, headers } = {}) {
  const normalizedMethod = String(method || "GET").toUpperCase();
  const config = {
    method: normalizedMethod,
    headers: {
      ...(headers || {}),
    },
    credentials: "same-origin",
  };
  if (!["GET", "HEAD", "OPTIONS"].includes(normalizedMethod)) {
    if (!csrfToken) {
      throw new Error("CSRF token is missing. Reload the page and try again.");
    }
    config.headers["X-CSRF-Token"] = csrfToken;
  }
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
    const contentType = (response.headers.get("content-type") || "").toLowerCase();
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
    if (contentType.includes("text/html") || looksLikeHtml(raw)) {
      const statusLabel = response.statusText ? `${response.status} ${response.statusText}` : `${response.status}`;
      message = `Request failed (${statusLabel}). Received an HTML error page from an upstream service.`;
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

function looksLikeHtml(value) {
  const sample = String(value || "").trimStart().slice(0, 240).toLowerCase();
  return sample.startsWith("<!doctype html") || sample.startsWith("<html");
}

async function fetchAllPages(path, { pageSize = 200 } = {}) {
  const allItems = [];
  let offset = 0;
  while (true) {
    const separator = path.includes("?") ? "&" : "?";
    const payload = await api(`${path}${separator}limit=${pageSize}&offset=${offset}`);
    if (Array.isArray(payload)) {
      return payload;
    }
    const pageItems = Array.isArray(payload?.items) ? payload.items : [];
    const total = Number(payload?.total);
    allItems.push(...pageItems);
    if (!Number.isFinite(total)) {
      if (pageItems.length < pageSize) {
        break;
      }
    } else if (allItems.length >= total || pageItems.length === 0) {
      break;
    }
    offset += pageItems.length;
    if (!pageItems.length) {
      break;
    }
  }
  return allItems;
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

function normalizeFilamentViewMode(value) {
  return FILAMENT_VIEW_MODES.has(value) ? value : "gallery";
}

function filamentViewStorageKey(section) {
  return `${FILAMENT_VIEW_STORAGE_KEY_PREFIX}${section}`;
}

function loadStoredFilamentViewMode(section) {
  try {
    const stored = localStorage.getItem(filamentViewStorageKey(section));
    return normalizeFilamentViewMode(stored || "gallery");
  } catch {
    return "gallery";
  }
}

function storeFilamentViewMode(section, mode) {
  try {
    localStorage.setItem(filamentViewStorageKey(section), normalizeFilamentViewMode(mode));
  } catch {
    // Ignore storage access issues
  }
}

function syncFilamentViewControls() {
  if (materialsFilamentViewSelect) {
    materialsFilamentViewSelect.value = normalizeFilamentViewMode(filamentViewState.materials);
  }
  if (inventoryFilamentViewSelect) {
    inventoryFilamentViewSelect.value = normalizeFilamentViewMode(filamentViewState.inventory);
  }
  syncFilamentSectionView("materials", normalizeFilamentViewMode(filamentViewState.materials));
  syncFilamentSectionView("inventory", normalizeFilamentViewMode(filamentViewState.inventory));
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
