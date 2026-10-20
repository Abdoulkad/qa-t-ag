"""revue AG-01 v2 (QA-REV-02) : constat, criticite motivee, validation humaine

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-20 13:50:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '0005'
down_revision: Union[str, Sequence[str], None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Applicable sur une base contenant déjà des données : tous les ajouts sont
    facultatifs ou ont une valeur par défaut ; les précisions humaines existantes
    sont reclassées PRECISION."""
    for nom, type_ in (('constat', sa.Text()), ('justification', sa.Text()),
                       ('validation', sa.String(length=20)), ('motif_validation', sa.Text()),
                       ('gravite_initiale', sa.String(length=20)),
                       ('motif_requalification', sa.Text()),
                       ('valide_par_id', sa.Integer()),
                       ('valide_le', sa.DateTime(timezone=True))):
        op.add_column('defaut', sa.Column(nom, type_, nullable=True))
    op.create_foreign_key('fk_defaut_valide_par', 'defaut', 'utilisateur',
                          ['valide_par_id'], ['id'])
    op.create_check_constraint('ck_defaut_validation', 'defaut',
                               "validation IS NULL OR validation IN ('CONFIRME', 'ECARTE')")
    op.add_column('question_metier', sa.Column('nature', sa.String(length=20), nullable=False,
                                               server_default='DEFAUT'))
    op.add_column('question_metier', sa.Column('sujet', sa.Text(), nullable=True))
    op.add_column('question_metier', sa.Column('pourquoi', sa.Text(), nullable=True))
    op.execute("UPDATE question_metier SET nature = 'PRECISION' WHERE ajoutee_par_id IS NOT NULL")
    op.create_check_constraint('ck_question_nature', 'question_metier',
                               "nature IN ('DEFAUT', 'COMPLEMENTAIRE', 'PRECISION')")


def downgrade() -> None:
    op.drop_constraint('ck_question_nature', 'question_metier', type_='check')
    for nom in ('pourquoi', 'sujet', 'nature'):
        op.drop_column('question_metier', nom)
    op.drop_constraint('ck_defaut_validation', 'defaut', type_='check')
    op.drop_constraint('fk_defaut_valide_par', 'defaut', type_='foreignkey')
    for nom in ('valide_le', 'valide_par_id', 'motif_requalification', 'gravite_initiale',
                'motif_validation', 'validation', 'justification', 'constat'):
        op.drop_column('defaut', nom)
