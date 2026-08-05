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
    if (path.startsWith("/api/v1/export/") || path.startsWith("/api/v1/generate/hpe/")) {
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
  async function downloadBlobFrom(path, fallbackName) {
    const resp = await api(path);
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
