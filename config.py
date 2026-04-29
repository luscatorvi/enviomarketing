# config.py — configurações não-sensíveis da campanha
# (credenciais ficam nos Secrets do GitHub, nunca aqui)

# SMTP — Outlook / Microsoft 365
SMTP_HOST = "smtp.office365.com"
SMTP_PORT = 587

# E-mail
ASSUNTO = "Via Star na Expo Revestir 2026 — Venha nos visitar!"

# Planilha de contatos (commitar no repositório)
PLANILHA  = "contatos.xlsx"   # ou contatos.csv
COL_EMAIL = "e-mail"           # nome exato da coluna de e-mail
COL_NOME  = ""            # nome exato da coluna de nome (ou "" para ignorar)

# Template HTML
TEMPLATE_HTML = "email_viastar_exporevestir_v4_3.html"

# Pausa entre envios (segundos) — evita throttling do servidor
PAUSA_ENTRE_ENVIOS = 2
