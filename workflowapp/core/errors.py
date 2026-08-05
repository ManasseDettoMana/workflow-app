"""The one exception type the core raises."""


class WorkflowAppError(Exception):
    """A failure the user needs to be told about, in words they can act on.

    The GUI prints ``str(exc)`` straight into a message box, so the message must
    read as a sentence and must not leak a path the user has no business seeing
    or a Python type name. ``hint`` carries the "what to do about it" half, which
    the dialog shows as informative text.

    Every failure path in ``core`` raises this and nothing else. PySide6 ends the
    process on an unhandled exception inside a slot, so an escaping ValueError is
    a crash where this is a message.
    """

    def __init__(self, message: str, hint: str | None = None):
        super().__init__(message)
        self.hint = hint

    def __str__(self) -> str:
        base = super().__str__()
        return f"{base}\n\n{self.hint}" if self.hint else base
