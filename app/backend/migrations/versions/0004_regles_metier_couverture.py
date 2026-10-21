"""regles metier et couverture du texte d'origine

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-20 12:40:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0004'
down_revision: Union[str, Sequence[str], None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Règles métier séparées (RA-47) et couverture du texte d'origine (RA-48).
    Applicable sur une base contenant déjà des données."""
    op.create_table(
        'regle_metier',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('version_id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('texte', sa.Text(), nullable=False),
        sa.Column('sources', postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column('sources_rejetees', postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column('statut', sa.String(length=20), nullable=False),
        sa.CheckConstraint("statut IN ('SOURCE', 'HYPOTHESE')", name='ck_regle_statut'),
        sa.ForeignKeyConstraint(['version_id'], ['version_exigence.id'],
                                name='fk_regle_version'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('version_id', 'code', name='uq_regle_code'))
    op.create_index('ix_regle_metier_version_id', 'regle_metier', ['version_id'])
    op.create_table(
        'phrase_source',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('version_id', sa.Integer(), nullable=False),
        sa.Column('numero', sa.Integer(), nullable=False),
        sa.Column('texte', sa.Text(), nullable=False),
        sa.Column('titre', sa.Boolean(), nullable=False),
        sa.Column('motif_non_reprise', sa.Text(), nullable=True),
        sa.Column('justifie_par_id', sa.Integer(), nullable=True),
        sa.Column('justifie_le', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['version_id'], ['version_exigence.id'],
                                name='fk_phrase_version'),
        sa.ForeignKeyConstraint(['justifie_par_id'], ['utilisateur.id'],
                                name='fk_phrase_justifie_par'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('version_id', 'numero', name='uq_phrase_numero'))
    op.create_index('ix_phrase_source_version_id', 'phrase_source', ['version_id'])
    op.add_column('critere_acceptation', sa.Column(
        'regles', postgresql.ARRAY(sa.String(length=20)), nullable=False, server_default='{}'))


def downgrade() -> None:
    op.drop_column('critere_acceptation', 'regles')
    op.drop_index('ix_phrase_source_version_id', table_name='phrase_source')
    op.drop_table('phrase_source')
    op.drop_index('ix_regle_metier_version_id', table_name='regle_metier')
    op.drop_table('regle_metier')
