"""clarification reecriture conception

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-19 12:23:46.404107

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema. Les valeurs par défaut serveur permettent d'appliquer
    la migration sur une base qui contient déjà des données du lot 1."""
    op.add_column('cas_test', sa.Column('motif_statut', sa.Text(), nullable=False,
                                        server_default=''))
    op.add_column('cas_test', sa.Column('confirme_par_id', sa.Integer(), nullable=True))
    op.create_unique_constraint('uq_cas_code', 'cas_test', ['version_id', 'code'])
    op.create_foreign_key('fk_cas_test_confirme_par', 'cas_test', 'utilisateur',
                          ['confirme_par_id'], ['id'])
    op.add_column('critere_acceptation', sa.Column(
        'sources_rejetees', postgresql.ARRAY(sa.Text()), nullable=False, server_default='{}'))
    op.add_column('question_metier', sa.Column('code', sa.String(length=10), nullable=True))
    # Questions existantes : Q-1, Q-2… dans l'ordre de création, par version
    op.execute("""
        UPDATE question_metier q SET code = 'Q-' || n.rang
        FROM (SELECT id, row_number() OVER (PARTITION BY version_id ORDER BY id) AS rang
              FROM question_metier) n
        WHERE q.id = n.id
    """)
    op.alter_column('question_metier', 'code', nullable=False)
    op.add_column('question_metier', sa.Column('ajoutee_par_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_question_ajoutee_par', 'question_metier', 'utilisateur',
                          ['ajoutee_par_id'], ['id'])
    op.add_column('version_exigence', sa.Column('controle_reecriture', sa.Text(), nullable=True))
    op.add_column('version_exigence', sa.Column('controle_conception', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('version_exigence', 'controle_conception')
    op.drop_column('version_exigence', 'controle_reecriture')
    op.drop_constraint('fk_question_ajoutee_par', 'question_metier', type_='foreignkey')
    op.drop_column('question_metier', 'ajoutee_par_id')
    op.drop_column('question_metier', 'code')
    op.drop_column('critere_acceptation', 'sources_rejetees')
    op.drop_constraint('fk_cas_test_confirme_par', 'cas_test', type_='foreignkey')
    op.drop_constraint('uq_cas_code', 'cas_test', type_='unique')
    op.drop_column('cas_test', 'confirme_par_id')
    op.drop_column('cas_test', 'motif_statut')
