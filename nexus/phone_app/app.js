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
  // ---------- teste de alcance (PC no cabo x celular no Wi-Fi) ----------
  $("btnTest").addEventListener("click", function () {
    if (!setBase($("inIp").value, $("inPort").value)) {
      $("pairMsg").className = "msg";
      $("pairMsg").textContent = "Preencha IP e porta primeiro.";
      return;
    }
    save();
    $("pairMsg").className = "msg";
    $("pairMsg").textContent = "Testando...";
    var xhr = new XMLHttpRequest();
    try {
      xhr.open("GET", S.base + "/", true);
    } catch (e) {
      $("pairMsg").textContent = "IP inválido.";
      return;
    }
    xhr.timeout = 6000;
    xhr.onload = function () {
      $("pairMsg").className = "msg ok";
      $("pairMsg").textContent = "PC alcançado! Agora é só parear.";
    };
    xhr.ontimeout = function () { failReach(); };
    xhr.onerror = function () { failReach(); };
    try { xhr.send(); } catch (e) { failReach(); }
  });
  function failReach() {
    $("pairMsg").className = "msg";
    $("pairMsg").textContent = "PC não responde. Confira: 1) mesmo roteador (cabo + Wi-Fi) 2) porta liberada no firewall 3) IP certo.";
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
      } else if (st === 0) {
        $("pairMsg").className = "msg";
        $("pairMsg").textContent = "Sem resposta: mesmo Wi-Fi? IP certo? Firewall liberado?";
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
      // Formato novo: URL direta (http://IP:porta/?code=...).
      var m = /^(https?:\/\/[^\/?#]+)(?:\/[^?#]*)?\?([^#]*)$/.exec(text || "");
      if (m) {
        try {
          var host = m[1].replace(/^https?:\/\//, "");
          var hn = host, pt = "";
          var ci = host.lastIndexOf(":");
          if (ci > 0) { hn = host.slice(0, ci); pt = host.slice(ci + 1); }
          var q = m[2], cm = /(?:^|&)code=([^&]*)/.exec(q);
          if (hn) $("inIp").value = hn;
          if (pt) $("inPort").value = pt;
          if (cm) $("inCode").value = decodeURIComponent(cm[1]);
          $("camMsg").textContent = "QR lido! Aperte Parear.";
          return;
        } catch (e) {}
      }
      // Formato legado: JSON {"t":"nexus",...}.
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
  // Touchpad relativo: deslize move (direcao do dedo), toque = clique.
  // Segue UM dedo pelo identifier: outro dedo encostando no meio do
  // gesto nao sequestra o cursor (causa do teleporte).
  var pad = $("pad"), lastX = 0, lastY = 0, accX = 0, accY = 0,
      pid = null, moved = false, t0 = 0, tracking = false, padId = null;
  function trackedTouch(list) {
    for (var i = 0; i < list.length; i++) {
      if (list[i].identifier === padId) return list[i];
    }
    return null;
  }
  function clamp(v) { return Math.max(-150, Math.min(150, v)); }
  function flushPad() {
    var dx = Math.round(clamp(accX) * 2.5), dy = Math.round(clamp(accY) * 2.5);
    accX = 0; accY = 0;
    if (Math.abs(dx) + Math.abs(dy) > 1) {
      moved = true;
      send("move", { dx: dx, dy: dy });
    }
  }
  pad.addEventListener("touchstart", function (e) {
    e.preventDefault();
    if (tracking) return; // segundo dedo: ignora, nao rouba o gesto
    var t = e.changedTouches[0];
    padId = t.identifier;
    lastX = t.clientX; lastY = t.clientY;
    accX = 0; accY = 0;
    moved = false; t0 = Date.now(); tracking = true;
    if (pid) clearInterval(pid);
    pid = setInterval(flushPad, 30);
  }, { passive: false });
  pad.addEventListener("touchmove", function (e) {
    e.preventDefault();
    if (!tracking) return;
    var t = trackedTouch(e.changedTouches);
    if (!t) return;
    accX += t.clientX - lastX;
    accY += t.clientY - lastY;
    lastX = t.clientX; lastY = t.clientY;
  }, { passive: false });
  function padEnd(e) {
    if (e) {
      e.preventDefault();
      var t = trackedTouch(e.changedTouches);
      if (e.type !== "touchcancel" && !t && tracking) return; // dedo alheio
    }
    tracking = false;
    padId = null;
    if (pid) { clearInterval(pid); pid = null; }
    flushPad();
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
      else if (c === "voldn") send("volstep", { dir: -1 });
      else if (c === "volup") send("volstep", { dir: 1 });
      else if (cmap[c]) send(cmap[c], {});
    });
  });
  // Vol-/Vol+ usam "volstep" (passos de 5% no volume master do PC).
  document.querySelectorAll('[data-cmd="voldn"],[data-cmd="volup"]').forEach(function () {});
  $("btnSendText").addEventListener("click", function () {
    var v = $("inText").value || "";
    if (!v) return;
    send("text", { text: v });
    $("inText").value = "";
  });
  // ---------- modo jogo: botoes logicos do controle ----------
  document.querySelectorAll("[data-pad]").forEach(function (b) {
    b.addEventListener("click", function () {
      if (!S.token) return;
      api("/api/input", { token: S.token, cmd: "pad",
        args: { button: b.getAttribute("data-pad") } }, function (st) {
        if (st === 403) { S.token = ""; save(); who(); }
      });
    });
  });
  $("btnNexus").addEventListener("click", function () {
    send("exit_remote", {});
  });
  // mouse via clique longo? nao. teclado fisico do celular no campo acima.

  // QR via camera nativa: ?code= na URL preenche e pula p/ o pareamento.
  try {
    var qm = /(?:^|[?&])code=([^&]*)/.exec(location.search || "");
    if (qm && !$("inCode").value) {
      $("inCode").value = decodeURIComponent(qm[1]);
      var hn = location.hostname || "";
      if (hn && !$("inIp").value) $("inIp").value = hn;
      if (location.port && !$("inPort").value) $("inPort").value = location.port;
      $("pairMsg").className = "msg ok";
      $("pairMsg").textContent = "Veio do QR: confira o nome e aperte Parear.";
    }
  } catch (e) {}

  who();
  if (S.token) loadStreams();
})();
