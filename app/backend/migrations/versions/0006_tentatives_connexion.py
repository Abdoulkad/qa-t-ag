"""tentatives de connexion (RA-52)

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-21 17:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '0006'
down_revision: Union[str, Sequence[str], None] = '0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Nouvelle table seule : applicable sur une base contenant déjà des données."""
    op.create_table(
        'tentative_connexion',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=320), nullable=False),
        sa.Column('ip', sa.String(length=45), nullable=False),
        sa.Column('reussie', sa.Boolean(), nullable=False),
        sa.Column('horodatage', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_tentative_connexion_email'), 'tentative_connexion', ['email'])
    op.create_index(op.f('ix_tentative_connexion_ip'), 'tentative_connexion', ['ip'])
    op.create_index(op.f('ix_tentative_connexion_horodatage'), 'tentative_connexion',
                    ['horodatage'])


def downgrade() -> None:
    op.drop_index(op.f('ix_tentative_connexion_horodatage'), table_name='tentative_connexion')
    op.drop_index(op.f('ix_tentative_connexion_ip'), table_name='tentative_connexion')
    op.drop_index(op.f('ix_tentative_connexion_email'), table_name='tentative_connexion')
    op.drop_table('tentative_connexion')
