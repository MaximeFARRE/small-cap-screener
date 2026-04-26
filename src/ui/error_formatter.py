from __future__ import annotations

"""User-facing error message formatting for the UI layer.

All functions in this module produce clean, French-language messages
suitable for display in dialogs and status bars. Raw provider exception
text is never shown to the user — technical details stay in logs only.
"""

_KIND_MESSAGES: dict[str, str] = {
    "not_found": "Le ticker est introuvable chez le fournisseur de données.",
    "provider_error": "Le fournisseur de données est temporairement indisponible. Réessayez dans quelques instants.",
    "data_inconsistent": "Les données reçues sont incohérentes. Vérifiez le ticker ou réessayez.",
}

_STAGE_FALLBACK_MESSAGES: dict[str, str] = {
    "validate": "Les données ne respectent pas les critères de validation.",
    "normalize": "Normalisation des données impossible.",
    "fetch": "Récupération des données impossible.",
    "offline": "Mode hors ligne : données locales insuffisantes.",
    "unexpected": "Une erreur inattendue s'est produite.",
}

_GENERIC_FALLBACK = "Une erreur s'est produite. Consultez les journaux pour plus de détails."


def format_refresh_error(
    ticker: str,
    error_kind: str | None,
    stage: str | None = None,
) -> str:
    """Return a clean French message for a failed company refresh.

    Uses error_kind when available; falls back to stage or a generic message.
    The ticker is included so the user knows which company is affected.
    """
    prefix = f"Impossible d'actualiser {ticker} : " if ticker else "Actualisation impossible : "
    if error_kind and error_kind in _KIND_MESSAGES:
        return prefix + _KIND_MESSAGES[error_kind]
    if stage and stage in _STAGE_FALLBACK_MESSAGES:
        return prefix + _STAGE_FALLBACK_MESSAGES[stage]
    return prefix + _GENERIC_FALLBACK


def format_ingestion_error(
    identifier: str,
    error_kind: str | None,
    stage: str | None = None,
) -> str:
    """Return a clean French message for a failed ticker ingestion.

    Validation-stage errors (already clean French) pass through unchanged
    so we preserve the detailed format help. Provider-level errors are
    replaced with friendly messages.
    """
    if stage == "validate":
        return _GENERIC_FALLBACK
    if error_kind and error_kind in _KIND_MESSAGES:
        label = identifier or "inconnu"
        return f"Impossible d'importer {label} : {_KIND_MESSAGES[error_kind]}"
    if stage and stage in _STAGE_FALLBACK_MESSAGES:
        return _STAGE_FALLBACK_MESSAGES[stage]
    return _GENERIC_FALLBACK


def format_batch_summary(
    label: str,
    succeeded: int,
    total: int,
    failed: int,
    failed_tickers: list[str],
) -> str:
    """Build a status-bar summary string for batch universe/watchlist refresh.

    Shows how many companies succeeded and lists the first few failures
    without exposing raw error strings.
    """
    msg = f"{label} — {succeeded}/{total} société(s) rafraîchie(s)"
    if failed:
        visible = [t for t in failed_tickers[:3] if t]
        if visible:
            msg += f", {failed} échec(s) : {', '.join(visible)}"
        else:
            msg += f", {failed} échec(s)"
    return msg + "."
