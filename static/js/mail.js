/**
 * mail.js — FishingMail frontend
 *
 * Handles:
 *  - Clicking an email row  → navigate to /email/<id>
 *  - Refresh button         → reload page
 *  - Reply / discard        → show/hide reply form, AJAX submit
 *  - Auto-refresh polling   → check /api/status every 30 s for new mail
 *  - Keyboard nav           → Up/Down arrows to move between emails
 *  - Search filter          → client-side filter of inbox list
 */

(function () {
  "use strict";

  /* ── Helpers ─────────────────────────────────────────────────────────── */

  function qs(sel, root) { return (root || document).querySelector(sel); }
  function qsa(sel, root) { return Array.from((root || document).querySelectorAll(sel)); }

  /* ── Email row navigation ────────────────────────────────────────────── */

  const inbox = qs("#inbox-list");
  if (inbox) {
    inbox.addEventListener("click", function (e) {
      // Don't navigate when clicking the checkbox
      if (e.target.type === "checkbox") return;

      const row = e.target.closest(".email-row");
      if (!row) return;

      const id = row.dataset.emailId;
      if (id) {
        window.location.href = "/email/" + id;
      }
    });

    // Keyboard navigation
    inbox.addEventListener("keydown", function (e) {
      const rows = qsa(".email-row");
      const current = qs(".email-row.selected");
      const idx = rows.indexOf(current);

      if (e.key === "ArrowDown" || e.key === "j") {
        e.preventDefault();
        const next = rows[idx + 1];
        if (next) {
          window.location.href = "/email/" + next.dataset.emailId;
        }
      } else if (e.key === "ArrowUp" || e.key === "k") {
        e.preventDefault();
        const prev = rows[idx - 1];
        if (prev) {
          window.location.href = "/email/" + prev.dataset.emailId;
        }
      } else if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        const sel = qs(".email-row:focus");
        if (sel) window.location.href = "/email/" + sel.dataset.emailId;
      }
    });
  }

  /* ── Refresh button ──────────────────────────────────────────────────── */

  const refreshBtn = qs("#refresh-btn");
  if (refreshBtn) {
    refreshBtn.addEventListener("click", function () {
      window.location.reload();
    });
  }

  /* ── Reply toggle ────────────────────────────────────────────────────── */

  const replyBtn    = qs("#reply-btn");
  const replyForm   = qs("#reply-form");
  const discardBtn  = qs("#reply-discard");
  const replyToggle = qs("#reply-toggle");

  if (replyBtn && replyForm) {
    replyBtn.addEventListener("click", function () {
      replyForm.classList.remove("hidden");
      replyToggle.classList.add("hidden");
      qs("#reply-body").focus();
    });
  }

  if (discardBtn) {
    discardBtn.addEventListener("click", function () {
      replyForm.classList.add("hidden");
      replyToggle.classList.remove("hidden");
      qs("#reply-body").value = "";
    });
  }

  /* ── Reply form AJAX submit ──────────────────────────────────────────── */

  if (replyForm) {
    replyForm.addEventListener("submit", function (e) {
      e.preventDefault();
      const fd = new FormData(replyForm);

      fetch("/compose/reply", { method: "POST", body: fd })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.ok) {
            // Show brief confirmation, reset form
            const sendBtn = qs("#reply-send");
            const origText = sendBtn.textContent;
            sendBtn.textContent = "Sent ✓";
            sendBtn.disabled = true;
            setTimeout(function () {
              replyForm.classList.add("hidden");
              replyToggle.classList.remove("hidden");
              qs("#reply-body").value = "";
              sendBtn.textContent = origText;
              sendBtn.disabled = false;
            }, 1500);
          }
        })
        .catch(function () {});
    });
  }

  /* ── Client-side search / filter ─────────────────────────────────────── */

  const searchInput = qs("#search-input");
  if (searchInput && inbox) {
    searchInput.addEventListener("input", function () {
      const q = searchInput.value.toLowerCase().trim();
      qsa(".email-row", inbox).forEach(function (row) {
        const text = row.textContent.toLowerCase();
        row.style.display = (!q || text.includes(q)) ? "" : "none";
      });
    });
  }

  /* ── Select-all checkbox ─────────────────────────────────────────────── */

  const selectAll = qs("#select-all-cb");
  if (selectAll && inbox) {
    selectAll.addEventListener("change", function () {
      qsa(".row-cb", inbox).forEach(function (cb) {
        cb.checked = selectAll.checked;
      });
    });
  }

  /* ── Auto-refresh polling ─────────────────────────────────────────────
   *
   * Every 30 seconds, check /api/status.
   * If there are more emails than currently shown, reload the page
   * so the new mail appears in the list.
   */

  var _knownTotal = qsa(".email-row", inbox || document).length;
  var _knownUnread = (function () {
    var badge = qs("#unread-badge");
    return badge ? parseInt(badge.textContent, 10) : 0;
  })();

  function _poll() {
    fetch("/api/status")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (
          data.total_emails > _knownTotal ||
          data.unread > _knownUnread
        ) {
          // There is new mail — reload the list pane
          // Only reload if no detail is open (avoid interrupting reading)
          var detail = qs("#email-detail");
          if (!detail) {
            window.location.reload();
          }
          // If a detail is open, just nudge the badges
          _knownTotal  = data.total_emails;
          _knownUnread = data.unread;
          var badge = qs("#unread-badge");
          if (badge) badge.textContent = data.unread;
        }
      })
      .catch(function () {});
  }

  setInterval(_poll, 30000);

  /* ── Scroll selected row into view ──────────────────────────────────── */

  (function () {
    var sel = qs(".email-row.selected");
    if (sel) {
      sel.scrollIntoView({ block: "nearest" });
    }
  })();

})();
