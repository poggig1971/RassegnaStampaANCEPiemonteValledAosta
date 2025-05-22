#!/bin/bash

# Script di backup Git automatico
NOW=$(date "+%Y-%m-%d %H:%M:%S")
echo "➡️  Eseguo backup alle $NOW"

git add .
git commit -m "Backup automatico del Codespace - $NOW"
git push origin main

echo "✅ Backup completato!"
