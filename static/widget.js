/* ShopSage embeddable chat widget. No dependencies.
 * Embed with one tag: <script src="/static/widget.js" data-endpoint="/chat"></script>
 * Prices and stock badges are rendered from database rows returned by the API,
 * never from model text. All styles are scoped under .shopsage- classes. */
(function () {
  "use strict";
  var script = document.currentScript;
  var endpoint = (script && script.getAttribute("data-endpoint")) || "/chat";
  var sessionId = "ss-" + Math.random().toString(36).slice(2, 10); // in memory only

  var css = [
    ".shopsage-launcher{position:fixed;right:20px;bottom:20px;width:56px;height:56px;border-radius:50%;",
    "border:none;background:#1f6f54;color:#fff;font-size:24px;cursor:pointer;box-shadow:0 4px 14px rgba(0,0,0,.25);z-index:99998}",
    ".shopsage-panel{position:fixed;right:20px;bottom:88px;width:340px;max-width:calc(100vw - 40px);height:460px;",
    "display:none;flex-direction:column;background:#fff;color:#1c2430;border-radius:12px;overflow:hidden;",
    "box-shadow:0 8px 30px rgba(0,0,0,.3);font:14px/1.45 system-ui,sans-serif;z-index:99999}",
    ".shopsage-panel.shopsage-open{display:flex}",
    ".shopsage-head{background:#1f6f54;color:#fff;padding:12px 16px;font-weight:600}",
    ".shopsage-msgs{flex:1;overflow-y:auto;padding:12px;background:#f4f6f5}",
    ".shopsage-msg{margin:0 0 10px;padding:8px 12px;border-radius:10px;max-width:85%;white-space:pre-wrap}",
    ".shopsage-msg-user{background:#1f6f54;color:#fff;margin-left:auto}",
    ".shopsage-msg-bot{background:#fff;border:1px solid #dde3e0}",
    ".shopsage-card{background:#fff;border:1px solid #dde3e0;border-radius:10px;padding:10px;margin:0 0 8px;display:flex;gap:10px;align-items:center}",
    ".shopsage-thumb{width:42px;height:42px;border-radius:8px;background:#e3ede8;display:flex;align-items:center;justify-content:center;font-size:20px;flex:none}",
    ".shopsage-card-title{font-weight:600;font-size:13px}",
    ".shopsage-price{color:#1f6f54;font-weight:700}",
    ".shopsage-badge{font-size:11px;padding:1px 7px;border-radius:9px;margin-left:6px}",
    ".shopsage-badge-in{background:#dcf1e7;color:#17604a}",
    ".shopsage-badge-out{background:#fbe3e3;color:#a03030}",
    ".shopsage-view{font-size:12px;color:#1f6f54;text-decoration:underline;margin-left:auto}",
    ".shopsage-table{border-collapse:collapse;background:#fff;font-size:12px;margin:0 0 8px;width:100%}",
    ".shopsage-table th,.shopsage-table td{border:1px solid #dde3e0;padding:5px 8px;text-align:left}",
    ".shopsage-form{display:flex;border-top:1px solid #dde3e0}",
    ".shopsage-input{flex:1;border:none;padding:12px;font:inherit;outline:none}",
    ".shopsage-send{border:none;background:#1f6f54;color:#fff;padding:0 18px;cursor:pointer;font:inherit}"
  ].join("");

  function el(tag, cls, text) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function money(cents) { return "$" + (cents / 100).toFixed(2); }

  var style = document.createElement("style");
  style.textContent = css;
  document.head.appendChild(style);

  var launcher = el("button", "shopsage-launcher", "🛍️");
  launcher.setAttribute("aria-label", "Open ShopSage chat");
  var panel = el("div", "shopsage-panel");
  panel.appendChild(el("div", "shopsage-head", "ShopSage — shopping assistant"));
  var msgs = el("div", "shopsage-msgs");
  panel.appendChild(msgs);
  var form = el("form", "shopsage-form");
  var input = el("input", "shopsage-input");
  input.placeholder = "Ask about our packs…";
  var send = el("button", "shopsage-send", "Send");
  form.appendChild(input);
  form.appendChild(send);
  panel.appendChild(form);
  document.body.appendChild(launcher);
  document.body.appendChild(panel);

  function addMessage(kind, text) {
    msgs.appendChild(el("p", "shopsage-msg shopsage-msg-" + kind, text));
    msgs.scrollTop = msgs.scrollHeight;
  }

  function renderProducts(products) {
    products.forEach(function (p) {
      var card = el("div", "shopsage-card");
      card.appendChild(el("div", "shopsage-thumb", "🎒"));
      var body = el("div");
      body.appendChild(el("div", "shopsage-card-title", p.title));
      var line = el("div");
      line.appendChild(el("span", "shopsage-price", money(p.price_cents))); // DB price only
      var inStock = p.stock > 0;
      line.appendChild(el("span",
        "shopsage-badge shopsage-badge-" + (inStock ? "in" : "out"),
        inStock ? "In stock" : "Out of stock"));
      body.appendChild(line);
      card.appendChild(body);
      if (inStock) { // no purchase link for out-of-stock items
        var view = el("a", "shopsage-view", "View");
        view.href = "/products/" + p.id;
        view.target = "_blank";
        card.appendChild(view);
      }
      msgs.appendChild(card);
    });
  }

  function renderComparison(comparison, products) {
    if (!comparison || !comparison.length) return;
    var titles = {};
    products.forEach(function (p) { titles[String(p.id)] = p.title; });
    var ids = Object.keys(comparison[0].values);
    var table = el("table", "shopsage-table");
    var head = el("tr");
    head.appendChild(el("th", "", ""));
    ids.forEach(function (id) { head.appendChild(el("th", "", titles[id] || "#" + id)); });
    table.appendChild(head);
    comparison.forEach(function (row) {
      var tr = el("tr");
      tr.appendChild(el("th", "", row.attribute.replace(/_/g, " ")));
      ids.forEach(function (id) { tr.appendChild(el("td", "", row.values[id])); });
      table.appendChild(tr);
    });
    msgs.appendChild(table);
    msgs.scrollTop = msgs.scrollHeight;
  }

  function ask(question) {
    addMessage("user", question);
    fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, question: question })
    }).then(function (res) {
      if (res.status === 429) {
        addMessage("bot", "Rate limit reached — please wait a minute and try again.");
        return null;
      }
      if (!res.ok) throw new Error("HTTP " + res.status);
      return res.json();
    }).then(function (data) {
      if (!data) return;
      addMessage("bot", data.message);
      renderProducts(data.products || []);
      renderComparison(data.comparison, data.products || []);
    }).catch(function () {
      addMessage("bot", "Something went wrong — please try again.");
    });
  }

  launcher.addEventListener("click", function () {
    panel.classList.toggle("shopsage-open");
    if (panel.classList.contains("shopsage-open") && !msgs.childElementCount) {
      addMessage("bot", "Hi! Ask me to find or compare hiking backpacks.");
      input.focus();
    }
  });
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var q = input.value.trim();
    if (!q) return;
    input.value = "";
    ask(q);
  });
})();
