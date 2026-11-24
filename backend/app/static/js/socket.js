/**
 * ConnectX Real-Time Socket Connection Manager
 * Manages WebSocket connectivity, automatic reconnection, and global presence sync.
 */

const SocketManager = {
  socket: null,
  isConnected: false,

  init() {
    if (typeof io === "undefined") {
      console.warn("Socket.io library not loaded");
      return;
    }

    this.socket = io({
      reconnection: true,
      reconnectionAttempts: 10,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      timeout: 20000,
    });

    this.bindEvents();
  },

  bindEvents() {
    this.socket.on("connect", () => {
      this.isConnected = true;
      console.log("ConnectX WebSocket connected, sid:", this.socket.id);
      window.dispatchEvent(new CustomEvent("socket:connected"));
    });

    this.socket.on("disconnect", (reason) => {
      this.isConnected = false;
      console.log("ConnectX WebSocket disconnected:", reason);
      window.dispatchEvent(new CustomEvent("socket:disconnected"));
    });

    this.socket.on("user_status_changed", (data) => {
      console.log("Presence update:", data);
      this.updateUserPresenceUI(data.user_id, data.is_online);
      if (window.ChatApp && typeof window.ChatApp.fetchOnlineContacts === "function") {
        window.ChatApp.fetchOnlineContacts();
      }
    });

    this.socket.on("error_alert", (data) => {
      showToast(data.message || "An error occurred", "danger");
      // If error related to optimistic message, remove sending spinner
      if (data.temp_id) {
        const tempEl = document.getElementById(`msg-${data.temp_id}`);
        if (tempEl) {
          tempEl.classList.add("msg-send-failed");
          const bubble = tempEl.querySelector(".message-bubble");
          if (bubble) bubble.style.opacity = "0.5";
        }
      }
    });

    this.socket.on("message_notification", (data) => {
      // If message is in another conversation, play sound and show subtle badge
      AudioAlerts.playReceive();
      if (window.AppNotifications) {
        window.AppNotifications.fetchNotifications();
      }
      const currentActiveConv = window.ChatApp ? window.ChatApp.currentConversationId : null;
      if (currentActiveConv !== data.conversation_id) {
        showToast(`💬 ${data.sender_name}: ${data.message_snippet}`, "info");
        this.incrementUnreadBadge(data.conversation_id);
      }
    });

    this.socket.on("conversation_created", (data) => {
      console.log("New conversation created:", data);
      showToast(`✨ New ${data.type === "group" ? "group" : "direct"} channel: ${data.title}`, "info");
      this.socket.emit("join_conversation", { conversation_id: data.id });
      if (window.ChatApp && typeof window.ChatApp.addConversationToSidebar === "function") {
        window.ChatApp.addConversationToSidebar(data);
      }
    });

    this.socket.on("message_confirmed", (data) => {
      if (window.ChatApp && typeof window.ChatApp.handleMessageConfirmed === "function") {
        window.ChatApp.handleMessageConfirmed(data);
      }
    });
  },

  updateUserPresenceUI(userId, isOnline) {
    document.querySelectorAll(`.status-dot-user-${userId}`).forEach(el => {
      if (isOnline) {
        el.classList.add("online");
      } else {
        el.classList.remove("online");
      }
    });
  },

  incrementUnreadBadge(conversationId) {
    const item = document.querySelector(`.conversation-item[data-id="${conversationId}"]`);
    if (item) {
      let badge = item.querySelector(".unread-badge");
      if (!badge) {
        badge = document.createElement("span");
        badge.className = "unread-badge";
        badge.textContent = "1";
        item.querySelector(".conv-bottom-line").appendChild(badge);
      } else {
        const count = parseInt(badge.textContent || "0", 10) + 1;
        badge.textContent = count;
      }
    }
  }
};

window.SocketManager = SocketManager;

