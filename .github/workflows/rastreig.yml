name: Rastreig Integral Mallorca

on:
  schedule:
    - cron: '0 11 * * *' # 12:00 hora de Mallorca
  workflow_dispatch:

jobs:
  executa-rastreig:
    runs-on: ubuntu-latest
    steps:
      - name: Descarrega el repositori
        uses: actions/checkout@v4

      - name: Configura Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Instal·la dependències i navegador
        run: |
          pip install requests beautifulsoup4 psycopg2-binary playwright
          playwright install chromium

      - name: Executa rastrejador contra Neon
        env:
          NEON_DATABASE_URL: ${{ secrets.NEON_DATABASE_URL }}
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: python rastreig_mallorca.py
