"""Every string the user reads, in Italian.

One file, so that "is the whole interface actually Italian?" is a question with
an answer rather than a search. A literal Italian string among the widgets is a
bug; import it from here instead.

The single exception is the message carried by a ``WorkflowAppError``, which is
written in Italian where it is raised inside ``core``. See invariant 9 in
CLAUDE.md for why.

No emojis, anywhere.
"""

from __future__ import annotations

from workflowapp.core.models import Status

# Application ------------------------------------------------------------

APP_NAME = "Workflow App"
ORGANISATION = "ManasseDettoMana"

# Status -----------------------------------------------------------------

#: The Italian label for each stored status token. The tokens themselves stay in
#: the file and never appear on screen.
STATUS_LABELS: dict[Status, str] = {
    Status.OPEN: "Aperto",
    Status.IN_PROGRESS: "In Lavorazione",
    Status.DONE: "Fatto",
    Status.URGENT: "Urgente",
}

# Main window ------------------------------------------------------------

WINDOW_TITLE = APP_NAME

ACTION_NEW = "Nuovo Ticket"
ACTION_NEW_TIP = "Crea un nuovo ticket (Ctrl+N)"
ACTION_EDIT = "Modifica"
ACTION_EDIT_TIP = "Apri il ticket selezionato (Invio)"
ACTION_DELETE = "Elimina"
ACTION_DELETE_TIP = "Elimina il ticket selezionato (Canc)"
ACTION_THEME = "Tema"
ACTION_THEME_TIP = "Alterna il tema chiaro e scuro"

FILTER_LABEL = "Filtra:"
FILTER_PLACEHOLDER = "Cerca per titolo o descrizione"
FILTER_ALL_STATUSES = "Tutti gli stati"
FILTER_OVERDUE_ONLY = "Solo in scadenza"

COLUMN_TITLE = "Titolo"
COLUMN_STATUS = "Stato"
COLUMN_DUE_DATE = "Scadenza"
COLUMN_ACTIVITIES = "Attività"
COLUMN_UPDATED = "Aggiornato"

NO_DUE_DATE = "—"
EMPTY_LIST = "Nessun ticket. Usa \"Nuovo Ticket\" per crearne uno."
EMPTY_FILTER = "Nessun ticket corrisponde al filtro."

#: Shown in the status bar. Positional so the numbers read naturally in Italian.
STATUS_BAR_COUNT = "{visibili} ticket visualizzati su {totali}"
STATUS_BAR_OVERDUE = "{scaduti} in ritardo"

TOOLTIP_OVERDUE = "Scaduto"

# Ticket dialog ----------------------------------------------------------

DIALOG_NEW_TITLE = "Nuovo Ticket"
DIALOG_EDIT_TITLE = "Dettaglio Ticket"

FIELD_TITLE = "Titolo:"
FIELD_DESCRIPTION = "Descrizione:"
FIELD_STATUS = "Stato:"
FIELD_DUE_DATE = "Scadenza:"
FIELD_NO_DUE_DATE = "Senza scadenza"
FIELD_ACTIVITIES = "Attività:"

ACTIVITY_ADD = "+"
ACTIVITY_ADD_TIP = "Aggiungi un'attività"
ACTIVITY_REMOVE = "-"
ACTIVITY_REMOVE_TIP = "Rimuovi l'attività selezionata"
ACTIVITY_PLACEHOLDER = "Nuova attività"
ACTIVITY_NEW_TEXT = "Nuova attività"
ACTIVITY_COUNT = "{completate} di {totali} completate"

BUTTON_SAVE = "Salva Modifiche"
BUTTON_CANCEL = "Annulla"

META_CREATED = "Aperto il {data}"
META_UPDATED = "Aggiornato il {data}"

# Messages ---------------------------------------------------------------

CONFIRM_DELETE_TITLE = "Eliminare il ticket?"
CONFIRM_DELETE_TEXT = "Il ticket \"{titolo}\" verrà eliminato definitivamente."
CONFIRM_DELETE_HINT = "L'operazione non può essere annullata."

CONFIRM_DISCARD_TITLE = "Annullare le modifiche?"
CONFIRM_DISCARD_TEXT = "Le modifiche non salvate andranno perse."

BUTTON_YES_DELETE = "Elimina"
BUTTON_YES_DISCARD = "Annulla le modifiche"
BUTTON_NO = "Torna indietro"

ERROR_TITLE = "Errore"
ERROR_STARTUP_TITLE = "Impossibile avviare l'applicazione"
ERROR_TITLE_REQUIRED = "Il titolo è obbligatorio."
ERROR_TITLE_REQUIRED_HINT = "Inserire un titolo per il ticket."

# Date presentation ------------------------------------------------------

#: Qt date format. dd/MM/yyyy is what an Italian user expects to read and type.
DATE_FORMAT = "dd/MM/yyyy"
#: Python strftime equivalent, for text built outside a Qt date widget.
DATE_FORMAT_PY = "%d/%m/%Y"
DATETIME_FORMAT_PY = "%d/%m/%Y %H:%M"


def status_label(status: Status) -> str:
    return STATUS_LABELS[status]
