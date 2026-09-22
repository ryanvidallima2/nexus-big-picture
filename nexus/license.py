# -*- coding: utf-8 -*-
"""Licenca Pro via Gumroad (Fase 3 - monetizacao).

SETUP DO VENDEDOR (fora do codigo, 1x no Gumroad):
  1. Criar 4 produtos (mensal $5.90, semestral $33.60, anual $60,
     vitalicio $500) e ATIVAR "license keys" em cada um.
  2. Copiar o product_id de cada produto (bloco License key na edicao).
     ATENCAO: produtos criados a partir de 09/01/2023 exigem product_id
     (nao permalink) no verify.
  3. Colar os ids em settings.json -> "pro_products" ou em
     DEFAULT_PRODUCTS abaixo. Sem ids configurados, a ativacao informa
     "noconfig" (loja ainda nao ligada) e o app segue gratuito.

FLUXO NO APP (mesmo binario do GitHub):
  - Ativacao: Sistema > Ativar Nexus Pro (ou card no Novidades) pede a
    chave do recibo -> POST https://api.gumroad.com/v2/licenses/verify
    com increment_uses_count=false -> guarda chave + tier + last_check.
  - Recheck: no startup, se ultimo check > RECHECK_DAYS, revalida em
    thread. Assinatura reembolsada/disputada/falha/expirada invalida.
  - Carencia offline: sem internet vale o ultimo check valido por ate
    GRACE_DAYS; depois, rebaixa sozinho p/ gratuito (ads voltam).
  - Mesma chave vale em quantos PCs o vendedor permitir (controle de
    "uses" e do lado do Gumroad, nao aqui).

So stdlib (urllib/json/datetime): sem dependencia nova.
"""

import json
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

VERIFY_URL = "https://api.gumroad.com/v2/licenses/verify"
TIMEOUT = 15
RECHECK_DAYS = 7
GRACE_DAYS = 14

TIERS = ("monthly", "semiannual", "annual", "lifetime")

# product_id de cada plano (vazio = loja nao ligada). Override via
# settings.json -> "pro_products" (mesmas chaves).
DEFAULT_PRODUCTS = {
    "monthly": "",
    "semiannual": "",
    "annual": "",
    "lifetime": "",
}


def product_ids(settings):
    """Mapa tier -> product_id (settings sobrepoe os padroes)."""
    try:
        custom = (settings or {}).get("pro_products") or {}
    except Exception:
        custom = {}
    merged = dict(DEFAULT_PRODUCTS)
    try:
        for tier in TIERS:
            val = (custom.get(tier) or "").strip()
            if val:
                merged[tier] = val
    except Exception:
        pass
    return merged


def parse_time(value):
    """ISO -> datetime ciente de fuso (None se invalido)."""
    try:
        s = str(value or "").strip()
        if not s:
            return None
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def now_utc():
    return datetime.now(timezone.utc)


def purchase_problem(purchase, now=None):
    """'refunded' | 'expired' | None (assinatura ainda valida)."""
    try:
        p = purchase or {}
        if p.get("refunded") or p.get("disputed"):
            return "refunded"
        if p.get("subscription_failed_at"):
            return "expired"
        ended = parse_time(p.get("subscription_ended_at"))
        if ended is not None and ended <= (now or now_utc()):
            return "expired"
    except Exception:
        pass
    return None


def _post_verify(product_id, key):
    data = urllib.parse.urlencode({
        "product_id": product_id,
        "license_key": key,
        "increment_uses_count": "false",
    }).encode("utf-8")
    req = urllib.request.Request(VERIFY_URL, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def verify_key(product_ids_map, key, _post=None):
    """(ok, tier, detalhe). Tenta cada product_id configurado.

    detalhe: {"email", "product_name"} no sucesso;
    {"error": "invalid"|"offline"|"refunded"|"expired"|"noconfig"} na falha.
    _post(pid, key) -> dict existe p/ testes (sem rede).
    """
    key = (key or "").strip()
    if not key:
        return False, None, {"error": "invalid"}
    post = _post or _post_verify
    tried = False
    for tier in TIERS:
        try:
            pid = ((product_ids_map or {}).get(tier) or "").strip()
        except Exception:
            pid = ""
        if not pid:
            continue
        tried = True
        try:
            data = post(pid, key)
        except Exception:
            return False, None, {"error": "offline"}
        if not isinstance(data, dict) or not data.get("success"):
            continue
        purchase = data.get("purchase") or {}
        bad = purchase_problem(purchase)
        if bad:
            return False, None, {"error": bad}
        return True, tier, {
            "email": purchase.get("email", "") or "",
            "product_name": purchase.get("product_name", "") or "",
        }
    if not tried:
        return False, None, {"error": "noconfig"}
    return False, None, {"error": "invalid"}


def license_status(settings, now=None):
    """('pro'|'free', motivo) a partir do cache local (sem rede)."""
    try:
        s = settings or {}
        if not (s.get("pro_license") or "").strip():
            return ("free", "none")
        info = s.get("pro_license_info") or {}
        if not info.get("valid"):
            return ("free", "invalid")
        last = parse_time(info.get("last_check"))
        if last is None:
            return ("free", "stale")
        if (now or now_utc()) - last <= timedelta(days=GRACE_DAYS):
            return ("pro", "cached")
        return ("free", "expired")
    except Exception:
        return ("free", "error")


def needs_recheck(settings, now=None):
    """True se ha chave valida e o ultimo check passou de RECHECK_DAYS."""
    try:
        s = settings or {}
        if not (s.get("pro_license") or "").strip():
            return False
        info = s.get("pro_license_info") or {}
        if not info.get("valid"):
            return False
        last = parse_time(info.get("last_check"))
        if last is None:
            return True
        return (now or now_utc()) - last > timedelta(days=RECHECK_DAYS)
    except Exception:
        return False


def mark_verified(settings, key, tier, product_id, email=""):
    """Grava chave + tier + check atual (chamar antes de save_settings)."""
    try:
        settings["pro_license"] = (key or "").strip()
        settings["pro_license_info"] = {
            "valid": True,
            "tier": tier,
            "product_id": product_id,
            "email": email or "",
            "last_check": now_utc().isoformat(),
        }
    except Exception:
        pass
    return settings


def mark_invalid(settings):
    """Mantem a chave, derruba o cache valido (volta ao gratuito)."""
    try:
        info = dict(settings.get("pro_license_info") or {})
        info["valid"] = False
        settings["pro_license_info"] = info
    except Exception:
        pass
    return settings


def has_pro(app):
    """Gate central: True se o app tem Pro (ou se o objeto nao tem
    is_pro — stubs de teste liberam p/ nao quebrar a suite)."""
    try:
        fn = getattr(app, "is_pro", None)
        if callable(fn):
            return bool(fn())
    except Exception:
        pass
    return True
