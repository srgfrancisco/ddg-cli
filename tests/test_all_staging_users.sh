#!/bin/bash
# Comprehensive test for sync-server staging users
# Tests connectivity and permissions for all 5 users

set -e

HOST="sync-server-stg.cmal47k4rse1.us-west-2.rds.amazonaws.com"
PORT="5432"
DB="postgres"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# User credentials (simplified for compatibility)
USER1="user_syncserver_staging_rw"
PASS1="WaHm6T33JX8MSt7Pnta01eIfCS4U+y5zuVaH9NT4otE="

USER2="user_syncsupervisor_staging_rw"
PASS2="+luB9cqUEHB3h3Q8snOZougNhIsy/YYd5fX6NdVAq94="

USER3="user_superset_staging_ro"
PASS3="t7FoqTeE1t1qKmzUO36XqHEMMzogrycbp1/8PdSe0UY="

USER4="user_ftpidentity_staging_ro"
PASS4="/tN09t9kg+txK/DWgqYL5oZkrl6Aj2fsJQKh3YYr9FI="

USER5="user_syncserver_staging_migration"
PASS5="UKvpN1+mfG3AUU7XsKj0wEPt6AaBmFBSqP7pLOZt5RE="

echo "================================================================"
echo "Sync-Server Staging User Connectivity & Permission Tests"
echo "================================================================"
echo ""

test_connection() {
  local user=$1
  local pass=$2
  echo -n "Testing $user... "

  result=$(PGPASSWORD="$pass" psql -h $HOST -p $PORT -U "$user" -d $DB -t -c "SELECT 1;" 2>&1)

  if echo "$result" | grep -q "1"; then
    echo -e "${GREEN}✓ Connected${NC}"
    return 0
  else
    echo -e "${RED}✗ Failed${NC}"
    echo "  Error: $result"
    return 1
  fi
}

test_select() {
  local user=$1
  local pass=$2
  echo -n "  SELECT... "

  result=$(PGPASSWORD="$pass" psql -h $HOST -p $PORT -U "$user" -d $DB -t -c "SELECT COUNT(*) FROM public.\"Agent\";" 2>&1)

  if echo "$result" | grep -qE "^[[:space:]]*[0-9]+"; then
    echo -e "${GREEN}✓ Can SELECT${NC}"
    return 0
  else
    echo -e "${RED}✗ Failed${NC}"
    return 1
  fi
}

test_insert() {
  local user=$1
  local pass=$2
  echo -n "  INSERT... "

  result=$(PGPASSWORD="$pass" psql -h $HOST -p $PORT -U "$user" -d $DB -c "BEGIN; INSERT INTO public.\"Task\" (id, status) VALUES ('test-$RANDOM', 'PENDING'); ROLLBACK;" 2>&1)

  if echo "$result" | grep -q "ROLLBACK"; then
    echo -e "${GREEN}✓ Can INSERT${NC}"
    return 0
  else
    echo -e "${RED}✗ Failed: $result${NC}"
    return 1
  fi
}

test_insert_blocked() {
  local user=$1
  local pass=$2
  echo -n "  INSERT (should block)... "

  result=$(PGPASSWORD="$pass" psql -h $HOST -p $PORT -U "$user" -d $DB -c "BEGIN; INSERT INTO public.\"Task\" (id, status) VALUES ('test-$RANDOM', 'PENDING'); ROLLBACK;" 2>&1)

  if echo "$result" | grep -qE "(permission denied|must be owner)"; then
    echo -e "${GREEN}✓ Correctly blocked${NC}"
    return 0
  else
    echo -e "${RED}✗ Should have been blocked!${NC}"
    return 1
  fi
}

test_create_table() {
  local user=$1
  local pass=$2
  echo -n "  CREATE TABLE... "

  result=$(PGPASSWORD="$pass" psql -h $HOST -p $PORT -U "$user" -d $DB -c "BEGIN; CREATE TABLE public.test_ddl_$RANDOM (id INT); ROLLBACK;" 2>&1)

  if echo "$result" | grep -q "ROLLBACK"; then
    echo -e "${GREEN}✓ Can CREATE TABLE${NC}"
    return 0
  else
    echo -e "${RED}✗ Failed${NC}"
    return 1
  fi
}

test_create_table_blocked() {
  local user=$1
  local pass=$2
  echo -n "  CREATE TABLE (should block)... "

  result=$(PGPASSWORD="$pass" psql -h $HOST -p $PORT -U "$user" -d $DB -c "BEGIN; CREATE TABLE public.test_ddl_$RANDOM (id INT); ROLLBACK;" 2>&1)

  if echo "$result" | grep -qE "(permission denied|must be owner)"; then
    echo -e "${GREEN}✓ Correctly blocked${NC}"
    return 0
  else
    echo -e "${RED}✗ Should have been blocked!${NC}"
    return 1
  fi
}

# Run tests
echo "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo "${BLUE}TEST 1: Basic Connectivity${NC}"
echo "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

test_connection "$USER1" "$PASS1"
test_connection "$USER2" "$PASS2"
test_connection "$USER3" "$PASS3"
test_connection "$USER4" "$PASS4"
test_connection "$USER5" "$PASS5"
echo ""

echo "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo "${BLUE}TEST 2: Readonly Users (superset, ftpidentity)${NC}"
echo "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

echo "$USER3 (superset readonly):"
test_select "$USER3" "$PASS3"
test_insert_blocked "$USER3" "$PASS3"
test_create_table_blocked "$USER3" "$PASS3"
echo ""

echo "$USER4 (ftpidentity readonly):"
test_select "$USER4" "$PASS4"
test_insert_blocked "$USER4" "$PASS4"
test_create_table_blocked "$USER4" "$PASS4"
echo ""

echo "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo "${BLUE}TEST 3: Readwrite Users (syncserver, syncsupervisor)${NC}"
echo "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

echo "$USER1 (syncserver readwrite):"
test_select "$USER1" "$PASS1"
test_insert "$USER1" "$PASS1"
test_create_table_blocked "$USER1" "$PASS1"
echo ""

echo "$USER2 (syncsupervisor readwrite):"
test_select "$USER2" "$PASS2"
test_insert "$USER2" "$PASS2"
test_create_table_blocked "$USER2" "$PASS2"
echo ""

echo "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo "${BLUE}TEST 4: Migration User${NC}"
echo "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

echo "$USER5 (migration - full DDL):"
test_select "$USER5" "$PASS5"
test_insert "$USER5" "$PASS5"
test_create_table "$USER5" "$PASS5"
echo ""

echo "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo "${BLUE}TEST 5: Default Privileges${NC}"
echo "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

echo "Checking default privileges configuration:"
PGPASSWORD='GJtQtysNVd9m8PFroUhWu4hhwTVLEx' psql -h $HOST -p $PORT -U syncserverstg -d $DB -c "
SELECT
  pg_get_userbyid(defaclrole) AS object_creator,
  nspname AS schema,
  CASE defaclobjtype
    WHEN 'r' THEN 'tables'
    WHEN 'S' THEN 'sequences'
    WHEN 'f' THEN 'functions'
  END AS object_type,
  pg_get_userbyid(grantee.oid) AS grantee,
  privilege_type
FROM pg_default_acl def
JOIN pg_namespace nsp ON def.defaclnamespace = nsp.oid
CROSS JOIN LATERAL (
  SELECT (aclexplode(def.defaclacl)).grantee, (aclexplode(def.defaclacl)).privilege_type
) AS grantee
WHERE nspname = 'public'
  AND pg_get_userbyid(defaclrole) LIKE '%staging_migration'
ORDER BY object_type, grantee;
" 2>&1 || echo "Note: Default privileges query may need adjustment"

echo ""
echo "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo "${BLUE}TEST COMPLETE${NC}"
echo "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""
