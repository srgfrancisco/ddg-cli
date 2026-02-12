#!/bin/bash
# Test script for sync-server staging users

set -e

HOST="sync-server-stg.cmal47k4rse1.us-west-2.rds.amazonaws.com"
PORT="5432"
DB="postgres"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================="
echo "Sync-Server Staging User Testing"
echo "========================================="
echo ""

# Test 1: Check what roles and users exist
echo "TEST 1: Verify roles and users exist"
echo "-------------------------------------"
PGPASSWORD='GJtQtysNVd9m8PFroUhWu4hhwTVLEx' psql -h $HOST -p $PORT -U syncserverstg -d $DB -t -c "
SELECT
  rolname,
  rolcanlogin as can_login,
  CASE WHEN rolconnlimit = -1 THEN 'unlimited' ELSE rolconnlimit::text END as conn_limit
FROM pg_roles
WHERE rolname IN (
  'role_readonly', 'role_readwrite', 'role_migration',
  'role_staging_ro', 'role_staging_rw', 'role_staging_admin',
  'syncserver_staging_rw',
  'syncsupervisor_staging_rw',
  'superset_staging_ro',
  'ftpidentity_staging_ro',
  'syncserver_staging_migration'
)
ORDER BY rolname;
"
echo ""

# Test 2: Check role memberships
echo "TEST 2: Verify role memberships"
echo "-------------------------------------"
PGPASSWORD='GJtQtysNVd9m8PFroUhWu4hhwTVLEx' psql -h $HOST -p $PORT -U syncserverstg -d $DB -t -c "
SELECT
  u.rolname AS user_name,
  r.rolname AS granted_role
FROM pg_auth_members am
JOIN pg_roles r ON r.oid = am.roleid
JOIN pg_roles u ON u.oid = am.member
WHERE u.rolname IN (
  'syncserver_staging_rw',
  'syncsupervisor_staging_rw',
  'superset_staging_ro',
  'ftpidentity_staging_ro',
  'syncserver_staging_migration'
)
ORDER BY u.rolname, r.rolname;
"
echo ""

# Test 3: Check what schemas exist
echo "TEST 3: Check available schemas"
echo "-------------------------------------"
PGPASSWORD='GJtQtysNVd9m8PFroUhWu4hhwTVLEx' psql -h $HOST -p $PORT -U syncserverstg -d $DB -t -c "
SELECT schema_name FROM information_schema.schemata
WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
ORDER BY schema_name;
"
echo ""

# Test 4: Check for tables in public schema
echo "TEST 4: List tables in public schema"
echo "-------------------------------------"
PGPASSWORD='GJtQtysNVd9m8PFroUhWu4hhwTVLEx' psql -h $HOST -p $PORT -U syncserverstg -d $DB -t -c "
SELECT schemaname, tablename
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename
LIMIT 10;
"
echo ""

# Test 5: Check for \"default\" schema
echo "TEST 5: Check if 'default' schema exists"
echo "-------------------------------------"
PGPASSWORD='GJtQtysNVd9m8PFroUhWu4hhwTVLEx' psql -h $HOST -p $PORT -U syncserverstg -d $DB -t -c "
SELECT EXISTS(
  SELECT 1 FROM information_schema.schemata
  WHERE schema_name = 'default'
) as default_schema_exists;
"
echo ""

echo "========================================="
echo "Initial verification complete!"
echo "========================================="
