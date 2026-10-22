"""rapport de test rédigé par AG-11 et validé par l'humain (RA-66 à RA-68)

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-22 12:30:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '0009'
down_revision: Union[str, Sequence[str], None] = '0008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Nouvelle table seule : applicable sur une base contenant déjà des données."""
    op.create_table(
        'rapport_recette',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('mission_id', sa.Integer(), nullable=False),
        sa.Column('etat_agent', sa.String(length=20), nullable=True),
        sa.Column('erreur_agent', sa.Text(), nullable=True),
        sa.Column('ia', sa.String(length=120), nullable=True),
        sa.Column('proposition', sa.Text(), nullable=True),
        sa.Column('propose_le', sa.DateTime(timezone=True), nullable=True),
        sa.Column('redaction', sa.Text(), nullable=True),
        sa.Column('modifie_par_id', sa.Integer(), nullable=True),
        sa.Column('modifie_le', sa.DateTime(timezone=True), nullable=True),
        sa.Column('valide_par_id', sa.Integer(), nullable=True),
        sa.Column('valide_le', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['mission_id'], ['mission.id']),
        sa.ForeignKeyConstraint(['modifie_par_id'], ['utilisateur.id']),
        sa.ForeignKeyConstraint(['valide_par_id'], ['utilisateur.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('mission_id'),
    )


def downgrade() -> None:
    op.drop_table('rapport_recette')
