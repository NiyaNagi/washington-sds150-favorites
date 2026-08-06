(function () {
  "use strict";

  const TOKEN = window.WASDS150_TOKEN;
  const statusLine = document.getElementById("status-line");

  function setStatus(msg, isError) {
    statusLine.textContent = msg || "";
    statusLine.style.color = isError ? "#f87171" : "#94a3b8";
  }

  async function api(path, options) {
    options = options || {};
    const headers = Object.assign({ "X-Wasds150-Token": TOKEN }, options.headers || {});
    if (options.body && !(options.body instanceof Blob)) {
      headers["Content-Type"] = "application/json";
    }
    const resp = await fetch(path, Object.assign({}, options, { headers }));
    if (path.startsWith("/api/v1/export/") || path.startsWith("/api/v1/generate/hpe/") || path.startsWith("/api/v1/display/palettes/") || path === "/api/v1/display/custom") {
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ error: resp.statusText }));
        throw new Error(err.error || "download failed");
      }
      return resp; // caller handles blob download
    }
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      throw new Error(data.error || `${resp.status} ${resp.statusText}`);
    }
    return data;
  }

  function apiGet(path) {
    return api(path);
  }
  function apiPost(path, body) {
    return api(path, { method: "POST", body: JSON.stringify(body || {}) });
  }
  function apiDelete(path) {
    return api(path, { method: "DELETE" });
  }

  // ---------------------------------------------------------------- tabs --
  const tabButtons = document.querySelectorAll(".tab-btn");
  const tabPanels = document.querySelectorAll(".tab-panel");
  tabButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      tabButtons.forEach((b) => b.classList.remove("active"));
      tabPanels.forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById("tab-" + btn.dataset.tab).classList.add("active");
      refreshTab(btn.dataset.tab);
    });
  });

  function refreshTab(name) {
    if (name === "dashboard") loadDashboard();
    if (name === "catalog") loadCatalog();
    if (name === "display") loadDisplayPalettes();
    if (name === "profile") loadProfile();
    if (name === "export") {
      loadHistory();
      loadHpeList();
      loadSentinelWorkspace();
    }
    if (name === "advanced") {
      loadSourcesList();
      loadInstallSlugOptions();
    }
  }

  // ----------------------------------------------------------- dashboard --
  async function loadDashboard() {
    try {
      const data = await apiGet("/api/v1/dashboard");
      const c = data.counts || {};
      const cards = [
        { label: "Baseline enabled", value: c.baseline_enabled },
        { label: "Baseline disabled", value: c.baseline_disabled },
        { label: "Baseline removed", value: c.baseline_removed },
        { label: "Local lists", value: c.local_total },
        { label: "With structured systems (importable .hpe)", value: c.with_systems },
        { label: "Pending changes", value: data.pending_changes },
        { label: "Warnings", value: (data.warnings || []).length, warn: (data.warnings || []).length > 0 },
      ];
      const container = document.getElementById("dashboard-content");
      container.innerHTML = "";
      cards.forEach((card) => {
        const el = document.createElement("div");
        el.className = "card" + (card.warn ? " warn" : "");
        el.innerHTML = `<div class="label">${card.label}</div><div class="value">${card.value}</div>`;
        container.appendChild(el);
      });
      const hashCard = document.createElement("div");
      hashCard.className = "card";
      hashCard.innerHTML = `<div class="label">Content hash</div><div class="hash">${data.content_hash}</div>`;
      container.appendChild(hashCard);

      const sourceCard = document.createElement("div");
      sourceCard.className = "card";
      const latest = data.latest_snapshot;
      sourceCard.innerHTML = `<div class="label">Catalog source</div><div class="value" style="font-size:1rem">${data.catalog_source}</div>`;
      container.appendChild(sourceCard);

      const snapCard = document.createElement("div");
      snapCard.className = "card";
      snapCard.innerHTML = `<div class="label">Latest snapshot</div><div class="value" style="font-size:1rem">${latest ? latest.id : "none yet"}</div>`;
      container.appendChild(snapCard);
    } catch (e) {
      setStatus("Dashboard error: " + e.message, true);
    }
  }

  // ------------------------------------------------------------- catalog --
  const catalogDetailCache = new Map();

  function humanizeMetadataKey(key) {
    return String(key).replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  function scalarMetadataValue(value) {
    const span = document.createElement("span");
    span.className = "metadata-value";
    if (value === null || value === undefined) {
      span.textContent = "—";
      span.classList.add("empty-value");
    } else if (value === "") {
      span.textContent = "(empty)";
      span.classList.add("empty-value");
    } else if (typeof value === "boolean") {
      span.textContent = value ? "Yes" : "No";
    } else if (typeof value === "string" && /^https?:\/\//i.test(value)) {
      const link = document.createElement("a");
      link.href = value;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = value;
      span.appendChild(link);
    } else {
      span.textContent = String(value);
    }
    return span;
  }

  function metadataItemLabel(item, index) {
    if (!item || typeof item !== "object") return `Item ${index + 1}`;
    return item.favorite_key || item.label || item.name || item.id || `Item ${index + 1}`;
  }

  function attachLazyDetails(details, factory) {
    details.addEventListener("toggle", () => {
      if (!details.open || details.dataset.loaded === "true") return;
      details.appendChild(factory());
      details.dataset.loaded = "true";
    });
  }

  function renderMetadataArray(values, depth) {
    const container = document.createElement("div");
    container.className = "nested-list";
    if (!values.length) {
      container.appendChild(scalarMetadataValue([]));
      container.firstChild.textContent = "None";
      return container;
    }
    let rendered = 0;
    const batchSize = 100;
    const renderNext = () => {
      const fragment = document.createDocumentFragment();
      const end = Math.min(rendered + batchSize, values.length);
      for (let index = rendered; index < end; index += 1) {
        const item = values[index];
        if (item && typeof item === "object") {
          const details = document.createElement("details");
          details.className = "metadata-section";
          const summary = document.createElement("summary");
          summary.textContent = metadataItemLabel(item, index);
          details.appendChild(summary);
          attachLazyDetails(details, () => renderMetadataObject(item, depth + 1));
          fragment.appendChild(details);
        } else {
          fragment.appendChild(scalarMetadataValue(item));
        }
      }
      rendered = end;
      container.appendChild(fragment);
      const previous = container.querySelector("button.show-more");
      if (previous) previous.remove();
      if (rendered < values.length) {
        const more = document.createElement("button");
        more.type = "button";
        more.className = "show-more";
        more.textContent = `Show ${Math.min(batchSize, values.length - rendered)} more`;
        more.addEventListener("click", renderNext);
        container.appendChild(more);
      }
    };
    renderNext();
    return container;
  }

  function renderMetadataObject(value, depth) {
    const container = document.createElement("div");
    container.className = "metadata-object";
    if (depth > 12) {
      container.appendChild(scalarMetadataValue("Maximum display depth reached"));
      return container;
    }
    const scalarGrid = document.createElement("dl");
    scalarGrid.className = "metadata-grid";
    const nested = [];
    Object.entries(value || {}).forEach(([key, item]) => {
      if (item !== null && typeof item === "object") {
        nested.push([key, item]);
        return;
      }
      const term = document.createElement("dt");
      term.className = "metadata-key";
      term.textContent = humanizeMetadataKey(key);
      const definition = document.createElement("dd");
      definition.appendChild(scalarMetadataValue(item));
      scalarGrid.append(term, definition);
    });
    if (scalarGrid.children.length) container.appendChild(scalarGrid);
    nested.forEach(([key, item]) => {
      const details = document.createElement("details");
      details.className = "metadata-section";
      const summary = document.createElement("summary");
      summary.textContent = `${humanizeMetadataKey(key)}${Array.isArray(item) ? ` (${item.length})` : ""}`;
      details.appendChild(summary);
      attachLazyDetails(details, () => (
        Array.isArray(item) ? renderMetadataArray(item, depth + 1) : renderMetadataObject(item, depth + 1)
      ));
      container.appendChild(details);
    });
    return container;
  }

  function appendCatalogCell(row, value) {
    const cell = document.createElement("td");
    cell.textContent = value === null || value === undefined || value === "" ? "—" : String(value);
    row.appendChild(cell);
  }

  async function toggleCatalogDetail(fl, button, detailRow, detailCell) {
    const expanding = button.getAttribute("aria-expanded") !== "true";
    button.setAttribute("aria-expanded", String(expanding));
    button.textContent = expanding ? "Collapse" : "Expand";
    detailRow.hidden = !expanding;
    if (!expanding || detailRow.dataset.loaded === "true") return;
    button.disabled = true;
    detailCell.textContent = "Loading full metadata…";
    try {
      let detail = catalogDetailCache.get(fl.slug);
      if (!detail) {
        detail = await apiGet("/api/v1/catalog/" + encodeURIComponent(fl.slug));
        catalogDetailCache.set(fl.slug, detail);
      }
      detailCell.textContent = "";
      const wrapper = document.createElement("div");
      wrapper.className = "catalog-detail";
      wrapper.appendChild(renderMetadataObject(detail, 0));
      detailCell.appendChild(wrapper);
      detailRow.dataset.loaded = "true";
      document.getElementById("catalog-detail-status").textContent = `Loaded full details for ${fl.favorite_key}`;
    } catch (error) {
      detailCell.textContent = "Unable to load details: " + error.message;
      detailCell.classList.add("detail-error");
      button.setAttribute("aria-expanded", "false");
      button.textContent = "Expand";
      detailRow.hidden = true;
    } finally {
      button.disabled = false;
    }
  }

  async function loadCatalog() {
    try {
      const region = document.getElementById("catalog-region-filter").value;
      const qs = region ? "?region=" + encodeURIComponent(region) : "";
      const data = await apiGet("/api/v1/catalog-summaries" + qs);
      const tbody = document.querySelector("#catalog-table tbody");
      tbody.replaceChildren();
      document.getElementById("catalog-count").textContent = `${data.total || 0} catalog items`;
      (data.favorites || []).forEach((fl) => {
        const tr = document.createElement("tr");
        const detailId = `catalog-detail-${fl.slug}`;
        const actionCell = document.createElement("td");
        const expandButton = document.createElement("button");
        expandButton.type = "button";
        expandButton.textContent = "Expand";
        expandButton.setAttribute("aria-expanded", "false");
        expandButton.setAttribute("aria-controls", detailId);
        actionCell.appendChild(expandButton);
        tr.appendChild(actionCell);
        appendCatalogCell(tr, fl.favorite_key);
        appendCatalogCell(tr, fl.favorite_name);
        appendCatalogCell(tr, fl.region);
        appendCatalogCell(tr, fl.scenario);
        appendCatalogCell(tr, fl.mode);
        appendCatalogCell(
          tr,
          `${fl.system_count} systems / ${fl.site_count} sites / ${fl.channel_count} channels`
        );

        const detailRow = document.createElement("tr");
        detailRow.id = detailId;
        detailRow.className = "catalog-detail-row";
        detailRow.hidden = true;
        const detailCell = document.createElement("td");
        detailCell.colSpan = 7;
        detailRow.appendChild(detailCell);
        expandButton.addEventListener("click", () => toggleCatalogDetail(fl, expandButton, detailRow, detailCell));
        tbody.append(tr, detailRow);
      });
    } catch (e) {
      setStatus("Catalog error: " + e.message, true);
    }
  }
  document.getElementById("catalog-region-filter").addEventListener("input", debounce(loadCatalog, 250));

  function debounce(fn, ms) {
    let t;
    return function () {
      clearTimeout(t);
      t = setTimeout(fn, ms);
    };
  }

  // -------------------------------------------------------------- display --
  let selectedDisplayPalette = null;
  let selectedDisplayTemplate = null;
  let selectedDisplayGrouping = null;
  let displayPaletteData = null;
  let displayCustomConfig = null;
  let activeDisplayItem = null;
  let displayDialogOpener = null;
  const DISPLAY_STORAGE_KEY = "wasds150.displayPalettes.v1";
  const DISPLAY_RECENT_COLORS_KEY = "wasds150.displayRecentColors.v1";

  function copyJson(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function supportedDisplayColorValues() {
    return new Set((displayPaletteData.supported_colors || []).map((color) => color.value));
  }

  function populateSupportedColorSelect(select, value) {
    select.replaceChildren();
    (displayPaletteData.supported_colors || []).forEach((color) => {
      const option = document.createElement("option");
      option.value = color.value;
      option.textContent = `${color.name} · #${color.value}`;
      option.style.backgroundColor = "#" + color.value;
      const contrast = jsContrast(color.value, "FFFFFF");
      option.style.color = contrast >= 4.5 ? "#FFFFFF" : "#000000";
      select.appendChild(option);
    });
    select.value = value;
  }

  function displayPaletteView() {
    return {
      id: selectedDisplayPalette ? selectedDisplayPalette.id : "custom",
      name: displayCustomConfig.name,
      colors: displayCustomConfig.colors,
    };
  }

  function effectiveDisplayOption(item) {
    if (!item) return null;
    const screenOption = displayCustomConfig.screen_item_options[item.screen_key];
    if (screenOption !== undefined) return screenOption;
    const globalOption = displayCustomConfig.global_item_options[item.item_key];
    return globalOption !== undefined ? globalOption : item.option;
  }

  function effectiveDisplayCategory(item) {
    const option = effectiveDisplayOption(item);
    const category = (item.option_categories || {})[option] || item.category;
    if (!selectedDisplayGrouping) return category;
    return selectedDisplayGrouping.item_categories[item.screen_key]
      || selectedDisplayGrouping.category_map[category]
      || category;
  }

  function optionDisplayName(option) {
    const labels = {
      Empty: "(Empty)", ATT: "Attenuator", Bluetooth: "Bluetooth", Day: "Date",
      P25Status: "Digital Status", TdmaSlot: "TDMA Slot", P_Ch: "P-Channel",
      PRI: "Priority Scan", REC: "REC", REP: "Repeater Find", CC: "Close Call",
      WxPRI: "WX Priority", SCR: "Broadcast Screen", FL_Name: "Favorites List Name",
      SiteName: "Site Name", ServiceType: "Service Type", "CTCSS/DCS": "CTCSS/DCS/NAC",
      SystemId: "System/Network ID", SysSubID: "RF Sub System (RFSS) ID",
      SiteId: "Site ID", BattVoltage: "Battery Voltage", UnitId: "Unit ID",
      Rssi: "RSSI", "Rssi Bar": "RSSI Graph", "Volume&Squelch": "Volume and Squelch",
      SystemType: "System Type", Frequency: "Frequency", TGID: "TGID", WACN: "WACN",
      UnitIdName: "Unit ID Name", UnitIdName_1: "Unit ID Name 1–16",
      UnitIdName_2: "Unit ID Name 17–30", UnitIdName_3: "Unit ID Name 31–46",
      UnitIdName_4: "Unit ID Name 47–60", NumberTag: "Number Tag", Lcn: "LCN",
      latitude: "Latitude", longitude: "Longitude", Filter: "Filter", Noise: "Noise",
      D_ErrorCount: "Digital Error Count", "Battery Current": "Battery Current",
      "Battery Temperature": "Battery Temperature", USB2_vbus: "USB Vbus Voltage",
    };
    return labels[option] || option || "(Empty)";
  }

  function iconDisplayName(option) {
    const labels = {
      Empty: "(Empty)", Modulation: "Mod", P_Ch: "P-ch", IFX: "IFX", LVL: "LVL",
      REC: "REC", GPS: "GPS", PRI: "Priority", CC: "Close", WxPRI: "WX",
      SCR: "Broadc", REP: "Repeat",
    };
    return labels[option] || optionDisplayName(option);
  }

  function resolvedDisplayColors(screenName, item, category) {
    const palette = displayPaletteView();
    const screenOverride = item ? displayCustomConfig.screen_item_colors[item.screen_key] : null;
    const globalOverride = item ? displayCustomConfig.global_item_colors[item.item_key] : null;
    const override = Object.assign({}, globalOverride || {}, screenOverride || {});
    const selectedOption = item ? effectiveDisplayOption(item) : null;
    let spectrumSlot = item && selectedDisplayGrouping
      ? selectedDisplayGrouping.option_color_slots[selectedOption]
      : undefined;
    if (spectrumSlot === undefined && item && selectedDisplayGrouping) {
      spectrumSlot = selectedDisplayGrouping.item_color_slots[item.screen_key];
    }
    const groupedText = spectrumSlot !== undefined && displayCustomConfig.spectrum_colors
      ? displayCustomConfig.spectrum_colors[spectrumSlot % displayCustomConfig.spectrum_colors.length]
      : palette.colors[category];
    return {
      text: override.text || groupedText,
      back: override.back || palette.colors.background,
    };
  }

  function visualDisplayColors(item, colors) {
    return item && item.reverse ? { text: colors.back, back: colors.text } : colors;
  }

  function displayItemSample(item) {
    const option = effectiveDisplayOption(item);
    if (option === "Empty") return "";
    if (item.name.startsWith("Icon")) return iconDisplayName(option);
    if (option !== null && option !== undefined) return optionDisplayName(option);
    const samples = {
      Func: "Fun", SIG: "SIG", BATT: "BAT", key: "Key", Dir: "Dir",
      "System Name": "System Name", "Department Name": "Department Name",
      "Channel Name": "Channel Name", Avoid: "Avoid", Hold: "Hold",
      "Primary Area-1": "Primary Area 1", "Primary Area-2": "Primary Area 2",
      "Primary Area-3": "Primary Area 3", "Sub Info": "Sub Info",
      Modulation: "Mod", "Detail Info": "Detail Info",
      "Info Area 1": "Info 1", "Info Area 2": "Info 2", "Info Area 3": "Info 3",
      "Soft1 Key": "Soft 1", "Soft2 Key": "Soft 2", "Soft3 Key": "Soft 3",
      SP0: "", SP1: "", SP2: "",
    };
    return samples[item.name] !== undefined ? samples[item.name] : item.name;
  }

  function displayField(screenName, item, className) {
    const element = document.createElement("div");
    element.className = "scanner-field " + (className || "");
    const selectedOption = effectiveDisplayOption(item);
    element.textContent = displayItemSample(item);
    element.dataset.itemIndex = String(item.index);
    element.dataset.itemName = item.name;
    const xmlColors = resolvedDisplayColors(screenName, item, effectiveDisplayCategory(item));
    const colors = visualDisplayColors(item, xmlColors);
    element.dataset.textColor = colors.text;
    element.dataset.backColor = colors.back;
    element.dataset.xmlTextColor = xmlColors.text;
    element.dataset.xmlBackColor = xmlColors.back;
    element.style.color = "#" + colors.text;
    element.style.backgroundColor = "#" + colors.back;
    element.classList.add("editable");
    if (!element.textContent) element.classList.add("scanner-spacer");
    element.tabIndex = 0;
    element.title = `Customize ${screenName}: ${item.name}${selectedOption ? ` (${optionDisplayName(selectedOption)})` : ""}`;
    if (!item.xml_import_color_supported) {
      element.classList.add("import-limited");
      element.title += ` — ${item.xml_import_note}`;
    }
    element.addEventListener("click", () => openDisplayItemDialog(screenName, item));
    element.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        openDisplayItemDialog(screenName, item);
      }
    });
    return element;
  }

  function readRecentDisplayColors() {
    try {
      const supported = supportedDisplayColorValues();
      return JSON.parse(localStorage.getItem(DISPLAY_RECENT_COLORS_KEY) || "[]")
        .filter((color) => supported.has(color));
    }
    catch (_) { return []; }
  }

  function rememberDisplayColors(colors) {
    const recent = readRecentDisplayColors();
    const supported = supportedDisplayColorValues();
    colors.forEach((color) => {
      const normalized = color.toUpperCase();
      if (!supported.has(normalized)) return;
      const index = recent.indexOf(normalized);
      if (index >= 0) recent.splice(index, 1);
      recent.unshift(normalized);
    });
    localStorage.setItem(DISPLAY_RECENT_COLORS_KEY, JSON.stringify(recent.slice(0, 18)));
  }

  function updateDisplayDialogContrast() {
    const text = document.getElementById("display-dialog-text").value;
    const back = document.getElementById("display-dialog-back").value;
    [["text", text], ["back", back]].forEach(([target, color]) => {
      const metadata = colorMetadata(color);
      const card = document.getElementById(`display-dialog-${target}-card`);
      card.style.setProperty("--choice-color", "#" + color);
      document.getElementById(`display-dialog-${target}-label`).textContent = `${metadata ? metadata.name : "Color"} · #${color}`;
    });
    const ratio = jsContrast(text, back);
    const badge = document.getElementById("display-dialog-contrast");
    badge.textContent = `${ratio.toFixed(2)}:1${ratio < 4.5 ? " — low contrast" : ""}`;
    badge.classList.toggle("low", ratio < 4.5);
    updateDisplaySwatchSelection();
  }

  function colorMetadata(value) {
    return (displayPaletteData.supported_colors || []).find((color) => color.value === value);
  }

  function updateDisplaySwatchSelection() {
    const target = document.getElementById("display-swatch-target").value;
    const selected = document.getElementById(target === "text" ? "display-dialog-text" : "display-dialog-back").value;
    document.querySelectorAll("#display-item-dialog .display-color-swatch").forEach((swatch) => {
      const active = swatch.dataset.color === selected;
      swatch.classList.toggle("selected", active);
      swatch.setAttribute("aria-pressed", String(active));
    });
    document.querySelectorAll(".current-color-card").forEach((card) => {
      const active = card.dataset.target === target;
      card.classList.toggle("active", active);
      card.setAttribute("aria-pressed", String(active));
    });
  }

  function makeDisplayColorSwatch(color) {
    const metadata = colorMetadata(color);
    const button = document.createElement("button");
    button.type = "button";
    button.className = "display-color-swatch";
    button.dataset.color = color;
    button.style.backgroundColor = "#" + color;
    button.title = metadata ? `${metadata.name} · #${color}` : "#" + color;
    button.setAttribute("aria-label", metadata ? `Choose ${metadata.name} #${color}` : "Choose #" + color);
    button.addEventListener("click", () => {
      const target = document.getElementById("display-swatch-target").value;
      document.getElementById(target === "text" ? "display-dialog-text" : "display-dialog-back").value = color;
      updateDisplayDialogContrast();
    });
    return button;
  }

  function renderDisplayColorSwatches(containerId, colors) {
    const container = document.getElementById(containerId);
    container.replaceChildren();
    if (!colors.length) {
      const placeholder = document.createElement("p");
      placeholder.className = "swatch-placeholder";
      placeholder.textContent = "No recent colors yet. Selected colors will appear here.";
      container.appendChild(placeholder);
      return;
    }
    colors.forEach((color) => {
      container.appendChild(makeDisplayColorSwatch(color));
    });
    updateDisplaySwatchSelection();
  }

  function renderSupportedDisplayColorPicker() {
    const container = document.getElementById("display-color-swatches");
    const query = document.getElementById("display-color-filter").value.trim().toLowerCase().replace(/^#/, "");
    const colors = (displayPaletteData.supported_colors || []).filter((color) =>
      !query || color.name.toLowerCase().includes(query) || color.family.toLowerCase().includes(query) || color.value.toLowerCase().includes(query)
    );
    container.replaceChildren();
    document.getElementById("display-color-count").textContent = `${colors.length} of ${displayPaletteData.supported_colors.length}`;
    if (!colors.length) {
      const empty = document.createElement("p");
      empty.className = "swatch-placeholder";
      empty.textContent = "No supported colors match that search.";
      container.appendChild(empty);
      return;
    }
    const families = new Map();
    colors.forEach((color) => {
      if (!families.has(color.family)) families.set(color.family, []);
      families.get(color.family).push(color);
    });
    families.forEach((familyColors, family) => {
      const section = document.createElement("section");
      section.className = "display-color-family";
      const heading = document.createElement("h5");
      heading.textContent = `${family} (${familyColors.length})`;
      const grid = document.createElement("div");
      grid.className = "display-color-swatches";
      familyColors.forEach((color) => grid.appendChild(makeDisplayColorSwatch(color.value)));
      section.append(heading, grid);
      container.appendChild(section);
    });
    updateDisplaySwatchSelection();
  }

  function updateDisplayDialogOptionChoices() {
    if (!activeDisplayItem) return;
    const item = activeDisplayItem.item;
    const sync = document.getElementById("display-dialog-sync").checked;
    const choices = sync ? item.sync_option_choices : item.option_choices;
    const optionLabel = document.getElementById("display-item-option-label");
    const optionSelect = document.getElementById("display-item-option");
    const current = effectiveDisplayOption(item);
    optionSelect.replaceChildren();
    choices.forEach((choice) => {
      const option = document.createElement("option");
      option.value = choice;
      option.textContent = optionDisplayName(choice);
      optionSelect.appendChild(option);
    });
    optionSelect.value = choices.includes(current) ? current : (choices[0] || "");
    optionLabel.classList.toggle("hidden", !choices.length);
  }

  function openDisplayItemDialog(screenName, item, preferredTarget) {
    displayDialogOpener = document.activeElement;
    activeDisplayItem = { screenName, item };
    const category = effectiveDisplayCategory(item);
    const colors = visualDisplayColors(item, resolvedDisplayColors(screenName, item, category));
    document.getElementById("display-item-dialog-title").textContent = item.name;
    document.getElementById("display-item-dialog-context").textContent =
      `${screenName.replace(/([a-z])([A-Z])/g, "$1 $2")} · ${category} group`
      + (item.reverse ? " · Sentinel reverse-rendered field" : "")
      + (!item.xml_import_color_supported ? ` · ${item.xml_import_note}` : "");
    document.getElementById("display-dialog-text").value = colors.text;
    document.getElementById("display-dialog-back").value = colors.back;
    document.getElementById("display-swatch-target").value = preferredTarget || "text";
    document.getElementById("display-color-filter").value = "";
    document.getElementById("display-dialog-sync").checked = document.getElementById("display-sync-items").checked;
    updateDisplayDialogOptionChoices();
    renderSupportedDisplayColorPicker();
    const recent = readRecentDisplayColors();
    renderDisplayColorSwatches("display-recent-colors", recent);
    document.getElementById("display-recent-section").classList.toggle("hidden", !recent.length);
    updateDisplayDialogContrast();
    const dialog = document.getElementById("display-item-dialog");
    dialog.classList.remove("hidden");
    (!document.getElementById("display-item-option-label").classList.contains("hidden")
      ? document.getElementById("display-item-option")
      : document.getElementById("display-color-filter")).focus();
  }

  function closeDisplayItemDialog() {
    document.getElementById("display-item-dialog").classList.add("hidden");
    activeDisplayItem = null;
    if (displayDialogOpener && document.contains(displayDialogOpener)) {
      displayDialogOpener.focus();
    } else {
      const displayTab = document.querySelector('[data-tab="display"]');
      if (displayTab) displayTab.focus();
    }
    displayDialogOpener = null;
  }

  function restoreTemplateOption(item) {
    const selected = selectedDisplayTemplate && selectedDisplayTemplate.screen_item_options[item.screen_key];
    if (selected !== undefined) displayCustomConfig.screen_item_options[item.screen_key] = selected;
    else delete displayCustomConfig.screen_item_options[item.screen_key];
  }

  function applyDisplayDialog() {
    if (!activeDisplayItem) return;
    const { screenName, item } = activeDisplayItem;
    const sync = document.getElementById("display-dialog-sync").checked;
    const text = document.getElementById("display-dialog-text").value;
    const back = document.getElementById("display-dialog-back").value;
    const xmlColors = item.reverse ? { text: back, back: text } : { text, back };
    const option = !document.getElementById("display-item-option-label").classList.contains("hidden")
      ? document.getElementById("display-item-option").value
      : null;
    if (sync) {
      displayCustomConfig.global_item_colors[item.item_key] = xmlColors;
      if (option !== null) displayCustomConfig.global_item_options[item.item_key] = option;
      Object.values(displayPaletteData.items).flat().forEach((candidate) => {
        if (candidate.item_key === item.item_key) {
          delete displayCustomConfig.screen_item_colors[candidate.screen_key];
          delete displayCustomConfig.screen_item_options[candidate.screen_key];
        }
      });
    } else {
      displayCustomConfig.screen_item_colors[item.screen_key] = xmlColors;
      if (option !== null) displayCustomConfig.screen_item_options[item.screen_key] = option;
    }
    rememberDisplayColors([text, back]);
    closeDisplayItemDialog();
    renderDisplayItemEditor();
    renderDisplayPreviews();
  }

  function resetActiveDisplayItem() {
    if (!activeDisplayItem) return;
    const { item } = activeDisplayItem;
    const sync = document.getElementById("display-dialog-sync").checked;
    if (sync) {
      delete displayCustomConfig.global_item_colors[item.item_key];
      delete displayCustomConfig.global_item_options[item.item_key];
      Object.values(displayPaletteData.items).flat().forEach((candidate) => {
        if (candidate.item_key === item.item_key) {
          delete displayCustomConfig.screen_item_colors[candidate.screen_key];
          restoreTemplateOption(candidate);
        }
      });
    } else {
      delete displayCustomConfig.screen_item_colors[item.screen_key];
      restoreTemplateOption(item);
    }
    closeDisplayItemDialog();
    renderDisplayItemEditor();
    renderDisplayPreviews();
  }

  document.getElementById("display-dialog-text").addEventListener("input", updateDisplayDialogContrast);
  document.getElementById("display-dialog-back").addEventListener("input", updateDisplayDialogContrast);
  document.getElementById("display-swatch-target").addEventListener("change", updateDisplaySwatchSelection);
  document.querySelectorAll(".current-color-card").forEach((card) => card.addEventListener("click", () => {
    document.getElementById("display-swatch-target").value = card.dataset.target;
    updateDisplaySwatchSelection();
  }));
  document.getElementById("display-color-filter").addEventListener("input", renderSupportedDisplayColorPicker);
  document.getElementById("display-dialog-sync").addEventListener("change", updateDisplayDialogOptionChoices);
  document.getElementById("display-dialog-apply").addEventListener("click", applyDisplayDialog);
  document.getElementById("display-dialog-reset").addEventListener("click", resetActiveDisplayItem);
  document.getElementById("display-dialog-cancel").addEventListener("click", closeDisplayItemDialog);
  document.getElementById("display-dialog-close").addEventListener("click", closeDisplayItemDialog);
  document.getElementById("display-item-dialog").addEventListener("click", (event) => {
    if (event.target.id === "display-item-dialog") closeDisplayItemDialog();
  });
  document.addEventListener("keydown", (event) => {
    const dialog = document.getElementById("display-item-dialog");
    if (event.key === "Escape" && !dialog.classList.contains("hidden")) {
      closeDisplayItemDialog();
    } else if (event.key === "Tab" && !dialog.classList.contains("hidden")) {
      const focusable = Array.from(dialog.querySelectorAll("button:not([disabled]), select:not([disabled]), input:not([disabled]):not([type='hidden'])"))
        .filter((element) => !element.closest(".hidden") && element.offsetParent !== null);
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
  });

  function renderScannerPreview(screenName, palette) {
    const preview = document.createElement("article");
    preview.className = "scanner-preview";
    preview.dataset.screen = screenName;
    preview.style.backgroundColor = "#" + palette.colors.background;
    const heading = document.createElement("h3");
    heading.textContent = screenName.replace(/([a-z])([A-Z])/g, "$1 $2");
    heading.style.color = "#" + palette.colors.status;
    preview.appendChild(heading);

    const items = displayPaletteData.items[screenName];
    const appendRow = (className, indices, primaryIndices) => {
      const row = document.createElement("div");
      row.className = `scanner-slot-row ${className}`;
      indices.forEach((index) => row.appendChild(displayField(
        screenName,
        items[index],
        (primaryIndices || []).includes(index) ? "scanner-primary" : ""
      )));
      preview.appendChild(row);
    };

    displayPaletteData.layouts[screenName].forEach((row) =>
      appendRow(row.class_name, row.indices, row.primary_indices)
    );
    return preview;
  }

  function jsLuminance(hex) {
    const values = [0, 2, 4].map((index) => parseInt(hex.slice(index, index + 2), 16) / 255)
      .map((value) => value <= 0.04045 ? value / 12.92 : Math.pow((value + 0.055) / 1.055, 2.4));
    return 0.2126 * values[0] + 0.7152 * values[1] + 0.0722 * values[2];
  }

  function jsContrast(first, second) {
    const values = [jsLuminance(first), jsLuminance(second)].sort((a, b) => b - a);
    return (values[0] + 0.05) / (values[1] + 0.05);
  }

  function renderDisplayPreviews() {
    const palette = displayPaletteView();
    const grid = document.getElementById("display-preview-grid");
    grid.replaceChildren();
    displayPaletteData.screens.forEach((screen) => grid.appendChild(renderScannerPreview(screen, palette)));
    let minimum = Infinity;
    let low = 0;
    Object.entries(displayPaletteData.items).forEach(([screen, items]) => items.forEach((item) => {
      const colors = resolvedDisplayColors(screen, item, effectiveDisplayCategory(item));
      const ratio = jsContrast(colors.text, colors.back);
      minimum = Math.min(minimum, ratio);
      if (ratio < 4.5) low += 1;
    }));
    const summary = document.getElementById("display-contrast-summary");
    summary.textContent = `${displayCustomConfig.name}: minimum contrast ${minimum.toFixed(2)}:1${low ? ` — ${low} item(s) below 4.5:1` : " — all items pass 4.5:1"}`;
    summary.style.color = low ? "#f87171" : "";
  }

  function renderSemanticColors() {
    const container = document.getElementById("display-semantic-colors");
    container.replaceChildren();
    ["background", "status", "system", "department", "channel", "metadata", "alert", "accent"].forEach((category) => {
      const wrapper = document.createElement("label");
      wrapper.className = "semantic-color-control";
      const input = document.createElement("select");
      input.className = "semantic-color-select";
      populateSupportedColorSelect(input, displayCustomConfig.colors[category]);
      input.setAttribute("aria-label", `${category} color`);
      const label = document.createElement("span");
      label.className = "semantic-color-label";
      const strong = document.createElement("strong");
      strong.textContent = category;
      const badge = document.createElement("span");
      badge.className = "contrast-badge";
      const updateBadge = () => {
        if (category === "background") {
          badge.textContent = "#" + input.value;
          return;
        }
        const ratio = jsContrast(input.value, displayCustomConfig.colors.background);
        badge.textContent = `#${input.value} · ${ratio.toFixed(2)}:1`;
        badge.classList.toggle("low", ratio < 4.5);
      };
      input.addEventListener("input", () => {
        displayCustomConfig.colors[category] = input.value;
        updateBadge();
        updateDisplayGroupingSwatches();
        renderDisplayPreviews();
        renderDisplayItemEditor();
      });
      if (category === "background") input.addEventListener("change", renderSemanticColors);
      label.append(strong, badge);
      wrapper.append(input, label);
      container.appendChild(wrapper);
      updateBadge();
    });
  }

  function renderDisplayItemEditor() {
    if (!displayPaletteData || !displayCustomConfig) return;
    const screen = document.getElementById("display-screen-select").value || displayPaletteData.screens[0];
    const tbody = document.querySelector("#display-item-editor tbody");
    tbody.replaceChildren();
    (displayPaletteData.items[screen] || []).forEach((item) => {
      const category = effectiveDisplayCategory(item);
      const colors = visualDisplayColors(item, resolvedDisplayColors(screen, item, category));
      const row = document.createElement("tr");
      if (!item.xml_import_color_supported) {
        row.classList.add("import-limited");
        row.title = item.xml_import_note;
      }
      [item.name, optionDisplayName(effectiveDisplayOption(item)) || "—", category + (!item.xml_import_color_supported ? " ⚠" : "")].forEach((value) => {
        const cell = document.createElement("td");
        cell.textContent = value;
        row.appendChild(cell);
      });
      ["text", "back"].forEach((field) => {
        const cell = document.createElement("td");
        const picker = document.createElement("button");
        picker.type = "button";
        picker.className = "item-color-button";
        picker.textContent = "#" + colors[field];
        picker.style.backgroundColor = "#" + colors[field];
        picker.style.color = jsContrast(colors[field], "FFFFFF") >= 4.5 ? "#FFFFFF" : "#000000";
        picker.setAttribute("aria-label", `${screen} ${item.name} ${field} color #${colors[field]}`);
        picker.addEventListener("click", () => openDisplayItemDialog(screen, item, field));
        cell.appendChild(picker);
        row.appendChild(cell);
      });
      const ratioCell = document.createElement("td");
      const ratio = jsContrast(colors.text, colors.back);
      ratioCell.textContent = ratio.toFixed(2) + ":1";
      ratioCell.className = "contrast-badge" + (ratio < 4.5 ? " low" : "");
      row.appendChild(ratioCell);
      const resetCell = document.createElement("td");
      const reset = document.createElement("button");
      reset.textContent = "Reset";
      reset.addEventListener("click", () => {
        if (document.getElementById("display-sync-items").checked) {
          delete displayCustomConfig.global_item_colors[item.item_key];
          delete displayCustomConfig.global_item_options[item.item_key];
          Object.values(displayPaletteData.items).flat().forEach((candidate) => {
            if (candidate.item_key === item.item_key) {
              delete displayCustomConfig.screen_item_colors[candidate.screen_key];
              restoreTemplateOption(candidate);
            }
          });
        } else {
          delete displayCustomConfig.screen_item_colors[item.screen_key];
          restoreTemplateOption(item);
        }
        renderDisplayPreviews();
        renderDisplayItemEditor();
      });
      resetCell.appendChild(reset);
      row.appendChild(resetCell);
      tbody.appendChild(row);
    });
  }

  function selectDisplayPalette(palette) {
    selectedDisplayPalette = palette;
    const templateOptions = selectedDisplayTemplate ? copyJson(selectedDisplayTemplate.screen_item_options) : {};
    const existingGlobalOptions = displayCustomConfig ? copyJson(displayCustomConfig.global_item_options) : {};
    const existingScreenOptions = displayCustomConfig ? copyJson(displayCustomConfig.screen_item_options) : templateOptions;
    displayCustomConfig = {
      name: palette.name,
      description: palette.description,
      colors: copyJson(palette.colors),
      spectrum_colors: copyJson(palette.spectrum_colors),
      layout_template_id: selectedDisplayTemplate ? selectedDisplayTemplate.id : "sentinel-export",
      color_grouping_id: selectedDisplayGrouping ? selectedDisplayGrouping.id : "balanced",
      global_item_colors: {},
      screen_item_colors: {},
      global_item_options: existingGlobalOptions,
      screen_item_options: existingScreenOptions,
    };
    document.getElementById("display-custom-name").value = palette.name + " Custom";
    populateSupportedColorSelect(document.getElementById("display-view-text"), palette.colors.status);
    populateSupportedColorSelect(document.getElementById("display-view-back"), palette.colors.background);
    document.querySelectorAll(".display-palette-card").forEach((card) => {
      const selected = card.dataset.paletteId === palette.id;
      card.classList.toggle("selected", selected);
      card.setAttribute("aria-checked", String(selected));
    });
    document.getElementById("display-download-btn").disabled = false;
    renderSemanticColors();
    renderDisplayItemEditor();
    renderDisplayPreviews();
    updateDisplayGroupingSwatches();
  }

  function updateDisplayGroupingSwatches() {
    if (!displayCustomConfig) return;
    document.querySelectorAll(".grouping-swatch").forEach((swatch) => {
      const color = swatch.dataset.spectrumSlot !== undefined
        ? displayCustomConfig.spectrum_colors[Number(swatch.dataset.spectrumSlot)]
        : displayCustomConfig.colors[swatch.dataset.category];
      swatch.style.backgroundColor = "#" + color;
    });
  }

  function selectDisplayColorGrouping(grouping) {
    selectedDisplayGrouping = grouping;
    document.querySelectorAll(".display-grouping-card").forEach((card) => {
      const selected = card.dataset.groupingId === grouping.id;
      card.classList.toggle("selected", selected);
      card.setAttribute("aria-checked", String(selected));
    });
    if (!displayCustomConfig) return;
    displayCustomConfig.color_grouping_id = grouping.id;
    displayCustomConfig.global_item_colors = {};
    displayCustomConfig.screen_item_colors = {};
    renderDisplayItemEditor();
    renderDisplayPreviews();
    setStatus(`Applied ${grouping.name} color grouping; layout and theme unchanged`);
  }

  function selectDisplayLayoutTemplate(template) {
    selectedDisplayTemplate = template;
    document.querySelectorAll(".display-layout-card").forEach((card) => {
      const selected = card.dataset.templateId === template.id;
      card.classList.toggle("selected", selected);
      card.setAttribute("aria-checked", String(selected));
    });
    if (!displayCustomConfig) return;
    displayCustomConfig.layout_template_id = template.id;
    displayCustomConfig.global_item_options = {};
    displayCustomConfig.screen_item_options = copyJson(template.screen_item_options);
    displayCustomConfig.global_item_colors = {};
    displayCustomConfig.screen_item_colors = {};
    renderDisplayItemEditor();
    renderDisplayPreviews();
    setStatus(`Applied ${template.name} layout; color theme unchanged`);
  }

  async function loadDisplayPalettes() {
    if (displayPaletteData && displayCustomConfig) {
      renderSemanticColors();
      renderDisplayItemEditor();
      renderDisplayPreviews();
      return;
    }
    try {
      const data = await apiGet("/api/v1/display/palettes");
      displayPaletteData = data;
      const layoutContainer = document.getElementById("display-layout-options");
      layoutContainer.replaceChildren();
      data.layout_templates.forEach((template) => {
        const card = document.createElement("button");
        card.type = "button";
        card.className = "display-layout-card";
        card.dataset.templateId = template.id;
        card.setAttribute("role", "radio");
        card.setAttribute("aria-checked", "false");
        const title = document.createElement("strong");
        title.textContent = template.name;
        const description = document.createElement("span");
        description.textContent = template.description;
        const scenario = document.createElement("em");
        scenario.textContent = template.scenario;
        card.append(title, description, scenario);
        card.addEventListener("click", () => selectDisplayLayoutTemplate(template));
        layoutContainer.appendChild(card);
      });
      selectedDisplayTemplate = selectedDisplayTemplate
        ? data.layout_templates.find((template) => template.id === selectedDisplayTemplate.id) || data.layout_templates[0]
        : data.layout_templates[0];
      selectDisplayLayoutTemplate(selectedDisplayTemplate);
      const container = document.getElementById("display-palette-options");
      container.replaceChildren();
      data.palettes.forEach((palette) => {
        const card = document.createElement("button");
        card.type = "button";
        card.className = "display-palette-card";
        card.dataset.paletteId = palette.id;
        card.setAttribute("role", "radio");
        card.setAttribute("aria-checked", "false");
        const title = document.createElement("strong");
        title.textContent = palette.name;
        const description = document.createElement("span");
        description.textContent = palette.description;
        const swatches = document.createElement("span");
        swatches.className = "palette-swatches";
        ["system", "department", "channel", "metadata", "alert", "accent"].forEach((category) => {
          const swatch = document.createElement("span");
          swatch.className = "palette-swatch";
          swatch.style.backgroundColor = "#" + palette.colors[category];
          swatch.title = `${category}: #${palette.colors[category]} (${palette.contrast_ratios[category]}:1)`;
          swatches.appendChild(swatch);
        });
        card.append(title, description, swatches);
        card.addEventListener("click", () => selectDisplayPalette(palette));
        container.appendChild(card);
      });
      const groupingContainer = document.getElementById("display-grouping-options");
      groupingContainer.replaceChildren();
      data.color_groupings.forEach((grouping) => {
        const card = document.createElement("button");
        card.type = "button";
        card.className = "display-grouping-card";
        card.dataset.groupingId = grouping.id;
        card.setAttribute("role", "radio");
        card.setAttribute("aria-checked", "false");
        const title = document.createElement("strong");
        title.textContent = grouping.name;
        const description = document.createElement("span");
        description.textContent = grouping.description;
        const style = document.createElement("em");
        style.textContent = grouping.style;
        const swatches = document.createElement("span");
        swatches.className = "grouping-swatches";
        const spectrumSlots = Array.from(new Set([
          ...Object.values(grouping.item_color_slots), ...Object.values(grouping.option_color_slots),
        ])).sort((a, b) => a - b);
        const baseCategories = ["status", "system", "department", "channel", "metadata", "alert", "accent"];
        const samples = spectrumSlots.length
          ? spectrumSlots.map((slot) => ({ spectrumSlot: slot }))
          : Array.from(new Set([
              ...baseCategories.map((category) => grouping.category_map[category] || category),
              ...Object.values(grouping.item_categories),
            ])).map((category) => ({ category }));
        samples.forEach((sample) => {
          const swatch = document.createElement("span");
          swatch.className = "grouping-swatch";
          if (sample.spectrumSlot !== undefined) {
            swatch.dataset.spectrumSlot = String(sample.spectrumSlot);
            swatch.title = `Spectrum color ${sample.spectrumSlot + 1}`;
          } else {
            swatch.dataset.category = sample.category;
            swatch.title = sample.category;
          }
          swatches.appendChild(swatch);
        });
        card.append(title, description, style, swatches);
        card.addEventListener("click", () => selectDisplayColorGrouping(grouping));
        groupingContainer.appendChild(card);
      });
      selectedDisplayGrouping = selectedDisplayGrouping
        ? data.color_groupings.find((grouping) => grouping.id === selectedDisplayGrouping.id) || data.color_groupings[0]
        : data.color_groupings[0];
      selectDisplayColorGrouping(selectedDisplayGrouping);
      const screenSelect = document.getElementById("display-screen-select");
      screenSelect.replaceChildren();
      data.screens.forEach((screen) => {
        const option = document.createElement("option");
        option.value = screen;
        option.textContent = screen.replace(/([a-z])([A-Z])/g, "$1 $2");
        screenSelect.appendChild(option);
      });
      const preferred = selectedDisplayPalette
        ? data.palettes.find((palette) => palette.id === selectedDisplayPalette.id)
        : data.palettes[0];
      if (preferred) selectDisplayPalette(preferred);
      refreshSavedDisplayPalettes();
    } catch (error) {
      setStatus("Display palette error: " + error.message, true);
    }
  }

  document.getElementById("display-download-btn").addEventListener("click", async () => {
    if (!displayCustomConfig) return;
    try {
      displayCustomConfig.name = document.getElementById("display-custom-name").value || displayCustomConfig.name;
      const filename = await downloadBlobFrom(
        "/api/v1/display/custom",
        "wasds150-display-custom.xml",
        { method: "POST", body: JSON.stringify(displayCustomConfig) }
      );
      setStatus("Downloaded " + filename);
    } catch (error) {
      setStatus("Display XML download failed: " + error.message, true);
    }
  });

  function readSavedDisplayPalettes() {
    try { return JSON.parse(localStorage.getItem(DISPLAY_STORAGE_KEY) || "[]"); }
    catch (_) { return []; }
  }

  function refreshSavedDisplayPalettes() {
    const select = document.getElementById("display-saved-palettes");
    const current = select.value;
    select.replaceChildren();
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "Saved palettes…";
    select.appendChild(placeholder);
    readSavedDisplayPalettes().forEach((saved) => {
      const option = document.createElement("option");
      option.value = saved.id;
      option.textContent = saved.name;
      select.appendChild(option);
    });
    select.value = current;
  }

  function loadCustomDisplayConfig(config) {
    const colorKeys = ["background", "status", "system", "department", "channel", "metadata", "alert", "accent"];
    const supported = supportedDisplayColorValues();
    if (!config || !config.colors || !colorKeys.every((key) => supported.has((config.colors[key] || "").toUpperCase()))) {
      throw new Error("Palette contains a semantic color not supported by Sentinel");
    }
    const matchingPalette = displayPaletteData.palettes.find((palette) =>
      colorKeys.every((key) => palette.colors[key] === (config.colors[key] || "").toUpperCase())
    );
    const fallbackSpectrum = (matchingPalette || displayPaletteData.palettes[0]).spectrum_colors;
    const savedSpectrum = config.spectrum_colors || [];
    if (!Array.isArray(savedSpectrum) || savedSpectrum.some((color) => !supported.has((color || "").toUpperCase()))) {
      throw new Error("Palette spectrum contains an unsupported Sentinel color");
    }
    const spectrum = Array.from(new Set([...savedSpectrum, ...fallbackSpectrum]));
    if (spectrum.length < 30) throw new Error("Palette spectrum must resolve to at least 30 colors");
    if (!config.global_item_colors || typeof config.global_item_colors !== "object" ||
        !config.screen_item_colors || typeof config.screen_item_colors !== "object") {
      throw new Error("Palette is missing item override maps");
    }
    [config.global_item_colors, config.screen_item_colors].forEach((overrides) => {
      Object.values(overrides).forEach((colors) => {
        if (!colors || ["text", "back"].some((field) => colors[field] && !supported.has(colors[field].toUpperCase()))) {
          throw new Error("Palette contains an item color not supported by Sentinel");
        }
      });
    });
    displayCustomConfig = copyJson(config);
    displayCustomConfig.spectrum_colors = spectrum.map((color) => color.toUpperCase());
    colorKeys.forEach((key) => { displayCustomConfig.colors[key] = displayCustomConfig.colors[key].toUpperCase(); });
    [displayCustomConfig.global_item_colors, displayCustomConfig.screen_item_colors].forEach((overrides) => {
      Object.values(overrides).forEach((colors) => {
        if (colors.text) colors.text = colors.text.toUpperCase();
        if (colors.back) colors.back = colors.back.toUpperCase();
      });
    });
    displayCustomConfig.global_item_options = displayCustomConfig.global_item_options || {};
    displayCustomConfig.screen_item_options = displayCustomConfig.screen_item_options || {};
    const templateId = displayCustomConfig.layout_template_id || "sentinel-export";
    selectedDisplayTemplate = displayPaletteData.layout_templates.find((template) => template.id === templateId);
    if (!selectedDisplayTemplate) throw new Error(`Unknown display layout template: ${templateId}`);
    displayCustomConfig.layout_template_id = selectedDisplayTemplate.id;
    displayCustomConfig.screen_item_options = Object.assign(
      {}, copyJson(selectedDisplayTemplate.screen_item_options), displayCustomConfig.screen_item_options
    );
    const groupingId = displayCustomConfig.color_grouping_id || "balanced";
    selectedDisplayGrouping = displayPaletteData.color_groupings.find((grouping) => grouping.id === groupingId);
    if (!selectedDisplayGrouping) throw new Error(`Unknown display color grouping: ${groupingId}`);
    displayCustomConfig.color_grouping_id = selectedDisplayGrouping.id;
    selectedDisplayPalette = null;
    document.querySelectorAll(".display-palette-card").forEach((card) => {
      card.classList.remove("selected");
      card.setAttribute("aria-checked", "false");
    });
    document.querySelectorAll(".display-layout-card").forEach((card) => {
      const selected = card.dataset.templateId === selectedDisplayTemplate.id;
      card.classList.toggle("selected", selected);
      card.setAttribute("aria-checked", String(selected));
    });
    document.querySelectorAll(".display-grouping-card").forEach((card) => {
      const selected = card.dataset.groupingId === selectedDisplayGrouping.id;
      card.classList.toggle("selected", selected);
      card.setAttribute("aria-checked", String(selected));
    });
    document.getElementById("display-custom-name").value = displayCustomConfig.name || "My Custom Palette";
    populateSupportedColorSelect(document.getElementById("display-view-text"), displayCustomConfig.colors.status);
    populateSupportedColorSelect(document.getElementById("display-view-back"), displayCustomConfig.colors.background);
    renderSemanticColors();
    updateDisplayGroupingSwatches();
    renderDisplayItemEditor();
    renderDisplayPreviews();
  }

  document.getElementById("display-screen-select").addEventListener("change", renderDisplayItemEditor);
  document.getElementById("display-sync-items").addEventListener("change", renderDisplayItemEditor);
  document.getElementById("display-reset-screen").addEventListener("click", () => {
    const screen = document.getElementById("display-screen-select").value + "||";
    Object.keys(displayCustomConfig.screen_item_colors).forEach((key) => {
      if (key.startsWith(screen)) delete displayCustomConfig.screen_item_colors[key];
    });
    Object.keys(displayCustomConfig.screen_item_options).forEach((key) => {
      if (key.startsWith(screen)) delete displayCustomConfig.screen_item_options[key];
    });
    Object.entries(selectedDisplayTemplate.screen_item_options).forEach(([key, value]) => {
      if (key.startsWith(screen)) displayCustomConfig.screen_item_options[key] = value;
    });
    renderDisplayItemEditor();
    renderDisplayPreviews();
  });
  document.getElementById("display-reset-all-items").addEventListener("click", () => {
    displayCustomConfig.global_item_colors = {};
    displayCustomConfig.screen_item_colors = {};
    displayCustomConfig.global_item_options = {};
    displayCustomConfig.screen_item_options = copyJson(selectedDisplayTemplate.screen_item_options);
    renderDisplayItemEditor();
    renderDisplayPreviews();
  });
  function applyColorToCurrentView(field, pickerId) {
    const screen = document.getElementById("display-screen-select").value;
    const color = document.getElementById(pickerId).value;
    const sync = document.getElementById("display-sync-items").checked;
    (displayPaletteData.items[screen] || []).forEach((item) => {
      const xmlField = item.reverse ? (field === "text" ? "back" : "text") : field;
      if (sync) {
        displayCustomConfig.global_item_colors[item.item_key] = Object.assign(
          {}, displayCustomConfig.global_item_colors[item.item_key] || {}, { [xmlField]: color }
        );
        Object.values(displayPaletteData.items).flat().forEach((candidate) => {
          if (candidate.item_key === item.item_key) delete displayCustomConfig.screen_item_colors[candidate.screen_key];
        });
      } else {
        displayCustomConfig.screen_item_colors[item.screen_key] = Object.assign(
          {}, displayCustomConfig.screen_item_colors[item.screen_key] || {}, { [xmlField]: color }
        );
      }
    });
    renderDisplayItemEditor();
    renderDisplayPreviews();
  }
  document.getElementById("display-apply-view-text").addEventListener("click", () => applyColorToCurrentView("text", "display-view-text"));
  document.getElementById("display-apply-view-back").addEventListener("click", () => applyColorToCurrentView("back", "display-view-back"));
  document.getElementById("display-reset-custom").addEventListener("click", () => {
    const palette = selectedDisplayPalette || (displayPaletteData && displayPaletteData.palettes[0]);
    if (palette) selectDisplayPalette(palette);
  });
  document.getElementById("display-custom-name").addEventListener("input", (event) => {
    if (!displayCustomConfig) return;
    displayCustomConfig.name = event.target.value || "My Custom Palette";
    renderDisplayPreviews();
  });
  document.getElementById("display-save-custom").addEventListener("click", () => {
    displayCustomConfig.name = document.getElementById("display-custom-name").value || "My Custom Palette";
    const saved = readSavedDisplayPalettes();
    const select = document.getElementById("display-saved-palettes");
    const id = select.value || `custom-${Date.now()}`;
    const entry = { id, name: displayCustomConfig.name, config: copyJson(displayCustomConfig) };
    const index = saved.findIndex((item) => item.id === id);
    if (index >= 0) saved[index] = entry; else saved.push(entry);
    localStorage.setItem(DISPLAY_STORAGE_KEY, JSON.stringify(saved));
    refreshSavedDisplayPalettes();
    select.value = id;
    setStatus(`Saved custom palette ${entry.name}`);
  });
  document.getElementById("display-saved-palettes").addEventListener("change", (event) => {
    const saved = readSavedDisplayPalettes().find((item) => item.id === event.target.value);
    if (saved) {
      try { loadCustomDisplayConfig(saved.config); }
      catch (error) { setStatus("Saved palette is invalid: " + error.message, true); }
    }
  });
  document.getElementById("display-delete-custom").addEventListener("click", () => {
    const select = document.getElementById("display-saved-palettes");
    if (!select.value) return;
    const saved = readSavedDisplayPalettes().filter((item) => item.id !== select.value);
    localStorage.setItem(DISPLAY_STORAGE_KEY, JSON.stringify(saved));
    refreshSavedDisplayPalettes();
    setStatus("Deleted saved custom palette");
  });
  document.getElementById("display-export-json").addEventListener("click", () => {
    displayCustomConfig.name = document.getElementById("display-custom-name").value || displayCustomConfig.name;
    const blob = new Blob([JSON.stringify(displayCustomConfig, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "wasds150-custom-display-palette.json";
    link.click();
    URL.revokeObjectURL(url);
  });
  document.getElementById("display-import-json").addEventListener("change", (event) => {
    const file = event.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const config = JSON.parse(reader.result);
        loadCustomDisplayConfig(config);
        setStatus("Imported custom display palette JSON");
      } catch (error) {
        setStatus("Custom palette import failed: " + error.message, true);
      }
    };
    reader.readAsText(file);
  });

  // ------------------------------------------------------------- profile --
  async function loadProfile() {
    try {
      const data = await apiGet("/api/v1/profile");
      const overridden = new Set(data.overridden_slugs || []);
      const local = new Set(data.local_slugs || []);
      const tbody = document.querySelector("#profile-table tbody");
      tbody.innerHTML = "";
      (data.favorites || []).forEach((fl) => {
        const tr = document.createElement("tr");
        const statePill = fl.enabled
          ? '<span class="pill enabled">enabled</span>'
          : '<span class="pill disabled">disabled</span>';
        const originPill = local.has(fl.slug)
          ? '<span class="pill local">local</span>'
          : overridden.has(fl.slug)
          ? '<span class="pill overridden">overridden</span>'
          : "";
        tr.innerHTML = `
          <td>${statePill}</td>
          <td>${fl.favorite_key}</td>
          <td>${originPill}</td>
          <td>${fl.favorite_name}</td>
          <td>${fl.region}</td>
          <td class="actions"></td>
        `;
        const actions = tr.querySelector(".actions");

        const toggleBtn = document.createElement("button");
        toggleBtn.textContent = fl.enabled ? "Disable" : "Enable";
        toggleBtn.addEventListener("click", async () => {
          await apiPost("/api/v1/profile/enable", { slug: fl.slug, enabled: !fl.enabled });
          loadProfile();
          loadDashboard();
        });
        actions.appendChild(toggleBtn);

        const editBtn = document.createElement("button");
        editBtn.textContent = "Edit";
        editBtn.addEventListener("click", () => openEditModal(fl));
        actions.appendChild(editBtn);

        const removeBtn = document.createElement("button");
        removeBtn.textContent = "Remove";
        removeBtn.className = "danger";
        removeBtn.addEventListener("click", async () => {
          if (!confirm(`Remove ${fl.favorite_key} from the generated output?`)) return;
          if (local.has(fl.slug)) {
            await apiDelete("/api/v1/profile/local/" + encodeURIComponent(fl.slug));
          } else {
            await apiPost("/api/v1/profile/remove", { slug: fl.slug });
          }
          loadProfile();
          loadDashboard();
        });
        actions.appendChild(removeBtn);

        if (overridden.has(fl.slug)) {
          const restoreBtn = document.createElement("button");
          restoreBtn.textContent = "Restore";
          restoreBtn.addEventListener("click", async () => {
            await apiPost("/api/v1/profile/restore", { slug: fl.slug });
            loadProfile();
            loadDashboard();
          });
          actions.appendChild(restoreBtn);
        }

        tbody.appendChild(tr);
      });
    } catch (e) {
      setStatus("Profile error: " + e.message, true);
    }
  }

  const EDITABLE_FIELDS = [
    "favorite_name",
    "region",
    "counties",
    "scenario",
    "source_type",
    "system_or_category",
    "sites_or_coverage",
    "departments_or_channels",
    "mode",
    "monitorability",
    "upgrade_required",
    "source_url",
    "notes",
    "flqk",
  ];

  const modalBackdrop = document.getElementById("modal-backdrop");
  const modalTitle = document.getElementById("modal-title");
  const modalBody = document.getElementById("modal-body");
  document.getElementById("modal-cancel").addEventListener("click", closeModal);

  function closeModal() {
    modalBackdrop.classList.add("hidden");
    modalBody.innerHTML = "";
    document.getElementById("modal-save").onclick = null;
  }

  function openEditModal(fl) {
    modalTitle.textContent = "Edit " + fl.favorite_key;
    modalBody.innerHTML = "";
    const select = document.createElement("select");
    EDITABLE_FIELDS.forEach((f) => {
      const opt = document.createElement("option");
      opt.value = f;
      opt.textContent = f;
      select.appendChild(opt);
    });
    const label1 = document.createElement("label");
    label1.textContent = "Field";
    label1.appendChild(select);
    modalBody.appendChild(label1);

    const valueInput = document.createElement("input");
    valueInput.type = "text";
    const label2 = document.createElement("label");
    label2.textContent = "Value";
    label2.appendChild(valueInput);
    modalBody.appendChild(label2);

    function syncValue() {
      valueInput.value = fl[select.value] != null ? fl[select.value] : "";
    }
    select.addEventListener("change", syncValue);
    syncValue();

    modalBackdrop.classList.remove("hidden");
    document.getElementById("modal-save").onclick = async () => {
      try {
        await apiPost("/api/v1/profile/edit", { slug: fl.slug, field: select.value, value: valueInput.value });
        closeModal();
        loadProfile();
        loadDashboard();
      } catch (e) {
        setStatus("Edit failed: " + e.message, true);
      }
    };
  }

  document.getElementById("add-local-btn").addEventListener("click", () => {
    modalTitle.textContent = "Add local Favorites List";
    modalBody.innerHTML = "";
    const fields = [
      ["key", "Key (e.g. LOCAL01)"],
      ["favorite_name", "Name"],
      ["region", "Region"],
      ["counties", "Counties"],
      ["scenario", "Scenario"],
      ["mode", "Mode"],
      ["notes", "Notes"],
    ];
    const inputs = {};
    fields.forEach(([name, label]) => {
      const l = document.createElement("label");
      l.textContent = label;
      const input = document.createElement("input");
      input.type = "text";
      l.appendChild(input);
      modalBody.appendChild(l);
      inputs[name] = input;
    });
    modalBackdrop.classList.remove("hidden");
    document.getElementById("modal-save").onclick = async () => {
      const body = {};
      Object.keys(inputs).forEach((k) => (body[k] = inputs[k].value));
      try {
        await apiPost("/api/v1/profile/local", body);
        closeModal();
        loadProfile();
        loadDashboard();
      } catch (e) {
        setStatus("Add failed: " + e.message, true);
      }
    };
  });

  // -------------------------------------------------------------- export --
  async function downloadBlobFrom(path, fallbackName, options) {
    const resp = await api(path, options);
    const blob = await resp.blob();
    const disposition = resp.headers.get("Content-Disposition") || "";
    const match = /filename="([^"]+)"/.exec(disposition);
    const filename = match ? match[1] : fallbackName;
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    return filename;
  }

  async function downloadExport(format) {
    try {
      setStatus("Preparing " + format + " export…");
      const filename = await downloadBlobFrom("/api/v1/export/" + format, "wasds150-export." + format);
      setStatus("Downloaded " + filename);
    } catch (e) {
      setStatus("Export failed: " + e.message, true);
    }
  }
  document.getElementById("export-csv").addEventListener("click", () => downloadExport("csv"));
  document.getElementById("export-md").addEventListener("click", () => downloadExport("md"));
  document.getElementById("export-zip").addEventListener("click", () => downloadExport("zip"));

  document.getElementById("generate-btn").addEventListener("click", async () => {
    try {
      const result = await apiPost("/api/v1/generate", {});
      document.getElementById("export-result").textContent = JSON.stringify(result, null, 2);
      setStatus("Generated snapshot " + result.snapshot_id);
      loadHistory();
      loadHpeList();
      loadDashboard();
    } catch (e) {
      setStatus("Generate failed: " + e.message, true);
    }
  });

  // ------------------------------------------------------- per-list .hpe --
  let sentinelPlanId = "";

  async function loadHpeList() {
    try {
      const data = await apiGet("/api/v1/profile");
      const tbody = document.querySelector("#hpe-list-table tbody");
      tbody.innerHTML = "";
      (data.favorites || [])
        .filter((fl) => fl.enabled)
        .forEach((fl) => {
          const hasSystems = (fl.systems || []).length > 0;
          const tr = document.createElement("tr");
          const selectCell = document.createElement("td");
          const checkbox = document.createElement("input");
          checkbox.type = "checkbox";
          checkbox.className = "sentinel-list-select";
          checkbox.dataset.slug = fl.slug;
          checkbox.checked = hasSystems;
          checkbox.disabled = !hasSystems;
          checkbox.setAttribute("aria-label", `Select ${fl.favorite_key} for Sentinel bulk install`);
          checkbox.addEventListener("change", updateSentinelSelectedCount);
          selectCell.appendChild(checkbox);
          tr.appendChild(selectCell);
          [fl.favorite_key, fl.favorite_name].forEach((value) => {
            const cell = document.createElement("td");
            cell.textContent = value;
            tr.appendChild(cell);
          });
          const statusCell = document.createElement("td");
          const actionCell = document.createElement("td");
          tr.append(statusCell, actionCell);
          if (hasSystems) {
            const pill = document.createElement("span");
            pill.className = "pill enabled";
            pill.textContent = `${fl.systems.length} system(s)`;
            statusCell.appendChild(pill);
            const btn = document.createElement("button");
            btn.textContent = "Download .hpe";
            btn.addEventListener("click", async () => {
              try {
                const filename = await downloadBlobFrom("/api/v1/generate/hpe/" + encodeURIComponent(fl.slug), fl.favorite_key + ".hpe");
                setStatus("Downloaded " + filename);
              } catch (e) {
                setStatus("Download failed: " + e.message, true);
              }
            });
            actionCell.appendChild(btn);
          } else {
            const pill = document.createElement("span");
            pill.className = "pill disabled";
            pill.textContent = "none yet";
            statusCell.appendChild(pill);
            actionCell.textContent = "needs local HPDB/RR match or manual entry";
          }
          tbody.appendChild(tr);
        });
      updateSentinelSelectedCount();
    } catch (e) {
      setStatus("HPE list error: " + e.message, true);
    }
  }

  function selectedSentinelSlugs() {
    return Array.from(document.querySelectorAll(".sentinel-list-select:checked")).map(
      (checkbox) => checkbox.dataset.slug
    );
  }

  function updateSentinelSelectedCount() {
    const count = selectedSentinelSlugs().length;
    document.getElementById("sentinel-selected-count").textContent = `${count} selected`;
    document.getElementById("sentinel-execute-btn").disabled = true;
    sentinelPlanId = "";
  }

  async function loadSentinelWorkspace() {
    const workspaceInput = document.getElementById("sentinel-workspace");
    const query = workspaceInput.value ? "?path=" + encodeURIComponent(workspaceInput.value) : "";
    try {
      const data = await apiGet("/api/v1/sentinel/workspace" + query);
      workspaceInput.value = data.workspace || "";
      if (!document.getElementById("sentinel-backup-dir").value) {
        document.getElementById("sentinel-backup-dir").value = data.default_backup_dir || "";
      }
      const profile = document.getElementById("sentinel-profile");
      profile.replaceChildren();
      (data.profiles || []).forEach((name) => {
        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        profile.appendChild(option);
      });
      if (!data.exists) setStatus("Sentinel workspace was not found at the selected path.", true);
    } catch (error) {
      setStatus("Sentinel discovery failed: " + error.message, true);
    }
  }

  async function runSentinelBulkInstall(execute) {
    const body = {
      workspace: document.getElementById("sentinel-workspace").value,
      profile_name: document.getElementById("sentinel-profile").value,
      backup_dir: document.getElementById("sentinel-backup-dir").value,
      slugs: selectedSentinelSlugs(),
      execute: Boolean(execute),
      confirm: document.getElementById("sentinel-confirm").value,
      plan_id: sentinelPlanId,
      allow_replacements: document.getElementById("sentinel-allow-replacements").checked,
    };
    if (!body.slugs.length) {
      setStatus("Select at least one populated Favorites List.", true);
      return;
    }
    if (execute && !confirm(`Close Sentinel before continuing. Install ${body.slugs.length} selected lists into profile ${body.profile_name}?`)) {
      return;
    }
    try {
      setStatus(execute ? "Backing up and installing selected lists…" : "Planning Sentinel bulk install…");
      const data = await apiPost("/api/v1/sentinel/install", body);
      document.getElementById("sentinel-install-result").textContent = JSON.stringify(data, null, 2);
      if (!execute) {
        sentinelPlanId = data.plan_id;
        document.getElementById("sentinel-confirm").placeholder = data.confirmation_phrase;
        document.getElementById("sentinel-execute-btn").disabled = false;
        setStatus(`Plan ready for ${data.assignments.length} lists. Type ${data.confirmation_phrase} to execute.`);
      } else {
        sentinelPlanId = "";
        document.getElementById("sentinel-execute-btn").disabled = true;
        setStatus(`Installed and verified ${data.assignments.length} lists. Reopen Sentinel to inspect them.`);
      }
    } catch (error) {
      document.getElementById("sentinel-execute-btn").disabled = true;
      setStatus("Sentinel bulk install failed: " + error.message, true);
    }
  }

  document.getElementById("sentinel-select-all").addEventListener("click", () => {
    document.querySelectorAll(".sentinel-list-select:not(:disabled)").forEach((checkbox) => { checkbox.checked = true; });
    updateSentinelSelectedCount();
  });
  document.getElementById("sentinel-select-none").addEventListener("click", () => {
    document.querySelectorAll(".sentinel-list-select").forEach((checkbox) => { checkbox.checked = false; });
    updateSentinelSelectedCount();
  });
  document.getElementById("sentinel-discover-btn").addEventListener("click", loadSentinelWorkspace);
  document.getElementById("sentinel-plan-btn").addEventListener("click", () => runSentinelBulkInstall(false));
  document.getElementById("sentinel-execute-btn").addEventListener("click", () => runSentinelBulkInstall(true));

  async function loadHistory() {
    try {
      const data = await apiGet("/api/v1/history");
      const tbody = document.querySelector("#history-table tbody");
      tbody.innerHTML = "";
      (data.snapshots || []).slice().reverse().forEach((snap) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td>${snap.id}</td><td>${snap.created_at}</td><td>${snap.message || ""}</td><td class="hash">${snap.content_hash.slice(0, 16)}…</td><td></td>`;
        const rollbackBtn = document.createElement("button");
        rollbackBtn.textContent = "Rollback";
        rollbackBtn.addEventListener("click", async () => {
          if (!confirm(`Restore profile to snapshot ${snap.id}? A backup of the current profile is kept.`)) return;
          await apiPost("/api/v1/history/" + snap.id + "/rollback", {});
          setStatus("Rolled back to " + snap.id);
          loadProfile();
          loadDashboard();
        });
        tr.lastElementChild.appendChild(rollbackBtn);
        tbody.appendChild(tr);
      });
    } catch (e) {
      setStatus("History error: " + e.message, true);
    }
  }

  // ------------------------------------------------------- advanced: hpe --
  function fileToBase64(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const result = reader.result; // "data:...;base64,XXXX"
        resolve(result.substring(result.indexOf(",") + 1));
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }

  async function hpeAction(endpoint) {
    const input = document.getElementById("hpe-file-input");
    const resultBox = document.getElementById("hpe-result");
    if (!input.files.length) {
      setStatus("Choose a .hpe/.hpd file first", true);
      return;
    }
    try {
      const content_base64 = await fileToBase64(input.files[0]);
      const result = await apiPost("/api/v1/hpe/" + endpoint, { content_base64 });
      resultBox.textContent = JSON.stringify(result, null, 2);
      setStatus(endpoint + " complete");
    } catch (e) {
      setStatus("HPE " + endpoint + " failed: " + e.message, true);
    }
  }
  document.getElementById("hpe-inspect-btn").addEventListener("click", () => hpeAction("inspect"));
  document.getElementById("hpe-validate-btn").addEventListener("click", () => hpeAction("validate"));

  // ----------------------------------------------------- advanced: merge --
  document.getElementById("merge-preview-btn").addEventListener("click", async () => {
    const upstream_path = document.getElementById("merge-upstream-path").value;
    const resultBox = document.getElementById("merge-result");
    try {
      const result = await apiPost("/api/v1/merge/preview", { upstream_path });
      resultBox.textContent = JSON.stringify(result, null, 2);
      setStatus(`Merge preview: ${result.changes.length} change(s), ${result.conflicts.length} conflict(s)`);
    } catch (e) {
      setStatus("Merge preview failed: " + e.message, true);
    }
  });
  document.getElementById("merge-apply-btn").addEventListener("click", async () => {
    const upstream_path = document.getElementById("merge-upstream-path").value;
    const resultBox = document.getElementById("merge-result");
    if (!confirm("Apply this merge? The merged catalog becomes your new baseline. Your presentation overrides are always preserved.")) return;
    try {
      let result;
      try {
        result = await apiPost("/api/v1/merge/apply", { upstream_path, force: false });
      } catch (e) {
        if (!confirm("Conflicts were found. Local overrides are preserved either way — apply anyway?")) throw e;
        result = await apiPost("/api/v1/merge/apply", { upstream_path, force: true });
      }
      resultBox.textContent = JSON.stringify(result, null, 2);
      setStatus("Merge applied");
      loadDashboard();
    } catch (e) {
      setStatus("Merge apply failed: " + e.message, true);
    }
  });

  // --------------------------------------------------- advanced: install --
  async function loadInstallVolumes() {
    try {
      const data = await apiGet("/api/v1/install/detect");
      const tbody = document.querySelector("#install-volumes-table tbody");
      tbody.innerHTML = "";
      (data.volumes || []).forEach((v) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td>${v.mount_point}</td><td>${v.is_sds150_candidate ? "yes" : "no"}</td>`;
        tbody.appendChild(tr);
      });
      setStatus(`Found ${(data.volumes || []).length} candidate volume(s)`);
    } catch (e) {
      setStatus("Detect failed: " + e.message, true);
    }
  }
  document.getElementById("install-detect-btn").addEventListener("click", loadInstallVolumes);

  // Default workflow: profile -> generated favorites -> install. Only
  // Favorites Lists with 1+ populated systems are offered, since those
  // are the only ones that can produce a real (non-empty) write.
  async function loadInstallSlugOptions() {
    try {
      const data = await apiGet("/api/v1/profile");
      const select = document.getElementById("install-slug-select");
      select.innerHTML = "";
      (data.favorites || [])
        .filter((fl) => fl.enabled && (fl.systems || []).length > 0)
        .forEach((fl) => {
          const opt = document.createElement("option");
          opt.value = fl.slug;
          opt.textContent = `${fl.favorite_key} — ${fl.favorite_name} (${fl.systems.length} system(s))`;
          select.appendChild(opt);
        });
      if (!select.options.length) {
        const opt = document.createElement("option");
        opt.value = "";
        opt.textContent = "(no Favorites Lists with structured systems yet)";
        select.appendChild(opt);
      }
    } catch (e) {
      setStatus("Could not load generated Favorites Lists: " + e.message, true);
    }
  }

  const installGeneratedPanel = document.getElementById("install-generated-panel");
  const installRawPanel = document.getElementById("install-raw-panel");
  function updateInstallSourceMode() {
    const useRaw = document.getElementById("install-source-raw").checked;
    installGeneratedPanel.classList.toggle("hidden", useRaw);
    installRawPanel.classList.toggle("hidden", !useRaw);
  }
  document.getElementById("install-source-generated").addEventListener("change", updateInstallSourceMode);
  document.getElementById("install-source-raw").addEventListener("change", updateInstallSourceMode);

  document.getElementById("install-backup-btn").addEventListener("click", async () => {
    const mount = document.getElementById("install-mount").value;
    const out_dir = document.getElementById("install-backup-dir").value;
    const resultBox = document.getElementById("install-result");
    try {
      const result = await apiPost("/api/v1/install/backup", { mount, out_dir });
      resultBox.textContent = JSON.stringify(result, null, 2);
      setStatus("Backup written: " + result.backup_path);
    } catch (e) {
      setStatus("Backup failed: " + e.message, true);
    }
  });

  function readInstallSystemsPayload() {
    const raw = document.getElementById("install-systems-json").value;
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : parsed.systems || [];
  }

  async function installWrite(execute) {
    const resultBox = document.getElementById("install-result");
    try {
      const useRaw = document.getElementById("install-source-raw").checked;
      const body = {
        mount: document.getElementById("install-mount").value,
        index: parseInt(document.getElementById("install-index").value || "0", 10),
        backup_dir: document.getElementById("install-backup-dir").value,
        execute: execute,
      };
      const userName = document.getElementById("install-user-name").value;
      if (userName) body.user_name = userName;
      if (useRaw) {
        body.systems = readInstallSystemsPayload();
      } else {
        body.slug = document.getElementById("install-slug-select").value;
        if (!body.slug) throw new Error("choose a generated Favorites List first (or switch to Raw Systems JSON)");
      }
      if (execute) {
        body.confirm = document.getElementById("install-confirm-phrase").value;
      }
      const result = await apiPost("/api/v1/install/write", body);
      resultBox.textContent = JSON.stringify(result, null, 2);
      setStatus(execute ? "Write complete" : "Dry run complete");
    } catch (e) {
      setStatus("Install write failed: " + e.message, true);
    }
  }
  document.getElementById("install-dry-run-btn").addEventListener("click", () => installWrite(false));

  const executeBtn = document.getElementById("install-execute-btn");
  const confirmInput = document.getElementById("install-confirm-phrase");
  confirmInput.addEventListener("input", () => {
    const mount = document.getElementById("install-mount").value;
    const label = mount.split("/").filter(Boolean).pop() || mount;
    executeBtn.disabled = confirmInput.value !== `WRITE ${label}`;
  });
  executeBtn.addEventListener("click", () => {
    if (!confirm("This will WRITE to the SD card for real, after taking a mandatory backup. Continue?")) return;
    installWrite(true);
  });

  document.getElementById("install-rollback-btn").addEventListener("click", async () => {
    const mount = document.getElementById("install-mount").value;
    const backup = document.getElementById("install-rollback-backup").value;
    const resultBox = document.getElementById("install-result");
    if (!confirm("Restore this card from the given backup? Anything written since the backup will be removed.")) return;
    try {
      const result = await apiPost("/api/v1/install/rollback", { mount, backup });
      resultBox.textContent = JSON.stringify(result, null, 2);
      setStatus("Rollback complete");
    } catch (e) {
      setStatus("Rollback failed: " + e.message, true);
    }
  });

  // ---------------------------------------------------- advanced: sources --
  let lastSourcesList = [];

  async function loadSourcesList() {
    try {
      const data = await apiGet("/api/v1/sources");
      lastSourcesList = data.sources || [];
      renderSourcesTable(lastSourcesList, {});
    } catch (e) {
      setStatus("Sources list failed: " + e.message, true);
    }
  }
  document.getElementById("sources-list-btn").addEventListener("click", loadSourcesList);

  document.getElementById("sources-status-btn").addEventListener("click", async () => {
    try {
      const data = await apiGet("/api/v1/sources/status");
      document.getElementById("sources-offline").checked = !!data.offline;
      const statusByName = {};
      (data.sources || []).forEach((s) => (statusByName[s.name] = s));
      renderSourcesTable(lastSourcesList, statusByName);
      setStatus("Offline mode: " + data.offline);
    } catch (e) {
      setStatus("Sources status failed: " + e.message, true);
    }
  });

  function renderSourcesTable(sources, statusByName) {
    const tbody = document.querySelector("#sources-table tbody");
    tbody.innerHTML = "";
    sources.forEach((s) => {
      const st = statusByName[s.name] || {};
      const tr = document.createElement("tr");
      tr.innerHTML =
        `<td>${s.name}</td><td>${s.kind}</td><td>${s.available ? "yes" : "no"}</td>` +
        `<td>${st.cached_urls !== undefined ? st.cached_urls : ""}</td>` +
        `<td>${st.most_recent_fetch || ""}</td><td></td>`;
      const actionCell = tr.querySelector("td:last-child");
      if (s.available && s.kind !== "legacy") {
        const btn = document.createElement("button");
        btn.textContent = "Fetch";
        btn.addEventListener("click", () => sourcesFetchOne(s.name));
        actionCell.appendChild(btn);
      }
      tbody.appendChild(tr);
    });
  }

  async function sourcesFetchOne(name) {
    const resultBox = document.getElementById("sources-result");
    try {
      const result = await apiPost("/api/v1/sources/fetch", { name: name });
      resultBox.textContent = JSON.stringify(result, null, 2);
      setStatus(`Fetched ${name}: ${result.outcome.fact_count} fact(s)`);
    } catch (e) {
      setStatus(`Fetch ${name} failed: ` + e.message, true);
    }
  }

  document.getElementById("sources-configure-btn").addEventListener("click", async () => {
    const resultBox = document.getElementById("sources-result");
    try {
      const body = {
        offline: document.getElementById("sources-offline").checked,
        sentinel_local_mount: document.getElementById("sources-sentinel-mount").value,
        sentinel_local_hpdb_cfg: document.getElementById("sources-sentinel-hpdb-cfg").value,
        radioreference_export_path: document.getElementById("sources-rr-export-path").value,
      };
      const result = await apiPost("/api/v1/sources/configure", body);
      resultBox.textContent = JSON.stringify(result, null, 2);
      setStatus("Source configuration saved");
    } catch (e) {
      setStatus("Configure failed: " + e.message, true);
    }
  });

  function sourcesOnlyList() {
    const raw = document.getElementById("sources-only").value.trim();
    return raw ? raw.split(",").map((s) => s.trim()).filter(Boolean) : undefined;
  }

  async function sourcesUpdate(apply) {
    const resultBox = document.getElementById("sources-result");
    if (apply && !confirm("Apply this update? Local presentation overrides are always preserved; only upstream fact fields may change, and only for rows with no conflicting override.")) return;
    try {
      const body = { only: sourcesOnlyList(), apply: apply, force: false };
      let result;
      try {
        result = await apiPost("/api/v1/sources/update", body);
      } catch (e) {
        if (apply && confirm("Conflicts were found. Local overrides are preserved either way — apply anyway?")) {
          result = await apiPost("/api/v1/sources/update", Object.assign({}, body, { force: true }));
        } else {
          throw e;
        }
      }
      resultBox.textContent = JSON.stringify(result, null, 2);
      setStatus(apply ? "Update applied" : "Update preview complete");
      if (apply) loadDashboard();
    } catch (e) {
      setStatus("Sources update failed: " + e.message, true);
    }
  }
  document.getElementById("sources-update-preview-btn").addEventListener("click", () => sourcesUpdate(false));
  document.getElementById("sources-update-apply-btn").addEventListener("click", () => sourcesUpdate(true));

  document.getElementById("sources-provenance-btn").addEventListener("click", async () => {
    const slug = document.getElementById("sources-provenance-slug").value.trim();
    const resultBox = document.getElementById("sources-result");
    if (!slug) return;
    try {
      const result = await apiGet("/api/v1/sources/provenance/" + encodeURIComponent(slug));
      resultBox.textContent = JSON.stringify(result, null, 2);
      setStatus(`Provenance for ${slug}: ${result.provenance.length} entr${result.provenance.length === 1 ? "y" : "ies"}`);
    } catch (e) {
      setStatus("Provenance lookup failed: " + e.message, true);
    }
  });

  // ------------------------------------------------------------- initial --
  loadDashboard();
})();
