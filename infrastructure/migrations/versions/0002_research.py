"""Additive research jobs and evidence. Never changes Phase 1 tables."""
from alembic import op
import sqlalchemy as sa
revision='0002'
down_revision='0001'
branch_labels=None
depends_on=None

def col(name,type_,**kw): return sa.Column(name,type_,nullable=kw.pop('nullable',False),**kw)
def upgrade():
    op.create_table('research_jobs',col('id',sa.String(36),primary_key=True),sa.Column('project_id',sa.String(36),sa.ForeignKey('projects.id'),nullable=False),col('idempotency_key',sa.String(128)),col('kind',sa.String(20)),col('status',sa.String(20)),col('created_at',sa.Float),col('updated_at',sa.Float),col('deadline',sa.Float),col('owner',sa.String(36),nullable=True),col('cancel_requested',sa.Integer),col('input',sa.JSON),col('result',sa.JSON),col('error',sa.String(500),nullable=True),sa.UniqueConstraint('project_id','idempotency_key'))
    op.create_table('research_trials',col('id',sa.String(36),primary_key=True),sa.Column('job_id',sa.String(36),sa.ForeignKey('research_jobs.id'),nullable=False),sa.Column('project_id',sa.String(36),sa.ForeignKey('projects.id'),nullable=False),col('created_at',sa.Float),col('scenario',sa.JSON),col('variant',sa.String(20)),col('classification',sa.String(40)),col('signature',sa.String(64),nullable=True),col('cost_seconds',sa.Float),col('evidence',sa.JSON))
    op.create_table('research_findings',col('id',sa.String(36),primary_key=True),sa.Column('project_id',sa.String(36),sa.ForeignKey('projects.id'),nullable=False),col('signature',sa.String(64)),sa.Column('first_trial_id',sa.String(36),sa.ForeignKey('research_trials.id'),nullable=False),col('occurrences',sa.Integer),col('summary',sa.String(300)),sa.UniqueConstraint('project_id','signature'))
    op.create_table('research_decisions',col('id',sa.String(36),primary_key=True),sa.Column('job_id',sa.String(36),sa.ForeignKey('research_jobs.id'),nullable=False),col('step',sa.Integer),col('context',sa.JSON),col('scenario',sa.JSON),col('score',sa.Float),col('reward',sa.Float),col('cost_seconds',sa.Float))
    op.create_table('repair_candidates',col('id',sa.String(36),primary_key=True),sa.Column('project_id',sa.String(36),sa.ForeignKey('projects.id'),nullable=False),sa.Column('source_trial_id',sa.String(36),sa.ForeignKey('research_trials.id'),nullable=False),col('created_at',sa.Float),col('status',sa.String(40)),col('patch',sa.String(20000)),col('metadata',sa.JSON))
    op.create_table('research_artifacts',col('id',sa.String(36),primary_key=True),sa.Column('job_id',sa.String(36),sa.ForeignKey('research_jobs.id'),nullable=False),col('kind',sa.String(40)),col('created_at',sa.Float),col('sha256',sa.String(64)),col('payload',sa.JSON))
    op.bulk_insert(sa.table('sandbox_leases',sa.column('id',sa.String),sa.column('expires_at',sa.Float)),[{'id':'benchmark','expires_at':0}])
    for table,fields in {'research_jobs':['project_id','status'],'research_trials':['job_id','project_id','signature'],'research_findings':['project_id'],'research_decisions':['job_id'],'repair_candidates':['project_id'],'research_artifacts':['job_id']}.items():
        for field in fields: op.create_index('ix_'+table+'_'+field,table,[field])
def downgrade():
    op.execute(sa.text("DELETE FROM sandbox_leases WHERE id='benchmark'"))
    for table in ('research_artifacts','repair_candidates','research_decisions','research_findings','research_trials','research_jobs'): op.drop_table(table)
