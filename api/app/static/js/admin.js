(async () => {
  const me = await requireUser("admin");
  if (!me) return;

  const $ = (id) => document.getElementById(id);
  const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;
  const form = $("user-form");
  const filters = $("user-filters");
  const rows = $("user-rows");
  let users = [];
  let editing = null; // user being edited, or null when adding

  const roleBadge = (role) => `<span class="badge role-${slug(role)}"><i></i>${esc(roleLabel(role))}</span>`;

  function row(u) {
    const self = u.id === me.id;
    const actions = [`<button type="button" class="pill-btn" data-action="edit" data-id="${u.id}">Edit</button>`];
    if (!self) {
      actions.push(
        `<button type="button" class="pill-btn" data-action="toggle" data-id="${u.id}">${u.is_active ? "Deactivate" : "Activate"}</button>`,
        `<button type="button" class="pill-btn danger" data-action="delete" data-id="${u.id}">Delete</button>`
      );
    }
    return `<tr${u.is_active ? "" : ' class="inactive"'}>
      <td><span class="person">${avatar(u.full_name, "sm")}${esc(u.full_name)}${self ? ' <span class="muted">(you)</span>' : ""}</span></td>
      <td>${esc(u.email)}</td>
      <td>${roleBadge(u.role)}</td>
      <td>${u.is_active ? '<span class="badge status-active"><i></i>Active</span>' : '<span class="badge status-inactive"><i></i>Inactive</span>'}</td>
      <td class="muted">${esc(formatDate(u.created_at))}</td>
      <td class="row-actions">${actions.join("")}</td>
    </tr>`;
  }

  function renderRows() {
    const q = filters.elements["q"].value.trim().toLowerCase();
    const role = filters.elements["role"].value;
    const shown = users.filter((u) =>
      (!role || u.role === role) && (!q || u.full_name.toLowerCase().includes(q) || u.email.toLowerCase().includes(q))
    );
    rows.innerHTML = shown.length ? shown.map(row).join("") : '<tr><td colspan="6" class="muted">No users found.</td></tr>';
    $("count").textContent = plural(shown.length, "user");
    const counts = { employee: 0, it_team: 0, admin: 0 };
    for (const u of users) counts[u.role] += 1;
    $("n-employee").textContent = counts.employee;
    $("n-it").textContent = counts.it_team;
    $("n-admin").textContent = counts.admin;
    $("hero-sub").textContent = `${plural(counts.employee, "employee")}, ${plural(counts.it_team, "IT team member")} and ${plural(counts.admin, "admin")}.`;
  }

  async function loadUsers() {
    try {
      users = await api("/admin/users");
      renderRows();
    } catch (e) {
      showMessage($("list-error"), e.message);
    }
  }

  function resetForm() {
    editing = null;
    form.reset();
    $("form-title").textContent = "Add a user";
    $("form-submit").textContent = "Add user";
    $("password-label").textContent = "Password (min 8 characters)";
    $("form-cancel").hidden = true;
    form.elements["role"].disabled = false;
    showMessage($("form-error"), "");
  }

  function startEdit(u) {
    editing = u;
    const f = form.elements;
    f["full_name"].value = u.full_name;
    f["email"].value = u.email;
    f["role"].value = u.role;
    f["role"].disabled = u.id === me.id; // the API refuses removing your own admin role
    f["password"].value = "";
    $("form-title").textContent = `Edit ${u.full_name}`;
    $("form-submit").textContent = "Save changes";
    $("password-label").textContent = "New password (leave blank to keep)";
    $("form-cancel").hidden = false;
    showMessage($("form-error"), "");
    showMessage($("form-ok"), "");
    form.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const error = $("form-error"), ok = $("form-ok");
    showMessage(error, "");
    showMessage(ok, "");
    const f = form.elements;
    const data = { full_name: f["full_name"].value.trim(), email: f["email"].value.trim(), role: f["role"].value };
    const password = f["password"].value;
    if (!data.full_name || !data.email) return showMessage(error, "Name and email are required.");
    if ((!editing || password) && password.length < 8) return showMessage(error, "Password must be at least 8 characters.");
    if (password) data.password = password;

    let body = data;
    if (editing) {
      body = {};
      if (data.full_name !== editing.full_name) body.full_name = data.full_name;
      if (data.email.toLowerCase() !== editing.email) body.email = data.email;
      if (!f["role"].disabled && data.role !== editing.role) body.role = data.role;
      if (password) body.password = password;
      if (!Object.keys(body).length) return showMessage(error, "No changes to save.");
    }

    await submitting($("form-submit"), async () => {
      try {
        const saved = editing
          ? await api(`/admin/users/${editing.id}`, { method: "PATCH", body })
          : await api("/admin/users", { method: "POST", body });
        const message = editing ? `Saved changes for ${saved.full_name}.` : `Added ${saved.full_name} as ${roleLabel(saved.role)}.`;
        resetForm();
        showMessage(ok, message);
        await loadUsers();
      } catch (err) {
        showMessage(error, err.message);
      }
    });
  });

  $("form-cancel").addEventListener("click", resetForm);
  filters.addEventListener("input", renderRows);
  filters.addEventListener("submit", (e) => e.preventDefault());

  rows.addEventListener("click", async (e) => {
    const button = e.target.closest("button[data-action]");
    if (!button) return;
    const u = users.find((x) => x.id === Number(button.dataset.id));
    if (!u) return;
    const error = $("list-error");
    showMessage(error, "");
    if (button.dataset.action === "edit") return startEdit(u);
    if (button.dataset.action === "delete" && !confirm(`Delete ${u.full_name}? This cannot be undone.`)) return;
    await submitting(button, async () => {
      try {
        if (button.dataset.action === "delete") await api(`/admin/users/${u.id}`, { method: "DELETE" });
        else await api(`/admin/users/${u.id}`, { method: "PATCH", body: { is_active: !u.is_active } });
        if (editing && editing.id === u.id) resetForm();
        await loadUsers();
      } catch (err) {
        showMessage(error, err.message);
      }
    });
  });

  await loadUsers();
})();
