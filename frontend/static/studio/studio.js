document.addEventListener("DOMContentLoaded", () => {
  const shell = document.querySelector(".studio-shell");
  const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]")?.value;
  const alertBox = document.querySelector("[data-studio-alert]");

  function showMessage(text, isError = false) {
    if (!alertBox) return;
    alertBox.textContent = text;
    alertBox.hidden = false;
    alertBox.style.background = isError ? "var(--rose)" : "var(--teal)";
    window.clearTimeout(showMessage.timer);
    showMessage.timer = window.setTimeout(() => {
      alertBox.hidden = true;
    }, 2600);
  }

  document.querySelectorAll("[data-tab]").forEach((tab) => {
    tab.addEventListener("click", () => {
      const target = tab.dataset.tab;
      document.querySelectorAll("[data-tab]").forEach((item) => item.classList.toggle("is-active", item === tab));
      document.querySelectorAll("[data-view]").forEach((view) => {
        view.classList.toggle("is-active", view.dataset.view === target);
      });
    });
  });

  let draggedGuest = null;

  function syncEmptyStates() {
    document.querySelectorAll(".table-dropzone").forEach((zone) => {
      const hasGuests = zone.querySelector(".guest-chip");
      let empty = zone.querySelector(".empty-drop");
      if (!hasGuests && !empty) {
        empty = document.createElement("p");
        empty.className = "empty-drop";
        empty.textContent = "Свободный стол";
        zone.append(empty);
      }
      if (hasGuests && empty) empty.remove();
    });
  }

  function updateCounts(counts) {
    Object.entries(counts || {}).forEach(([tableId, count]) => {
      const node = document.querySelector(`[data-table-count="${tableId}"]`);
      if (node) node.textContent = count;
    });
  }

  async function moveGuest(guestId, tableId, chip) {
    const response = await fetch(shell.dataset.moveUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
      },
      body: JSON.stringify({ guest_id: guestId, table_id: tableId }),
    });
    const payload = await response.json();
    if (!response.ok || !payload.ok) {
      showMessage(payload.error || "Не получилось переместить гостя.", true);
      return false;
    }

    const targetZone = document.querySelector(`[data-drop-table="${tableId}"]`);
    targetZone?.append(chip);
    chip.querySelector("select").value = String(tableId);
    updateCounts(payload.counts);
    syncEmptyStates();
    showMessage("Гость перемещен.");
    return true;
  }

  document.querySelectorAll(".guest-chip").forEach((chip) => {
    chip.addEventListener("dragstart", (event) => {
      draggedGuest = chip;
      chip.classList.add("is-dragging");
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", chip.dataset.guestId);
    });

    chip.addEventListener("dragend", () => {
      chip.classList.remove("is-dragging");
      draggedGuest = null;
    });
  });

  document.querySelectorAll(".table-dropzone").forEach((zone) => {
    zone.addEventListener("dragover", (event) => {
      event.preventDefault();
      zone.classList.add("is-over");
    });

    zone.addEventListener("dragleave", () => {
      zone.classList.remove("is-over");
    });

    zone.addEventListener("drop", async (event) => {
      event.preventDefault();
      zone.classList.remove("is-over");
      const guestId = event.dataTransfer.getData("text/plain");
      const chip = draggedGuest || document.querySelector(`[data-guest-id="${guestId}"]`);
      if (!chip) return;
      await moveGuest(guestId, zone.dataset.dropTable, chip);
    });
  });

  document.querySelectorAll("[data-guest-move]").forEach((select) => {
    select.addEventListener("change", async () => {
      const chip = select.closest(".guest-chip");
      const oldValue = chip.closest("[data-drop-table]")?.dataset.dropTable;
      const moved = await moveGuest(select.dataset.guestMove, select.value, chip);
      if (!moved && oldValue) select.value = oldValue;
    });
  });

  const qrInput = document.querySelector("[data-qr-url]");
  const qrImage = document.querySelector("[data-qr-image]");
  function updateQr() {
    if (!qrInput || !qrImage) return;
    const encoded = encodeURIComponent(qrInput.value.trim() || shell.dataset.entryUrl);
    qrImage.src = `https://api.qrserver.com/v1/create-qr-code/?size=260x260&margin=12&data=${encoded}`;
  }

  document.querySelector("[data-update-qr]")?.addEventListener("click", () => {
    updateQr();
    showMessage("QR обновлен.");
  });

  document.querySelector("[data-copy-link]")?.addEventListener("click", async () => {
    await navigator.clipboard.writeText(qrInput.value.trim());
    showMessage("Ссылка скопирована.");
  });

  document.querySelector("[data-print-qr]")?.addEventListener("click", () => {
    window.print();
  });

  const previewTargets = {
    groom: document.querySelector("[data-preview-groom]"),
    bride: document.querySelector("[data-preview-bride]"),
    place: document.querySelector("[data-preview-place]"),
    date: document.querySelector("[data-preview-date]"),
    text: document.querySelector("[data-preview-text]"),
  };

  document.querySelectorAll("[data-invite-field]").forEach((field) => {
    field.addEventListener("input", () => {
      const target = previewTargets[field.dataset.inviteField];
      if (target) target.textContent = field.value;
    });
  });

  syncEmptyStates();
});
