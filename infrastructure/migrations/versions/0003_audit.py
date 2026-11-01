"""Durable sanitized administrative audit records."""
from alembic import op
import sqlalchemy as sa
revision='0003'
down_revision='0002'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('audit_events',sa.Column('id',sa.String(36),primary_key=True),sa.Column('created_at',sa.Float,nullable=False),sa.Column('actor_id',sa.String(64),nullable=False),sa.Column('role',sa.String(20),nullable=False),sa.Column('method',sa.String(8),nullable=False),sa.Column('route',sa.String(200),nullable=False),sa.Column('resource_id',sa.String(36)),sa.Column('status',sa.Integer,nullable=False),sa.Column('request_id',sa.String(36),nullable=False))
    op.create_index('ix_audit_events_created_at','audit_events',['created_at'])
    op.create_index('ix_audit_events_actor_id','audit_events',['actor_id'])
def downgrade(): op.drop_table('audit_events')
