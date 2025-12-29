#!/bin/bash

echo "=================================="
echo "Normalization Verification Tests"
echo "=================================="
echo ""

API_KEY="kasparro_secret_key_2025"
BASE_URL="http://localhost:8000"

# Test 1: Health
echo "1. Health Check..."
curl -s "$BASE_URL/api/v1/health" | jq -r '.status'
echo ""

# Test 2: Trigger ETL
echo "2. Triggering ETL..."
curl -s -X POST -H "X-API-Key: $API_KEY" "$BASE_URL/api/v1/etl/run" | jq -r '.status'
echo ""

# Wait for ETL
echo "Waiting 30 seconds for ETL to complete..."
sleep 30
echo ""

# Test 3: Get canonical coins
echo "3. Canonical Coins (Proof of Normalization)..."
COINS=$(curl -s -H "X-API-Key: $API_KEY" "$BASE_URL/api/v1/coins")
TOTAL=$(echo "$COINS" | jq -r '.total_coins')
echo "   Total canonical coins: $TOTAL"

# Check BTC specifically
BTC=$(echo "$COINS" | jq '.coins[] | select(.symbol == "BTC")')
if [ ! -z "$BTC" ]; then
    echo "   ✓ BTC found with source identifiers:"
    echo "$BTC" | jq -r '.source_identifiers[] | "     - \(.source): \(.source_id)"'
else
    echo "   ✗ BTC not found"
fi
echo ""

# Test 4: Get BTC data from all sources
echo "4. BTC Data from Multiple Sources..."
BTC_DATA=$(curl -s -H "X-API-Key: $API_KEY" "$BASE_URL/api/v1/data?coin=BTC&limit=10")
BTC_COUNT=$(echo "$BTC_DATA" | jq '.data | length')
echo "   BTC records found: $BTC_COUNT"
echo "$BTC_DATA" | jq -r '.data[] | "   - \(.source): $\(.price_usd)"'
echo ""

# Test 5: Stats
echo "5. Statistics..."
STATS=$(curl -s -H "X-API-Key: $API_KEY" "$BASE_URL/api/v1/stats")
echo "   Total records: $(echo "$STATS" | jq -r '.total_records')"
echo "   Total sources: $(echo "$STATS" | jq -r '.total_sources')"
echo "   Records by source:"
echo "$STATS" | jq -r '.records_by_source | to_entries[] | "     - \(.key): \(.value)"'
echo ""

# Test 6: Database verification
echo "6. Database Table Check..."
docker-compose exec -T db psql -U postgres -d kasparro -c "
SELECT 
    (SELECT COUNT(*) FROM coins) as canonical_coins,
    (SELECT COUNT(*) FROM coin_prices) as price_records,
    (SELECT COUNT(*) FROM coin_identifiers) as identifiers;
" 2>/dev/null
echo ""

echo "=================================="
echo "✅ Normalization Tests Complete"
echo "=================================="
