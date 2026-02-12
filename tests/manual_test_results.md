# Sync-Server Staging User Test Results

**Date:** 2026-02-11
**Database:** `postgres` on `sync-server-stg.cmal47k4rse1.us-west-2.rds.amazonaws.com`
**Schema:** `public`

## Test Summary

### Users Created

| Username | Role | Expected Permissions |
|----------|------|---------------------|
| `user_syncserver_staging_rw` | `role_readwrite` | SELECT, INSERT, UPDATE, DELETE |
| `user_syncsupervisor_staging_rw` | `role_readwrite` | SELECT, INSERT, UPDATE, DELETE |
| `user_superset_staging_ro` | `role_readonly` | SELECT only |
| `user_ftpidentity_staging_ro` | `role_readonly` | SELECT only |
| `user_syncserver_staging_migration` | `role_migration` | Full DDL (CREATE, DROP, ALTER) |

## Test Results

### ✓ TEST 1: Basic Connectivity
All 5 users can connect successfully.

- [x] user_syncserver_staging_rw
- [x] user_syncsupervisor_staging_rw
- [x] user_superset_staging_ro
- [x] user_ftpidentity_staging_ro
- [x] user_syncserver_staging_migration

### TEST 2: Readonly Users - SELECT Permission

#### user_superset_staging_ro
