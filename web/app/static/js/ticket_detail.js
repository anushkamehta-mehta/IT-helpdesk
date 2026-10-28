(async () => {
  const page = document.getElementById("ticket-page");
  const ticketId = page.dataset.ticketId;
  const user = await requireUser();
  if (!user) return;
  const isIT = user.role === "it_team";

  // Mirrors the workflow enforced by the API (the API remains the authority).
  const NEXT = { "Open": ["Assigned", "Closed"], "Assigned": ["In Progress", "Closed"], "In Progress": ["Closed"], "Closed": [] };

  const $ = (id) => document.getElementById(id);
  const panel = $("it-panel");
  const commentForm = $("comment-form");
  const editForm = $("edit-form");
  let ticket = null;

  $("back-link").href = homeFor(user.role);

  const person = (u) => (u ? `<span class="person">${avatar(u.full_name, "sm")}${esc(u.full_name)}</span>` : '<span class="muted">Unassigned</span>');

  function render(t) {
    ticket = t;
    $("ticket-title").textContent = `#${t.id} ${t.title}`;
    $("badge-status").innerHTML = badge("status", t.status);
    $("badge-priority").innerHTML = badge("priority", t.priority);
    $("ticket-meta").innerHTML = [
      ["Category", esc(t.category.name)],
      ["Requester", person(t.creator)],
      ["Assigned to", person(t.assignee)],
      ["Created", esc(formatDate(t.created_at))],
      ["Last updated", esc(formatDate(t.updated_at))],
      ["Closed", t.closed_at ? esc(formatDate(t.closed_at)) : "-"],
    ].map(([k, v]) => `<div><dt>${esc(k)}</dt><dd>${v}</dd></div>`).join("");
    $("ticket-description").textContent = t.description;
    $("resolution-box").hidden = !(t.status === "Closed" && t.resolution_notes);
    $("ticket-resolution").textContent = t.resolution_notes || "";

    $("comments").innerHTML = t.comments.length
      ? t.comments.map((c) => `<div class="comment${c.author.id === user.id ? " me" : ""}">
          ${avatar(c.author.full_name)}
          <div class="bubble"><div class="who">${esc(c.author.full_name)}<span class="when">${esc(formatDate(c.created_at))}</span></div>
          <p class="pre">${esc(c.body)}</p></div></div>`).join("")
      : '<p class="muted">No comments yet.</p>';

    const closed = t.status === "Closed";
    commentForm.hidden = closed;
    $("comments-closed").hidden = !closed;

    panel.hidden = !(isIT && !closed);
    if (isIT && !closed) fillPanel(t);

    // The API lets owners and IT edit/delete; closed tickets can only be deleted.
    const canManage = isIT || t.creator.id === user.id;
    $("ticket-actions").hidden = !canManage;
    $("edit-btn").hidden = closed;
    $("edit-closed").hidden = !(canManage && closed);
    editForm.hidden = true;
  }

  function openEditForm() {
    const f = editForm.elements;
    f["title"].value = ticket.title;
    f["description"].value = ticket.description;
    f["category_id"].value = String(ticket.category.id);
    f["priority"].value = ticket.priority;
    showMessage($("edit-error"), "");
    showMessage($("actions-ok"), "");
    editForm.hidden = false;
    editForm.scrollIntoView({ behavior: "smooth", block: "start" });
    f["title"].focus({ preventScroll: true });
  }

  editForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const error = $("edit-error");
    showMessage(error, "");
    const f = editForm.elements;
    const changes = {};
    const title = f["title"].value.trim(), description = f["description"].value.trim();
    if (!title || !description) return showMessage(error, "Title and description are required.");
    if (title !== ticket.title) changes.title = title;
    if (description !== ticket.description) changes.description = description;
    if (Number(f["category_id"].value) !== ticket.category.id) changes.category_id = Number(f["category_id"].value);
    if (f["priority"].value !== ticket.priority) changes.priority = f["priority"].value;
    if (!Object.keys(changes).length) return showMessage(error, "No changes to save.");
    await submitting(editForm.querySelector("button[type=submit]"), async () => {
      try {
        render(await api(`/tickets/${ticketId}`, { method: "PATCH", body: changes }));
        showMessage($("actions-ok"), "Ticket updated.");
        $("ticket-view").scrollIntoView({ behavior: "smooth", block: "start" });
      } catch (err) {
        showMessage(error, err.message);
      }
    });
  });

  $("edit-btn").addEventListener("click", openEditForm);
  $("edit-cancel").addEventListener("click", () => { editForm.hidden = true; });

  $("delete-btn").addEventListener("click", async (e) => {
    if (!confirm("Delete this ticket and all its comments? This cannot be undone.")) return;
    const error = $("actions-error");
    showMessage(error, "");
    await submitting(e.currentTarget, async () => {
      try {
        await api(`/tickets/${ticketId}`, { method: "DELETE" });
        window.location.href = homeFor(user.role);
      } catch (err) {
        showMessage(error, err.message);
      }
    });
  });

  function fillPanel(t) {
    const f = panel.elements;
    const statusSelect = f["status"];
    statusSelect.innerHTML = [t.status, ...NEXT[t.status]].map((s) => `<option>${esc(s)}</option>`).join("");
    statusSelect.value = t.status;
    f["priority"].value = t.priority;
    f["assignee"].value = t.assignee ? String(t.assignee.id) : "";
    f["resolution"].value = t.resolution_notes || "";
  }

  function changesFromPanel(forceClose) {
    const f = panel.elements;
    const changes = {};
    const assignee = f["assignee"].value;
    if (assignee && Number(assignee) !== (ticket.assignee && ticket.assignee.id)) changes.assigned_to = Number(assignee);
    const status = forceClose ? "Closed" : f["status"].value;
    if (status !== ticket.status) changes.status = status;
    if (f["priority"].value !== ticket.priority) changes.priority = f["priority"].value;
    const notes = f["resolution"].value.trim();
    if (notes !== (ticket.resolution_notes || "")) changes.resolution_notes = notes;
    return changes;
  }

  async function savePanel(forceClose, button) {
    const error = $("panel-error"), ok = $("panel-ok");
    showMessage(error, "");
    showMessage(ok, "");
    const changes = changesFromPanel(forceClose);
    if (!Object.keys(changes).length) return showMessage(error, "No changes to save.");
    await submitting(button, async () => {
      try {
        render(await api(`/tickets/${ticketId}`, { method: "PATCH", body: changes }));
        showMessage($("panel-ok"), "Ticket updated.");
      } catch (e) {
        showMessage(error, e.message);
      }
    });
  }

  if (isIT) {
    try {
      for (const u of await api("/users/it-team")) panel.elements["assignee"].add(new Option(u.full_name, u.id));
    } catch (e) {
      showMessage($("load-error"), e.message);
    }
    panel.addEventListener("submit", (e) => {
      e.preventDefault();
      savePanel(false, panel.querySelector("button[type=submit]"));
    });
    $("close-btn").addEventListener("click", (e) => {
      if (confirm("Close this ticket? Closed tickets cannot be changed.")) savePanel(true, e.currentTarget);
    });
  }

  commentForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const error = $("comment-error");
    showMessage(error, "");
    const body = commentForm.elements["body"].value.trim();
    if (!body) return showMessage(error, "Enter a comment.");
    await submitting(commentForm.querySelector("button[type=submit]"), async () => {
      try {
        render(await api(`/tickets/${ticketId}/comments`, { method: "POST", body: { body } }));
        commentForm.reset();
      } catch (err) {
        showMessage(error, err.message);
      }
    });
  });

  try {
    await loadCategories(editForm.elements["category_id"]);
    render(await api(`/tickets/${ticketId}`));
    $("ticket-view").hidden = false;
  } catch (e) {
    showMessage($("load-error"), e.status === 404 ? "Ticket not found." : e.message);
  }
})();
