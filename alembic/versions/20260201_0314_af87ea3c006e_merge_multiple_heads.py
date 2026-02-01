"""Merge multiple heads

Revision ID: af87ea3c006e
Revises: 002_contact_logs, c72907111232
Create Date: 2026-02-01 03:14:10.270689+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'af87ea3c006e'
down_revision = ('002_contact_logs', 'c72907111232')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
