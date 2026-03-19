"""add disclosed flag to ctf channels

Revision ID: 20260319_0004
Revises: 20260319_0003
Create Date: 2026-03-19 02:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260319_0004"
down_revision = "20260319_0003"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("ctf_channels")}
    if "disclosed" not in columns:
        op.add_column("ctf_channels", sa.Column("disclosed", sa.Integer(), nullable=True))
        bind.execute(sa.text("UPDATE ctf_channels SET disclosed = 0 WHERE disclosed IS NULL"))


def downgrade():
    pass
