(async () => {
  const user = await requireUser("employee");
  if (!user) return;

  const form = document.getElementById("ticket-form");
  const error = document.getElementById("error");
  try {
    await loadCategories(form.elements["category_id"]);
  } catch (e) {
    showMessage(error, e.message);
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    showMessage(error, "");
    const f = form.elements;
    const body = {
      title: f["title"].value.trim(),
      description: f["description"].value.trim(),
      category_id: Number(f["category_id"].value),
      priority: f["priority"].value,
    };
    if (!body.title) return showMessage(error, "Enter a title.");
    if (!body.category_id) return showMessage(error, "Select a category.");
    if (!body.description) return showMessage(error, "Enter a description.");
    await submitting(form.querySelector("button[type=submit]"), async () => {
      try {
        const ticket = await api("/tickets", { method: "POST", body });
        window.location.href = `/tickets/${ticket.id}`;
      } catch (e) {
        showMessage(error, e.message);
      }
    });
  });
})();
