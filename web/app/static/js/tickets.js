// Ticket list + dashboard cards, used by both the employee and the IT pages.
(async () => {
  const page = document.getElementById("ticket-page");
  const isIT = page.dataset.mode === "it";
  const user = await requireUser(isIT ? "it_team" : "employee");
  if (!user) return;

  const form = document.getElementById("filters");
  const rows = document.getElementById("ticket-rows");
  const count = document.getElementById("count");
  const statsBox = document.getElementById("stats");
  const columns = isIT ? 8 : 7;

  const heroName = document.getElementById("hero-name");
  if (heroName) heroName.textContent = user.full_name.split(" ")[0];

  /* ---------- dashboard cards ---------- */
  const pct = (n, total) => (total ? Math.round((n * 100) / total) : 0);
  const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;

  const GAUGE_PATH = "M 20 100 A 80 80 0 0 1 180 100";
  function gauge(segments, total) {
    const active = segments.filter((s) => s.value > 0);
    let offset = 0;
    const gap = active.length > 1 ? 1.4 : 0;
    const arcs = active
      .map((s) => {
        const len = (s.value / total) * 100;
        const draw = Math.max(len - gap, 0.6);
        const arc = `<path d="${GAUGE_PATH}" pathLength="100" fill="none" stroke="${s.stroke}" stroke-width="26" stroke-dasharray="${draw} ${100 - draw}" stroke-dashoffset="${-(offset + gap / 2)}"/>`;
        offset += len;
        return arc;
      })
      .join("");
    return `<svg viewBox="0 0 200 110" role="img" aria-label="Tickets by status">
      <defs><pattern id="hatch" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
        <rect width="5" height="5" fill="#b3bccb"/><line x1="0" y1="0" x2="0" y2="5" stroke="#97a2b5" stroke-width="2"/></pattern></defs>
      <path class="g-track" d="${GAUGE_PATH}" />${arcs}</svg>`;
  }

  function bar(colorClass, percent) {
    const w = percent > 0 ? Math.max(percent, 4) : 0;
    return `<div class="bar"><span class="${colorClass}" data-w="${w}"></span></div>`;
  }

  function renderStats(all) {
    const total = all.length;
    const count = (s) => all.filter((t) => t.status === s).length;
    const st = { Open: count("Open"), Assigned: count("Assigned"), "In Progress": count("In Progress"), Closed: count("Closed") };
    const active = total - st.Closed;
    const unassigned = all.filter((t) => !t.assignee && t.status !== "Closed").length;
    const resolved = pct(st.Closed, total);

    const priorities = [
      ["High", "c-orange"],
      ["Medium", "c-navy"],
      ["Low", "c-slate"],
    ].map(([name, cls]) => ({ name, cls, n: all.filter((t) => t.status !== "Closed" && t.priority === name).length }));

    const segments = [
      { label: "Open", value: st.Open, stroke: "#ff5a1f", cls: "c-orange" },
      { label: "Assigned", value: st.Assigned, stroke: "#1b2a3d", cls: "c-navy" },
      { label: "In Progress", value: st["In Progress"], stroke: "url(#hatch)", cls: "c-slate" },
      { label: "Closed", value: st.Closed, stroke: "#dfe3ea", cls: "c-light" },
    ];

    const hero = document.getElementById("hero-sub");
    if (hero) {
      hero.textContent = isIT
        ? `${plural(active, "active ticket")}, ${unassigned} waiting for an assignee.`
        : active
        ? `You have ${plural(active, "active ticket")} with IT.`
        : "No active tickets. Create one if something needs fixing.";
    }

    statsBox.innerHTML = `
      <div class="card card-gauge">
        <div class="card-title"><span class="icon-circle">${ICONS.flag}</span>${isIT ? "Tickets by status" : "My tickets by status"}</div>
        <div class="gauge">${gauge(segments, total)}
          <div class="gauge-center"><strong>${total}</strong><span>Total tickets</span></div></div>
        <ul class="legend">${segments.map((s) => `<li><i class="dot ${s.cls}"></i>${esc(s.label)} <b>${s.value}</b></li>`).join("")}</ul>
      </div>

      <div class="card card-work">
        <div class="card-title"><span class="icon-circle">${ICONS.flag}</span>${isIT ? "Workload" : "Progress"}</div>
        <div class="work">
          <div>
            <div class="big-number">${total}</div>
            <div class="lbl">${isIT ? "Received" : "Submitted"}</div>
            <button type="button" class="pill-btn" data-scroll="ticket-list">Details</button>
          </div>
          <div>
            <div class="mini">
              <div class="mini-top"><b>${st.Closed}</b><small>closed</small></div>
              ${bar("c-navy", resolved)}
              <span class="chip chip-green">${resolved}% resolved</span>
            </div>
            <div class="mini">
              <div class="mini-top"><b>${unassigned}</b><small>${isIT ? "unassigned" : "awaiting assignment"}</small></div>
              ${bar("c-orange", pct(unassigned, active))}
              <span class="chip chip-pink">${isIT ? "needs an owner" : "in the queue"}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="card card-tall">
        <div class="big-number">${active}<span class="arrow-btn">${ICONS.arrowUpRight}</span></div>
        <div class="sub-row"><span>Active tickets</span><button type="button" class="pill-btn" data-scroll="ticket-list">Details</button></div>
        ${priorities
          .map(
            (p) => `<div class="stat-row">
              <div class="stat-label"><i class="tick ${p.cls}"></i>${p.name} priority</div>
              ${bar(p.cls, pct(p.n, active))}
              <div class="stat-meta"><b>${pct(p.n, active)}%</b> &middot; ${plural(p.n, "ticket")}</div>
            </div>`
          )
          .join("")}
      </div>`;

    // Bar widths are set through the CSSOM (inline style attributes are blocked by our CSP).
    statsBox.querySelectorAll("[data-w]").forEach((el) => requestAnimationFrame(() => (el.style.width = el.dataset.w + "%")));
    statsBox.querySelectorAll("[data-scroll]").forEach((btn) =>
      btn.addEventListener("click", () => document.getElementById(btn.dataset.scroll).scrollIntoView({ behavior: "smooth" }))
    );
  }

  async function loadStats() {
    try {
      renderStats(await api("/tickets")); // always unfiltered
    } catch (e) {
      statsBox.innerHTML = "";
    }
  }

  /* ---------- filters + table ---------- */
  if (isIT) {
    try {
      await loadCategories(form.elements["category_id"]);
      for (const u of await api("/users/it-team")) form.elements["assigned"].add(new Option(u.full_name, u.id));
    } catch (e) {
      count.textContent = e.message;
    }
  }

  function buildQuery() {
    const params = new URLSearchParams();
    for (const name of ["q", "status", "priority", "category_id"]) {
      const el = form.elements[name];
      if (el && el.value.trim()) params.set(name, el.value.trim());
    }
    const assigned = form.elements["assigned"];
    if (assigned && assigned.value) {
      if (assigned.value === "unassigned") params.set("unassigned", "true");
      else params.set("assigned_to", assigned.value);
    }
    return params.toString();
  }

  function row(t) {
    const cells = [
      `<td><a class="ticket-id" href="/tickets/${t.id}">#${t.id}</a></td>`,
      `<td class="wrap"><a class="ticket-link" href="/tickets/${t.id}">${esc(t.title)}</a></td>`,
    ];
    if (isIT) cells.push(`<td><span class="person">${avatar(t.creator.full_name, "sm")}${esc(t.creator.full_name)}</span></td>`);
    cells.push(
      `<td>${esc(t.category.name)}</td>`,
      `<td>${badge("priority", t.priority)}</td>`,
      `<td>${badge("status", t.status)}</td>`,
      `<td>${t.assignee ? `<span class="person">${avatar(t.assignee.full_name, "sm")}${esc(t.assignee.full_name)}</span>` : '<span class="muted">Unassigned</span>'}</td>`,
      `<td class="muted">${esc(formatDate(t.created_at))}</td>`
    );
    return `<tr>${cells.join("")}</tr>`;
  }

  let requestId = 0;
  async function load() {
    const current = ++requestId;
    try {
      const tickets = await api(`/tickets?${buildQuery()}`);
      if (current !== requestId) return; // a newer request superseded this one
      rows.innerHTML = tickets.length
        ? tickets.map(row).join("")
        : `<tr><td colspan="${columns}" class="muted">No tickets found.</td></tr>`;
      count.textContent = plural(tickets.length, "ticket");
    } catch (e) {
      if (e.status === 401) return (window.location.href = "/login");
      rows.innerHTML = `<tr><td colspan="${columns}"><span class="alert alert-bad">${esc(e.message)}</span></td></tr>`;
    }
  }

  let timer;
  form.addEventListener("input", (e) => {
    if (e.target.name === "q") {
      clearTimeout(timer);
      timer = setTimeout(load, 300);
    }
  });
  form.addEventListener("change", (e) => {
    if (e.target.name !== "q") load();
  });
  form.addEventListener("submit", (e) => e.preventDefault());
  const reset = document.getElementById("reset-filters");
  if (reset) reset.addEventListener("click", () => { form.reset(); load(); });

  loadStats();
  load();
})();
