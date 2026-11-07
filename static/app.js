document.addEventListener("DOMContentLoaded", () => {
  const messagesContainer = document.getElementById("messages-container");
  const chatForm = document.getElementById("chat-form");
  const chatInput = document.getElementById("chat-input");
  const btnSend = document.getElementById("btn-send");
  const typingIndicator = document.getElementById("typing-indicator");
  const typingText = document.getElementById("typing-text");

  const modalMemories = document.getElementById("modal-memories");
  const modalSettings = document.getElementById("modal-settings");
  const btnMemories = document.getElementById("btn-memories");
  const btnSettings = document.getElementById("btn-settings");
  const memoriesList = document.getElementById("memories-list");
  const formNewMemory = document.getElementById("form-new-memory");
  const formSettings = document.getElementById("form-settings");

  const settingProvider = document.getElementById("setting-provider");
  const groupOpenai = document.getElementById("group-openai");
  const groupGemini = document.getElementById("group-gemini");

  loadMessages();
  loadSettings();

  chatInput.addEventListener("input", () => {
    chatInput.style.height = "auto";
    chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + "px";
  });

  chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      chatForm.dispatchEvent(new Event("submit"));
    }
  });

  chatForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const content = chatInput.value.trim();
    if (!content) return;

    chatInput.value = "";
    chatInput.style.height = "auto";
    btnSend.disabled = true;

    const tempUserMsg = {
      sender: "Huy",
      content: content,
      timestamp: formatTime(new Date())
    };
    appendMessage(tempUserMsg);
    scrollToBottom();

    showTyping("Jules và Bánh đang suy nghĩ...");

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: content })
      });
      const data = await res.json();
      hideTyping();

      if (data.status === "ok" && data.agent_replies) {
        for (let i = 0; i < data.agent_replies.length; i++) {
          const reply = data.agent_replies[i];
          if (i > 0) {
            showTyping(`${reply.sender} đang trả lời...`);
            await new Promise((r) => setTimeout(r, 600));
            hideTyping();
          }
          appendMessage(reply);
          scrollToBottom();
        }
      }
    } catch (err) {
      hideTyping();
      appendMessage({
        sender: "System",
        content: "Không thể kết nối đến phòng. Hãy kiểm tra server nha!",
        timestamp: formatTime(new Date())
      });
    } finally {
      btnSend.disabled = false;
      chatInput.focus();
    }
  });

  async function loadMessages() {
    try {
      const res = await fetch("/api/messages?limit=100");
      const data = await res.json();
      if (data.status === "ok" && data.messages) {
        messagesContainer.innerHTML = "";
        data.messages.forEach(appendMessage);
        scrollToBottom();
      }
    } catch (err) {
      console.error("Failed to load messages", err);
    }
  }

  function appendMessage(msg) {
    const item = document.createElement("div");
    const senderLower = msg.sender.toLowerCase();
    item.className = `message-item ${senderLower}`;

    let avatar = "💬";
    if (senderLower === "huy") avatar = "✨";
    else if (senderLower === "jules") avatar = "🐙";
    else if (senderLower === "banh" || senderLower === "bánh") avatar = "🤍";

    item.innerHTML = `
      <div class="message-avatar">${avatar}</div>
      <div class="message-bubble">
        <div class="message-meta">
          <span class="message-sender">${escapeHtml(msg.sender)}</span>
          <span class="message-time">${escapeHtml(msg.timestamp || "")}</span>
        </div>
        <div class="message-text">${escapeHtml(msg.content)}</div>
      </div>
    `;

    messagesContainer.appendChild(item);
  }

  function scrollToBottom() {
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  function showTyping(text) {
    typingText.textContent = text;
    typingIndicator.classList.remove("hidden");
    scrollToBottom();
  }

  function hideTyping() {
    typingIndicator.classList.add("hidden");
  }

  function formatTime(date) {
    const pad = (n) => String(n).padStart(2, "0");
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
  }

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  btnMemories.addEventListener("click", () => {
    loadMemories();
    modalMemories.classList.remove("hidden");
  });

  btnSettings.addEventListener("click", () => {
    modalSettings.classList.remove("hidden");
  });

  document.querySelectorAll("[data-close]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const modalId = btn.getAttribute("data-close");
      document.getElementById(modalId).classList.add("hidden");
    });
  });

  async function loadMemories() {
    try {
      const res = await fetch("/api/memories");
      const data = await res.json();
      if (data.status === "ok" && data.memories) {
        memoriesList.innerHTML = "";
        data.memories.forEach((m) => {
          const div = document.createElement("div");
          div.className = "memory-item";
          div.innerHTML = `
            <h5>📌 ${escapeHtml(m.title)}</h5>
            <p>${escapeHtml(m.content)}</p>
          `;
          memoriesList.appendChild(div);
        });
      }
    } catch (err) {
      console.error(err);
    }
  }

  formNewMemory.addEventListener("submit", async (e) => {
    e.preventDefault();
    const title = document.getElementById("memory-title").value.trim();
    const content = document.getElementById("memory-content").value.trim();
    if (!title || !content) return;

    try {
      const res = await fetch("/api/memories", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ category: "custom", title, content })
      });
      const data = await res.json();
      if (data.status === "ok") {
        document.getElementById("memory-title").value = "";
        document.getElementById("memory-content").value = "";
        loadMemories();
      }
    } catch (err) {
      alert("Không thể lưu memory!");
    }
  });

  settingProvider.addEventListener("change", () => {
    const val = settingProvider.value;
    groupOpenai.classList.toggle("hidden", val !== "openai");
    groupGemini.classList.toggle("hidden", val !== "gemini");
  });

  async function loadSettings() {
    try {
      const res = await fetch("/api/settings");
      const data = await res.json();
      if (data.status === "ok" && data.settings) {
        const s = data.settings;
        if (s.api_provider) {
          settingProvider.value = s.api_provider;
          settingProvider.dispatchEvent(new Event("change"));
        }
        if (s.openai_model) document.getElementById("setting-openai-model").value = s.openai_model;
        if (s.gemini_model) document.getElementById("setting-gemini-model").value = s.gemini_model;
        if (s.openai_api_key_masked) {
          document.getElementById("setting-openai-key").placeholder = s.openai_api_key_masked;
        }
        if (s.gemini_api_key_masked) {
          document.getElementById("setting-gemini-key").placeholder = s.gemini_api_key_masked;
        }
      }
    } catch (err) {
      console.error(err);
    }
  }

  formSettings.addEventListener("submit", async (e) => {
    e.preventDefault();
    const payload = {
      api_provider: settingProvider.value,
      openai_model: document.getElementById("setting-openai-model").value.trim(),
      gemini_model: document.getElementById("setting-gemini-model").value.trim()
    };
    const openAiKey = document.getElementById("setting-openai-key").value.trim();
    if (openAiKey) payload.openai_api_key = openAiKey;
    const geminiKey = document.getElementById("setting-gemini-key").value.trim();
    if (geminiKey) payload.gemini_api_key = geminiKey;

    try {
      const res = await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data.status === "ok") {
        alert("Đã lưu cài đặt thành công!");
        modalSettings.classList.add("hidden");
        loadSettings();
      }
    } catch (err) {
      alert("Lỗi khi lưu cài đặt!");
    }
  });
});
