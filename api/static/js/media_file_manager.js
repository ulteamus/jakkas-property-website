/**
 * Multi-file picker with DataTransfer-backed remove buttons.
 * Accumulates selections across picker opens; X removes one file and syncs input.
 * Usage: MediaFileManager.bind(inputEl, previewEl, { listClass: 'media-file-list--photos' })
 */
(function (global) {
  function formatSize(bytes) {
    if (!bytes && bytes !== 0) return "";
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / 1048576).toFixed(1) + " MB";
  }

  function fileKey(file) {
    return [file.name, file.size, file.lastModified].join(":");
  }

  function syncInput(input, files) {
    const dt = new DataTransfer();
    files.forEach((f) => dt.items.add(f));
    input.files = dt.files;
  }

  function render(input, preview, files, state) {
    preview.innerHTML = "";
    if (!files.length) {
      preview.classList.add("d-none");
      return;
    }
    preview.classList.remove("d-none");
    files.forEach((file, index) => {
      const row = document.createElement("div");
      row.className = "media-file-item";

      const thumb = document.createElement("div");
      thumb.className = "media-file-thumb";
      if (file.type.startsWith("image/")) {
        const img = document.createElement("img");
        img.alt = "";
        img.src = URL.createObjectURL(file);
        img.onload = () => URL.revokeObjectURL(img.src);
        thumb.appendChild(img);
      } else if (file.type.startsWith("video/")) {
        thumb.innerHTML = '<i class="bi bi-film" aria-hidden="true"></i>';
      } else {
        thumb.innerHTML = '<i class="bi bi-file-earmark" aria-hidden="true"></i>';
      }

      const meta = document.createElement("div");
      meta.className = "media-file-meta";
      meta.innerHTML =
        '<div class="media-file-name"></div><div class="media-file-size text-muted"></div>';
      meta.querySelector(".media-file-name").textContent = file.name;
      meta.querySelector(".media-file-size").textContent = formatSize(file.size);

      const removeBtn = document.createElement("button");
      removeBtn.type = "button";
      removeBtn.className = "media-file-remove";
      removeBtn.setAttribute("aria-label", "Remove " + file.name);
      removeBtn.innerHTML = '<i class="bi bi-x-lg" aria-hidden="true"></i>';
      removeBtn.addEventListener("click", () => {
        const next = state.files.filter((_, i) => i !== index);
        state.files = next;
        syncInput(input, next);
        render(input, preview, next, state);
      });

      row.appendChild(thumb);
      row.appendChild(meta);
      row.appendChild(removeBtn);
      preview.appendChild(row);
    });
  }

  function bind(input, preview, options) {
    if (!input || !preview) return;
    const opts = options || {};
    const state = { files: Array.from(input.files || []) };
    preview.classList.add("media-file-list");
    if (opts.listClass) preview.classList.add(opts.listClass);

    input.addEventListener("change", () => {
      const incoming = Array.from(input.files || []);
      const map = new Map(state.files.map((f) => [fileKey(f), f]));
      incoming.forEach((f) => map.set(fileKey(f), f));
      state.files = Array.from(map.values());
      syncInput(input, state.files);
      render(input, preview, state.files, state);
    });

    if (state.files.length) {
      render(input, preview, state.files, state);
    }
  }

  global.MediaFileManager = { bind, syncInput, render };
})(window);
