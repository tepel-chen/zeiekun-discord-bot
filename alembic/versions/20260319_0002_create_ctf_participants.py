"""create ctf participants and team settings

Revision ID: 20260319_0002
Revises: 20260319_0001
Create Date: 2026-03-19 00:10:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260319_0002"
down_revision = "20260319_0001"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("ctf_participants"):
        op.create_table(
            "ctf_participants",
            sa.Column("channel_id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), primary_key=True),
            sa.Column("participation_type", sa.Text(), nullable=False),
            sa.Column(
                "joined_at",
                sa.TIMESTAMP(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )

    columns = {column["name"] for column in inspector.get_columns("ctf_channels")}
    if "root_channel_id" not in columns:
        op.add_column("ctf_channels", sa.Column("root_channel_id", sa.Integer(), nullable=True))
        bind.execute(sa.text("UPDATE ctf_channels SET root_channel_id = channel_id WHERE root_channel_id IS NULL"))
    if "team_type" not in columns:
        op.add_column("ctf_channels", sa.Column("team_type", sa.Text(), nullable=True))
        bind.execute(sa.text("UPDATE ctf_channels SET team_type = 'all' WHERE team_type IS NULL"))
    if "split_completed" not in columns:
        op.add_column("ctf_channels", sa.Column("split_completed", sa.Integer(), nullable=True))
        bind.execute(sa.text("UPDATE ctf_channels SET split_completed = 0 WHERE split_completed IS NULL"))
    if "team_mode" not in columns:
        op.add_column("ctf_channels", sa.Column("team_mode", sa.Text(), nullable=True))
        bind.execute(sa.text("UPDATE ctf_channels SET team_mode = 'auto' WHERE team_mode IS NULL"))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("ctf_participants"):
        op.drop_table("ctf_participants")
