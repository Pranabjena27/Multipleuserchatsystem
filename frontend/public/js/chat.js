/**
 * ConnectX Chat Client Application Controller
 * Handles real-time messaging, typing events, attachments, reactions, NLP features,
 * mobile views, emoji picker, online contacts, and cursor pagination.
 */

const ChatApp = {
  currentUserId: null,
  currentConversationId: null,
  currentConversation: null,
  replyParentId: null,
  replyParentSnippet: null,
  pendingAttachments: [],
  typingTimeout: null,
  isTyping: false,
  oldestMessageId: null,
  hasMoreMessages: false,
  isLoadingOlder: false,
  editingMessageId: null,
  deletingMessageId: null,

  emojiCategories: {
    smileys: ["😀","😃","😄","😁","😆","😅","🤣","😂","🙂","🙃","😉","😊","😇","🥰","😍","🤩","😘","😗","😋","😛","😜","🤪","😝","🤑","🤗","🤭","🤫","🤔","🤐","🤨","😐","😑","😶","😏","😒","🙄","😬","🤥","😌","😔","😪","🤤","😴","😷","🤒","🤕","🤢","🤮","🤧","🥵","🥶","🥴","😵","🤯","🤠","🥳","😎","🤓","🧐","😕","😟","🙁","😮","😯","😲","😳","🥺","😦","😧","😨","😰","😥","😢","😭","😱","😖","😣","😞","😓","😩","😫","🥱","😤","😡","😠","🤬"],
    gestures: ["👍","👎","👏","🙌","👐","🤲","🤝","👊","✊","🤛","🤜","🤞","✌️","🤟","🤘","👌","🤏","👈","👉","👆","👇","☝️","👋","🤚","🖐️","✋","🖖","🤙","🦾","✍️","🙏"],
    hearts: ["❤️","🧡","💛","💚","💙","💜","🖤","🤍","🤎","💔","❣️","💕","💞","💓","💗","💖","💘","💝","💟"],
    tech: ["💻","🖥️","🖨️","📱","📲","💾","💿","📀","🕹️","🔌","🔋","📡","🚀","🛸","🛰️","💡","🔬","🧪","⚙️","🔧","🔨","🛡️","🔑","🔒","🔓"],
    party: ["🎉","🎊","🎈","🎂","🍰","🎁","🏆","🥇","🥈","🥉","🎯","🎲","🎮","🎪","🎨","🎬","🎤","🎧","🎷","🎸","🎹","🎺","🎻","🥁","🥂","🍻","🍾"]
  },

  init(currentUserId, defaultConversationId = null) {
    this.currentUserId = currentUserId;
    this.currentConversationId = defaultConversationId;

    this.cacheDom();
    this.bindEvents();
    this.setupSocketListeners();
    this.initEmojiPicker();
    this.fetchOnlineContacts();

    if (this.currentConversationId) {
      this.selectConversation(this.currentConversationId);
    }
  },

  cacheDom() {
    this.dom = {
      chatLayout: document.querySelector(".chat-layout"),
      convList: document.getElementById("conversations-list"),
      messagesContainer: document.getElementById("chat-messages-container"),
      emptyState: document.getElementById("chat-empty-state"),
      activeChatArea: document.getElementById("chat-active-area"),
      headerTitle: document.getElementById("chat-header-title"),
      headerSubtitle: document.getElementById("chat-header-subtitle"),
      headerAvatar: document.getElementById("chat-header-avatar"),
      headerStatusDot: document.getElementById("chat-header-status-dot"),
      messageInput: document.getElementById("chat-message-input"),
      sendBtn: document.getElementById("chat-send-btn"),
      attachBtn: document.getElementById("chat-attach-btn"),
      fileInput: document.getElementById("chat-file-input"),
      replyBanner: document.getElementById("input-reply-banner"),
      replySnippet: document.getElementById("reply-snippet-text"),
      cancelReplyBtn: document.getElementById("cancel-reply-btn"),
      typingIndicator: document.getElementById("chat-typing-indicator"),
      typingUsernames: document.getElementById("typing-usernames"),
      detailsPanel: document.getElementById("chat-details-panel"),
      detailsToggleBtn: document.getElementById("toggle-details-btn"),
      closeDetailsBtn: document.getElementById("close-details-btn"),
      summarizeBtn: document.getElementById("summarize-chat-btn"),
      searchConvInput: document.getElementById("sidebar-search-input"),
      pendingAttachmentsPreview: document.getElementById("pending-attachments-preview"),
      emojiPickerPopover: document.getElementById("emoji-picker-popover"),
      emojiGridBody: document.getElementById("emoji-grid-body"),
    };
  },

  bindEvents() {
    // Send message on Enter (without Shift)
    if (this.dom.messageInput) {
      this.dom.messageInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          this.sendMessage();
        } else {
          this.handleTyping();
        }
      });
    }

    if (this.dom.sendBtn) {
      this.dom.sendBtn.addEventListener("click", () => this.sendMessage());
    }

    // Attachments upload trigger
    if (this.dom.attachBtn && this.dom.fileInput) {
      this.dom.attachBtn.addEventListener("click", () => this.dom.fileInput.click());
      this.dom.fileInput.addEventListener("change", (e) => this.handleFileUpload(e));
    }

    // Cancel reply preview
    if (this.dom.cancelReplyBtn) {
      this.dom.cancelReplyBtn.addEventListener("click", () => this.clearReply());
    }

    // Toggle details panel
    if (this.dom.detailsToggleBtn && this.dom.detailsPanel) {
      this.dom.detailsToggleBtn.addEventListener("click", () => {
        this.dom.detailsPanel.classList.toggle("hidden");
      });
    }
    if (this.dom.closeDetailsBtn && this.dom.detailsPanel) {
      this.dom.closeDetailsBtn.addEventListener("click", () => {
        this.dom.detailsPanel.classList.add("hidden");
      });
    }

    // Conversation Summarizer button
    if (this.dom.summarizeBtn) {
      this.dom.summarizeBtn.addEventListener("click", () => this.triggerSummarize());
    }

    // Sidebar search filter
    if (this.dom.searchConvInput) {
      this.dom.searchConvInput.addEventListener("input", (e) => {
        const query = e.target.value.toLowerCase().trim();
        document.querySelectorAll(".conversation-item").forEach((item) => {
          const title = (item.dataset.title || "").toLowerCase();
          item.style.display = title.includes(query) ? "flex" : "none";
        });
      });
    }

    // Filter pills (All, Direct, Groups, Online)
    document.querySelectorAll(".filter-pill").forEach((pill) => {
      pill.addEventListener("click", () => {
        document.querySelectorAll(".filter-pill").forEach((p) => p.classList.remove("active"));
        pill.classList.add("active");
        this.applyFilter(pill.dataset.filter);
      });
    });

    // Scroll to top: load older messages (Cursor Pagination)
    if (this.dom.messagesContainer) {
      this.dom.messagesContainer.addEventListener("scroll", () => {
        if (
          this.dom.messagesContainer.scrollTop <= 20 &&
          this.hasMoreMessages &&
          !this.isLoadingOlder &&
          this.currentConversationId
        ) {
          this.loadOlderMessages();
        }
      });
    }

    // Dismiss emoji popover on outside click
    document.addEventListener("click", (e) => {
      const popover = document.getElementById("emoji-picker-popover");
      const toggleBtn = document.getElementById("emoji-picker-toggle-btn");
      if (popover && !popover.classList.contains("hidden")) {
        if (!popover.contains(e.target) && e.target !== toggleBtn && !toggleBtn.contains(e.target)) {
          popover.classList.add("hidden");
        }
      }
    });

    // Reconnection & connection sync
    window.addEventListener("socket:connected", () => {
      console.log("ChatApp: WebSocket connected, synchronizing room & listeners");
      this.setupSocketListeners();
      if (this.currentConversationId && SocketManager.socket) {
        SocketManager.socket.emit("join_conversation", { conversation_id: this.currentConversationId });
      }
    });
  },

  setupSocketListeners() {
    const s = SocketManager.socket;
    if (!s) return;

    // Remove any previously bound listeners to avoid duplicate callbacks
    s.off("new_message");
    s.off("user_typing");
    s.off("reaction_updated");
    s.off("message_read");
    s.off("message_edited");
    s.off("message_deleted");
    s.off("conversation_updated");
    s.off("message_confirmed");

    s.on("new_message", (msg) => {
      if (msg.conversation_id === this.currentConversationId) {
        this.appendMessage(msg);
        this.scrollToBottom();

        // Send read receipt if active in chat
        if (msg.sender_id !== this.currentUserId) {
          AudioAlerts.playReceive();
          s.emit("read_receipt", {
            conversation_id: this.currentConversationId,
            message_id: msg.id,
          });
        }
      }
      this.updateSidebarSnippet(msg);
    });

    s.on("message_confirmed", (data) => {
      this.handleMessageConfirmed(data);
    });

    s.on("user_typing", (data) => {
      if (data.conversation_id === this.currentConversationId) {
        this.showTypingIndicator(data.username, data.is_typing);
      }
    });

    s.on("reaction_updated", (data) => {
      if (data.conversation_id === this.currentConversationId) {
        this.updateMessageReactions(data.message_id, data.reactions);
      }
    });

    s.on("message_read", (data) => {
      if (data.conversation_id === this.currentConversationId) {
        const msgEl = document.getElementById(`msg-${data.message_id}`);
        if (msgEl) {
          const tick = msgEl.querySelector(".receipt-status");
          if (tick) {
            tick.className = "receipt-status read";
            tick.textContent = "✓✓";
          }
        }
      }
    });

    s.on("message_edited", (msg) => {
      if (msg.conversation_id === this.currentConversationId) {
        this.handleMessageEdited(msg);
      }
    });

    s.on("message_deleted", (data) => {
      if (data.conversation_id === this.currentConversationId) {
        this.handleMessageDeleted(data.message_id);
      }
    });

    s.on("conversation_updated", (data) => {
      if (data.id === this.currentConversationId) {
        if (this.dom.headerTitle) this.dom.headerTitle.textContent = data.title;
        const titleEl = document.getElementById("drawer-conv-title");
        const descEl = document.getElementById("drawer-conv-desc");
        if (titleEl) titleEl.textContent = data.title;
        if (descEl) descEl.textContent = data.description || "No description set.";
        if (this.dom.headerSubtitle && data.type === "group") {
          this.dom.headerSubtitle.textContent = `${data.participant_count} members`;
        }
      }
      const sideItem = document.querySelector(`.conversation-item[data-id="${data.id}"]`);
      if (sideItem) {
        const sideName = sideItem.querySelector(".conv-name");
        if (sideName) sideName.textContent = data.title;
        sideItem.dataset.title = data.title;
      }
    });
  },

  selectConversation(convId) {
    if (this.currentConversationId && SocketManager.socket) {
      SocketManager.socket.emit("leave_conversation", { conversation_id: this.currentConversationId });
    }

    this.currentConversationId = convId;

    if (this.dom.chatLayout) {
      this.dom.chatLayout.classList.add("chat-open");
    }

    // Highlight item in sidebar
    document.querySelectorAll(".conversation-item").forEach((item) => {
      item.classList.toggle("active", parseInt(item.dataset.id, 10) === convId);
    });

    // Clear unread badge
    const activeItem = document.querySelector(`.conversation-item[data-id="${convId}"]`);
    if (activeItem) {
      const badge = activeItem.querySelector(".unread-badge");
      if (badge) badge.remove();
    }

    // Join room via socket
    if (SocketManager.socket) {
      SocketManager.socket.emit("join_conversation", { conversation_id: convId });
    }

    // Fetch conversation messages
    this.fetchMessages(convId);
  },

  closeMobileChat() {
    if (this.dom.chatLayout) {
      this.dom.chatLayout.classList.remove("chat-open");
    }
  },

  applyFilter(filter) {
    document.querySelectorAll(".conversation-item").forEach((item) => {
      if (filter === "all") {
        item.style.display = "flex";
      } else if (filter === "direct") {
        item.style.display = item.dataset.type === "direct" ? "flex" : "none";
      } else if (filter === "group") {
        item.style.display = item.dataset.type === "group" ? "flex" : "none";
      } else if (filter === "online") {
        const hasOnline = item.querySelector(".status-indicator.online");
        item.style.display = hasOnline ? "flex" : "none";
      }
    });
  },

  fetchMessages(convId) {
    this.dom.emptyState.style.display = "none";
    this.dom.activeChatArea.style.display = "flex";
    this.dom.messagesContainer.innerHTML = '<div style="text-align:center;padding:2rem;color:var(--text-muted);"><i class="fas fa-circle-notch fa-spin"></i> Loading conversation messages...</div>';

    fetch(`/api/conversations/${convId}/messages`)
      .then((r) => r.json())
      .then((data) => {
        if (!data.success) {
          showToast(data.message || "Failed to load messages", "danger");
          return;
        }

        this.currentConversation = data.conversation;
        this.updateHeaderUI(data.conversation);
        this.renderDetailsDrawer(data.conversation);

        this.dom.messagesContainer.innerHTML = "";
        data.messages.forEach((m) => this.appendMessage(m));
        this.scrollToBottom();

        this.oldestMessageId = data.messages.length > 0 ? data.messages[0].id : null;
        this.hasMoreMessages = Boolean(data.has_more);
        this.isLoadingOlder = false;

        // Emit read receipt for the latest message
        if (data.messages.length > 0) {
          const lastMsg = data.messages[data.messages.length - 1];
          if (lastMsg.sender_id !== this.currentUserId && SocketManager.socket) {
            SocketManager.socket.emit("read_receipt", {
              conversation_id: convId,
              message_id: lastMsg.id,
            });
          }
        }
      })
      .catch((err) => {
        console.error("Fetch error:", err);
        showToast("Error retrieving messages", "danger");
      });
  },

  loadOlderMessages() {
    if (!this.currentConversationId || !this.oldestMessageId || this.isLoadingOlder) return;
    this.isLoadingOlder = true;

    const previousScrollHeight = this.dom.messagesContainer.scrollHeight;
    const previousScrollTop = this.dom.messagesContainer.scrollTop;

    fetch(
      `/api/conversations/${this.currentConversationId}/messages?before_id=${this.oldestMessageId}&limit=30`
    )
      .then((r) => r.json())
      .then((data) => {
        this.isLoadingOlder = false;
        if (!data.success || !data.messages || data.messages.length === 0) {
          this.hasMoreMessages = false;
          return;
        }

        this.hasMoreMessages = Boolean(data.has_more);
        this.oldestMessageId = data.messages[0].id;

        const fragment = document.createDocumentFragment();
        data.messages.forEach((m) => {
          const el = this.createMessageElement(m);
          fragment.appendChild(el);
        });

        this.dom.messagesContainer.insertBefore(
          fragment,
          this.dom.messagesContainer.firstChild
        );

        // Maintain scroll offset so viewport doesn't snap to top
        const newScrollHeight = this.dom.messagesContainer.scrollHeight;
        this.dom.messagesContainer.scrollTop =
          newScrollHeight - previousScrollHeight + previousScrollTop;
      })
      .catch((err) => {
        console.error("Pagination error:", err);
        this.isLoadingOlder = false;
      });
  },

  updateHeaderUI(conv) {
    if (this.dom.headerTitle) this.dom.headerTitle.textContent = conv.title;
    if (this.dom.headerAvatar) {
      this.dom.headerAvatar.src = `/static/uploads/avatars/${conv.icon}`;
    }
    if (this.dom.headerSubtitle) {
      const isGroup = conv.type === "group";
      this.dom.headerSubtitle.textContent = isGroup
        ? `${conv.participant_count} members`
        : "Direct Conversation";
    }
    if (this.dom.headerStatusDot) {
      if (conv.type === "direct") {
        this.dom.headerStatusDot.style.display = "block";
        const otherUser = conv.participants ? conv.participants.find(p => p.user_id !== this.currentUserId) : null;
        if (otherUser && otherUser.is_online) {
          this.dom.headerStatusDot.className = "status-indicator online";
        } else {
          this.dom.headerStatusDot.className = "status-indicator";
        }
      } else {
        this.dom.headerStatusDot.style.display = "none";
      }
    }
  },

  renderDetailsDrawer(conv) {
    const listEl = document.getElementById("drawer-members-list");
    const titleEl = document.getElementById("drawer-conv-title");
    const descEl = document.getElementById("drawer-conv-desc");
    const manageBtn = document.getElementById("manage-members-btn");

    const myPart = conv.participants ? conv.participants.find(p => p.user_id === this.currentUserId) : null;
    const isChannelAdmin = myPart && (myPart.role === "admin" || myPart.role === "moderator");

    if (titleEl) {
      if (conv.type === "group" && isChannelAdmin) {
        titleEl.innerHTML = `
          <span>${this.escapeHtml(conv.title)}</span>
          <button class="btn-icon" style="font-size:0.8rem; margin-left:6px; cursor:pointer; background:none; border:none; color:var(--primary);" title="Rename group" onclick="ChatApp.promptRenameGroup()">
            <i class="fas fa-edit"></i>
          </button>
        `;
      } else {
        titleEl.textContent = conv.title;
      }
    }
    if (descEl) descEl.textContent = conv.description || "No description set.";

    if (manageBtn) {
      manageBtn.style.display = (conv.type === "group" && isChannelAdmin) ? "inline-flex" : "none";
    }

    if (listEl && conv.participants) {
      listEl.innerHTML = "";
      conv.participants.forEach((p) => {
        const item = document.createElement("div");
        item.className = "member-item";
        const canRemove = isChannelAdmin && p.user_id !== this.currentUserId && p.role !== "admin";
        item.innerHTML = `
          <div class="member-info">
            <div class="avatar-wrapper">
              <img src="/static/uploads/avatars/${p.avatar}" class="avatar-img" style="width:28px;height:28px;" />
              <span class="status-indicator status-dot-user-${p.user_id} ${p.is_online ? "online" : ""}" style="width:8px;height:8px;"></span>
            </div>
            <span style="font-size:0.85rem;font-weight:600;">${this.escapeHtml(p.full_name || p.username)}</span>
          </div>
          <div style="display:flex; align-items:center; gap:6px;">
            <span class="member-role-badge">${p.role}</span>
            ${canRemove ? `
              <button class="btn-icon" style="color:var(--danger); background:none; border:none; cursor:pointer; font-size:0.8rem;" title="Remove member" onclick="ChatApp.removeGroupMember(${p.user_id}, '${this.escapeHtml(p.username)}')">
                <i class="fas fa-user-minus"></i>
              </button>
            ` : ""}
          </div>
        `;
        listEl.appendChild(item);
      });

      if (conv.type === "group") {
        const leaveContainer = document.createElement("div");
        leaveContainer.style.marginTop = "1rem";
        leaveContainer.innerHTML = `
          <button class="btn btn-secondary btn-sm" style="width:100%; color:var(--danger); border-color:var(--danger);" onclick="ChatApp.leaveCurrentGroup()">
            <i class="fas fa-arrow-right-from-bracket"></i> Leave Group
          </button>
        `;
        listEl.appendChild(leaveContainer);
      }
    }
  },

  promptRenameGroup() {
    if (!this.currentConversation) return;
    const titleInput = document.getElementById("rename-group-title-input");
    const descInput = document.getElementById("rename-group-desc-input");
    if (titleInput) titleInput.value = this.currentConversation.title || "";
    if (descInput) descInput.value = this.currentConversation.description || "";
    openModal("rename-group-modal");
  },

  submitRenameGroup() {
    if (!this.currentConversationId) return;
    const title = (document.getElementById("rename-group-title-input").value || "").trim();
    const desc = (document.getElementById("rename-group-desc-input").value || "").trim();
    if (!title) {
      showToast("Group title cannot be empty", "warning");
      return;
    }

    fetch(`/api/conversations/${this.currentConversationId}/rename`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: title, description: desc }),
    })
      .then((r) => r.json())
      .then((res) => {
        closeModal("rename-group-modal");
        if (res.success) {
          showToast(res.message || "Group updated", "success");
          if (this.currentConversation) {
            this.currentConversation.title = title;
            this.currentConversation.description = desc;
          }
          this.renderDetailsDrawer(this.currentConversation);
        } else {
          showToast(res.message || "Failed to update group", "danger");
        }
      })
      .catch((err) => showToast("Network error", "danger"));
  },

  removeGroupMember(userId, username) {
    if (!this.currentConversationId) return;
    if (!confirm(`Are you sure you want to remove ${username} from this group?`)) return;

    fetch(`/api/conversations/${this.currentConversationId}/participants/${userId}`, {
      method: "DELETE",
    })
      .then((r) => r.json())
      .then((res) => {
        if (res.success) {
          showToast(`${username} removed`, "info");
          this.fetchMessages(this.currentConversationId);
        } else {
          showToast(res.message || "Failed to remove member", "danger");
        }
      })
      .catch((err) => showToast("Network error", "danger"));
  },

  leaveCurrentGroup() {
    if (!this.currentConversationId) return;
    if (!confirm("Are you sure you want to leave this group channel?")) return;

    fetch(`/api/conversations/${this.currentConversationId}/participants/${this.currentUserId}`, {
      method: "DELETE",
    })
      .then((r) => r.json())
      .then((res) => {
        if (res.success) {
          showToast("You left the group", "info");
          window.location.href = "/c";
        } else {
          showToast(res.message || "Failed to leave group", "danger");
        }
      })
      .catch((err) => showToast("Network error", "danger"));
  },

  handleTyping() {
    if (!this.currentConversationId || !SocketManager.socket) return;

    if (!this.isTyping) {
      this.isTyping = true;
      SocketManager.socket.emit("typing", {
        conversation_id: this.currentConversationId,
        is_typing: true,
      });
    }

    clearTimeout(this.typingTimeout);
    this.typingTimeout = setTimeout(() => {
      this.isTyping = false;
      SocketManager.socket.emit("typing", {
        conversation_id: this.currentConversationId,
        is_typing: false,
      });
    }, 1200);
  },

  showTypingIndicator(username, isTyping) {
    if (!this.dom.typingIndicator) return;
    if (isTyping) {
      this.dom.typingUsernames.textContent = `${username} is typing`;
      this.dom.typingIndicator.style.visibility = "visible";
    } else {
      this.dom.typingIndicator.style.visibility = "hidden";
    }
  },

  sendMessage() {
    const text = this.dom.messageInput.value.trim();
    if (!text && this.pendingAttachments.length === 0) return;
    if (!this.currentConversationId) return;

    const tempId = "temp_" + Date.now();
    const payload = {
      conversation_id: this.currentConversationId,
      content: text,
      parent_id: this.replyParentId,
      attachment_ids: this.pendingAttachments.map((a) => a.id),
      temp_id: tempId,
    };

    // Optimistic UI append
    this.appendOptimisticMessage(payload, text);
    this.scrollToBottom();
    AudioAlerts.playSent();

    // Reset input states
    this.dom.messageInput.value = "";
    this.clearReply();
    this.clearAttachments();

    // Emit via WebSocket if connected, else fallback to REST API
    if (SocketManager.socket && SocketManager.socket.connected) {
      SocketManager.socket.emit("send_message", payload);
    } else {
      fetch(`/api/conversations/${this.currentConversationId}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
        .then((r) => r.json())
        .then((res) => {
          if (res.success && res.message) {
            this.handleMessageConfirmed({ temp_id: tempId, message: res.message });
          } else {
            showToast(res.message || "Failed to deliver message", "danger");
            const tempEl = document.getElementById(`msg-${tempId}`);
            if (tempEl) {
              tempEl.classList.add("msg-send-failed");
              const bubble = tempEl.querySelector(".message-bubble");
              if (bubble) bubble.style.opacity = "0.5";
            }
          }
        })
        .catch((err) => {
          console.error("HTTP send fallback error:", err);
          showToast("Network error while sending message", "danger");
          const tempEl = document.getElementById(`msg-${tempId}`);
          if (tempEl) {
            tempEl.classList.add("msg-send-failed");
            const bubble = tempEl.querySelector(".message-bubble");
            if (bubble) bubble.style.opacity = "0.5";
          }
        });
    }
  },

  handleMessageConfirmed(data) {
    if (!data || !data.message) return;
    const msg = data.message;
    if (data.temp_id) {
      const optEl = document.getElementById(`msg-${data.temp_id}`);
      if (optEl) {
        optEl.remove();
      }
    }
    if (msg.conversation_id === this.currentConversationId) {
      if (!document.getElementById(`msg-${msg.id}`)) {
        this.appendMessage(msg);
        this.scrollToBottom();
      }
    }
    this.updateSidebarSnippet(msg);
  },

  addConversationToSidebar(conv) {
    if (!conv || !this.dom.convList) return;
    if (document.querySelector(`.conversation-item[data-id="${conv.id}"]`)) return;

    const item = document.createElement("div");
    item.className = "conversation-item";
    item.dataset.id = conv.id;
    item.dataset.type = conv.type;
    item.dataset.title = conv.title;
    item.onclick = () => this.selectConversation(conv.id);

    const avatarUrl = `/static/uploads/avatars/${conv.icon || "default_group.svg"}`;
    item.innerHTML = `
      <div class="conv-avatar-box">
        <img src="${avatarUrl}" class="conv-avatar-img" alt="Avatar" />
      </div>
      <div class="conv-info">
        <div class="conv-top-line">
          <span class="conv-title">${this.escapeHtml(conv.title)}</span>
          <span class="conv-time">Just now</span>
        </div>
        <div class="conv-bottom-line">
          <span class="conv-snippet">${this.escapeHtml(conv.description || "New conversation")}</span>
          <span class="unread-badge">1</span>
        </div>
      </div>
    `;
    this.dom.convList.prepend(item);
  },

  appendOptimisticMessage(payload, text) {
    const row = document.createElement("div");
    row.id = `msg-${payload.temp_id}`;
    row.className = "message-row self optimistic";
    row.innerHTML = `
      <div class="msg-content-wrapper">
        <div class="msg-header">
          <span class="msg-timestamp">Sending...</span>
        </div>
        <div class="message-bubble">
          ${payload.parent_id ? `<div class="reply-quote-preview">Replying...</div>` : ""}
          <div class="msg-text">${this.escapeHtml(text)}</div>
          <span class="receipt-status">⏳</span>
        </div>
      </div>
    `;
    this.dom.messagesContainer.appendChild(row);
  },

  appendMessage(msg) {
    if (!msg) return;

    // Duplicate message prevention
    if (msg.id && document.getElementById(`msg-${msg.id}`)) {
      return;
    }

    // If optimistic message exists, replace it
    if (msg.temp_id) {
      const optEl = document.getElementById(`msg-${msg.temp_id}`);
      if (optEl) {
        optEl.remove();
      }
    }

    const row = this.createMessageElement(msg);
    this.dom.messagesContainer.appendChild(row);
  },

  createMessageElement(msg) {
    const isSelf = msg.sender_id === this.currentUserId;
    const row = document.createElement("div");
    row.id = `msg-${msg.id}`;
    row.className = `message-row ${isSelf ? "self" : "other"}`;

    if (msg.is_deleted) {
      row.innerHTML = `
        ${!isSelf ? `<img src="/static/uploads/avatars/${msg.sender_avatar}" class="msg-sender-avatar" />` : ""}
        <div class="msg-content-wrapper">
          <div class="msg-header">
            ${!isSelf ? `<span class="msg-sender-name">${this.escapeHtml(msg.sender_name)}</span>` : ""}
            <span class="msg-timestamp">${msg.formatted_time}</span>
          </div>
          <div class="message-bubble deleted-bubble" style="opacity:0.65;font-style:italic;background:var(--bg-tertiary);">
            <div class="msg-text"><i class="fas fa-ban" style="margin-right:4px;"></i>This message was deleted</div>
          </div>
        </div>
      `;
      return row;
    }

    // Sentiment indicator dot
    const sentimentClass =
      msg.sentiment_score >= 0.08
        ? "sentiment-dot-pos"
        : msg.sentiment_score <= -0.08
        ? "sentiment-dot-neg"
        : "sentiment-dot-neu";

    // Category tag
    const categoryTag =
      msg.category && msg.category !== "general"
        ? `<span class="badge-category badge-cat-${msg.category}">${msg.category}</span>`
        : "";

    // Attachments HTML
    let attachmentsHtml = "";
    if (msg.attachments && msg.attachments.length > 0) {
      attachmentsHtml = '<div class="msg-attachments-grid">';
      msg.attachments.forEach((att) => {
        if (att.file_type === "image") {
          attachmentsHtml += `
            <a href="${att.file_url}" target="_blank">
              <img src="${att.file_url}" class="msg-image-preview" alt="${this.escapeHtml(att.original_filename)}" />
            </a>
          `;
        } else {
          attachmentsHtml += `
            <a href="${att.file_url}" download="${this.escapeHtml(att.original_filename)}" class="msg-file-card">
              <i class="fas fa-file-alt" style="font-size:1.4rem;"></i>
              <div>
                <div style="font-weight:600;font-size:0.85rem;">${this.escapeHtml(att.original_filename)}</div>
                <div style="font-size:0.75rem;opacity:0.8;">${this.formatFileSize(att.file_size)}</div>
              </div>
            </a>
          `;
        }
      });
      attachmentsHtml += "</div>";
    }

    // Reactions HTML
    const reactionsHtml = this.renderReactionsHtml(msg.reactions || {});

    // Read Receipt Tick
    let tickHtml = "";
    if (isSelf) {
      const isRead = msg.read_count && msg.read_count > 0;
      tickHtml = `<span class="receipt-status ${isRead ? "read" : ""}">${isRead ? "✓✓" : "✓"}</span>`;
    }

    row.innerHTML = `
      ${!isSelf ? `<img src="/static/uploads/avatars/${msg.sender_avatar}" class="msg-sender-avatar" />` : ""}
      <div class="msg-content-wrapper">
        <div class="msg-header">
          ${!isSelf ? `<span class="msg-sender-name">${this.escapeHtml(msg.sender_name)}</span>` : ""}
          ${categoryTag}
          <span class="sentiment-indicator-dot ${sentimentClass}" title="Sentiment: ${msg.sentiment_label} (${msg.sentiment_score})"></span>
          <span class="msg-timestamp">${msg.formatted_time}</span>
          ${msg.is_edited ? `<span class="msg-edited-badge" style="font-size:0.7rem;opacity:0.65;margin-left:4px;font-style:italic;">(edited)</span>` : ""}
        </div>
        <div class="message-bubble">
          <!-- Quick reaction hover bar -->
          <div class="quick-reaction-bar">
            <button class="quick-reaction-btn" onclick="ChatApp.addReaction(${msg.id}, '👍')">👍</button>
            <button class="quick-reaction-btn" onclick="ChatApp.addReaction(${msg.id}, '❤️')">❤️</button>
            <button class="quick-reaction-btn" onclick="ChatApp.addReaction(${msg.id}, '😂')">😂</button>
            <button class="quick-reaction-btn" onclick="ChatApp.addReaction(${msg.id}, '🔥')">🔥</button>
            <button class="quick-reaction-btn" onclick="ChatApp.addReaction(${msg.id}, '🎉')">🎉</button>
            <button class="quick-reaction-btn" title="Reply" onclick="ChatApp.setReply(${msg.id}, '${this.escapeHtml(msg.content).slice(0, 30)}')"><i class="fas fa-reply" style="font-size:0.75rem;"></i></button>
            ${isSelf ? `
              <button class="quick-reaction-btn" title="Edit" onclick="ChatApp.openEditModal(${msg.id})"><i class="fas fa-pencil-alt" style="font-size:0.75rem;"></i></button>
              <button class="quick-reaction-btn" title="Delete" onclick="ChatApp.promptDeleteMessage(${msg.id})" style="color:var(--danger);"><i class="fas fa-trash-alt" style="font-size:0.75rem;"></i></button>
            ` : ""}
          </div>

          ${msg.parent_snippet ? `<div class="reply-quote-preview">↩ ${this.escapeHtml(msg.parent_snippet)}</div>` : ""}
          <div class="msg-text">${this.formatMessageBody(msg.content)}</div>
          ${attachmentsHtml}
          ${tickHtml}
        </div>
        <div class="reactions-wrapper" id="reactions-for-${msg.id}">
          ${reactionsHtml}
        </div>
      </div>
    `;

    return row;
  },

  renderReactionsHtml(reactionsDict) {
    let html = "";
    for (const [emoji, users] of Object.entries(reactionsDict)) {
      if (users.length > 0) {
        const usernames = users.map((u) => u.username).join(", ");
        html += `
          <button class="reaction-pill" title="${usernames}" onclick="ChatApp.addReaction(this.closest('.message-row').id.replace('msg-',''), '${emoji}')">
            <span>${emoji}</span>
            <span>${users.length}</span>
          </button>
        `;
      }
    }
    return html;
  },

  updateMessageReactions(msgId, reactions) {
    const container = document.getElementById(`reactions-for-${msgId}`);
    if (container) {
      container.innerHTML = this.renderReactionsHtml(reactions);
    }
  },

  addReaction(msgId, reactionEmoji) {
    if (!SocketManager.socket) return;
    SocketManager.socket.emit("add_reaction", {
      message_id: parseInt(msgId, 10),
      reaction: reactionEmoji,
    });
  },

  setReply(parentId, snippet) {
    this.replyParentId = parentId;
    this.replyParentSnippet = snippet;
    if (this.dom.replyBanner && this.dom.replySnippet) {
      this.dom.replySnippet.textContent = snippet + "...";
      this.dom.replyBanner.classList.add("active");
    }
    if (this.dom.messageInput) this.dom.messageInput.focus();
  },

  clearReply() {
    this.replyParentId = null;
    this.replyParentSnippet = null;
    if (this.dom.replyBanner) {
      this.dom.replyBanner.classList.remove("active");
    }
  },

  handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    showToast("Uploading attachment...", "info", 2000);

    fetch("/api/upload", {
      method: "POST",
      body: formData,
    })
      .then((r) => r.json())
      .then((data) => {
        if (!data.success) {
          showToast(data.message || "Upload failed", "danger");
          return;
        }

        this.pendingAttachments.push(data.attachment);
        this.renderPendingAttachments();
        showToast("Attachment ready!", "success");
      })
      .catch((err) => {
        console.error("Upload error:", err);
        showToast("Failed to upload file", "danger");
      });
  },

  renderPendingAttachments() {
    if (!this.dom.pendingAttachmentsPreview) return;
    this.dom.pendingAttachmentsPreview.innerHTML = "";
    this.pendingAttachments.forEach((att, idx) => {
      const pill = document.createElement("div");
      pill.style.cssText = "display:inline-flex;align-items:center;gap:6px;background:var(--bg-tertiary);padding:4px 8px;border-radius:var(--radius-sm);font-size:0.8rem;border:1px solid var(--border-color);";
      pill.innerHTML = `
        <i class="fas fa-paperclip"></i>
        <span>${this.escapeHtml(att.original_filename)}</span>
        <button style="background:none;border:none;cursor:pointer;color:var(--danger);" onclick="ChatApp.removePendingAttachment(${idx})">✕</button>
      `;
      this.dom.pendingAttachmentsPreview.appendChild(pill);
    });
  },

  removePendingAttachment(index) {
    this.pendingAttachments.splice(index, 1);
    this.renderPendingAttachments();
  },

  clearAttachments() {
    this.pendingAttachments = [];
    if (this.dom.pendingAttachmentsPreview) {
      this.dom.pendingAttachmentsPreview.innerHTML = "";
    }
    if (this.dom.fileInput) {
      this.dom.fileInput.value = "";
    }
  },

  openEditModal(msgId) {
    const msgEl = document.getElementById(`msg-${msgId}`);
    if (!msgEl) return;
    const textEl = msgEl.querySelector(".msg-text");
    const rawText = textEl ? textEl.innerText.trim() : "";
    document.getElementById("edit-message-id").value = msgId;
    document.getElementById("edit-message-text").value = rawText;
    openModal("edit-message-modal");
  },

  submitEditMessage() {
    const msgId = parseInt(document.getElementById("edit-message-id").value, 10);
    const newContent = document.getElementById("edit-message-text").value.trim();
    if (!msgId || !newContent) return;

    if (SocketManager.socket) {
      SocketManager.socket.emit("edit_message", {
        message_id: msgId,
        content: newContent,
      });
    } else {
      fetch(`/api/messages/${msgId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: newContent }),
      });
    }
    closeModal("edit-message-modal");
    showToast("Message updated", "success");
  },

  handleMessageEdited(msg) {
    const msgEl = document.getElementById(`msg-${msg.id}`);
    if (!msgEl) return;

    const textEl = msgEl.querySelector(".msg-text");
    if (textEl) {
      textEl.innerHTML = this.formatMessageBody(msg.content);
    }

    let editedBadge = msgEl.querySelector(".msg-edited-badge");
    if (!editedBadge) {
      const headerEl = msgEl.querySelector(".msg-header");
      if (headerEl) {
        const badge = document.createElement("span");
        badge.className = "msg-edited-badge";
        badge.style.cssText =
          "font-size:0.7rem;opacity:0.65;margin-left:4px;font-style:italic;";
        badge.textContent = "(edited)";
        headerEl.appendChild(badge);
      }
    }

    const dot = msgEl.querySelector(".sentiment-indicator-dot");
    if (dot && msg.sentiment_score !== undefined) {
      dot.className = `sentiment-indicator-dot ${
        msg.sentiment_score >= 0.08
          ? "sentiment-dot-pos"
          : msg.sentiment_score <= -0.08
          ? "sentiment-dot-neg"
          : "sentiment-dot-neu"
      }`;
      dot.title = `Sentiment: ${msg.sentiment_label} (${msg.sentiment_score})`;
    }
  },

  promptDeleteMessage(msgId) {
    document.getElementById("delete-message-id").value = msgId;
    openModal("delete-message-modal");
  },

  submitDeleteMessage() {
    const msgId = parseInt(document.getElementById("delete-message-id").value, 10);
    if (!msgId) return;

    if (SocketManager.socket) {
      SocketManager.socket.emit("delete_message", { message_id: msgId });
    } else {
      fetch(`/api/messages/${msgId}`, { method: "DELETE" });
    }
    closeModal("delete-message-modal");
    showToast("Message deleted", "info");
  },

  handleMessageDeleted(msgId) {
    const msgEl = document.getElementById(`msg-${msgId}`);
    if (!msgEl) return;

    const bubble = msgEl.querySelector(".message-bubble");
    if (bubble) {
      bubble.className = "message-bubble deleted-bubble";
      bubble.style.opacity = "0.65";
      bubble.style.fontStyle = "italic";
      bubble.style.background = "var(--bg-tertiary)";
      bubble.innerHTML =
        '<div class="msg-text"><i class="fas fa-ban" style="margin-right:4px;"></i>This message was deleted</div>';
    }

    const rxWrapper = msgEl.querySelector(".reactions-wrapper");
    if (rxWrapper) rxWrapper.remove();
  },

  executeMessageSearch() {
    const q = (document.getElementById("msg-search-query").value || "").trim();
    const cat = document.getElementById("msg-search-category").value;
    const sent = document.getElementById("msg-search-sentiment").value;
    const resultsContainer = document.getElementById("msg-search-results-list");

    if (!q && !cat && !sent) {
      resultsContainer.innerHTML =
        '<div style="text-align:center;color:var(--text-muted);padding:2rem;">Please enter keywords or select a filter.</div>';
      return;
    }

    resultsContainer.innerHTML =
      '<div style="text-align:center;padding:2rem;"><i class="fas fa-circle-notch fa-spin"></i> Searching messages...</div>';

    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (cat) params.set("category", cat);
    if (sent) params.set("sentiment", sent);

    fetch(`/api/messages/search?${params.toString()}`)
      .then((r) => r.json())
      .then((data) => {
        if (!data.success || !data.results || data.results.length === 0) {
          resultsContainer.innerHTML =
            '<div style="text-align:center;color:var(--text-muted);padding:2rem;">No matching messages found.</div>';
          return;
        }

        resultsContainer.innerHTML = "";
        data.results.forEach((m) => {
          const item = document.createElement("div");
          item.style.cssText =
            "padding:10px; background:var(--bg-tertiary); border:1px solid var(--border-color); border-radius:var(--radius-sm); cursor:pointer; transition:background 0.2s;";
          item.onmouseover = () => (item.style.background = "var(--bg-secondary)");
          item.onmouseout = () => (item.style.background = "var(--bg-tertiary)");
          item.onclick = () => {
            closeModal("search-messages-modal");
            this.selectConversation(m.conversation_id);
          };

          const catBadge =
            m.category && m.category !== "general"
              ? `<span class="badge-category badge-cat-${m.category}">${m.category}</span>`
              : "";
          const sentColor =
            m.sentiment_score >= 0.08
              ? "var(--success)"
              : m.sentiment_score <= -0.08
              ? "var(--danger)"
              : "var(--text-muted)";

          item.innerHTML = `
            <div style="display:flex; justify-content:space-between; margin-bottom:4px; font-size:0.8rem;">
              <span style="font-weight:700;">${this.escapeHtml(m.sender_name || "System")}</span>
              <span style="color:var(--text-muted);">${m.formatted_time || ""}</span>
            </div>
            <div style="font-size:0.9rem; margin-bottom:4px; color:var(--text-primary);">${this.escapeHtml(m.content || "[Attachment]")}</div>
            <div style="display:flex; gap:6px; align-items:center; font-size:0.75rem;">
              ${catBadge}
              <span style="color:${sentColor};">Sentiment: ${m.sentiment_label || "neutral"}</span>
            </div>
          `;
          resultsContainer.appendChild(item);
        });
      })
      .catch((err) => {
        console.error("Search error:", err);
        resultsContainer.innerHTML =
          '<div style="text-align:center;color:var(--danger);padding:2rem;">Search failed. Please try again.</div>';
      });
  },

  triggerSummarize() {
    if (!this.currentConversationId) return;

    openModal("summary-modal");
    const body = document.getElementById("summary-modal-content");
    if (body) {
      body.innerHTML = `
        <div style="text-align:center;padding:2rem;">
          <div class="fas fa-circle-notch fa-spin" style="font-size:2rem;color:var(--primary);margin-bottom:1rem;"></div>
          <div>Running Python extractive summarization algorithm...</div>
        </div>
      `;
    }

    fetch(`/api/conversations/${this.currentConversationId}/summarize`, { method: "POST" })
      .then((r) => r.json())
      .then((data) => {
        if (!data.success || !body) {
          if (body) body.textContent = "Summarization could not be completed.";
          return;
        }

        const s = data.summary;
        let bulletsHtml = s.bullets.map((b) => `<li style="margin-bottom:6px;">${this.escapeHtml(b)}</li>`).join("");
        let actionsHtml = s.action_items.map((a) => `<li style="margin-bottom:4px;color:var(--accent);">${this.escapeHtml(a)}</li>`).join("");
        let decisionsHtml = (s.decisions || []).map((d) => `<li style="margin-bottom:4px;">${this.escapeHtml(d)}</li>`).join("");
        let topicsHtml = s.key_topics.map((t) => `<span class="badge-category badge-cat-greeting">${this.escapeHtml(t)}</span>`).join(" ");

        body.innerHTML = `
          <div style="margin-bottom:1rem;">
            <h4 style="font-size:0.95rem;font-weight:700;margin-bottom:0.5rem;"><i class="fas fa-list-ul"></i> Key Discussion Points:</h4>
            <ul style="padding-left:1.25rem;font-size:0.9rem;">
              ${bulletsHtml || "<li>Conversation is too brief for key takeaways.</li>"}
            </ul>
          </div>

          ${s.decisions && s.decisions.length > 0 ? `
          <div style="margin-bottom:1rem;background:rgba(16, 185, 129, 0.08);border-left:3px solid var(--success);padding:0.75rem;border-radius:var(--radius-sm);">
            <h4 style="font-size:0.95rem;font-weight:700;margin-bottom:0.5rem;color:var(--success);"><i class="fas fa-circle-check"></i> Confirmed Decisions:</h4>
            <ul style="padding-left:1.25rem;font-size:0.85rem;">
              ${decisionsHtml}
            </ul>
          </div>
          ` : ""}

          ${s.action_items && s.action_items.length > 0 ? `
          <div style="margin-bottom:1rem;background:var(--bg-tertiary);padding:0.75rem;border-radius:var(--radius-sm);">
            <h4 style="font-size:0.95rem;font-weight:700;margin-bottom:0.5rem;"><i class="fas fa-tasks"></i> Extracted Action Items:</h4>
            <ul style="padding-left:1.25rem;font-size:0.85rem;">
              ${actionsHtml}
            </ul>
          </div>
          ` : ""}

          <div>
            <h4 style="font-size:0.85rem;font-weight:700;margin-bottom:0.4rem;"><i class="fas fa-tags"></i> Top Conversation Topics:</h4>
            <div>${topicsHtml || "None"}</div>
          </div>
        `;
      })
      .catch((err) => {
        if (body) body.textContent = "Failed to run summarizer.";
      });
  },

  fetchOnlineContacts() {
    fetch("/api/users/online")
      .then((r) => r.json())
      .then((data) => {
        if (!data.success || !data.users) return;
        const container = document.getElementById("online-contacts-list");
        const countBadge = document.getElementById("ribbon-online-count");
        if (countBadge) countBadge.textContent = data.users.length;
        if (!container) return;

        if (data.users.length === 0) {
          container.innerHTML =
            '<span style="font-size:0.75rem; color:var(--text-muted); padding:4px 0;">No contacts online</span>';
          return;
        }

        container.innerHTML = "";
        data.users.forEach((u) => {
          const item = document.createElement("div");
          item.className = "online-contact-item";
          item.title = `${u.full_name} (${u.status_message})`;
          item.innerHTML = `
            <div class="avatar-wrapper">
              <img src="/static/uploads/avatars/${u.avatar}" class="avatar-img" />
              <span class="status-indicator online"></span>
            </div>
            <div class="online-contact-name">${this.escapeHtml(u.username)}</div>
          `;
          item.addEventListener("click", () => {
            if (u.conversation_id) {
              this.selectConversation(u.conversation_id);
            } else {
              // Create direct conversation
              fetch("/api/conversations", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ type: "direct", recipient_id: u.id }),
              })
                .then((r) => r.json())
                .then((res) => {
                  if (res.success && res.conversation) {
                    window.location.href = `/c/${res.conversation.id}`;
                  }
                });
            }
          });
          container.appendChild(item);
        });
      })
      .catch((err) => console.debug("Error fetching online contacts", err));
  },

  initEmojiPicker() {
    this.switchEmojiTab("smileys");
  },

  toggleEmojiPicker(forceState) {
    const popover = document.getElementById("emoji-picker-popover");
    if (!popover) return;
    if (forceState !== undefined) {
      popover.classList.toggle("hidden", !forceState);
    } else {
      popover.classList.toggle("hidden");
    }
  },

  switchEmojiTab(tabName) {
    document.querySelectorAll(".emoji-tab-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.textContent.trim() === this.getTabIcon(tabName));
    });

    const grid = document.getElementById("emoji-grid-body");
    if (!grid) return;
    grid.innerHTML = "";

    const list = this.emojiCategories[tabName] || [];
    list.forEach((emoji) => {
      const cell = document.createElement("span");
      cell.className = "emoji-cell";
      cell.textContent = emoji;
      cell.addEventListener("click", () => this.insertEmoji(emoji));
      grid.appendChild(cell);
    });
  },

  getTabIcon(tabName) {
    const map = { smileys: "😀", gestures: "👍", hearts: "❤️", tech: "💻", party: "🎉" };
    return map[tabName] || "😀";
  },

  insertEmoji(emoji) {
    const input = this.dom.messageInput;
    if (!input) return;
    const start = input.selectionStart || 0;
    const end = input.selectionEnd || 0;
    const text = input.value;
    input.value = text.substring(0, start) + emoji + text.substring(end);
    input.selectionStart = input.selectionEnd = start + emoji.length;
    input.focus();
  },

  updateSidebarSnippet(msg) {
    const item = document.querySelector(`.conversation-item[data-id="${msg.conversation_id}"]`);
    if (item) {
      const snippetEl = item.querySelector(".conv-snippet");
      const timeEl = item.querySelector(".conv-time");
      if (snippetEl) snippetEl.textContent = msg.content || "[Attachment]";
      if (timeEl) timeEl.textContent = msg.formatted_time;
      // Re-order item to top of list
      this.dom.convList.prepend(item);
    }
  },

  scrollToBottom() {
    if (this.dom.messagesContainer) {
      this.dom.messagesContainer.scrollTop = this.dom.messagesContainer.scrollHeight;
    }
  },

  formatMessageBody(content) {
    if (!content) return "";
    let safe = this.escapeHtml(content);
    // Simple bold markdown
    safe = safe.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    // Simple inline code
    safe = safe.replace(/`([^`]+)`/g, "<code class='chat-inline-code'>$1</code>");
    return safe;
  },

  escapeHtml(str) {
    if (!str) return "";
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  },

  formatFileSize(bytes) {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  },
};

window.ChatApp = ChatApp;
