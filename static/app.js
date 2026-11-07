const POLL_MS = 5000;

const SMART_GRID_MODE = { 0: "Normalbetrieb", 1: "Vorzugsbetrieb", 2: "Gesperrt", 3: "Abnahmezwang" };
const SMART_GRID_TRIGGER = { 0: "AUS", 1: "Eingangskontakte", 2: "Systembus", 3: "Verfügbare Leistung gedämpft" };

const $ = (id) => document.getElementById(id);

function setText(id, text) {
  $(id).textContent = text;
}

function setValue(id, value, unit = "") {
  if (value === null || value === undefined) {
    setText(id, "—");
  } else {
    setText(id, unit ? `${value} ${unit}` : String(value));
  }
}

function setColor(id, cls) {
  const el = $(id);
  el.classList.remove("c-good", "c-warn", "c-error", "c-off", "c-info", "c-temp", "c-power");
  if (cls) el.classList.add(cls);
}

function setBar(id, pct) {
  $(id).style.width = pct == null ? "0" : `${Math.max(0, Math.min(100, pct))}%`;
}

function setDot(id, state) {
  $(id).className = `conn-dot ${state}`;
}

function onOff(value) {
  if (value === null || value === undefined) return "—";
  return value ? "Ein" : "Aus";
}

function code(value) {
  return value === null || value === undefined ? "—" : `Code ${value}`;
}

function lookup(map, value) {
  if (value === null || value === undefined) return "—";
  return map[value] ?? `Unbekannt (${value})`;
}

function timeText(ts) {
  return ts ? new Date(ts * 1000).toLocaleTimeString("de-DE") : "—";
}

function render(state) {
  const solis = state.solis.values || {};
  const ctl = state.control;
  const hoval = state.hoval;
  const regs = hoval.registers || {};
  const sys = state.system;

  setDot("solis-dot", !state.solis.values ? "" : sys.last_error ? "disconnected" : "connected");
  setText("solis-text", !state.solis.values ? "Solis…" : sys.last_error ? "Solis Fehler" : "Solis verbunden");
  setDot("hoval-dot", hoval.registers_error ? "disconnected" : hoval.registers ? "connected" : "");
  setText("hoval-text", hoval.registers_error ? "Hoval Fehler" : hoval.registers ? "Hoval verbunden" : "Hoval…");
  setText("last-solis", timeText(state.solis.updated));
  setText("last-hoval", timeText(hoval.updated));

  const errors = [sys.last_error, hoval.registers_error].filter(Boolean);
  const banner = $("error-banner");
  banner.textContent = errors.join(" · ");
  banner.classList.toggle("visible", errors.length > 0);

  setValue("pill-pv", solis.pv_total_dc_power_w, "W");
  setValue("pill-grid", solis.grid_power_w, "W");
  setValue("pill-soc", solis.battery_soc_pct, "%");
  setValue("pill-load", solis.household_load_w, "W");
  setText("pill-overload", hoval.overloading ? "Ja" : "Nein");
  setColor("pill-overload", hoval.overloading ? "c-power" : "c-off");

  setValue("bv-pv", solis.pv_total_dc_power_w, "W");
  setValue("bv-load", solis.household_load_w, "W");
  setValue("bv-grid", solis.grid_power_w, "W");
  setValue("bv-bat", solis.battery_power_w, "W");
  setValue("bv-soc", solis.battery_soc_pct, "%");
  setBar("bv-soc-bar", solis.battery_soc_pct);

  $("ctl-toggle").checked = hoval.overloading;
  setText("ctl-state", hoval.overloading ? "EIN" : "AUS");
  setColor("ctl-state", hoval.overloading ? "c-good" : "c-off");
  setValue("ctl-surplus", ctl.total_surplus_w, "W");
  setValue("ctl-bat", ctl.bat_charge_w, "W");
  setValue("ctl-soc", ctl.soc, "%");
  setText("ctl-since", timeText(hoval.overload_since));
  setText("ctl-updated", timeText(ctl.updated));

  setValue("sol-ac", solis.ac_active_power_w, "W");
  setValue("sol-temp", solis.inverter_temperature_c, "°C");
  setValue("sol-status", solis.inverter_status);
  setValue("sol-op", solis.operating_status);
  setValue("sol-pv-e", solis.pv_energy_total_kwh, "kWh");
  setValue("sol-bat-in", solis.battery_charge_total_kwh, "kWh");
  setValue("sol-bat-out", solis.battery_discharge_total_kwh, "kWh");
  setValue("sol-imp", solis.grid_import_total_kwh, "kWh");
  setValue("sol-exp", solis.grid_export_total_kwh, "kWh");
  setValue("sol-load-e", solis.load_total_kwh, "kWh");

  setValue("hv-mod", regs.generator_modulation_pct);
  setBar("hv-mod-bar", regs.generator_modulation_pct);
  setValue("hv-vl", regs.generator_actual_c, "°C");
  setValue("hv-vl-soll", regs.generator_target_c, "°C");
  setValue("hv-rl", regs.generator_return_c, "°C");
  setValue("hv-af", regs.outdoor_temp_c, "°C");
  setValue("hv-th", regs.generator_power_kw, "kW");
  setValue("hv-el", regs.generator_el_power_kw, "kW");
  setValue("hv-sg-avail", regs.smart_grid_available_power_kw, "kW");
  setValue("hv-bsh", regs.generator_operating_hours, "h");
  setValue("hv-szy", regs.generator_switch_cycles);
  setText("hv-meldung", code(regs.generator_operating_message));
  setText("hv-status", code(regs.generator_status));
  setValue("hv-en-th", regs.generator_heat_energy_mwh, "MWh");
  setValue("hv-en-el", regs.generator_el_energy_mwh, "MWh");

  setValue("hk1-vl", regs.hk1_flow_actual_c, "°C");
  setValue("hk1-vl-soll", regs.hk1_flow_target_c, "°C");
  setValue("hk1-raum-soll", regs.hk1_room_target_c, "°C");
  setValue("hk1-rl", regs.hk1_return_c, "°C");
  setText("hk1-pumpe", onOff(regs.hk1_pump));
  setText("hk1-mode", code(regs.hk1_mode));
  setText("hk1-status", code(regs.hk1_status));

  setValue("ww-ist", regs.ww_actual_c, "°C");
  setValue("ww-soll", regs.ww_target_c, "°C");
  setText("ww-pumpe", onOff(regs.ww_charge_pump));
  setText("ww-status", code(regs.ww_status));

  setText("sg-mode", lookup(SMART_GRID_MODE, regs.smart_grid_systembus));
  setText("sg-trigger", lookup(SMART_GRID_TRIGGER, regs.smart_grid_trigger));
}

async function refresh() {
  try {
    const response = await fetch("/api/status", { cache: "no-store" });
    render(await response.json());
  } catch (err) {
    const banner = $("error-banner");
    banner.textContent = `App nicht erreichbar: ${err}`;
    banner.classList.add("visible");
  }
}

refresh();
setInterval(refresh, POLL_MS);
