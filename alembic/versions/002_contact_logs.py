"""Add contact logs table

Revision ID: 002_contact_logs
Revises: 001_initial
Create Date: 2026-02-01

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = '002_contact_logs'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'contact_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('source_user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('target_user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('contact_method', sa.String(), nullable=False, server_default='whatsapp'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    
    op.execute("CREATE INDEX IF NOT EXISTS ix_contact_logs_source ON contact_logs (source_user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_contact_logs_target ON contact_logs (target_user_id);")


def downgrade() -> None:
    op.drop_table('contact_logs')
