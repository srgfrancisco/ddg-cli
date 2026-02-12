-- ============================================================================
-- Create Staging Users (roles already exist, permissions already granted)
-- ============================================================================
-- Execute as: syncserverstg (current master user)
-- Database: postgres
-- Schema: public
-- ============================================================================

-- =============================================================================
-- STEP 1: Create Migration User FIRST (will own future objects)
-- =============================================================================

CREATE USER syncserver_staging_migration WITH PASSWORD 'UKvpN1+mfG3AUU7XsKj0wEPt6AaBmFBSqP7pLOZt5RE=';
GRANT role_migration TO syncserver_staging_migration;

-- =============================================================================
-- STEP 2: Configure Default Privileges (CRITICAL - FOR ROLE migration user)
-- =============================================================================

-- Objects created by migration user → readable by readonly
ALTER DEFAULT PRIVILEGES FOR ROLE syncserver_staging_migration IN SCHEMA public
  GRANT SELECT ON TABLES TO role_readonly;
ALTER DEFAULT PRIVILEGES FOR ROLE syncserver_staging_migration IN SCHEMA public
  GRANT SELECT ON SEQUENCES TO role_readonly;
ALTER DEFAULT PRIVILEGES FOR ROLE syncserver_staging_migration IN SCHEMA public
  GRANT EXECUTE ON FUNCTIONS TO role_readonly;

-- Objects created by migration user → CRUD by readwrite
ALTER DEFAULT PRIVILEGES FOR ROLE syncserver_staging_migration IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO role_readwrite;
ALTER DEFAULT PRIVILEGES FOR ROLE syncserver_staging_migration IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO role_readwrite;
ALTER DEFAULT PRIVILEGES FOR ROLE syncserver_staging_migration IN SCHEMA public
  GRANT EXECUTE ON FUNCTIONS TO role_readwrite;

-- Objects created by migration user → full access by other migration users
ALTER DEFAULT PRIVILEGES FOR ROLE syncserver_staging_migration IN SCHEMA public
  GRANT ALL PRIVILEGES ON TABLES TO role_migration;
ALTER DEFAULT PRIVILEGES FOR ROLE syncserver_staging_migration IN SCHEMA public
  GRANT ALL PRIVILEGES ON SEQUENCES TO role_migration;
ALTER DEFAULT PRIVILEGES FOR ROLE syncserver_staging_migration IN SCHEMA public
  GRANT ALL PRIVILEGES ON FUNCTIONS TO role_migration;

-- =============================================================================
-- STEP 3: Create Application Users
-- =============================================================================

-- syncserver_staging_rw (sync-server ECS service)
CREATE USER syncserver_staging_rw WITH PASSWORD 'WaHm6T33JX8MSt7Pnta01eIfCS4U+y5zuVaH9NT4otE=';
GRANT role_readwrite TO syncserver_staging_rw;

-- syncsupervisor_staging_rw (sync-supervisor ECS service)
CREATE USER syncsupervisor_staging_rw WITH PASSWORD '+luB9cqUEHB3h3Q8snOZougNhIsy/YYd5fX6NdVAq94=';
GRANT role_readwrite TO syncsupervisor_staging_rw;

-- superset_staging_ro (Superset analytics)
CREATE USER superset_staging_ro WITH PASSWORD 't7FoqTeE1t1qKmzUO36XqHEMMzogrycbp1/8PdSe0UY=';
GRANT role_readonly TO superset_staging_ro;

-- ftpidentity_staging_ro (FTP Identity Provider Lambda)
CREATE USER ftpidentity_staging_ro WITH PASSWORD '/tN09t9kg+txK/DWgqYL5oZkrl6Aj2fsJQKh3YYr9FI=';
GRANT role_readonly TO ftpidentity_staging_ro;

-- =============================================================================
-- STEP 4: Verification
-- =============================================================================

-- Verify all users were created
SELECT
  rolname,
  rolcanlogin,
  CASE WHEN rolconnlimit = -1 THEN 'unlimited' ELSE rolconnlimit::text END as connection_limit
FROM pg_roles
WHERE rolname IN (
  'syncserver_staging_rw',
  'syncsupervisor_staging_rw',
  'superset_staging_ro',
  'ftpidentity_staging_ro',
  'syncserver_staging_migration'
)
ORDER BY rolname;

-- Verify role memberships
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
