"""decisions questions points ouverts

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-19 18:25:27.514356

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0003'
down_revision: Union[str, Sequence[str], None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Décisions humaines sur les questions (RA-42) et points ouverts (RA-43).
    Applicable sur une base contenant déjà des données."""
    op.add_column('question_metier', sa.Column('decision', sa.String(length=20), nullable=True))
    op.add_column('question_metier', sa.Column('motif_decision', sa.Text(), nullable=True))
    op.add_column('question_metier', sa.Column('decide_par_id', sa.Integer(), nullable=True))
    op.add_column('question_metier', sa.Column('decide_le', sa.DateTime(timezone=True),
                                               nullable=True))
    op.create_foreign_key('fk_question_decide_par', 'question_metier', 'utilisateur',
                          ['decide_par_id'], ['id'])
    op.create_check_constraint(
        'ck_question_decision', 'question_metier',
        "decision IS NULL OR decision IN ('HORS_PERIMETRE', 'REPORTEE')")
    op.add_column('version_exigence', sa.Column(
        'points_ouverts', postgresql.ARRAY(sa.Text()), nullable=False, server_default='{}'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('version_exigence', 'points_ouverts')
    op.drop_constraint('ck_question_decision', 'question_metier', type_='check')
    op.drop_constraint('fk_question_decide_par', 'question_metier', type_='foreignkey')
    op.drop_column('question_metier', 'decide_le')
    op.drop_column('question_metier', 'decide_par_id')
    op.drop_column('question_metier', 'motif_decision')
    op.drop_column('question_metier', 'decision')
