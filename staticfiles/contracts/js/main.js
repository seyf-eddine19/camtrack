const sidebar = document.getElementById("sidebar");
const overlay = document.getElementById("sidebarOverlay");
const toggleBtn = document.getElementById("sidebarToggle");

toggleBtn?.addEventListener("click", () => {
  if (window.innerWidth <= 768) {
    sidebar.classList.toggle("show");
    overlay.classList.toggle("show");
  } else {
    sidebar.classList.toggle("collapsed");
  }
});

overlay?.addEventListener("click", () => {
  sidebar.classList.remove("show");
  overlay.classList.remove("show");
});

$(document).ready(function () {
  $('select').select2({ width: '100%' });
});
