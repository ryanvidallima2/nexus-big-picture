/* Nexus Remote (PWA, sem build): pareamento, streams e controle. */
(function () {
  "use strict";
  var S = { base: "", token: "", profile: "" };
  try {
    S.base = localStorage.getItem("nx_base") || "";
    S.token = localStorage.getItem("nx_token") || "";
    S.profile = localStorage.getItem("nx_profile") || "";
  } catch (e) { /* sem storage: segue sem salvar */ }

  function save() {
    try {
      localStorage.setItem("nx_base", S.base);
      localStorage.setItem("nx_token", S.token);
      localStorage.setItem("nx_profile", S.profile);
    } catch (e) {}
  }
  function $(id) { return document.getElementById(id); }
  function who() {
    $("who").textContent = S.token
      ? ("conectado" + (S.profile ? (" como " + S.profile) : "") + " • " + S.base)
      : "desconectado";
    $("btnUnpair").style.display = S.token ? "block" : "none";
  }
  function api(path, body, cb) {
    var xhr = new XMLHttpRequest();
    try {
      xhr.open(body === null ? "GET" : "POST", S.base + path, true);
    } catch (e) { if (cb) cb(null); return; }
    xhr.timeout = 8000;
    xhr.onreadystatechange = function () {
      if (xhr.readyState !== 4 || !cb) return;
      var out = null;
      try { out = JSON.parse(xhr.responseText || "null"); } catch (e) {}
      cb(xhr.status, out);
    };
    xhr.ontimeout = function () { if (cb) cb(0, null); };
    xhr.onerror = function () { if (cb) cb(0, null); };
    try {
      if (body === null) xhr.send();
      else {
        xhr.setRequestHeader("Content-Type", "application/json");
        xhr.send(JSON.stringify(body));
      }
    } catch (e) { if (cb) cb(0, null); }
  }

  // ---------- nav ----------
  var tabs = document.querySelectorAll("nav button");
  Array.prototype.forEach.call(tabs, function (b) {
    b.addEventListener("click", function () {
      Array.prototype.forEach.call(tabs, function (x) { x.classList.remove("on"); });
      b.classList.add("on");
      Array.prototype.forEach.call(document.querySelectorAll(".screen"), function (s) {
        s.classList.remove("on");
      });
      document.getElementById(b.getAttribute("data-s")).classList.add("on");
    });
  });

  // ---------- pareamento ----------
  function setBase(ip, port) {
    ip = (ip || "").trim().replace(/\/+$/, "");
    if (!ip) return false;
    if (ip.indexOf("http") !== 0) ip = "http://" + ip;
    port = (port || "48721").trim() || "48721";
    S.base = ip.replace(/:\d+$/, "") + ":" + port;
    return true;
  }
  $("btnPair").addEventListener("click", function () {
    if (!setBase($("inIp").value, $("inPort").value)) {
      $("pairMsg").textContent = "Informe o IP.";
      return;
    }
    var code = ($("inCode").value || "").trim();
    var name = ($("inName").value || "celular").trim() || "celular";
    if (!/^\d{4,8}$/.test(code)) {
      $("pairMsg").textContent = "Código de 4 a 8 dígitos.";
      return;
    }
    $("pairMsg").textContent = "Pareando...";
    api("/api/pair", { code: code, device: name }, function (st, out) {
      if (st === 200 && out && out.ok && out.token) {
        S.token = out.token;
        S.profile = out.profile || "";
        save(); who();
        $("pairMsg").textContent = "";
        $("pairMsg").className = "msg ok";
        $("pairMsg").textContent = "Pareado!";
        loadStreams();
      } else {
        $("pairMsg").className = "msg";
        $("pairMsg").textContent = "Falhou: confira IP/porta/código.";
      }
    });
  });
  $("btnUnpair").addEventListener("click", function () {
    api("/api/unpair", { token: S.token }, function () {
      S.token = ""; S.profile = ""; save(); who();
    });
  });

  // ---------- camera (QR) ----------
  var stream = null, scanning = false;
  function stopCam() {
    scanning = false;
    try {
      if (stream) stream.getTracks().forEach(function (t) { t.stop(); });
    } catch (e) {}
    stream = null;
    $("video").style.display = "none";
  }
  $("btnCam").addEventListener("click", function () {
    if (stream) { stopCam(); return; }
    var msg = $("camMsg");
    if (!window.isSecureContext && location.hostname !== "localhost"
        && location.hostname !== "127.0.0.1") {
      msg.textContent = "Câmera bloqueada em HTTP. Digite os dados abaixo (ou abra via HTTPS).";
      return;
    }
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      msg.textContent = "Sem câmera neste navegador. Digite os dados.";
      return;
    }
    navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } })
      .then(function (st) {
        stream = st;
        var v = $("video");
        v.style.display = "block";
        v.srcObject = st;
        v.play();
        msg.textContent = "Mirando o QR...";
        scanLoop();
      })
      .catch(function () {
        msg.textContent = "Câmera negada. Digite os dados abaixo.";
      });
  });
  function hasDetector() {
    try { return typeof BarcodeDetector !== "undefined"; } catch (e) { return false; }
  }
  function scanLoop() {
    if (!stream) return;
    var v = $("video");
    function ok(text) {
      stopCam();
      try {
        var o = JSON.parse(text);
        if (o && o.t === "nexus") {
          if (o.ip) $("inIp").value = o.ip;
          if (o.port) $("inPort").value = o.port;
          if (o.code) $("inCode").value = o.code;
          $("camMsg").textContent = "QR lido! Aperte Parear.";
          return;
        }
      } catch (e) {}
      $("camMsg").textContent = "QR inválido.";
    }
    if (!hasDetector()) {
      $("camMsg").textContent = "Leitor indisponível aqui. Digite os dados.";
      return;
    }
    var det;
    try { det = new BarcodeDetector({ formats: ["qr_code"] }); }
    catch (e) { $("camMsg").textContent = "Leitor indisponível. Digite os dados."; return; }
    (function tick() {
      if (!stream) return;
      det.detect(v).then(function (codes) {
        if (codes && codes.length && codes[0].rawValue) { ok(codes[0].rawValue); return; }
        setTimeout(tick, 400);
      }).catch(function () { setTimeout(tick, 800); });
    })();
  }

  // ---------- streams ----------
  function needAuth(fn) {
    if (!S.token) {
      $("streamsMsg").textContent = "Pareie primeiro.";
      return false;
    }
    return true;
  }
  function loadStreams() {
    if (!needAuth()) return;
    api("/api/services?token=" + encodeURIComponent(S.token), null, function (st, out) {
      var g = $("grid");
      g.innerHTML = "";
      if (st === 403) {
        $("streamsMsg").textContent = "Sessão expirada. Pareie de novo.";
        S.token = ""; save(); who();
        return;
      }
      if (st !== 200 || !out || !out.ok) {
        $("streamsMsg").textContent = "Sem resposta do PC.";
        return;
      }
      $("streamsMsg").textContent = "";
      (out.services || []).forEach(function (s) {
        var b = document.createElement("button");
        b.textContent = (s.icon ? s.icon + " " : "") + s.name;
        b.style.background = s.color || "#7c4dff";
        b.addEventListener("click", function () {
          api("/api/launch", { token: S.token, name: s.name }, function () {});
        });
        g.appendChild(b);
      });
    });
  }
  $("btnReload").addEventListener("click", loadStreams);

  // ---------- controle ----------
  function send(cmd, args) {
    if (!S.token) return;
    api("/api/input", { token: S.token, cmd: cmd, args: args || {} }, function (st) {
      if (st === 403) { S.token = ""; save(); who(); }
    });
  }
  var pad = $("pad"), lx = 0, ly = 0, pid = null, moved = false, t0 = 0;
  function padPos(e) {
    var r = pad.getBoundingClientRect(), t = e.touches[0];
    return [t.clientX - (r.left + r.width / 2), t.clientY - (r.top + r.height / 2)];
  }
  pad.addEventListener("touchstart", function (e) {
    e.preventDefault();
    var p = padPos(e);
    lx = p[0]; ly = p[1]; moved = false; t0 = Date.now();
    if (pid) clearInterval(pid);
    pid = setInterval(function () {
      var dx = lx, dy = ly;
      lx = 0; ly = 0;
      if (Math.abs(dx) + Math.abs(dy) > 4) {
        moved = true;
        send("move", { dx: Math.round(dx / 3), dy: Math.round(dy / 3) });
      }
    }, 40);
  }, { passive: false });
  function padEnd(e) {
    if (e) e.preventDefault();
    if (pid) { clearInterval(pid); pid = null; }
    if (!moved && Date.now() - t0 < 300) send("click", { button: "left" });
  }
  pad.addEventListener("touchend", padEnd, { passive: false });
  pad.addEventListener("touchcancel", padEnd, { passive: false });
  document.querySelectorAll("[data-nav]").forEach(function (b) {
    b.addEventListener("click", function () {
      var d = b.getAttribute("data-nav");
      if (d === "ok") send("select", {});
      else send("nav", { dir: d });
    });
  });
  var cmap = { select: "select", back: "back", cards: "cards",
               sidebar: "sidebar", tabprev: null, tabnext: null,
               voldn: null, volup: null, keyboard: "keyboard",
               kbclose: "kb_close" };
  document.querySelectorAll("[data-cmd]").forEach(function (b) {
    b.addEventListener("click", function () {
      var c = b.getAttribute("data-cmd");
      if (c === "tabprev") send("tab", { dir: "prev" });
      else if (c === "tabnext") send("tab", { dir: "next" });
      else if (c === "voldn" || c === "volup") send("volume", {});
      else if (cmap[c]) send(cmap[c], {});
    });
  });
  // volume do aparelho: busca nivel atual? MVP: passos via master no PC.
  // (botoes Vol enviam comando de volume do SO pelo Nexus: implementado
  //  via teclas de mídia no PC)
  document.querySelectorAll('[data-cmd="voldn"],[data-cmd="volup"]').forEach(function () {});
  $("btnSendText").addEventListener("click", function () {
    var v = $("inText").value || "";
    if (!v) return;
    send("text", { text: v });
    $("inText").value = "";
  });
  // mouse via clique longo? nao. teclado fisico do celular no campo acima.

  who();
  if (S.token) loadStreams();
})();
