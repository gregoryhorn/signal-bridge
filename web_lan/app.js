(function () {
  const params = new URLSearchParams(window.location.search);
  const token = params.get("token") || "";
  const q = token ? ("?token=" + encodeURIComponent(token)) : "";

  const feedEl = document.getElementById("feed");
  const statusEl = document.getElementById("status");
  const channelEl = document.getElementById("channel");
  const countEl = document.getElementById("count");

  /** @type {Array<any>} */
  let rows = [];
  let channelFilter = "__ALL__";
  const channels = new Set();

  function setStatus(text, cls) {
    statusEl.textContent = text;
    statusEl.className = "status" + (cls ? " " + cls : "");
  }

  function renderSpans(spans, fallback) {
    if (!spans || !spans.length) {
      const s = document.createElement("span");
      s.className = "body";
      s.textContent = fallback || "";
      return [s];
    }
    return spans.map((sp) => {
      const s = document.createElement("span");
      s.className = sp.cls || "body";
      s.textContent = sp.text || "";
      return s;
    });
  }

  function rowVisible(row) {
    if (channelFilter === "__ALL__") return true;
    return row.channel === channelFilter;
  }

  function renderFeed() {
    feedEl.innerHTML = "";
    const visible = rows.filter(rowVisible);
    for (const row of visible) {
      const div = document.createElement("div");
      div.className = "row";
      if (row.ts) {
        const ts = document.createElement("span");
        ts.className = "ts";
        ts.textContent = row.ts;
        div.appendChild(ts);
      }
      if (row.sender) {
        const sender = document.createElement("span");
        sender.className = "sender";
        sender.textContent = row.sender;
        div.appendChild(sender);
        const sep = document.createElement("span");
        sep.className = "sep";
        sep.textContent = "›";
        div.appendChild(sep);
      }
      for (const node of renderSpans(row.spans, row.visible_text)) {
        div.appendChild(node);
      }
      feedEl.appendChild(div);
    }
    countEl.textContent = visible.length + " rows";
    feedEl.scrollTop = feedEl.scrollHeight;
  }

  function rememberChannel(ch) {
    if (!ch || channels.has(ch)) return;
    channels.add(ch);
    const opt = document.createElement("option");
    opt.value = ch;
    opt.textContent = ch;
    channelEl.appendChild(opt);
  }

  function pushRow(row) {
    rows.push(row);
    if (rows.length > 500) rows = rows.slice(-500);
    rememberChannel(row.channel);
    renderFeed();
  }

  channelEl.addEventListener("change", () => {
    channelFilter = channelEl.value;
    renderFeed();
  });

  // Fix static asset token for theme css / scripts loaded relative
  const themeLink = document.getElementById("theme-css");
  if (themeLink && token) {
    themeLink.href = "api/theme.css" + q;
  }

  fetch("api/snapshot" + q, { cache: "no-store" })
    .then((r) => {
      if (!r.ok) throw new Error("snapshot " + r.status);
      return r.json();
    })
    .then((data) => {
      rows = Array.isArray(data.rows) ? data.rows : [];
      rows.forEach((r) => rememberChannel(r.channel));
      renderFeed();
      setStatus("live", "ok");
      const es = new EventSource("api/stream" + q);
      es.addEventListener("row", (ev) => {
        try {
          pushRow(JSON.parse(ev.data));
        } catch (e) {}
      });
      es.addEventListener("hello", () => setStatus("live", "ok"));
      es.onerror = () => setStatus("reconnecting…", "err");
    })
    .catch((err) => {
      setStatus("auth/network error", "err");
      console.error(err);
    });
})();
