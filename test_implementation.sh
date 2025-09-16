#!/bin/bash

# Test Implementation Script for Staffer Sims
# Tests deterministic mode, config precedence, and RUN_SUMMARY_JSON output

set -e

echo "🧪 Testing Staffer Sims Implementation"
echo "======================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test configuration
PERSONA="personas/alex_smith.yml"
SCENARIO="scenarios/referralCrisis_seniorBackendEngineer.yml"
TEST_SEED=12345
TEST_TEMP=0.0
TEST_TOP_P=1.0

# Check if required files exist
if [ ! -f "$PERSONA" ]; then
    echo -e "${RED}❌ Persona file not found: $PERSONA${NC}"
    exit 1
fi

if [ ! -f "$SCENARIO" ]; then
    echo -e "${RED}❌ Scenario file not found: $SCENARIO${NC}"
    exit 1
fi

echo -e "${BLUE}📋 Test Configuration:${NC}"
echo "  Persona: $PERSONA"
echo "  Scenario: $SCENARIO"
echo "  Seed: $TEST_SEED"
echo "  Temperature: $TEST_TEMP"
echo "  Top-P: $TEST_TOP_P"
echo ""

# Test 1: Deterministic Mode
echo -e "${YELLOW}🔬 Test 1: Deterministic Mode${NC}"
echo "Running two identical deterministic runs..."

# First run
echo "  Run 1/2..."
python simulate.py \
    --persona "$PERSONA" \
    --scenario "$SCENARIO" \
    --seed "$TEST_SEED" \
    --temperature "$TEST_TEMP" \
    --top_p "$TEST_TOP_P" \
    --output test_run1 > test_run1.log 2>&1

# Second run
echo "  Run 2/2..."
python simulate.py \
    --persona "$PERSONA" \
    --scenario "$SCENARIO" \
    --seed "$TEST_SEED" \
    --temperature "$TEST_TEMP" \
    --top_p "$TEST_TOP_P" \
    --output test_run2 > test_run2.log 2>&1

# Compare outputs
echo "  Comparing outputs..."
if diff -r test_run1 test_run2 > /dev/null 2>&1; then
    echo -e "  ${GREEN}✅ Deterministic mode working: outputs are identical${NC}"
else
    echo -e "  ${RED}❌ Deterministic mode failed: outputs differ${NC}"
    echo "  Differences found:"
    diff -r test_run1 test_run2 || true
fi

# Test 2: Configuration Precedence
echo -e "${YELLOW}🔬 Test 2: Configuration Precedence${NC}"
echo "Testing CLI > ENV > Default precedence..."

# Set environment variables
export TEMPERATURE=0.9
export TOP_P=0.7

echo "  Environment set: TEMPERATURE=0.9, TOP_P=0.7"
echo "  CLI args: --temperature 0.2 --top_p 1.0"

# Run with CLI overrides
python simulate.py \
    --persona "$PERSONA" \
    --scenario "$SCENARIO" \
    --seed "$TEST_SEED" \
    --temperature 0.2 \
    --top_p 1.0 \
    --output test_precedence > test_precedence.log 2>&1

# Check RUN_SUMMARY_JSON for correct values
if grep -q '"temperature":0.2' test_precedence.log && grep -q '"top_p":1.0' test_precedence.log; then
    echo -e "  ${GREEN}✅ Configuration precedence working: CLI overrides ENV${NC}"
else
    echo -e "  ${RED}❌ Configuration precedence failed: CLI did not override ENV${NC}"
    echo "  Expected: temperature=0.2, top_p=1.0"
    echo "  Found in log:"
    grep "RUN_SUMMARY_JSON" test_precedence.log || echo "  No RUN_SUMMARY_JSON found"
fi

# Test 3: RUN_SUMMARY_JSON Output
echo -e "${YELLOW}🔬 Test 3: RUN_SUMMARY_JSON Output${NC}"
echo "Checking structured output..."

# Check for RUN_SUMMARY_JSON in logs
if grep -q "RUN_SUMMARY_JSON:" test_run1.log; then
    echo -e "  ${GREEN}✅ RUN_SUMMARY_JSON present in output${NC}"
    
    # Extract and validate JSON
    JSON_LINE=$(grep "RUN_SUMMARY_JSON:" test_run1.log | head -1 | sed 's/RUN_SUMMARY_JSON://')
    if echo "$JSON_LINE" | python -m json.tool > /dev/null 2>&1; then
        echo -e "  ${GREEN}✅ RUN_SUMMARY_JSON is valid JSON${NC}"
        
        # Check for required fields
        if echo "$JSON_LINE" | python -c "
import json, sys
data = json.load(sys.stdin)
required = ['batch_id', 'item_id', 'persona', 'scenario', 'seed', 'temperature', 'top_p', 'deterministic_mode', 'status', 'build_version']
missing = [f for f in required if f not in data]
if missing:
    print('Missing fields:', missing)
    sys.exit(1)
else:
    print('All required fields present')
" 2>/dev/null; then
            echo -e "  ${GREEN}✅ RUN_SUMMARY_JSON contains all required fields${NC}"
        else
            echo -e "  ${RED}❌ RUN_SUMMARY_JSON missing required fields${NC}"
        fi
    else
        echo -e "  ${RED}❌ RUN_SUMMARY_JSON is not valid JSON${NC}"
    fi
else
    echo -e "  ${RED}❌ RUN_SUMMARY_JSON not found in output${NC}"
fi

# Test 4: Required Config Validation
echo -e "${YELLOW}🔬 Test 4: Required Config Validation${NC}"
echo "Testing missing required environment variables..."

# Temporarily unset required vars
unset LANGFUSE_HOST
export LANGFUSE_HOST=""

# Run without required config
python simulate.py \
    --persona "$PERSONA" \
    --scenario "$SCENARIO" \
    --seed "$TEST_SEED" \
    --output test_validation > test_validation.log 2>&1 || true

# Check for proper error message
if grep -q "Missing required environment variables.*langfuse_host" test_validation.log; then
    echo -e "  ${GREEN}✅ Required config validation working: proper error message${NC}"
else
    echo -e "  ${RED}❌ Required config validation failed: no proper error message${NC}"
    echo "  Expected: Missing required environment variables: langfuse_host"
    echo "  Found:"
    grep -i "missing\|required\|error" test_validation.log || echo "  No error message found"
fi

# Restore environment
export LANGFUSE_HOST="${LANGFUSE_HOST:-https://cloud.langfuse.com}"

# Test 5: Docker Test (if available)
echo -e "${YELLOW}🔬 Test 5: Docker Integration${NC}"
if command -v docker >/dev/null 2>&1; then
    echo "  Testing Docker build and run..."
    
    # Build image
    if docker build -t staffer-sims-test:latest . > docker_build.log 2>&1; then
        echo -e "  ${GREEN}✅ Docker build successful${NC}"
        
        # Test Docker run (with minimal config)
        if docker run --rm \
            -e LANGFUSE_PUBLIC_KEY=test \
            -e LANGFUSE_SECRET_KEY=test \
            -e LANGFUSE_HOST=https://test.com \
            staffer-sims-test:latest \
            --help > docker_help.log 2>&1; then
            echo -e "  ${GREEN}✅ Docker run successful${NC}"
        else
            echo -e "  ${RED}❌ Docker run failed${NC}"
            cat docker_help.log
        fi
    else
        echo -e "  ${RED}❌ Docker build failed${NC}"
        cat docker_build.log
    fi
else
    echo -e "  ${YELLOW}⚠️  Docker not available, skipping Docker tests${NC}"
fi

# Cleanup
echo -e "${YELLOW}🧹 Cleaning up test files...${NC}"
rm -rf test_run1 test_run2 test_precedence test_validation
rm -f test_run1.log test_run2.log test_precedence.log test_validation.log
rm -f docker_build.log docker_help.log 2>/dev/null || true

echo ""
echo -e "${GREEN}🎉 Test Implementation Complete!${NC}"
echo ""
echo -e "${BLUE}📊 Summary:${NC}"
echo "  - Deterministic mode: ✅ Tested"
echo "  - Configuration precedence: ✅ Tested" 
echo "  - RUN_SUMMARY_JSON output: ✅ Tested"
echo "  - Required config validation: ✅ Tested"
echo "  - Docker integration: ✅ Tested (if available)"
echo ""
echo -e "${BLUE}💡 Next Steps:${NC}"
echo "  1. Review test results above"
echo "  2. Check runouts/ directory for generated summary files"
echo "  3. Verify Langfuse traces are being created"
echo "  4. Run production simulations with your actual API keys"
