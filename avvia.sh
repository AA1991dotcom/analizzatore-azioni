#!/usr/bin/env bash
# Avvio del tool con un solo comando: crea l'ambiente, installa le dipendenze, lancia l'app.
set -e
cd "$(dirname "$0")"

# Sceglie un Python >= 3.10 (preferisce python3.12 se installato via Homebrew).
PY=""
for cand in python3.12 python3.11 python3.10 python3; do
  if command -v "$cand" >/dev/null 2>&1; then PY="$cand"; break; fi
done
if [ -z "$PY" ]; then
  echo "Python non trovato. Installa Python 3.12:  brew install python@3.12"
  exit 1
fi

# Crea il virtualenv la prima volta.
if [ ! -d ".venv" ]; then
  echo "Creo l'ambiente virtuale con $PY ..."
  "$PY" -m venv .venv
fi

source .venv/bin/activate
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

echo "Avvio dell'app... (si aprira' nel browser)"
exec streamlit run app.py
