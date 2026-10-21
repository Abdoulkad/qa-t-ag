@echo off
rem Sauvegarde de la base QA-T-AG (RA-54), pour le Planificateur de taches Windows.
rem Le resultat de chaque execution est ajoute a sauvegarde.log, dans ce dossier.
cd /d "%~dp0"
".venv\Scripts\python.exe" -m qatag.sauvegarde >> "%~dp0sauvegarde.log" 2>&1
