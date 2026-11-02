"""Shared-runner allowlist: no HTTP fault services, chaos jobs or patch execution."""
import subprocess
import sys
SAFE_MODULES=['test_api.py','test_overview.py','test_invariants.py','test_migrations.py','test_secret_scan.py','test_security.py','test_study.py','test_operations.py','test_package_completeness.py','test_hosting.py','test_public_snapshot.py','test_frontend_demo.py']
SAFE_RESEARCH=' or '.join(['test_equal_budgets_reproducible_planner','test_reduction_and_flaky_rejection','test_patch_rejects_code_and_isolates','test_independent_verification_detects_regression','test_publication_fence_closes_check_write_race','test_model_proposals_reject_unknown_evidence','test_agent_auth_and_literal_patch_restrictions','test_agent_uses_fixed_limits_and_immutable_image','test_minimization_unknown_neighbors_do_not_prove_minimality'])
if __name__=='__main__':
    subprocess.run([sys.executable,'-m','pytest','-q',*[f'backend/tests/{name}' for name in SAFE_MODULES]],check=True)
    subprocess.run([sys.executable,'-m','pytest','-q','backend/tests/test_research.py','-k',SAFE_RESEARCH],check=True)
