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

  /* ---------- dashboard: pipeline band + overview cards ---------- */
  const pct = (n, total) => (total ? Math.round((n * 100) / total) : 0);
  const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;
  const IMG = (name) => `/static/img/${name}`;

  function bar(colorClass, percent) {
    const w = percent > 0 ? Math.max(percent, 4) : 0;
    return `<div class="bar"><span class="${colorClass}" data-w="${w}"></span></div>`;
  }

  function feature({ title, icon, num, desc, cls, percent, tags }) {
    return `<article class="feature">
      <h3>${esc(title)}</h3>
      <span class="icon3d"><img src="${IMG(icon)}" alt=""></span>
      <div class="num">${num}</div>
      <p class="desc">${esc(desc)}</p>
      ${bar(cls, percent)}
      <div class="tags">${tags.map((t) => `<span>${esc(t)}</span>`).join("")}</div>
    </article>`;
  }

  function renderStats(all) {
    const total = all.length;
    const count = (s) => all.filter((t) => t.status === s).length;
    const st = { Open: count("Open"), Assigned: count("Assigned"), "In Progress": count("In Progress"), Closed: count("Closed") };
    const active = total - st.Closed;
    const unassigned = all.filter((t) => !t.assignee && t.status !== "Closed").length;
    const resolved = pct(st.Closed, total);
    const byPriority = (p) => all.filter((t) => t.status !== "Closed" && t.priority === p).length;

    const segments = [
      { label: "Open", value: st.Open, cls: "c-open",
        text: isIT ? "New requests waiting to be triaged." : "Received by IT, waiting to be picked up." },
      { label: "Assigned", value: st.Assigned, cls: "c-assigned",
        text: isIT ? "Owned by a team member, not started yet." : "An IT team member owns your request." },
      { label: "In Progress", value: st["In Progress"], cls: "c-progress",
        text: isIT ? "Actively being worked on." : "Being worked on now. Watch the comments." },
      { label: "Closed", value: st.Closed, cls: "c-closed",
        text: isIT ? "Resolved with notes on record." : "Resolved, with notes on what was done." },
    ];

    const hero = document.getElementById("hero-sub");
    if (hero) {
      hero.textContent = isIT
        ? `${plural(active, "active ticket")} in the queue, ${unassigned} waiting for an assignee.`
        : active
        ? `You have ${plural(active, "active ticket")} with IT. We'll keep you posted at every step.`
        : "No active tickets. Raise one whenever something needs fixing.";
    }

    const cta = isIT
      ? `<article class="cta-card"><h3>Pick up the unassigned queue now.</h3>
           <img src="${IMG("blob-cushion-green.svg")}" alt="">
           <button type="button" class="btn btn-arrow" data-unassigned>Show unassigned <span class="arr">${ICONS.arrowRight}</span></button></article>`
      : `<article class="cta-card"><h3>Something broken? Raise a ticket now.</h3>
           <img src="${IMG("blob-cushion-green.svg")}" alt="">
           <a class="btn btn-arrow" href="/tickets/new">New ticket <span class="arr">${ICONS.arrowRight}</span></a></article>`;

    statsBox.innerHTML = `
      <div class="band">
        <h2>${isIT ? "Transforming IT, one ticket at a time" : "Your requests, one step at a time"}</h2>
        <p class="band-sub">${isIT
          ? "Every request moves through the same four stages. Here is where the whole queue stands right now."
          : "Every request moves through four stages. Here is where yours stand right now."}</p>
        <div class="band-grid">
          <div class="pulse-card">
            <div class="float"><img src="${IMG("robot.svg")}" alt=""><div>${resolved}% resolved<small>of all tickets</small></div></div>
            <div class="big-number">${total}</div>
            <div class="lbl">${isIT ? "Tickets received" : "Tickets submitted"}</div>
            <div class="stack-bar" role="img" aria-label="Tickets by status">${segments
              .map((s) => `<span class="${s.cls}" data-w="${pct(s.value, total)}" title="${esc(s.label)}: ${s.value}"></span>`)
              .join("")}</div>
            <ul class="legend">${segments.map((s) => `<li><i class="dot ${s.cls}"></i>${esc(s.label)}<b>${s.value}</b></li>`).join("")}</ul>
          </div>
          <ol class="steps">${segments
            .map((s, i) => `<li class="${s.value ? "on" : ""}"><span class="step-no">Step ${i + 1}</span>
              <div class="step-name">${esc(s.label)}<b>${s.value}</b></div><p>${esc(s.text)}</p></li>`)
            .join("")}</ol>
        </div>
      </div>

      <div class="section-title"><span class="kicker">At a glance</span><h2>Overview</h2></div>
      <div class="features">
        ${feature({ title: "High priority", icon: "blob-flower-pink.svg", num: byPriority("High"), cls: "c-high",
          desc: "Active tickets that are blocking work.", percent: pct(byPriority("High"), active), tags: [`${pct(byPriority("High"), active)}% of active`, "Urgent"] })}
        ${feature({ title: "Medium priority", icon: "blob-flower-violet.svg", num: byPriority("Medium"), cls: "c-violet",
          desc: "Active tickets that need attention soon.", percent: pct(byPriority("Medium"), active), tags: [`${pct(byPriority("Medium"), active)}% of active`, "Standard"] })}
        ${feature({ title: "Low priority", icon: "blob-clover-green.svg", num: byPriority("Low"), cls: "c-low",
          desc: "Active tickets with a workaround in place.", percent: pct(byPriority("Low"), active), tags: [`${pct(byPriority("Low"), active)}% of active`, "Routine"] })}
        ${feature({ title: "Resolved", icon: "blob-donut.svg", num: st.Closed, cls: "c-low",
          desc: isIT ? "Tickets closed with resolution notes." : "Your tickets that IT has closed.", percent: resolved, tags: [`${resolved}% resolved`, plural(total, "ticket")] })}
        ${feature({ title: "Unassigned", icon: "blob-spheres.svg", num: unassigned, cls: "c-peach",
          desc: isIT ? "Active tickets still needing an owner." : "Waiting for an IT team member.", percent: pct(unassigned, active), tags: [isIT ? "Needs an owner" : "In the queue"] })}
        ${cta}
      </div>`;

    // Bar widths are set through the CSSOM (inline style attributes are blocked by our CSP).
    statsBox.querySelectorAll("[data-w]").forEach((el) => requestAnimationFrame(() => (el.style.width = el.dataset.w + "%")));
    const showUnassigned = statsBox.querySelector("[data-unassigned]");
    if (showUnassigned) {
      showUnassigned.addEventListener("click", () => {
        form.reset();
        form.elements["assigned"].value = "unassigned";
        load();
        document.getElementById("ticket-list").scrollIntoView({ behavior: "smooth" });
      });
    }
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
