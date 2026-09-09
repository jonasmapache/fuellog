(function () {
  "use strict";

  var form = document.getElementById("entryForm");
  if (!form) return;

  var MAP_CFG = window.FUELLOG_MAP || { enabled: false };

  // ---------------- Entry-type toggle ----------------
  var typeRadios = Array.from(form.querySelectorAll('input[name="entry_type"]'));
  function currentType() {
    var checked = typeRadios.find(function (r) { return r.checked; });
    return checked ? checked.value : "fuel";
  }
  function applyType() {
    var odo = currentType() === "odometer_only";
    form.classList.toggle("odometer-only", odo);
    form.querySelectorAll(".step[data-fuel-only]").forEach(function (s) { s.hidden = odo; });
    form.querySelectorAll(".entry-type-toggle label").forEach(function (l) {
      l.classList.toggle("active", l.querySelector("input").checked);
    });
    if (wizard) { rebuildSteps(); show(Math.min(current, steps.length - 1)); }
  }
  typeRadios.forEach(function (r) { r.addEventListener("change", applyType); });

  // ---------------- Wizard navigation ----------------
  var wizard = form.classList.contains("wizard");
  var steps = [];
  var current = 0;
  var prevBtn = document.getElementById("prevBtn");
  var nextBtn = document.getElementById("nextBtn");

  function rebuildSteps() {
    steps = Array.from(form.querySelectorAll(".step")).filter(function (s) { return !s.hidden; });
  }

  function show(i) {
    current = Math.max(0, Math.min(i, steps.length - 1));
    steps.forEach(function (s, idx) { s.classList.toggle("active", idx === current); });
    if (prevBtn) prevBtn.disabled = current === 0;
    if (nextBtn) nextBtn.style.display = current === steps.length - 1 ? "none" : "block";
    var active = steps[current];
    if (active && active.querySelector("#minimap")) {
      ensureMap();
      setTimeout(function () { if (map) map.invalidateSize(); }, 50);
    }
  }

  if (wizard) {
    rebuildSteps();
    if (prevBtn) prevBtn.addEventListener("click", function () { show(current - 1); });
    if (nextBtn) nextBtn.addEventListener("click", function () { show(current + 1); });
    show(0);
  }

  applyType();

  // ---------------- Live liters / price / total ----------------
  var fLiters = document.getElementById("f_liters");
  var fPrice = document.getElementById("f_price");
  var fCost = document.getElementById("f_cost");

  function toNum(el) {
    var v = (el.value || "").trim().replace(",", ".");
    var n = parseFloat(v);
    return isNaN(n) ? null : n;
  }
  function autoCompute(changed) {
    if (!fLiters || !fPrice || !fCost) return;
    var l = toNum(fLiters), p = toNum(fPrice), c = toNum(fCost);
    if (changed !== "cost" && l !== null && p !== null && !fCost.value) {
      fCost.value = (l * p).toFixed(2).replace(".", ",");
    } else if (changed !== "liters" && p !== null && c !== null && !fLiters.value) {
      fLiters.value = (c / p).toFixed(2).replace(".", ",");
    } else if (changed !== "price" && l !== null && c !== null && !fPrice.value) {
      fPrice.value = (c / l).toFixed(3).replace(".", ",");
    }
  }
  if (fLiters) fLiters.addEventListener("blur", function () { autoCompute("liters"); });
  if (fPrice) fPrice.addEventListener("blur", function () { autoCompute("price"); });
  if (fCost) fCost.addEventListener("blur", function () { autoCompute("cost"); });

  // ---------------- Station autocomplete + minimap ----------------
  var nameInput = document.getElementById("station_name");
  if (!nameInput) return;

  var suggBox = document.getElementById("station_suggestions");
  var addrHidden = document.getElementById("station_address");
  var latHidden = document.getElementById("station_lat");
  var lonHidden = document.getElementById("station_lon");
  var addrDisplay = document.getElementById("station_address_display");
  var mapEl = document.getElementById("minimap");

  var map = null, marker = null;
  function ensureMap() {
    if (map || !mapEl || !MAP_CFG.enabled || typeof L === "undefined") return;
    map = L.map(mapEl).setView([51.1657, 10.4515], 5);
    L.tileLayer(MAP_CFG.tileUrl, { attribution: MAP_CFG.attribution, maxZoom: 19 }).addTo(map);
    var lat = parseFloat(latHidden.value), lon = parseFloat(lonHidden.value);
    if (!isNaN(lat) && !isNaN(lon)) setMarker(lat, lon);
  }
  function setMarker(lat, lon) {
    ensureMap();
    if (!map) return;
    if (marker) map.removeLayer(marker);
    marker = L.marker([lat, lon]).addTo(map);
    map.setView([lat, lon], 15);
    mapEl.classList.add("visible");
    setTimeout(function () { map.invalidateSize(); }, 50);
  }

  function renderSuggestions(items) {
    suggBox.innerHTML = "";
    items.forEach(function (it) {
      var div = document.createElement("div");
      div.className = "sugg-item";
      var tag = it.source === "osm" ? MAP_CFG.labels.osm : MAP_CFG.labels.known;
      div.textContent = it.name;
      var span = document.createElement("span");
      span.className = "sugg-source";
      span.textContent = tag;
      div.appendChild(span);
      div.addEventListener("click", function () {
        nameInput.value = it.name;
        addrHidden.value = it.address || "";
        addrDisplay.textContent = it.address || "";
        if (it.lat && it.lon) {
          latHidden.value = it.lat;
          lonHidden.value = it.lon;
          setMarker(it.lat, it.lon);
        }
        suggBox.innerHTML = "";
      });
      suggBox.appendChild(div);
    });
  }

  var debounceTimer = null;
  nameInput.addEventListener("input", function () {
    addrHidden.value = ""; latHidden.value = ""; lonHidden.value = "";
    addrDisplay.textContent = "";
    var q = nameInput.value.trim();
    if (q.length < 2) { suggBox.innerHTML = ""; return; }

    if (window.EXISTING_STATIONS) {
      renderSuggestions(window.EXISTING_STATIONS
        .filter(function (s) { return s.name.toLowerCase().indexOf(q.toLowerCase()) !== -1; })
        .slice(0, 6)
        .map(function (s) { return Object.assign({}, s, { source: "local" }); }));
    }

    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(function () {
      fetch("/api/stations/search?q=" + encodeURIComponent(q))
        .then(function (r) { return r.json(); })
        .then(renderSuggestions)
        .catch(function () {});
    }, 300);
  });

  document.addEventListener("click", function (e) {
    if (!suggBox.contains(e.target) && e.target !== nameInput) suggBox.innerHTML = "";
  });

  if (!wizard && MAP_CFG.enabled) {
    window.addEventListener("load", ensureMap);
  }
})();
