// Shared helpers: API client, auth guard, header, formatting, icons.
const API_BASE = document.body.dataset.apiBase || "";

const ICONS = {
  flag: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" y1="22" x2="4" y2="15"/></svg>',
  arrowUpRight: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><line x1="7" y1="17" x2="17" y2="7"/><polyline points="7 7 17 7 17 17"/></svg>',
};

class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

function formatDetail(detail) {
  if (!detail) return "";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((e) => {
        const field = (e.loc || []).slice(1).join(".");
        return field ? `${field}: ${e.msg}` : e.msg;
      })
      .join("; ");
  }
  return "Request failed";
}

// All calls go to the FastAPI service; the JWT travels in an httpOnly cookie.
async function api(path, { method = "GET", body } = {}) {
  const options = { method, credentials: "include", headers: { "X-Requested-With": "fetch" } };
  if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  let res;
  try {
    res = await fetch(`${API_BASE}/api${path}`, options);
  } catch (e) {
    throw new ApiError(0, "Cannot reach the server. Please try again.");
  }
  if (res.status === 204) return null;
  let data = null;
  try {
    data = await res.json();
  } catch (e) {
    /* non-JSON body */
  }
  if (!res.ok) throw new ApiError(res.status, formatDetail(data && data.detail) || res.statusText);
  return data;
}

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function slug(value) {
  return String(value).toLowerCase().replace(/[^a-z0-9]+/g, "-");
}

function badge(kind, value) {
  return `<span class="badge ${kind}-${slug(value)}"><i></i>${esc(value)}</span>`;
}

function initials(name) {
  const parts = String(name || "?").trim().split(/\s+/);
  return ((parts[0] || "?")[0] + (parts.length > 1 ? parts[parts.length - 1][0] : "")).toUpperCase();
}

function avatar(name, extra = "") {
  return `<span class="avatar ${extra}" title="${esc(name)}">${esc(initials(name))}</span>`;
}

// The API returns UTC timestamps without a timezone suffix.
function formatDate(value) {
  if (!value) return "";
  const d = new Date(/[zZ]|[+-]\d\d:\d\d$/.test(value) ? value : value + "Z");
  return d.toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
}

function homeFor(role) {
  return role === "it_team" ? "/it/tickets" : "/tickets";
}

function showMessage(el, text) {
  el.textContent = text || "";
  el.hidden = !text;
}

function setupHeader(user) {
  document.getElementById("user-avatar").textContent = initials(user.full_name);
  document.getElementById("user-name").textContent = user.full_name;
  document.getElementById("user-role").textContent = user.role === "it_team" ? "IT team" : "Employee";
  document.getElementById("user-box").hidden = false;
  const nav = document.getElementById("nav");
  const links = user.role === "it_team" ? [["/it/tickets", "Dashboard"]] : [["/tickets", "My tickets"], ["/tickets/new", "New ticket"]];
  nav.innerHTML = links
    .map(([href, label]) => `<a href="${href}"${window.location.pathname === href ? ' class="active"' : ""}>${esc(label)}</a>`)
    .join("");
  document.getElementById("logout-btn").addEventListener("click", async () => {
    try {
      await api("/auth/logout", { method: "POST" });
    } finally {
      window.location.href = "/login";
    }
  });
}

// Page guard. Real authorisation is enforced by the API; this only routes people sensibly.
async function requireUser(role) {
  try {
    const user = await api("/auth/me");
    if (role && user.role !== role) {
      window.location.href = homeFor(user.role);
      return null;
    }
    setupHeader(user);
    return user;
  } catch (e) {
    if (e.status === 401) {
      window.location.href = "/login";
      return null;
    }
    document.querySelector("main").innerHTML = `<p class="alert alert-bad">${esc(e.message)}</p>`;
    return null;
  }
}

async function loadCategories(select) {
  const categories = await api("/categories");
  for (const c of categories) select.add(new Option(c.name, c.id));
}

async function submitting(button, fn) {
  button.disabled = true;
  try {
    await fn();
  } finally {
    button.disabled = false;
  }
}
