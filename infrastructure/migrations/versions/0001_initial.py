"""Initial Phase 1 schema."""
from alembic import op
import sqlalchemy as sa
revision="0001"
down_revision=None
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("projects",sa.Column("id",sa.String(36),primary_key=True),sa.Column("name",sa.String(120),nullable=False,unique=True),sa.Column("created_at",sa.Float,nullable=False))
    op.create_table("services",sa.Column("id",sa.String(36),primary_key=True),sa.Column("project_id",sa.String(36),sa.ForeignKey("projects.id"),nullable=False),sa.Column("name",sa.String(64),nullable=False),sa.Column("version",sa.String(128),nullable=False),sa.Column("operations",sa.JSON,nullable=False),sa.Column("resources",sa.JSON,nullable=False),sa.UniqueConstraint("project_id","name"))
    op.create_table("dependencies",sa.Column("id",sa.String(36),primary_key=True),sa.Column("project_id",sa.String(36),sa.ForeignKey("projects.id"),nullable=False),sa.Column("source_id",sa.String(36),sa.ForeignKey("services.id"),nullable=False),sa.Column("target_id",sa.String(36),sa.ForeignKey("services.id"),nullable=False),sa.Column("kind",sa.String(32),nullable=False),sa.Column("operation",sa.String(160),nullable=False),sa.Column("workflow",sa.String(80),nullable=False))
    op.create_table("invariants",sa.Column("id",sa.String(36),primary_key=True),sa.Column("project_id",sa.String(36),sa.ForeignKey("projects.id"),nullable=False),sa.Column("name",sa.String(120),nullable=False),sa.Column("rule",sa.JSON,nullable=False))
    op.create_table("experiments",sa.Column("id",sa.String(36),primary_key=True),sa.Column("project_id",sa.String(36),sa.ForeignKey("projects.id"),nullable=False),sa.Column("name",sa.String(120),nullable=False),sa.Column("config",sa.JSON,nullable=False))
    op.create_table("runs",sa.Column("id",sa.String(36),primary_key=True),sa.Column("experiment_id",sa.String(36),sa.ForeignKey("experiments.id"),nullable=False),sa.Column("idempotency_key",sa.String(128),nullable=False),sa.Column("status",sa.String(20),nullable=False),sa.Column("created_at",sa.Float,nullable=False),sa.Column("updated_at",sa.Float,nullable=False),sa.Column("deadline",sa.Float,nullable=False),sa.Column("lease_until",sa.Float,nullable=False),sa.Column("owner",sa.String(36)),sa.Column("cancel_requested",sa.Integer,nullable=False),sa.Column("config",sa.JSON,nullable=False),sa.Column("result",sa.JSON,nullable=False),sa.UniqueConstraint("experiment_id","idempotency_key"))
    op.create_index("ix_runs_status","runs",["status"])
    op.create_table("sandbox_leases",sa.Column("id",sa.String(64),primary_key=True),sa.Column("run_id",sa.String(36)),sa.Column("expires_at",sa.Float,nullable=False))
    op.bulk_insert(sa.table("sandbox_leases",sa.column("id",sa.String),sa.column("expires_at",sa.Float)),[{"id":"demo","expires_at":0}])
    op.create_table("artifacts",sa.Column("id",sa.String(36),primary_key=True),sa.Column("run_id",sa.String(36),sa.ForeignKey("runs.id"),nullable=False),sa.Column("kind",sa.String(40),nullable=False),sa.Column("created_at",sa.Float,nullable=False),sa.Column("sha256",sa.String(64),nullable=False),sa.Column("payload",sa.JSON,nullable=False))
    op.create_index("ix_artifacts_run_id","artifacts",["run_id"])
    op.create_table("findings",sa.Column("id",sa.String(36),primary_key=True),sa.Column("run_id",sa.String(36),sa.ForeignKey("runs.id"),nullable=False),sa.Column("invariant_id",sa.String(36),sa.ForeignKey("invariants.id"),nullable=False),sa.Column("summary",sa.String(300),nullable=False),sa.Column("evidence",sa.JSON,nullable=False))
    op.create_index("ix_findings_run_id","findings",["run_id"])

def downgrade():
    for table in ("findings","artifacts","sandbox_leases","runs","experiments","invariants","dependencies","services","projects"):
        op.drop_table(table)
