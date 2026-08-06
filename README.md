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

## Applicazione eseguibile

Per usare l'applicazione senza terminale e senza ambiente virtuale, si costruisce un eseguibile
Windows e si mette l'icona sul Desktop:

```powershell
python -m pip install -r requirements-build.txt
.\tools\build.ps1
.\tools\install-shortcut.ps1
```

Vengono prodotti due file:

| File | Quando usarlo |
| --- | --- |
| `dist\Workflow App\Workflow App.exe` | Uso quotidiano. Si apre subito. E questo il file a cui puntano i collegamenti sul Desktop e nel menu Start. |
| `dist\Workflow App portable.exe` | File unico da copiare su un altro computer. Non richiede installazione, ma impiega qualche secondo ad aprirsi ogni volta. |

Da quel momento basta fare doppio clic sull'icona "Workflow App" sul Desktop.

Due avvertenze:

- **Al primo avvio Windows mostra un avviso di sicurezza** ("Windows ha protetto il PC"), perche
  l'eseguibile non ha una firma digitale. Scegliere "Ulteriori informazioni" e poi "Esegui
  comunque". Succede una volta sola.
- **I collegamenti puntano alla cartella `dist\`** dov'e stata costruita. Spostando o cancellando
  quella cartella i collegamenti smettono di funzionare: in tal caso rieseguire
  `.\tools\install-shortcut.ps1`. Per rimuoverli, `.\tools\install-shortcut.ps1 -Remove`.

I ticket restano in `%APPDATA%\WorkflowApp\tickets.json` come sempre: l'eseguibile non scrive nulla
nella propria cartella, e usa gli stessi dati della versione avviata da Python.

## Funzionalita

- Elenco dei ticket con titolo, stato, scadenza e data di aggiornamento, ordinabile per colonna
- Creazione, modifica ed eliminazione dei ticket
- Stati con colore: Aperto, In Lavorazione, Fatto, Urgente
- Lista di attivita per ogni ticket, con spunta di completamento
- Scadenza facoltativa, con evidenziazione dei ticket scaduti
- Filtri per testo, per stato e per soli ticket in scadenza
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
