(async () => {
  const page = document.getElementById("ticket-page");
  const ticketId = page.dataset.ticketId;
  const user = await requireUser();
  if (!user) return;
  const isIT = user.role === "it_team";

  // Statuses IT can pick; mirrors the workflow enforced by the API (the API remains the authority).
  // Assigning sets "Assigned" automatically; only the requester can close.
  const NEXT = {
    "Open": [], "Assigned": ["In Progress", "On Hold", "Resolved"], "In Progress": ["On Hold", "Resolved"],
    "On Hold": ["In Progress", "Resolved"], "Resolved": ["In Progress"], "Closed": [],
  };

  const $ = (id) => document.getElementById(id);
  const panel = $("it-panel");
  const commentForm = $("comment-form");
  const reviewForm = $("review-form");
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
    // Progress tracker: Open -> Assigned -> In Progress (or On Hold) -> Resolved -> Closed
    const order = ["Open", "Assigned", "In Progress", "Resolved", "Closed"];
    const onHold = t.status === "On Hold";
    const reached = order.indexOf(onHold ? "In Progress" : t.status);
    $("ticket-track").querySelectorAll("li").forEach((li, i) => {
      li.classList.toggle("done", i <= reached);
      li.classList.toggle("current", i === reached);
    });
    $("ticket-track").querySelector('[data-step="In Progress"]').textContent = onHold ? "On hold" : "In progress";
    $("ticket-description").textContent = t.description;
    $("resolution-box").hidden = !(["Resolved", "Closed"].includes(t.status) && t.resolution_notes);
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
    const isOwner = t.creator.id === user.id;
    const canManage = isIT || isOwner;
    $("ticket-actions").hidden = !canManage;
    $("edit-btn").hidden = closed;
    // Only the requester closes; a resolved ticket gets the review card instead.
    $("owner-close-btn").hidden = !(isOwner && !closed && t.status !== "Resolved");
    reviewForm.hidden = !(isOwner && t.status === "Resolved");
    showMessage($("review-error"), "");
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

  async function closeTicket(button, errorBox) {
    if (!confirm("Close this ticket? Closed tickets cannot be changed.")) return;
    showMessage(errorBox, "");
    await submitting(button, async () => {
      try {
        render(await api(`/tickets/${ticketId}/close`, { method: "POST" }));
        showMessage($("actions-ok"), "Ticket closed.");
        $("ticket-view").scrollIntoView({ behavior: "smooth", block: "start" });
      } catch (err) {
        showMessage(errorBox, err.message);
      }
    });
  }

  $("owner-close-btn").addEventListener("click", (e) => closeTicket(e.currentTarget, $("actions-error")));
  $("accept-btn").addEventListener("click", (e) => closeTicket(e.currentTarget, $("review-error")));

  reviewForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const error = $("review-error");
    showMessage(error, "");
    const body = reviewForm.elements["body"].value.trim();
    if (!body) return showMessage(error, "Tell the IT team what still needs to change.");
    await submitting(reviewForm.querySelector("button[type=submit]"), async () => {
      try {
        render(await api(`/tickets/${ticketId}/reopen`, { method: "POST", body: { body } }));
        reviewForm.reset();
        showMessage($("actions-ok"), "Sent back to the IT team.");
      } catch (err) {
        showMessage(error, err.message);
      }
    });
  });

  function fillStatus(current) {
    const statusSelect = panel.elements["status"];
    statusSelect.innerHTML = [current, ...NEXT[current]].map((s) => `<option>${esc(s)}</option>`).join("");
    statusSelect.value = current;
  }

  function fillPanel(t) {
    const f = panel.elements;
    fillStatus(t.status);
    f["priority"].value = t.priority;
    f["assignee"].value = t.assignee ? String(t.assignee.id) : "";
    f["resolution"].value = t.resolution_notes || "";
  }

  // Picking a (new) assignee makes the ticket Assigned, as the API does on save.
  panel.elements["assignee"].addEventListener("change", (e) => {
    const picked = e.target.value;
    const current = ticket.assignee ? String(ticket.assignee.id) : "";
    fillStatus(picked && picked !== current ? "Assigned" : ticket.status);
  });

  function changesFromPanel() {
    const f = panel.elements;
    const changes = {};
    const assignee = f["assignee"].value;
    if (assignee && Number(assignee) !== (ticket.assignee && ticket.assignee.id)) changes.assigned_to = Number(assignee);
    const status = f["status"].value;
    if (status !== ticket.status) changes.status = status;
    if (f["priority"].value !== ticket.priority) changes.priority = f["priority"].value;
    const notes = f["resolution"].value.trim();
    if (notes !== (ticket.resolution_notes || "")) changes.resolution_notes = notes;
    return changes;
  }

  async function savePanel(button) {
    const error = $("panel-error"), ok = $("panel-ok");
    showMessage(error, "");
    showMessage(ok, "");
    const changes = changesFromPanel();
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
      savePanel(panel.querySelector("button[type=submit]"));
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
