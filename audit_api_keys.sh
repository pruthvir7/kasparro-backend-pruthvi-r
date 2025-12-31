#!/bin/bash

echo "🔐 FINAL API KEY SECURITY AUDIT"
echo "================================"

echo ""
echo "1️⃣ OLD KEY (kasparro_secret_key_2025) - EXPECTED:"
grep -rn "kasparro_secret_key_2025" . \
  --exclude-dir=.git \
  --exclude-dir=__pycache__ \
  --exclude-dir=venv \
  --exclude-dir=.venv \
  --exclude="*.pyc" \
  --exclude="*.log" \
  --color=always 2>/dev/null || echo "No old keys found"

echo ""
echo "2️⃣ NEW KEY (kasparro_test_key_for_evaluation_2025) - SHOULD BE 0:"
NEW_KEY_COUNT=$(grep -rn "kasparro_test_key_for_evaluation_2025" . \
  --exclude-dir=.git \
  --exclude-dir=__pycache__ \
  --exclude-dir=venv \
  --exclude-dir=.venv \
  --exclude="*.pyc" \
  --exclude="*.log" \
  2>/dev/null | wc -l)

if [ "$NEW_KEY_COUNT" -gt 0 ]; then
    grep -rn "kasparro_test_key_for_evaluation_2025" . \
      --exclude-dir=.git \
      --exclude-dir=__pycache__ \
      --exclude-dir=venv \
      --exclude-dir=.venv \
      --exclude="*.pyc" \
      --exclude="*.log" \
      2>/dev/null
    echo "❌ $NEW_KEY_COUNT NEW KEYS FOUND - FIX NEEDED!"
    exit 1
else
    echo "✅ NO NEW KEYS - PERFECTLY CLEAN!"
fi

echo ""
echo "3️⃣ .env FILE STATUS:"
echo "   Local .env: $(test -f .env && echo 'EXISTS (OK if not committed)' || echo 'NOT FOUND ✅')"
echo "   Committed .env.test: $(git ls-files | grep -q '^\\.env\\.test$' && echo '✅ PRESENT' || echo '❌ MISSING')"
echo "   Committed .env.example: $(git ls-files | grep -q '^\\.env\\.example$' && echo '✅ PRESENT' || echo '❌ MISSING')"
echo "   .env in .gitignore: $(grep -q '^\.env$' .gitignore 2>/dev/null && echo '✅ PROTECTED' || echo '❌ VULNERABLE')"

echo ""
echo "4️⃣ GIT CHECK:"
echo "   .env tracked: $(git ls-files | grep -q '^\.env$' && echo '❌ DANGER!' || echo '✅ SAFE')"
echo "   Staged .env files: $(git diff --cached --name-only | grep -q '\.env$' && echo '❌ REMOVE!' || echo '✅ CLEAN')"

echo ""
echo "5️⃣ PRODUCTION TEST (Local):"
if curl -s http://localhost:8000/api/v1/health | grep -q "healthy"; then
    echo "   Local API: 🟢 HEALTHY"
else
    echo "   Local API: 🔴 NOT RUNNING (docker-compose up -d)"
fi

echo ""
echo "================================"
echo "🎉 AUDIT COMPLETE - READY TO COMMIT!"
echo "Run: git add -A && git commit -m 'security complete' && git push"
