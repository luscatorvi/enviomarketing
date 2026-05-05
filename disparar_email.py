"""
Via Star — Disparador de E-mail | GitHub Actions
=================================================
Reconexão automática ao SMTP + retomada a partir de linha específica.
"""

import os
import smtplib
import ssl
import time
import logging
import pandas as pd
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from datetime import datetime

from config import (
    SMTP_HOST, SMTP_PORT, ASSUNTO,
    PLANILHA, COL_EMAIL, COL_NOME,
    TEMPLATE_HTML, PAUSA_ENTRE_ENVIOS,
)

EMAIL_FROM   = os.environ["EMAIL_FROM"]
EMAIL_PASS   = os.environ["EMAIL_PASS"]
MODO_TESTE   = os.environ.get("MODO_TESTE", "false").lower() == "true"
DEST_TESTE   = os.environ.get("DEST_TESTE", "").strip()
LINHA_INICIO = int(os.environ.get("LINHA_INICIO", "1"))

log_file = f"envios_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


def conectar_smtp():
    context = ssl.create_default_context()
    server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30)
    server.ehlo()
    server.starttls(context=context)
    if not MODO_TESTE:
        server.login(EMAIL_FROM, EMAIL_PASS)
    log.info("🔌 Conectado ao SMTP.")
    return server


def carregar_contatos() -> pd.DataFrame:
    if DEST_TESTE:
        log.info(f"Modo teste com destinatário avulso: {DEST_TESTE}")
        return pd.DataFrame([{COL_EMAIL: DEST_TESTE, COL_NOME: "Teste"}])

    path = Path(PLANILHA)
    if not path.exists():
        raise FileNotFoundError(f"Planilha não encontrada: {PLANILHA}")

    df = pd.read_csv(path) if path.suffix.lower() == ".csv" else pd.read_excel(path)

    if COL_EMAIL not in df.columns:
        raise ValueError(
            f"Coluna '{COL_EMAIL}' não encontrada. "
            f"Disponíveis: {list(df.columns)}"
        )

    df = df.dropna(subset=[COL_EMAIL])
    df[COL_EMAIL] = df[COL_EMAIL].str.strip().str.lower()
    df = df.reset_index(drop=True)

    # Retoma a partir da linha informada
    if LINHA_INICIO > 1:
        df = df.iloc[LINHA_INICIO - 1:]
        log.info(f"Retomando a partir da linha {LINHA_INICIO} — {len(df)} contatos restantes.")
    else:
        log.info(f"{len(df)} contatos carregados de '{PLANILHA}'")

    return df


def carregar_html() -> str:
    path = Path(TEMPLATE_HTML)
    if not path.exists():
        raise FileNotFoundError(f"Template HTML não encontrado: {TEMPLATE_HTML}")
    return path.read_text(encoding="utf-8")


def montar_mensagem(email: str, nome: str, html_base: str) -> MIMEMultipart:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = ASSUNTO
    msg["From"]    = f"Via Star Tapetes <{EMAIL_FROM}>"
    msg["To"]      = email

    nome_fmt = nome.title() if nome else ""
    html = html_base.replace("{{NOME}}", nome_fmt)

    texto = (
        f"Olá{', ' + nome_fmt if nome_fmt else ''}!\n\n"
        "A Via Star esteve na Expo Revestir 2026.\n"
        "Venha nos visitar!\n\n"
        "WhatsApp: +55 11 2225-9090\n"
        "viastar.com.br\n"
    )

    msg.attach(MIMEText(texto, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))
    return msg


def disparar():
    if MODO_TESTE:
        log.warning("⚠️  MODO TESTE — e-mails não serão enviados.")

    df        = carregar_contatos()
    html_base = carregar_html()
    total     = len(df)
    enviados  = 0
    falhas    = 0

    try:
        server = conectar_smtp()
    except smtplib.SMTPAuthenticationError:
        log.critical("❌ Falha de autenticação. Verifique os Secrets EMAIL_FROM e EMAIL_PASS.")
        raise SystemExit(1)

    for i, (_, row) in enumerate(df.iterrows()):
        email = row[COL_EMAIL]
        nome  = (
            str(row[COL_NOME]).strip()
            if COL_NOME in df.columns and pd.notna(row.get(COL_NOME))
            else ""
        )

        # Reconecta a cada 200 envios
        if i > 0 and i % 200 == 0:
            try:
                server.quit()
            except Exception:
                pass
            log.info("🔄 Reconectando ao SMTP...")
            time.sleep(3)
            server = conectar_smtp()

        try:
            msg = montar_mensagem(email, nome, html_base)
            if not MODO_TESTE:
                server.sendmail(EMAIL_FROM, email, msg.as_string())
            enviados += 1
            log.info(f"[{enviados}/{total}] ✅  {email}")
            time.sleep(PAUSA_ENTRE_ENVIOS)

        except smtplib.SMTPServerDisconnected:
            log.warning(f"⚠️  Conexão perdida em {email}. Reconectando...")
            time.sleep(5)
            server = conectar_smtp()
            try:
                server.sendmail(EMAIL_FROM, email, msg.as_string())
                enviados += 1
                log.info(f"[{enviados}/{total}] ✅  {email} (após reconexão)")
            except Exception as e:
                falhas += 1
                log.error(f"[FALHA] {email} — {e}")

        except Exception as e:
            falhas += 1
            log.error(f"[FALHA] {email} — {e}")

    try:
        server.quit()
    except Exception:
        pass

    log.info(f"\n{'─'*50}")
    log.info(f"Concluído — Enviados: {enviados} | Falhas: {falhas} | Total: {total}")

    if falhas > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    disparar()
