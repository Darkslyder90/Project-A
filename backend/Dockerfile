# Produktiv-Image (siehe Briefing: Deployment per docker compose auf dem
# Hetzner-VPS). Fuer lokale Entwicklung wird bewusst KEIN Docker verwendet
# (siehe README "Lokale Entwicklung") - dieses Image ist ausschliesslich fuer
# Prod/CI relevant.
FROM python:3.14-slim

WORKDIR /app

# build-essential fuer den seltenen Fall, dass eine Abhaengigkeit (z. B. ueber
# sentence-transformers/torch) ein Wheel fuer die Ziel-Plattform nachbauen muss.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV ENV=prod \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# Ruft ausschliesslich /health auf - kein Claude-API-Aufruf (siehe Briefing:
# Healthcheck darf keine Kosten verursachen/von Claude abhaengen).
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

# Migrationen laufen NICHT automatisch beim Container-Start (siehe Briefing:
# "Migration kontrolliert genau einmal ausfuehren, nicht parallel aus mehreren
# Workern/Containern heraus") - siehe stattdessen scripts/update.sh im
# Repo-Root, das `alembic upgrade head` als eigenen, expliziten Schritt vor
# dem (Neu-)Start der Anwendung aufruft.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
