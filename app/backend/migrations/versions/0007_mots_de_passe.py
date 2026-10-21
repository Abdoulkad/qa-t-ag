"""mots de passe provisoires et version de session (RA-55 à RA-58)

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-21 18:40:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '0007'
down_revision: Union[str, Sequence[str], None] = '0006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Applicable sur une base contenant déjà des données : les comptes existants
    gardent leur mot de passe (non provisoire) et leurs sessions (version 0)."""
    op.add_column('utilisateur', sa.Column('mot_de_passe_provisoire', sa.Boolean(),
                                           server_default='false', nullable=False))
    op.add_column('utilisateur', sa.Column('version_session', sa.Integer(),
                                           server_default='0', nullable=False))


def downgrade() -> None:
    op.drop_column('utilisateur', 'version_session')
    op.drop_column('utilisateur', 'mot_de_passe_provisoire')
