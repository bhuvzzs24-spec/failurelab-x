-- OPERATOR REVIEW REQUIRED. Run against the private metadata DB after migrations.
-- Set passwords via your secret manager/provider; none are defined in this file.
-- Role creation requires provider administration and is not run by the app.
CREATE ROLE failurelab_api LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE ROLE failurelab_worker LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE ROLE failurelab_reader LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
GRANT USAGE ON SCHEMA public TO failurelab_api, failurelab_worker, failurelab_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO failurelab_api, failurelab_worker, failurelab_reader;
GRANT INSERT,UPDATE ON projects,services,dependencies,invariants,experiments,runs,research_jobs,audit_events TO failurelab_api;
GRANT INSERT,UPDATE ON runs,sandbox_leases,artifacts,findings,research_jobs,research_trials,research_findings,research_decisions,research_artifacts,repair_candidates TO failurelab_worker;
-- Reader is SELECT-only. Use it only on an approved, separate snapshot DB for public demos.
-- Reapply grants after future migrations; migration credentials are never runtime credentials.
