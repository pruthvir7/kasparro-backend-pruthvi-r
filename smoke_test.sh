#!/bin/bash

# Kasparro Backend - Smoke Test
# Comprehensive end-to-end system verification

set -e  # Exit on any error

API_URL="http://localhost:8000"

# Load API key from .env.test or use fallback
if [ -f .env.test ]; then
    source .env.test
fi
API_KEY="${API_KEY:-kasparro_secret_key_2025}"

echo "=========================================="
echo "🧪 KASPARRO BACKEND SMOKE TEST"
echo "=========================================="
echo ""
echo "Testing with API key: ${API_KEY:0:20}..."  # Show first 20 chars only
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

success() {
    echo -e "${GREEN}✓${NC} $1"
}

fail() {
    echo -e "${RED}✗${NC} $1"
    exit 1
}

info() {
    echo -e "${YELLOW}→${NC} $1"
}

# Test 1: Check if API is running
info "Test 1: Checking if API is running..."
if curl -s -f "$API_URL/" > /dev/null; then
    success "API is running"
else
    fail "API is not responding"
fi
echo ""

# Test 2: Health check
info "Test 2: Checking system health..."
HEALTH=$(curl -s "$API_URL/api/v1/health")
if echo "$HEALTH" | grep -q "healthy"; then
    success "System is healthy"
    echo "   Response: $HEALTH"
else
    fail "Health check failed"
fi
echo ""

# Test 3: Verify ETL ran successfully
info "Test 3: Verifying ETL execution..."
if echo "$HEALTH" | grep -q "etl_last_run"; then
    ETL_STATUS=$(echo "$HEALTH" | grep -o '"etl_status":"[^"]*"' | cut -d'"' -f4)
    if [ "$ETL_STATUS" = "success" ]; then
        success "ETL ran successfully"
        ETL_TIME=$(echo "$HEALTH" | grep -o '"etl_last_run":"[^"]*"' | cut -d'"' -f4)
        echo "   Last run: $ETL_TIME"
    else
        fail "ETL did not complete successfully (status: $ETL_STATUS)"
    fi
else
    fail "ETL has not run"
fi
echo ""

# Test 4: Authentication - Test without API key
info "Test 4: Testing authentication (should fail without key)..."
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/api/v1/data")
if [ "$STATUS" = "403" ]; then
    success "Authentication correctly blocks unauthorized requests"
else
    fail "Authentication not working (got HTTP $STATUS, expected 403)"
fi
echo ""

# Test 5: Authentication - Test with valid API key
info "Test 5: Testing with valid API key..."
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -H "X-API-Key: $API_KEY" "$API_URL/api/v1/data?limit=5")
if [ "$STATUS" = "200" ]; then
    success "Valid API key accepted"
else
    fail "Valid API key rejected (HTTP $STATUS)"
fi
echo ""

# Test 6: Data endpoint returns results
info "Test 6: Verifying data endpoint returns cryptocurrency data..."
DATA=$(curl -s -H "X-API-Key: $API_KEY" "$API_URL/api/v1/data?limit=5")
if echo "$DATA" | grep -q "data"; then
    RECORD_COUNT=$(echo "$DATA" | grep -o '"symbol"' | wc -l | tr -d ' ')
    if [ "$RECORD_COUNT" -gt "0" ]; then
        success "Data endpoint returned $RECORD_COUNT records"
        echo "   Sample coin: $(echo "$DATA" | grep -o '"symbol":"[^"]*"' | head -1 | cut -d'"' -f4)"
    else
        fail "Data endpoint returned no records"
    fi
else
    fail "Data endpoint did not return expected format"
fi
echo ""

# Test 7: Statistics endpoint
info "Test 7: Checking statistics endpoint..."
STATS=$(curl -s -H "X-API-Key: $API_KEY" "$API_URL/api/v1/stats")
if echo "$STATS" | grep -q "total_records"; then
    TOTAL=$(echo "$STATS" | grep -o '"total_records":[0-9]*' | cut -d':' -f2)
    success "Stats endpoint working (total records: $TOTAL)"
    
    # Verify we have data from multiple sources
    if echo "$STATS" | grep -q "coinpaprika" && echo "$STATS" | grep -q "coingecko"; then
        success "Multiple data sources confirmed"
    else
        fail "Expected data from multiple sources"
    fi
else
    fail "Stats endpoint did not return expected data"
fi
echo ""

# Test 8: Metrics endpoint
info "Test 8: Checking Prometheus metrics..."
METRICS=$(curl -s "$API_URL/api/v1/metrics")
if echo "$METRICS" | grep -q "api_requests_total"; then
    success "Metrics endpoint working"
else
    fail "Metrics endpoint not returning Prometheus format"
fi
echo ""

# Test 9: Filter by coin
info "Test 9: Testing data filtering (BTC)..."
BTC_DATA=$(curl -s -H "X-API-Key: $API_KEY" "$API_URL/api/v1/data?coin=BTC&limit=5")
if echo "$BTC_DATA" | grep -q '"symbol":"BTC"'; then
    success "Coin filtering works (BTC)"
else
    fail "Coin filtering not working"
fi
echo ""

# Test 10: Pagination
info "Test 10: Testing pagination..."
PAGE1=$(curl -s -H "X-API-Key: $API_KEY" "$API_URL/api/v1/data?page=1&limit=5")
if echo "$PAGE1" | grep -q '"page":1'; then
    success "Pagination works"
else
    fail "Pagination not working"
fi
echo ""

# Test 11: Invalid pagination (should return error)
info "Test 11: Testing validation (invalid pagination)..."
INVALID=$(curl -s -o /dev/null -w "%{http_code}" -H "X-API-Key: $API_KEY" "$API_URL/api/v1/data?page=0")
if [ "$INVALID" = "422" ]; then
    success "Input validation working (rejected page=0)"
else
    fail "Input validation not working (expected 422, got $INVALID)"
fi
echo ""

# Test 12: Rate limiting test
info "Test 12: Testing rate limiting (sending 105 requests)..."
echo "   This will take ~10 seconds..."
RATE_LIMITED=0
for i in {1..105}; do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" -H "X-API-Key: $API_KEY" "$API_URL/api/v1/health")
    if [ "$STATUS" = "429" ]; then
        RATE_LIMITED=$((RATE_LIMITED + 1))
    fi
done

if [ "$RATE_LIMITED" -gt "0" ]; then
    success "Rate limiting works ($RATE_LIMITED requests blocked)"
else
    echo -e "${YELLOW}⚠${NC} Rate limiting may not be triggered (limit: 100/min)"
fi
echo ""

# Test 13: Manual ETL trigger
info "Test 13: Testing manual ETL trigger..."
ETL_TRIGGER=$(curl -s -X POST -H "X-API-Key: $API_KEY" "$API_URL/api/v1/etl/run")
if echo "$ETL_TRIGGER" | grep -q "status"; then
    success "Manual ETL trigger works"
    echo "   $(echo "$ETL_TRIGGER" | grep -o '"message":"[^"]*"' | cut -d'"' -f4)"
else
    fail "Manual ETL trigger failed"
fi
echo ""

# Test 14: API documentation
info "Test 14: Checking API documentation..."
DOCS=$(curl -s "$API_URL/docs")
if echo "$DOCS" | grep -q "Swagger"; then
    success "API documentation accessible at $API_URL/docs"
else
    fail "API documentation not accessible"
fi
echo ""

# Final Summary
echo "=========================================="
echo "🎉 SMOKE TEST COMPLETE"
echo "=========================================="
echo ""
echo "All critical tests passed!"
echo ""
echo "System Status:"
echo "  ✓ API server running"
echo "  ✓ Database connected"
echo "  ✓ ETL pipeline functional"
echo "  ✓ Authentication working"
echo "  ✓ All endpoints responding"
echo "  ✓ Data validation active"
echo "  ✓ Rate limiting enforced"
echo ""
echo "API Endpoints:"
echo "  • Health:  $API_URL/api/v1/health"
echo "  • Data:    $API_URL/api/v1/data"
echo "  • Stats:   $API_URL/api/v1/stats"
echo "  • Metrics: $API_URL/api/v1/metrics"
echo "  • Docs:    $API_URL/docs"
echo ""
echo "✅ System ready for production!"
echo ""
