**Role:** You are an expert Python desktop application developer, specialized in building lightweight, functional apps with a professional UI for Windows.

**Context:**
- **User:** Single end user (the user themselves).
- **Platform:** Windows (with the possibility of extending to cross-platform in the future).
- **Purpose:** Build a lightweight desktop application for personal work-workflow management, similar to a simplified ticketing system.
- **Non-Functional Requirements:**
  - Lightweight app, to be run locally.
  - Professional, clean UI, no emoji.
  - Interface and texts entirely in Italian.
  - Data persistence without a database server (use a local file).
  - Code managed through a private Git repository on GitHub.

**Detailed Instructions:**

**Phase 1: Setup and Architecture**
1.  Create a private Git repository on GitHub with an appropriate name (e.g. `workflow-ticket-manager`). Initialize it with a README, a `.gitignore` file for Python and a `requirements.txt` file.
2.  Define the project structure. Example:
    ```
    workflow_app/
    ├── src/
    │   ├── models/          # Data models (Ticket, Activity)
    │   ├── data/            # Persistence handling (JSON manager)
    │   ├── ui/              # Interface components (windows, widgets)
    │   ├── core/            # Business logic and controllers
    │   └── themes/          # CSS/style files for light/dark theme
    ├── docs/                # Context and prompt files
    ├── tests/               # Unit tests (optional but recommended)
    ├── main.py              # App entry point
    └── requirements.txt
    ```
3.  Choose and configure the GUI framework. **Recommendation: use PySide6 (Qt for Python)** for a professional, modern UI. Add `pyside6` to `requirements.txt`.
4.  Create a `docs/context.txt` file describing the whole project, the technology stack, architectural decisions and user requirements.
5.  Create a `docs/todo.md` file with an updatable task list, structured by phases (Setup, Backend, UI, Integration, Testing). Use `- [ ]` checkboxes.

**Phase 2: Data Model and Persistence**
1.  Design the Python classes in `src/models/`:
    - `Ticket`: Attributes: `id` (unique), `titolo` (title), `descrizione` (description), `data_apertura` (opening date), `data_aggiornamento` (update date), `data_scadenza` (due date), `stato` (status, to be linked to colored tags), `lista_attivita` (list of `Attivita` objects).
    - `Attivita` (Activity): Attributes: `id`, `descrizione` (description), `completata` (completed, bool).
2.  Create a `src/data/json_manager.py` module that handles saving and loading a list of `Ticket` objects to/from a `tickets.json` file in the user folder (e.g. `%APPDATA%/WorkflowApp`). It must provide functions such as `load_tickets()`, `save_tickets(lista_ticket)`.
3.  Implement the logic to generate unique IDs and to handle dates.

**Phase 3: Business Logic (Core)**
1.  Create a `src/core/ticket_manager.py` module acting as the intermediary between UI and data. It must hold the in-memory "ticket list" and methods to:
    - Add, update, delete a ticket.
    - Add/remove/update activities within a ticket.
    - Change a ticket's status (e.g. "Aperto" / Open, "In Lavorazione" / In Progress, "Fatto" / Done, "Urgente" / Urgent).
    - Filter/sort tickets (by date, status, etc.).
2.  Connect this manager to the `json_manager` for automatic saving on every change.

**Phase 4: User Interface (UI) with PySide6**
1.  **Main Window (Home):** Create a window (`MainWindow`) with:
    - A toolbar or menu with buttons: "Nuovo Ticket" (New Ticket), "Toggle Tema Chiaro/Scuro" (Toggle Light/Dark Theme).
    - A main list/table (`QTableWidget` or `QListView`) showing all ticket cards/rows. Each row must show: **Ticket Title**, **Status** (with a visual colored tag), **Due Date**.
    - Double-clicking a row opens the detail window for that ticket.
    - A "Elimina" (Delete) button for the selected item in the toolbar.
2.  **Ticket Detail Window:** Create a dialog window (`QDialog`) that opens when a ticket is selected. It must contain:
    - Editable fields for: Title, Description (text area), Due Date (`QDateEdit`).
    - A section for the activities "Todo List": a list of activities with checkboxes (`QCheckBox`) to mark them as completed, plus "+" and "-" buttons to add and remove them.
    - **Status** selection via `QComboBox` with the options: "Aperto", "In Lavorazione", "Fatto", "Urgente". Each option must have an associated color displayed in the UI (e.g. a colored circle next to the text).
    - "Salva Modifiche" (Save Changes) and "Annulla" (Cancel) buttons.
3.  **Create New Ticket Window:** Similar to the detail window, but with empty fields.
4.  **Light/Dark Theme:** Implement a theming system using Qt style sheets (`QSS`). Create two `.qss` files in `src/themes/` (`light_theme.qss`, `dark_theme.qss`). The toolbar button must switch between the two themes and save the preference in the user settings (`QSettings`).

**Phase 5: Integration and Wiring**
1.  Connect the `MainWindow` to the `ticket_manager`. On startup, load the tickets from the JSON file and populate the list.
2.  Connect every user action (create, edit, delete, change status) to the corresponding `ticket_manager` functions, making sure the data is saved to file after every change.
3.  Implement the logic to automatically update the ticket's update date whenever it is modified.

**Phase 6: Testing and Polishing**
1.  Test all CRUD functionality.
2.  Verify that saving to and loading from JSON work correctly, including after restarting the app.
3.  Make sure the UI is responsive and that all texts are in Italian.
4.  Optimize the code for clarity and maintainability.

**Format and Conventions:**
- **Language:** All code (comments, docstrings), UI texts and documentation must be **in Italian**.
- **Support Files:** The files in `docs/` (`context.txt`, `todo.md`, `prompt_*.md`) must be written in a clear, structured way and optimized to be read and interpreted by an AI such as Claude Code, to make resuming work in future sessions easier.
- **UI Style:** Clean, modern, with consistent spacing. Use professional color palettes (e.g. blue/gray for the light theme, dark gray with blue accents for the dark theme). Status "tags" must use intuitive colors (e.g. Red for "Urgente", Green for "Fatto", Yellow for "In Lavorazione", Blue for "Aperto").
- **Versioning:** Make atomic Git commits for each significant feature or fix, with clear messages in Italian.

**Expected Final Output:**
A working desktop application, with well-organized source code, internal documentation, an active Git repository and context files ready for iterative development sessions.
