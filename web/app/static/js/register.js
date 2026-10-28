(() => {
  const form = document.getElementById("register-form");
  const error = document.getElementById("error");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    showMessage(error, "");
    const f = form.elements;
    const body = { full_name: f["full_name"].value.trim(), email: f["email"].value.trim(), password: f["password"].value };
    if (!body.full_name || !body.email) return showMessage(error, "Name and email are required.");
    if (body.password.length < 8) return showMessage(error, "Password must be at least 8 characters.");
    if (body.password !== f["confirm"].value) return showMessage(error, "Passwords do not match.");
    await submitting(form.querySelector("button[type=submit]"), async () => {
      try {
        await api("/auth/register", { method: "POST", body });
        window.location.href = "/login?registered=1";
      } catch (e) {
        showMessage(error, e.message);
      }
    });
  });
})();
