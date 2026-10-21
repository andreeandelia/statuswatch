from app.db import Database


def update_incidents(
    db: Database, service: str, failure_threshold: int = 3
) -> str | None:
    """Actualizează incidentele pentru un serviciu, după o verificare nouă.

    Returnează "opened", "resolved" sau None. Valoarea va fi folosită
    la pasul următor pentru alerte.
    """
    recent = db.recent(service, failure_threshold)  # cele mai noi primele
    if not recent:
        return None

    open_incident = db.get_open_incident(service)
    newest = recent[0]

    if open_incident is None:
        enough = len(recent) == failure_threshold
        if enough and all(not r["ok"] for r in recent):
            db.open_incident(service, started_at=recent[-1]["ts"])
            return "opened"
        return None

    if newest["ok"]:
        db.close_incident(open_incident["id"], resolved_at=newest["ts"])
        return "resolved"
    return None