#!/bin/bash
# Test default privileges for sync-server staging
# Creates a table as migration user and tests access from other users

set -e

HOST="sync-server-stg.cmal47k4rse1.us-west-2.rds.amazonaws.com"
PORT="5432"
DB="postgres"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Passwords
MIGRATION_PASS="UKvpN1+mfG3AUU7XsKj0wEPt6AaBmFBSqP7pLOZt5RE="
RW_PASS="WaHm6T33JX8MSt7Pnta01eIfCS4U+y5zuVaH9NT4otE="
RO_PASS="t7FoqTeE1t1qKmzUO36XqHEMMzogrycbp1/8PdSe0UY="

echo -e "${BLUE}================================================================${NC}"
echo -e "${BLUE}Default Privileges Test for sync-server-staging${NC}"
echo -e "${BLUE}================================================================${NC}"
echo ""

# Step 1: Create test table as migration user
echo -e "${YELLOW}STEP 1: Creating test table as migration user...${NC}"
PGPASSWORD="$MIGRATION_PASS" psql -h $HOST -p $PORT -U user_syncserver_staging_migration -d $DB << 'EOF'
BEGIN;
CREATE TABLE public.test_default_privs (
  id SERIAL PRIMARY KEY,
  data TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);
INSERT INTO public.test_default_privs (data) VALUES ('row1'), ('row2'), ('row3');
COMMIT;

SELECT 'Created table with ' || COUNT(*) || ' rows' AS result FROM public.test_default_privs;
EOF
echo -e "${GREEN}✓ Table created${NC}"
echo ""

# Step 2: Test readonly user - SELECT should work
echo -e "${YELLOW}STEP 2: Testing readonly user (user_superset_staging_ro)...${NC}"
echo -n "  SELECT test... "
RESULT=$(PGPASSWORD="$RO_PASS" psql -h $HOST -p $PORT -U user_superset_staging_ro -d $DB -t -c "SELECT COUNT(*) FROM public.test_default_privs;" 2>&1)
if echo "$RESULT" | grep -qE "3"; then
  echo -e "${GREEN}✓ Can SELECT (found 3 rows)${NC}"
else
  echo -e "${RED}✗ Failed: $RESULT${NC}"
fi

# Step 3: Test readonly user - INSERT should fail
echo -n "  INSERT test (should fail)... "
RESULT=$(PGPASSWORD="$RO_PASS" psql -h $HOST -p $PORT -U user_superset_staging_ro -d $DB -c "INSERT INTO public.test_default_privs (data) VALUES ('should_fail');" 2>&1)
if echo "$RESULT" | grep -q "permission denied"; then
  echo -e "${GREEN}✓ INSERT correctly blocked${NC}"
else
  echo -e "${RED}✗ Should have been blocked: $RESULT${NC}"
fi
echo ""

# Step 4: Test readwrite user - SELECT should work
echo -e "${YELLOW}STEP 3: Testing readwrite user (user_syncserver_staging_rw)...${NC}"
echo -n "  SELECT test... "
RESULT=$(PGPASSWORD="$RW_PASS" psql -h $HOST -p $PORT -U user_syncserver_staging_rw -d $DB -t -c "SELECT COUNT(*) FROM public.test_default_privs;" 2>&1)
if echo "$RESULT" | grep -qE "3"; then
  echo -e "${GREEN}✓ Can SELECT (found 3 rows)${NC}"
else
  echo -e "${RED}✗ Failed: $RESULT${NC}"
fi

# Step 5: Test readwrite user - INSERT should work
echo -n "  INSERT test... "
RESULT=$(PGPASSWORD="$RW_PASS" psql -h $HOST -p $PORT -U user_syncserver_staging_rw -d $DB -c "INSERT INTO public.test_default_privs (data) VALUES ('row4'); SELECT 'Inserted' AS result;" 2>&1)
if echo "$RESULT" | grep -q "Inserted"; then
  echo -e "${GREEN}✓ Can INSERT${NC}"
else
  echo -e "${RED}✗ Failed: $RESULT${NC}"
fi

# Step 6: Test readwrite user - UPDATE should work
echo -n "  UPDATE test... "
RESULT=$(PGPASSWORD="$RW_PASS" psql -h $HOST -p $PORT -U user_syncserver_staging_rw -d $DB -c "UPDATE public.test_default_privs SET data = 'updated_row1' WHERE id = 1; SELECT 'Updated' AS result;" 2>&1)
if echo "$RESULT" | grep -q "Updated"; then
  echo -e "${GREEN}✓ Can UPDATE${NC}"
else
  echo -e "${RED}✗ Failed: $RESULT${NC}"
fi

# Step 7: Test readwrite user - DELETE should work
echo -n "  DELETE test... "
RESULT=$(PGPASSWORD="$RW_PASS" psql -h $HOST -p $PORT -U user_syncserver_staging_rw -d $DB -c "DELETE FROM public.test_default_privs WHERE id = 4; SELECT 'Deleted' AS result;" 2>&1)
if echo "$RESULT" | grep -q "Deleted"; then
  echo -e "${GREEN}✓ Can DELETE${NC}"
else
  echo -e "${RED}✗ Failed: $RESULT${NC}"
fi
echo ""

# Step 8: Show final state
echo -e "${YELLOW}STEP 4: Final table state...${NC}"
PGPASSWORD="$MIGRATION_PASS" psql -h $HOST -p $PORT -U user_syncserver_staging_migration -d $DB -c "SELECT * FROM public.test_default_privs ORDER BY id;"
echo ""

# Step 9: Check actual default privileges configuration
echo -e "${YELLOW}STEP 5: Checking default privileges configuration...${NC}"
PGPASSWORD="$MIGRATION_PASS" psql -h $HOST -p $PORT -U user_syncserver_staging_migration -d $DB << 'EOF'
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
  AND pg_get_userbyid(defaclrole) = 'user_syncserver_staging_migration'
ORDER BY object_type, grantee;
EOF
echo ""

# Step 10: Cleanup - drop test table
echo -e "${YELLOW}STEP 6: Cleaning up test table...${NC}"
PGPASSWORD="$MIGRATION_PASS" psql -h $HOST -p $PORT -U user_syncserver_staging_migration -d $DB -c "DROP TABLE public.test_default_privs;"
echo -e "${GREEN}✓ Test table dropped${NC}"
echo ""

echo -e "${BLUE}================================================================${NC}"
echo -e "${BLUE}Default Privileges Test Complete${NC}"
echo -e "${BLUE}================================================================${NC}"
