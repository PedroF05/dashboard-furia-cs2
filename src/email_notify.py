"""
src/email_notify.py — Notificações por email via SMTP Gmail
Lógica:
  - Lê destinatários de data/recipients.csv
  - Envia quando faltam <= NOTIFY_DAYS_BEFORE dias para uma partida
  - A partir daí envia todo dia (countdown: "faltam 6 dias", "faltam 5 dias"...)
  - Email contém: próxima partida em destaque + agenda futura + resumo semanal
"""

import csv
import json
import logging
import os
import smtplib
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from database.db import get_connection
from config import (
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, EMAIL_FROM,
    RECIPIENTS_CSV, NOTIFY_DAYS_BEFORE, RECENT_MATCHES_COUNT,
)

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Destinatários
# ──────────────────────────────────────────────────────────────────────────────

def load_recipients() -> List[Dict[str, str]]:
    """
    Lê recipients.csv com colunas: name,email
    Retorna lista de dicts [{"name": "...", "email": "..."}]
    """
    if not os.path.exists(RECIPIENTS_CSV):
        logger.warning(f"Arquivo de destinatários não encontrado: {RECIPIENTS_CSV}")
        return []

    recipients = []
    with open(RECIPIENTS_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            email = row.get("email", "").strip()
            name  = row.get("name", "").strip() or email
            if email:
                recipients.append({"name": name, "email": email})

    logger.info(f"{len(recipients)} destinatários carregados.")
    return recipients


# ──────────────────────────────────────────────────────────────────────────────
# Consultas ao banco
# ──────────────────────────────────────────────────────────────────────────────

def get_upcoming_matches() -> List[Dict]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT id, scheduled_at, opponent_name, opponent_acronym,
                   match_type, league_name, serie_name,
                   tournament_name, tournament_tier, notified_days,
                   -- Combina league + serie em um só campo
                   CASE 
                       WHEN league_name IS NOT NULL AND serie_name IS NOT NULL 
                           THEN league_name || ' — ' || serie_name
                       WHEN league_name IS NOT NULL 
                           THEN league_name
                       WHEN serie_name IS NOT NULL 
                           THEN serie_name
                       ELSE tournament_name
                   END as torneo_combined
            FROM matches
            WHERE status = 'not_started'
              AND scheduled_at IS NOT NULL
            ORDER BY scheduled_at ASC
        """).fetchall()
    return [dict(r) for r in rows]


def get_recent_matches(limit: int = RECENT_MATCHES_COUNT) -> List[Dict]:
    with get_connection() as conn:
        rows = conn.execute(f"""
            SELECT begin_at, opponent_name, furia_score, opponent_score,
                   winner, draw, league_name, tournament_name, match_type, serie_name,
                   -- Combina league + serie
                   CASE 
                       WHEN league_name IS NOT NULL AND serie_name IS NOT NULL 
                           THEN league_name || ' — ' || serie_name
                       WHEN league_name IS NOT NULL 
                           THEN league_name
                       WHEN serie_name IS NOT NULL 
                           THEN serie_name
                       ELSE tournament_name
                   END as torneo_combined
            FROM matches
            WHERE status = 'finished'
            ORDER BY begin_at DESC
            LIMIT {limit}
        """).fetchall()
    return [dict(r) for r in rows]


def get_team_info() -> Optional[Dict]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM team LIMIT 1").fetchone()
    return dict(row) if row else None


def mark_notified(match_id: int, days_left: int) -> None:
    """Registra que já enviamos notificação para este match com X dias restantes."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT notified_days FROM matches WHERE id=?", (match_id,)
        ).fetchone()
        notified = json.loads(row["notified_days"] or "[]") if row else []
        if days_left not in notified:
            notified.append(days_left)
            conn.execute(
                "UPDATE matches SET notified_days=? WHERE id=?",
                (json.dumps(notified), match_id)
            )


def already_notified(match: Dict, days_left: int) -> bool:
    notified = json.loads(match.get("notified_days") or "[]")
    return days_left in notified


# ──────────────────────────────────────────────────────────────────────────────
# Formatação de data (Horário de Brasília - UTC-3)
# ──────────────────────────────────────────────────────────────────────────────

def _fmt_dt(iso: Optional[str]) -> str:
    """
    Formata data/hora convertendo de UTC para horário de Brasília (UTC-3).
    """
    if not iso:
        return "A confirmar"
    try:
        # Parse UTC
        dt_utc = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        
        # Converte para Brasília (UTC-3)
        brasilia_tz = timezone(timedelta(hours=-3))
        dt_brasilia = dt_utc.astimezone(brasilia_tz)
        
        return dt_brasilia.strftime("%d/%m/%Y às %H:%M (BRT)")
    except Exception:
        return iso


def _days_until(iso: Optional[str]) -> Optional[int]:
    if not iso:
        return None
    try:
        dt  = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        return max(0, (dt.date() - now.date()).days)
    except Exception:
        return None


def _countdown_label(days: int) -> str:
    if days == 0:
        return "🔴 HOJE!"
    if days == 1:
        return "⚡ AMANHÃ!"
    return f"📅 Faltam {days} dias"


def _result_badge(m: Dict) -> str:
    if m.get("draw"):
        return "🟡 EMPATE"
    if m.get("winner") == "FURIA":
        return "🟢 VITÓRIA"
    if m.get("winner"):
        return "🔴 DERROTA"
    return "⚪ —"


def _score_str(m: Dict) -> str:
    fs = m.get("furia_score")
    os_ = m.get("opponent_score")
    if fs is None and os_ is None:
        return "—"
    return f"{fs} x {os_}"


# ──────────────────────────────────────────────────────────────────────────────
# HTML do email
# ──────────────────────────────────────────────────────────────────────────────

def _build_html(
    next_match: Optional[Dict],
    days_left: Optional[int],
    upcoming: List[Dict],
    recent: List[Dict],
) -> str:
    # ── Próxima partida em destaque ───────────────────────────────────────────
    if next_match and days_left is not None:
        countdown = _countdown_label(days_left)
        highlight = f"""
        <div style="background:#1a1a2e;border-radius:12px;padding:24px;margin-bottom:24px;text-align:center;">
          <div style="color:#a0a0c0;font-size:13px;margin-bottom:4px;">PRÓXIMA PARTIDA</div>
          <div style="color:#ffffff;font-size:26px;font-weight:700;margin:8px 0;">
            FURIA vs {next_match.get('opponent_name','?')}
          </div>
          <div style="color:#c084fc;font-size:15px;margin-bottom:12px;">{countdown}</div>
          <div style="color:#a0a0c0;font-size:13px;">{_fmt_dt(next_match.get('scheduled_at'))}</div>
          <div style="color:#6b7280;font-size:12px;margin-top:6px;">
            {next_match.get('league_name','') or ''} — {next_match.get('serie_name','') or ''}
            &nbsp;|&nbsp; {next_match.get('match_type','') or ''}
          </div>
        </div>"""
    else:
        highlight = """
        <div style="background:#1a1a2e;border-radius:12px;padding:20px;margin-bottom:24px;text-align:center;">
          <div style="color:#a0a0c0;">Nenhuma partida agendada no momento.</div>
        </div>"""

    # ── Agenda completa ───────────────────────────────────────────────────────
    agenda_rows = ""
    for m in upcoming[:8]:
        d = _days_until(m.get("scheduled_at"))
        badge = _countdown_label(d) if d is not None else "—"
        # Usa o campo combinado (league + serie)
        torneo = m.get('torneo_combined') or m.get('league_name') or m.get('serie_name') or m.get('tournament_name') or '—'
        
        agenda_rows += f"""
        <tr>
          <td style="padding:10px 8px;border-bottom:1px solid #f0f0f0;font-weight:600;">
            FURIA vs {m.get('opponent_name','?')}
          </td>
          <td style="padding:10px 8px;border-bottom:1px solid #f0f0f0;color:#6b7280;font-size:13px;">
            {_fmt_dt(m.get('scheduled_at'))}
          </td>
          <td style="padding:10px 8px;border-bottom:1px solid #f0f0f0;font-size:13px;">
            {torneo}
          </td>
          <td style="padding:10px 8px;border-bottom:1px solid #f0f0f0;font-size:13px;color:#7c3aed;">
            {badge}
          </td>
        </tr>"""

    agenda_section = f"""
    <h2 style="font-size:16px;font-weight:600;color:#111827;margin:0 0 12px;">📆 Agenda de Partidas</h2>
    <table style="width:100%;border-collapse:collapse;font-size:14px;margin-bottom:24px;">
      <thead>
        <tr style="background:#f9fafb;">
          <th style="padding:8px;text-align:left;color:#6b7280;font-weight:500;font-size:12px;">CONFRONTO</th>
          <th style="padding:8px;text-align:left;color:#6b7280;font-weight:500;font-size:12px;">DATA/HORA</th>
          <th style="padding:8px;text-align:left;color:#6b7280;font-weight:500;font-size:12px;">TORNEIO</th>
          <th style="padding:8px;text-align:left;color:#6b7280;font-weight:500;font-size:12px;">CONTAGEM</th>
        </tr>
      </thead>
      <tbody>{agenda_rows if agenda_rows else '<tr><td colspan="4" style="padding:12px;color:#9ca3af;">Sem partidas agendadas.</td></tr>'}</tbody>
    </table>"""

    # ── Forma recente ─────────────────────────────────────────────────────────
    form_badges = ""
    for m in recent[:10]:
        if m.get("draw"):
            color, letter = "#f59e0b", "D"
        elif m.get("winner") == "FURIA":
            color, letter = "#10b981", "V"
        else:
            color, letter = "#ef4444", "D"
        form_badges += f"""
        <span style="display:inline-block;width:28px;height:28px;line-height:28px;
                     border-radius:50%;background:{color};color:#fff;
                     font-size:12px;font-weight:700;text-align:center;margin:2px;">{letter}</span>"""

    recent_rows = ""
    for m in recent:
        # Usa o campo combinado (league + serie)
        torneo = m.get('torneo_combined') or m.get('league_name') or m.get('tournament_name') or '—'
        
        recent_rows += f"""
        <tr>
          <td style="padding:10px 8px;border-bottom:1px solid #f0f0f0;">
            FURIA vs {m.get('opponent_name','?')}
          </td>
          <td style="padding:10px 8px;border-bottom:1px solid #f0f0f0;text-align:center;font-weight:700;">
            {_score_str(m)}
          </td>
          <td style="padding:10px 8px;border-bottom:1px solid #f0f0f0;">{_result_badge(m)}</td>
          <td style="padding:10px 8px;border-bottom:1px solid #f0f0f0;color:#6b7280;font-size:13px;">
            {torneo}
          </td>
          <td style="padding:10px 8px;border-bottom:1px solid #f0f0f0;color:#9ca3af;font-size:12px;">
            {_fmt_dt(m.get('begin_at'))}
          </td>
        </tr>"""

    recent_section = f"""
    <h2 style="font-size:16px;font-weight:600;color:#111827;margin:0 0 8px;">📊 Forma Recente</h2>
    <div style="margin-bottom:16px;">{form_badges}</div>
    <table style="width:100%;border-collapse:collapse;font-size:14px;margin-bottom:24px;">
      <thead>
        <tr style="background:#f9fafb;">
          <th style="padding:8px;text-align:left;color:#6b7280;font-weight:500;font-size:12px;">CONFRONTO</th>
          <th style="padding:8px;text-align:center;color:#6b7280;font-weight:500;font-size:12px;">PLACAR</th>
          <th style="padding:8px;text-align:left;color:#6b7280;font-weight:500;font-size:12px;">RESULTADO</th>
          <th style="padding:8px;text-align:left;color:#6b7280;font-weight:500;font-size:12px;">TORNEIO</th>
          <th style="padding:8px;text-align:left;color:#6b7280;font-weight:500;font-size:12px;">DATA</th>
        </tr>
      </thead>
      <tbody>{recent_rows}</tbody>
    </table>"""

    now_str = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")

    return f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <div style="max-width:640px;margin:32px auto;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.1);">

    <!-- Header -->
    <div style="background:#0d0d1a;padding:24px 28px;display:flex;align-items:center;gap:12px;">
      <div>
        <div style="color:#ffffff;font-size:20px;font-weight:700;">FURIA CS2</div>
        <div style="color:#6b7280;font-size:13px;">Dashboard de Partidas — {now_str}</div>
      </div>
    </div>

    <!-- Body -->
    <div style="padding:28px;">
      {highlight}
      {agenda_section}
      {recent_section}
    </div>

    <!-- Footer -->
    <div style="background:#f9fafb;padding:16px 28px;border-top:1px solid #e5e7eb;text-align:center;">
      <p style="color:#9ca3af;font-size:12px;margin:0;">
        Dados via PandaScore API · Gerado automaticamente · Para cancelar, remova seu email de recipients.csv
      </p>
    </div>
  </div>
</body>
</html>"""


# ──────────────────────────────────────────────────────────────────────────────
# Envio
# ──────────────────────────────────────────────────────────────────────────────

def _send(recipients: List[Dict], subject: str, html: str) -> None:
    if not recipients:
        logger.warning("Nenhum destinatário — email não enviado.")
        return

    logger.info(f"Conectando ao SMTP {SMTP_HOST}:{SMTP_PORT}...")
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)

            for r in recipients:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"]    = EMAIL_FROM
                msg["To"]      = r["email"]
                msg.attach(MIMEText(html, "html", "utf-8"))
                server.sendmail(SMTP_USER, r["email"], msg.as_string())
                logger.info(f"  ✓ Enviado para {r['name']} <{r['email']}>")

    except smtplib.SMTPAuthenticationError:
        logger.error(
            "Falha de autenticação SMTP. Verifique SMTP_USER e SMTP_PASSWORD no config.py.\n"
            "Use uma App Password do Google (não a senha normal da conta)."
        )
    except Exception as exc:
        logger.error(f"Erro ao enviar email: {exc}")


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

def run(force: bool = False) -> None:
    """
    force=True envia o email independente da lógica de countdown.
    force=False (padrão) só envia se houver partida dentro de NOTIFY_DAYS_BEFORE dias.
    """
    recipients = load_recipients()
    if not recipients:
        logger.warning("Sem destinatários. Crie data/recipients.csv com colunas name,email")
        return

    upcoming = get_upcoming_matches()
    recent   = get_recent_matches()

    # Encontra partidas que precisam de notificação hoje
    matches_to_notify = []
    for m in upcoming:
        days = _days_until(m.get("scheduled_at"))
        if days is None:
            continue
        if days <= NOTIFY_DAYS_BEFORE:
            if force or not already_notified(m, days):
                matches_to_notify.append((m, days))

    if not matches_to_notify and not force:
        logger.info("Nenhuma partida dentro do período de notificação. Email não enviado.")
        return

    # Usa a partida mais próxima como destaque
    next_match, days_left = matches_to_notify[0] if matches_to_notify else (
        upcoming[0] if upcoming else None, None
    )

    # Assunto dinâmico
    if next_match and days_left is not None:
        if days_left == 0:
            subject = f"🔴 HOJE! FURIA vs {next_match.get('opponent_name','?')} — CS2"
        elif days_left == 1:
            subject = f"⚡ AMANHÃ! FURIA vs {next_match.get('opponent_name','?')} — CS2"
        else:
            subject = f"📅 Faltam {days_left} dias — FURIA vs {next_match.get('opponent_name','?')} · CS2"
    else:
        subject = "📊 FURIA CS2 — Resumo Semanal"

    html = _build_html(next_match, days_left, upcoming, recent)
    _send(recipients, subject, html)

    # Marca como notificado
    for m, d in matches_to_notify:
        mark_notified(m["id"], d)

    logger.info("Notificação concluída.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run(force="--force" in sys.argv)