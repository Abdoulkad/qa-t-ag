"""recette : preuves en base, anomalies qualifiées (AG-09), clôture (lot 3)

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-22 10:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '0008'
down_revision: Union[str, Sequence[str], None] = '0007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

STATUTS = "statut IN ('OUVERTE', 'CORRIGEE', 'FERMEE', 'REJETEE')"
GRAVITES = "gravite IS NULL OR gravite IN ('Bloquante', 'Critique', 'Majeure', 'Mineure')"


def upgrade() -> None:
    """Applicable sur une base existante : la recette n'avait encore aucune route,
    les tables execution, preuve et anomalie sont vides en pratique ; les ajouts
    sont facultatifs ou ont une valeur par défaut."""
    # Preuves : contenu en base (RA-31 modifiée), nom d'origine
    op.add_column('preuve', sa.Column('nom', sa.String(length=255), server_default='',
                                      nullable=False))
    op.add_column('preuve', sa.Column('contenu', sa.LargeBinary(), nullable=True))
    op.alter_column('preuve', 'chemin', existing_type=sa.Text(), nullable=True)

    # Anomalies
    for nom, type_ in (('mission_id', sa.Integer()), ('code', sa.String(length=20)),
                       ('reproductibilite', sa.String(length=30)),
                       ('etat_agent', sa.String(length=20)),
                       ('gravite_proposee', sa.String(length=20)),
                       ('reproductibilite_proposee', sa.String(length=30)),
                       ('titre_propose', sa.Text()), ('justification_agent', sa.Text()),
                       ('erreur_agent', sa.Text()), ('qualifie_par_id', sa.Integer()),
                       ('qualifie_le', sa.DateTime(timezone=True)),
                       ('motif_requalification', sa.Text()), ('motif_statut', sa.Text()),
                       ('cree_par_id', sa.Integer()),
                       ('corrigee_le', sa.DateTime(timezone=True)),
                       ('fermee_le', sa.DateTime(timezone=True)),
                       ('execution_fermeture_id', sa.Integer())):
        op.add_column('anomalie', sa.Column(nom, type_, nullable=True))
    op.add_column('anomalie', sa.Column('titre', sa.Text(), server_default='', nullable=False))
    op.alter_column('anomalie', 'gravite', existing_type=sa.String(length=20), nullable=True)
    op.create_index(op.f('ix_anomalie_mission_id'), 'anomalie', ['mission_id'])
    op.create_foreign_key('fk_anomalie_mission', 'anomalie', 'mission', ['mission_id'], ['id'])
    op.create_foreign_key('fk_anomalie_qualifie_par', 'anomalie', 'utilisateur',
                          ['qualifie_par_id'], ['id'])
    op.create_foreign_key('fk_anomalie_cree_par', 'anomalie', 'utilisateur',
                          ['cree_par_id'], ['id'])
    op.create_foreign_key('fk_anomalie_execution_fermeture', 'anomalie', 'execution',
                          ['execution_fermeture_id'], ['id'])
    op.create_unique_constraint('uq_anomalie_code', 'anomalie', ['mission_id', 'code'])
    op.create_check_constraint('ck_anomalie_statut', 'anomalie', STATUTS)
    op.create_check_constraint('ck_anomalie_gravite', 'anomalie', GRAVITES)

    # Tâche IA visant un autre objet que la version (AG-09 : une anomalie)
    op.add_column('tache_ia', sa.Column('cible_id', sa.Integer(), nullable=True))

    # Clôture de la recette (RA-63)
    op.create_table(
        'cloture_recette',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('mission_id', sa.Integer(), nullable=False),
        sa.Column('version_id', sa.Integer(), nullable=False),
        sa.Column('decision', sa.String(length=30), nullable=False),
        sa.Column('commentaire', sa.Text(), nullable=False),
        sa.Column('reserves', sa.Text(), nullable=False),
        sa.Column('decideur_id', sa.Integer(), nullable=False),
        sa.Column('auto_validation', sa.Boolean(), nullable=False),
        sa.Column('decide_le', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("decision IN ('CLOTURE', 'CLOTURE_AVEC_RESERVES')",
                           name='ck_cloture_decision'),
        sa.ForeignKeyConstraint(['decideur_id'], ['utilisateur.id']),
        sa.ForeignKeyConstraint(['mission_id'], ['mission.id']),
        sa.ForeignKeyConstraint(['version_id'], ['version_exigence.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('mission_id'),
    )


def downgrade() -> None:
    op.drop_table('cloture_recette')
    op.drop_column('tache_ia', 'cible_id')
    op.drop_constraint('ck_anomalie_gravite', 'anomalie', type_='check')
    op.drop_constraint('ck_anomalie_statut', 'anomalie', type_='check')
    op.drop_constraint('uq_anomalie_code', 'anomalie', type_='unique')
    for fk in ('fk_anomalie_execution_fermeture', 'fk_anomalie_cree_par',
               'fk_anomalie_qualifie_par', 'fk_anomalie_mission'):
        op.drop_constraint(fk, 'anomalie', type_='foreignkey')
    op.drop_index(op.f('ix_anomalie_mission_id'), table_name='anomalie')
    op.execute("UPDATE anomalie SET gravite = 'Majeure' WHERE gravite IS NULL")
    op.alter_column('anomalie', 'gravite', existing_type=sa.String(length=20), nullable=False)
    op.drop_column('anomalie', 'titre')
    for nom in ('execution_fermeture_id', 'fermee_le', 'corrigee_le', 'cree_par_id',
                'motif_statut', 'motif_requalification', 'qualifie_le', 'qualifie_par_id',
                'erreur_agent', 'justification_agent', 'titre_propose',
                'reproductibilite_proposee', 'gravite_proposee', 'etat_agent',
                'reproductibilite', 'code', 'mission_id'):
        op.drop_column('anomalie', nom)
    op.execute("DELETE FROM preuve WHERE chemin IS NULL")
    op.alter_column('preuve', 'chemin', existing_type=sa.Text(), nullable=False)
    op.drop_column('preuve', 'contenu')
    op.drop_column('preuve', 'nom')
