# Workflow App

Gestore personale di ticket e attivita per Windows. Un sistema di ticketing semplificato per
organizzare il proprio flusso di lavoro: ogni ticket ha un titolo, una descrizione, una scadenza,
uno stato con etichetta colorata e una lista di attivita da completare.

Applicazione locale e leggera. Nessun server, nessun database: i dati stanno in un file JSON in
`%APPDATA%\WorkflowApp\tickets.json`.

## Requisiti

- Windows
- Python 3.11 o superiore

## Installazione

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Avvio

```powershell
python -m workflowapp
```

## Funzionalita

- Elenco dei ticket con titolo, stato, scadenza e data di aggiornamento, ordinabile per colonna
- Creazione, modifica ed eliminazione dei ticket
- Stati con colore: Aperto, In Lavorazione, Fatto, Urgente
- Lista di attivita per ogni ticket, con spunta di completamento
- Scadenza facoltativa, con evidenziazione dei ticket scaduti
- Tema chiaro e scuro, con la preferenza ricordata tra un avvio e l'altro
- Salvataggio automatico a ogni modifica

## Sviluppo

Il codice, i commenti e la documentazione sono in inglese; tutti i testi mostrati all'utente sono
in italiano e stanno in `workflowapp/gui/strings.py`.

```powershell
python -m pip install -r requirements-dev.txt
.\tools\install-hooks.ps1          # una volta per clone
python -m ruff check .
python -m pytest -q
```

Vedere `CLAUDE.md` per l'architettura e gli invarianti, `PROGRESS.md` per lo stato di avanzamento
e `CONTRIBUTING.md` per il flusso di lavoro su Git.
