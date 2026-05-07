document.addEventListener("DOMContentLoaded", () => {
  const revealTargets = document.querySelectorAll(
    ".page-header, .couple-hero, .home-info-grid article, .location-card, .event-time-card, .section, .post-card, .author-row, .upload-card, .locked-card, .access-request-card, .profile-head, .account-actions, .manage-card, .host-form-card"
  );

  if ("IntersectionObserver" in window) {
    const revealObserver = new IntersectionObserver(
      (entries, observer) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        });
      },
      { rootMargin: "0px 0px -8% 0px", threshold: 0.12 }
    );

    revealTargets.forEach((target, index) => {
      target.classList.add("reveal-item");
      target.style.setProperty("--reveal-delay", `${Math.min(index % 6, 5) * 55}ms`);
      revealObserver.observe(target);
    });
  } else {
    revealTargets.forEach((target) => target.classList.add("is-visible"));
  }

  const invite = document.querySelector("[data-invite-modal]");
  if (invite) {
    const key = invite.dataset.inviteKey;
    if (sessionStorage.getItem(key) !== "closed") {
      invite.classList.add("is-open");
    }

    const openInvite = () => {
      sessionStorage.removeItem(key);
      invite.classList.add("is-open");
    };

    document.querySelectorAll("[data-invite-open]").forEach((trigger) => {
      trigger.addEventListener("click", openInvite);
      trigger.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          openInvite();
        }
      });
    });

    invite.querySelector("[data-invite-close]")?.addEventListener("click", () => {
      sessionStorage.setItem(key, "closed");
      invite.classList.remove("is-open");
    });

    invite.addEventListener("click", (event) => {
      if (event.target === invite) {
        sessionStorage.setItem(key, "closed");
        invite.classList.remove("is-open");
      }
    });
  }

  const format = (value) => String(value).padStart(2, "0");

  function partsUntil(startAt) {
    const diff = Math.max(0, new Date(startAt).getTime() - Date.now());
    const totalMinutes = Math.floor(diff / 60000);
    const days = Math.floor(totalMinutes / 1440);
    const hours = Math.floor((totalMinutes % 1440) / 60);
    const minutes = totalMinutes % 60;
    return { days, hours, minutes, diff };
  }

  function startInviteCountdown() {
    const modal = document.querySelector("[data-invite-modal][data-invite-start]");
    const inline = document.querySelector("[data-inline-countdown][data-invite-start]");
    const startAt = modal?.dataset.inviteStart || inline?.dataset.inviteStart;
    if (!startAt) return;

    const tick = () => {
      const time = partsUntil(startAt);
      document.querySelector("[data-countdown-days]")?.replaceChildren(format(time.days));
      document.querySelector("[data-countdown-hours]")?.replaceChildren(format(time.hours));
      document.querySelector("[data-countdown-minutes]")?.replaceChildren(format(time.minutes));
      document.querySelector("[data-inline-days]")?.replaceChildren(format(time.days));

      if (time.diff <= 0) {
        modal?.classList.remove("is-open");
        inline?.remove();
      }
    };

    tick();
    setInterval(tick, 30000);
  }

  startInviteCountdown();

  const tableMap = document.querySelector("[data-table-map]");
  const tableButtons = Array.from(document.querySelectorAll(".table-circle, .venue-table"));

  tableButtons.forEach((table) => {
    const occupied = Number(table.dataset.guestCount || 0);
    const capacity = Number(table.dataset.capacity || 10);
    table.querySelectorAll(".chair-ring i").forEach((chair, index) => {
      chair.hidden = index >= capacity;
      chair.classList.toggle("is-occupied", index < occupied);
    });
  });

  function closeTableSheets() {
    document.querySelectorAll(".table-modal.is-open").forEach((modal) => {
      modal.classList.remove("is-open");
      modal.setAttribute("aria-hidden", "true");
    });
    tableButtons.forEach((table) => table.classList.remove("is-selected"));
  }

  function openTableSheet(targetId) {
    const modal = document.getElementById(targetId);
    if (!modal) return;
    closeTableSheets();
    modal.classList.add("is-open");
    modal.setAttribute("aria-hidden", "false");
    document.querySelectorAll(`[data-table-open="${targetId}"]`).forEach((trigger) => {
      trigger.classList.add("is-selected");
    });
  }

  document.querySelectorAll("[data-table-open]").forEach((button) => {
    button.addEventListener("click", () => openTableSheet(button.dataset.tableOpen));
  });

  document.querySelectorAll("[data-table-close]").forEach((button) => {
    button.addEventListener("click", () => {
      closeTableSheets();
    });
  });

  document.querySelectorAll(".table-modal").forEach((modal) => {
    modal.addEventListener("click", (event) => {
      if (event.target === modal) {
        closeTableSheets();
      }
    });
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeTableSheets();
    }
  });

  const tableSearch = document.getElementById("tableSearch");
  const tableSearchResult = document.getElementById("tableSearchResult");
  if (tableSearch && tableMap) {
    tableSearch.addEventListener("input", () => {
      const query = tableSearch.value.trim().toLowerCase();
      let matches = 0;
      let firstMatch = null;

      tableMap.classList.toggle("is-searching", query.length > 0);

      tableButtons.forEach((table) => {
        const haystack = `${table.dataset.tableName || ""} ${table.dataset.guests || ""}`.toLowerCase();
        const isMatch = query.length > 0 && haystack.includes(query);
        table.classList.toggle("is-match", isMatch);
        if (isMatch) {
          matches += 1;
          firstMatch ||= table;
        }
      });

      if (!query) {
        tableSearchResult.textContent = "Введите имя гостя, чтобы подсветить его стол.";
        return;
      }

      if (matches === 0) {
        tableSearchResult.textContent = "Гость не найден. Проверьте написание имени.";
        return;
      }

      const label = firstMatch.dataset.tableName;
      const number = firstMatch.dataset.tableNumber;
      tableSearchResult.textContent = `Найдено: Стол №${number} · ${label}`;
    });
  }

  let pendingDeleteForm = null;
  const deleteForms = document.querySelectorAll("form[data-confirm-delete]");
  if (deleteForms.length) {
    const confirmModal = document.createElement("div");
    confirmModal.className = "confirm-modal";
    confirmModal.setAttribute("aria-hidden", "true");
    confirmModal.innerHTML = `
      <div class="confirm-card" role="dialog" aria-modal="true" aria-labelledby="deleteConfirmTitle">
        <h2 id="deleteConfirmTitle">Удалить медиа?</h2>
        <p data-confirm-text>После подтверждения публикация исчезнет из альбома.</p>
        <div class="confirm-actions">
          <button class="secondary-button" type="button" data-confirm-cancel>Нет</button>
          <button class="danger-button" type="button" data-confirm-yes>Да, удалить</button>
        </div>
      </div>
    `;
    document.body.append(confirmModal);

    const closeConfirm = () => {
      confirmModal.classList.remove("is-open");
      confirmModal.setAttribute("aria-hidden", "true");
      pendingDeleteForm = null;
    };

    const openConfirm = (form) => {
      pendingDeleteForm = form;
      confirmModal.querySelector("#deleteConfirmTitle").textContent = form.dataset.confirmTitle || "Удалить медиа?";
      confirmModal.querySelector("[data-confirm-text]").textContent =
        form.dataset.confirmText || "После подтверждения публикация исчезнет из альбома.";
      confirmModal.querySelector("[data-confirm-yes]").textContent = form.dataset.confirmYes || "Да, удалить";
      confirmModal.classList.add("is-open");
      confirmModal.setAttribute("aria-hidden", "false");
      confirmModal.querySelector("[data-confirm-cancel]")?.focus();
    };

    deleteForms.forEach((form) => {
      form.addEventListener("submit", (event) => {
        event.preventDefault();
        openConfirm(form);
      });
    });

    confirmModal.querySelector("[data-confirm-cancel]")?.addEventListener("click", closeConfirm);
    confirmModal.querySelector("[data-confirm-yes]")?.addEventListener("click", () => {
      const form = pendingDeleteForm;
      closeConfirm();
      form?.submit();
    });
    confirmModal.addEventListener("click", (event) => {
      if (event.target === confirmModal) {
        closeConfirm();
      }
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && confirmModal.classList.contains("is-open")) {
        closeConfirm();
      }
    });
  }

  const fileInput = document.getElementById("id_file");
  const fileName = document.getElementById("fileName");
  const preview = document.getElementById("uploadPreview");
  if (fileInput && preview) {
    fileInput.addEventListener("change", () => {
      const file = fileInput.files?.[0];
      if (!file) return;
      if (fileName) fileName.textContent = file.name;

      const url = URL.createObjectURL(file);
      const isVideo = file.type.startsWith("video/");
      preview.innerHTML = isVideo
        ? `<video src="${url}" controls playsinline></video>`
        : `<img src="${url}" alt="Предпросмотр">`;
      preview.classList.add("is-visible");
    });
  }

  document.querySelectorAll("[data-like-form]").forEach((form) => {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = form.querySelector("button");
      const counter = form.querySelector("[data-like-count]");
      const data = new FormData(form);
      const response = await fetch(form.action, {
        method: "POST",
        headers: { "X-Requested-With": "XMLHttpRequest" },
        body: data,
      });
      if (!response.ok) {
        form.submit();
        return;
      }
      const payload = await response.json();
      button?.classList.toggle("is-liked", payload.liked);
      if (counter) counter.textContent = payload.likes_count;
    });
  });

  document.querySelectorAll("[data-comment-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      const card = button.closest("[data-post-card]");
      const panel = card?.querySelector("[data-comment-panel]");
      if (!panel) return;
      const nextOpen = panel.hidden;
      panel.hidden = !nextOpen;
      button.setAttribute("aria-expanded", String(nextOpen));
      if (nextOpen) {
        panel.querySelector("input, textarea")?.focus();
      }
    });
  });

  document.querySelectorAll("[data-comment-form]").forEach((form) => {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const input = form.querySelector("input, textarea");
      if (!input?.value.trim()) return;

      const card = form.closest("[data-post-card]");
      const comments = card?.querySelector("[data-comments-list]");
      const counter = card?.querySelector("[data-comment-count]");
      const data = new FormData(form);
      const response = await fetch(form.action, {
        method: "POST",
        headers: { "X-Requested-With": "XMLHttpRequest" },
        body: data,
      });
      if (!response.ok) {
        form.submit();
        return;
      }
      const payload = await response.json();
      if (!payload.ok) return;

      const comment = document.createElement("p");
      const author = document.createElement("b");
      author.textContent = `@${payload.nickname}`;
      comment.append(author, ` ${payload.body}`);
      comments?.append(comment);
      if (counter) counter.textContent = payload.comments_count;
      form.reset();
    });
  });
});
