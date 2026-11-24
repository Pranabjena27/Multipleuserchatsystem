/**
 * ConnectX Core Client Infrastructure
 * Handles themes, Web Audio feedback cues, toast notifications, and modal controls.
 */

// 1. Theme Switcher Management
const ThemeManager = {
  STORAGE_KEY: "connectx_theme_preference",

  init() {
    const savedTheme = localStorage.getItem(this.STORAGE_KEY) || "light";
    this.applyTheme(savedTheme);

    const toggleBtn = document.getElementById("theme-toggle-btn");
    if (toggleBtn) {
      toggleBtn.addEventListener("click", () => this.toggleTheme());
    }
  },

  applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem(this.STORAGE_KEY, theme);
    const label = document.getElementById("theme-label");
    const icon = document.getElementById("theme-icon");
    if (label) label.textContent = theme === "dark" ? "Dark" : "Light";
    if (icon) icon.className = theme === "dark" ? "fas fa-moon" : "fas fa-sun";
  },

  toggleTheme() {
    const current = document.documentElement.getAttribute("data-theme") || "light";
    const nextTheme = current === "dark" ? "light" : "dark";
    this.applyTheme(nextTheme);
  }
};

// 2. Synthesized Web Audio Notification Engine
// Uses Web Audio API oscillator nodes for clean, cross-browser, zero-asset audio cues
const AudioAlerts = {
  ctx: null,

  getContext() {
    if (!this.ctx) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) this.ctx = new AudioCtx();
    }
    if (this.ctx && this.ctx.state === "suspended") {
      this.ctx.resume();
    }
    return this.ctx;
  },

  playReceive() {
    const ctx = this.getContext();
    if (!ctx) return;
    try {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(587.33, ctx.currentTime); // D5
      osc.frequency.exponentialRampToValueAtTime(880, ctx.currentTime + 0.12); // A5
      gain.gain.setValueAtTime(0.12, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.22);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.22);
    } catch (e) {
      console.debug("Audio play blocked", e);
    }
  },

  playSent() {
    const ctx = this.getContext();
    if (!ctx) return;
    try {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(440, ctx.currentTime); // A4
      osc.frequency.exponentialRampToValueAtTime(659.25, ctx.currentTime + 0.08); // E5
      gain.gain.setValueAtTime(0.08, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.12);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.12);
    } catch (e) {
      console.debug("Audio play blocked", e);
    }
  }
};

// 3. Toast Notifications Engine
function showToast(message, type = "info", duration = 4000) {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span>${message}</span>
    <button style="background:none;border:none;color:inherit;cursor:pointer;margin-left:8px;" onclick="this.parentElement.remove()">✕</button>
  `;
  container.appendChild(toast);

  setTimeout(() => {
    if (toast.parentElement) toast.remove();
  }, duration);
}

// 4. Modal Helpers
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add("active");
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove("active");
  }
}

// 5. Notifications Dropdown Manager
const AppNotifications = {
  isOpen: false,

  init() {
    const btn = document.getElementById("notifications-menu-btn");
    const dropdown = document.getElementById("notifications-dropdown");

    if (btn && dropdown) {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        this.toggleDropdown();
      });

      document.addEventListener("click", (e) => {
        if (!dropdown.contains(e.target) && e.target !== btn) {
          dropdown.classList.add("hidden");
          this.isOpen = false;
        }
      });

      this.fetchNotifications();
    }
  },

  toggleDropdown() {
    const dropdown = document.getElementById("notifications-dropdown");
    if (!dropdown) return;
    this.isOpen = !this.isOpen;
    dropdown.classList.toggle("hidden", !this.isOpen);
    if (this.isOpen) {
      this.fetchNotifications();
    }
  },

  fetchNotifications() {
    fetch("/api/notifications")
      .then((r) => r.json())
      .then((data) => {
        if (!data.success) return;
        this.updateBadge(data.unread_count);
        this.renderList(data.notifications);
      })
      .catch((err) => console.debug("Notifications fetch error", err));
  },

  updateBadge(count) {
    const badge = document.getElementById("nav-notif-badge");
    if (!badge) return;
    if (count > 0) {
      badge.textContent = count > 99 ? "99+" : count;
      badge.classList.remove("hidden");
    } else {
      badge.classList.add("hidden");
    }
  },

  renderList(notifications) {
    const list = document.getElementById("notif-items-list");
    if (!list) return;

    if (!notifications || notifications.length === 0) {
      list.innerHTML =
        '<div class="notif-empty"><i class="fas fa-check-circle" style="color:var(--success);margin-right:6px;"></i>No notifications</div>';
      return;
    }

    list.innerHTML = "";
    notifications.forEach((n) => {
      const a = document.createElement("a");
      a.className = `notif-item ${!n.is_read ? "unread" : ""}`;
      a.href = n.link_url || "#";
      a.innerHTML = `
        <i class="fas fa-comment-dots" style="color:var(--primary);margin-top:2px;"></i>
        <div>
          <div class="notif-item-title">${this.escapeHtml(n.title)}</div>
          <div class="notif-item-snippet">${this.escapeHtml(n.content)}</div>
          <div class="notif-item-time">${this.formatTime(n.created_at)}</div>
        </div>
      `;
      a.addEventListener("click", () => {
        if (!n.is_read) {
          fetch("/api/notifications/read", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ notification_id: n.id }),
          });
        }
      });
      list.appendChild(a);
    });
  },

  markAllRead() {
    fetch("/api/notifications/read", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    })
      .then(() => {
        this.updateBadge(0);
        this.fetchNotifications();
        showToast("All notifications marked as read", "success");
      })
      .catch((err) => console.error("Error marking notifications", err));
  },

  escapeHtml(str) {
    if (!str) return "";
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  },

  formatTime(isoStr) {
    if (!isoStr) return "";
    const d = new Date(isoStr);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  },
};

// 6. Quick Settings Manager
const QuickSettings = {
  toggleTheme(isDark) {
    ThemeManager.applyTheme(isDark ? "dark" : "light");
    this.saveRemote({ theme: isDark ? "dark" : "light" });
  },

  update(key, val) {
    const payload = {};
    payload[key] = val;
    this.saveRemote(payload);
    showToast("Preference saved", "info", 1500);
  },

  saveRemote(payload) {
    fetch("/api/users/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).catch((err) => console.debug("Settings save error", err));
  },
};

window.AppNotifications = AppNotifications;
window.QuickSettings = QuickSettings;

// Global initialization
document.addEventListener("DOMContentLoaded", () => {
  ThemeManager.init();
  AppNotifications.init();

  // Sync quick settings theme checkbox with current theme
  const darkToggle = document.getElementById("setting-dark-theme-toggle");
  if (darkToggle) {
    const currentTheme =
      document.documentElement.getAttribute("data-theme") || "light";
    darkToggle.checked = currentTheme === "dark";
  }

  // Close modals on overlay backdrop click
  document.querySelectorAll(".modal-overlay").forEach((overlay) => {
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) {
        overlay.classList.remove("active");
      }
    });
  });
});

