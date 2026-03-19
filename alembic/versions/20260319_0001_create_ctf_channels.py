"""create ctf channels

Revision ID: 20260319_0001
Revises: 
Create Date: 2026-03-19 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260319_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("ctf_channels"):
        op.create_table(
            "ctf_channels",
            sa.Column("channel_id", sa.Integer(), primary_key=True),
            sa.Column("guild_id", sa.Integer(), nullable=False),
            sa.Column("channel_name", sa.Text(), nullable=False),
            sa.Column("start_time", sa.TIMESTAMP(), nullable=True),
            sa.Column("end_time", sa.TIMESTAMP(), nullable=True),
            sa.Column(
                "created_at",
                sa.TIMESTAMP(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )
        return

    columns = {column["name"] for column in inspector.get_columns("ctf_channels")}
    if "start_time" not in columns:
        op.add_column("ctf_channels", sa.Column("start_time", sa.TIMESTAMP(), nullable=True))
    if "end_time" not in columns:
        op.add_column("ctf_channels", sa.Column("end_time", sa.TIMESTAMP(), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("ctf_channels"):
        op.drop_table("ctf_channels")
