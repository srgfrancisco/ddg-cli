#!/bin/bash
# Check role permissions on staging

set -e

HOST="sync-server-stg.cmal47k4rse1.us-west-2.rds.amazonaws.com"
PORT="5432"
DB="postgres"

echo "========================================="
echo "Checking Role Permissions"
echo "========================================="
echo ""

# Check table privileges by schema
echo "TEST 1: Table privileges by schema and role"
echo "-------------------------------------"
PGPASSWORD='GJtQtysNVd9m8PFroUhWu4hhwTVLEx' psql -h $HOST -p $PORT -U syncserverstg -d $DB -t -c "
SELECT
  table_schema,
  grantee,
  privilege_type,
  COUNT(*) as table_count
FROM information_schema.table_privileges
WHERE grantee IN ('role_readonly', 'role_readwrite', 'role_migration')
GROUP BY table_schema, grantee, privilege_type
ORDER BY table_schema, grantee, privilege_type;
"
echo ""

# Check schema usage privileges
echo "TEST 2: Schema USAGE privileges"
echo "-------------------------------------"
PGPASSWORD='GJtQtysNVd9m8PFroUhWu4hhwTVLEx' psql -h $HOST -p $PORT -U syncserverstg -d $DB -t -c "
SELECT
  nspname AS schema_name,
  r.rolname AS role_name,
  has_schema_privilege(r.oid, nspname, 'USAGE') AS has_usage,
  has_schema_privilege(r.oid, nspname, 'CREATE') AS has_create
FROM pg_namespace n
CROSS JOIN pg_roles r
WHERE r.rolname IN ('role_readonly', 'role_readwrite', 'role_migration')
  AND nspname IN ('public', 'default')
ORDER BY nspname, r.rolname;
"
echo ""

# Check default privileges
echo "TEST 3: Default privileges configured"
echo "-------------------------------------"
PGPASSWORD='GJtQtysNVd9m8PFroUhWu4hhwTVLEx' psql -h $HOST -p $PORT -U syncserverstg -d $DB -t -c "
SELECT
  pg_get_userbyid(defaclrole) AS object_creator,
  nspname AS schema,
  defaclobjtype AS object_type,
  pg_get_userbyid(grantee.oid) AS grantee,
  privilege_type
FROM pg_default_acl def
JOIN pg_namespace nsp ON def.defaclnamespace = nsp.oid
CROSS JOIN LATERAL (
  SELECT (aclexplode(defacl)).grantee, (aclexplode(defacl)).privilege_type
) AS grantee
WHERE nspname IN ('public', 'default')
ORDER BY nspname, object_type, grantee;
"
echo ""

echo "========================================="
echo "Permission check complete!"
echo "========================================="
