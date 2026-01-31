"""Initial schema with PostGIS support

Revision ID: 001_initial
Revises: 
Create Date: 2026-01-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable PostGIS extension (idempotent - won't fail if already exists)
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
    
    # Create users table with geospatial support
    op.create_table(
        'users',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('google_id', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('picture', sa.String(), nullable=True),
        sa.Column('role', sa.String(), nullable=True),
        sa.Column('onboarded', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('location', Geometry(geometry_type='POINT', srid=4326), nullable=True),
        sa.Column('visibility_radius_meters', sa.Integer(), nullable=True, server_default='5000'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    
    # Create indexes (using IF NOT EXISTS for idempotency)
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_google_id ON users (google_id);")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email);")
    
    # Create spatial index on location (GIST index for PostGIS)
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_location ON users USING GIST (location);")
    
    # Create parents table
    op.create_table(
        'parents',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('children_ages', sa.String(), nullable=True),
        sa.Column('curriculum', sa.String(), nullable=True),
        sa.Column('religion', sa.String(), nullable=True),
        sa.Column('whatsapp_number', sa.String(), nullable=True),
        sa.Column('whatsapp_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('in_coop', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('coop_name', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_parents_user_id ON parents (user_id);")
    
    # Create tutors table
    op.create_table(
        'tutors',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('subjects', sa.String(), nullable=True),
        sa.Column('curriculum', sa.String(), nullable=True),
        sa.Column('certifications', sa.String(), nullable=True),
        sa.Column('availability', sa.String(), nullable=True),
        sa.Column('whatsapp_number', sa.String(), nullable=True),
        sa.Column('whatsapp_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('verification_status', sa.String(), nullable=False, server_default="'verified'"),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_tutors_user_id ON tutors (user_id);")


def downgrade() -> None:
    # Drop tables (in reverse order)
    op.drop_table('tutors')
    op.drop_table('parents')
    op.drop_table('users')
