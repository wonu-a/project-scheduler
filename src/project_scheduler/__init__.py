"""project-scheduler: a PySide6 critical-path project scheduler."""


def main() -> None:
    from .app import main as run

    raise SystemExit(run())
