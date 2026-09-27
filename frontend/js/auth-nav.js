(function () {
  function updateAuthNav() {
    const isLoggedIn = localStorage.getItem("is_logged_in") === "true";

    // Semua link navigasi yang menuju Login
    document.querySelectorAll(
      'a[href="/pages/login.html"], a[href$="/pages/login.html"], a[href="./login.html"]'
    ).forEach(function (loginLink) {
      loginLink.style.display = isLoggedIn ? "none" : "";
    });

    // Container tombol auth pada Blog
    const authButtons = document.getElementById("authButtons");
    if (authButtons) {
      authButtons.style.display = isLoggedIn ? "none" : "";
    }

    // Dashboard
    document.querySelectorAll(
      'a[href="/pages/dashboard.html"], a[href$="/pages/dashboard.html"]'
    ).forEach(function (dashboardLink) {
      dashboardLink.style.display = isLoggedIn ? "inline-flex" : "none";
    });

    // Profile
    document.querySelectorAll(
      'a[href="/pages/profile.html"], a[href$="/pages/profile.html"]'
    ).forEach(function (profileLink) {
      profileLink.style.display = isLoggedIn ? "inline-flex" : "none";
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", updateAuthNav);
  } else {
    updateAuthNav();
  }

  window.addEventListener("pageshow", updateAuthNav);
  window.addEventListener("focus", updateAuthNav);

  window.updateAuthNav = updateAuthNav;
})();
