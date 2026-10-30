(async () => {
  const form = document.getElementById("login-form");
  const error = document.getElementById("error");

  if (new URLSearchParams(window.location.search).get("registered")) {
    showMessage(document.getElementById("notice"), "Registration successful. Please log in.");
  }

  // Already logged in? Go straight to the right home page.
  try {
    const user = await api("/auth/me");
    window.location.href = afterLogin(user.role);
    return;
  } catch (e) {
    /* not logged in */
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    showMessage(error, "");
    const email = form.elements["email"].value.trim();
    const password = form.elements["password"].value;
    if (!email || !password) return showMessage(error, "Enter your email and password.");
    await submitting(form.querySelector("button[type=submit]"), async () => {
      try {
        const user = await api("/auth/login", { method: "POST", body: { email, password } });
        window.location.href = afterLogin(user.role);
      } catch (e) {
        showMessage(error, e.message);
      }
    });
  });
})();
