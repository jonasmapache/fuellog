"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-09-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('app_settings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('default_language', sa.String(length=5), nullable=False),
    sa.Column('timezone', sa.String(length=64), nullable=False),
    sa.Column('currency_code', sa.String(length=8), nullable=False),
    sa.Column('currency_symbol', sa.String(length=8), nullable=False),
    sa.Column('currency_position', sa.String(length=6), nullable=False),
    sa.Column('default_fuel_type', sa.String(length=30), nullable=False),
    sa.Column('geocoding_enabled', sa.Boolean(), nullable=False),
    sa.Column('nominatim_url', sa.String(length=255), nullable=False),
    sa.Column('tile_url', sa.String(length=255), nullable=False),
    sa.Column('tile_attribution', sa.String(length=255), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('stations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=150), nullable=False),
    sa.Column('address', sa.String(length=300), nullable=True),
    sa.Column('lat', sa.Float(), nullable=True),
    sa.Column('lon', sa.Float(), nullable=True),
    sa.Column('usage_count', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=80), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('is_admin', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_users_username'), ['username'], unique=True)

    op.create_table('vehicles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=80), nullable=False),
    sa.Column('brand_model', sa.String(length=120), nullable=True),
    sa.Column('color', sa.String(length=20), nullable=False),
    sa.Column('photo_filename', sa.String(length=255), nullable=True),
    sa.Column('tank_capacity_l', sa.Float(), nullable=True),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('fuel_entries',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('vehicle_id', sa.Integer(), nullable=False),
    sa.Column('entry_type', sa.String(length=20), nullable=False),
    sa.Column('date', sa.Date(), nullable=False),
    sa.Column('liters', sa.Float(), nullable=True),
    sa.Column('price_per_liter', sa.Float(), nullable=True),
    sa.Column('total_cost', sa.Float(), nullable=True),
    sa.Column('odometer_km', sa.Float(), nullable=True),
    sa.Column('fuel_type', sa.String(length=30), nullable=True),
    sa.Column('full_tank', sa.Boolean(), nullable=False),
    sa.Column('station_id', sa.Integer(), nullable=True),
    sa.Column('computed_fields', sa.JSON(), nullable=False),
    sa.Column('estimated_fields', sa.JSON(), nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['station_id'], ['stations.id'], ),
    sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('fuel_entries')
    op.drop_table('vehicles')
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_users_username'))

    op.drop_table('users')
    op.drop_table('stations')
    op.drop_table('app_settings')
