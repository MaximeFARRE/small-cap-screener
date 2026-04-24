from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd


@dataclass
class ExportRow:
    nom: str
    ticker: str | None
    secteur: str | None
    marche: str | None
    score: float
    pe: float | None
    pb: float | None
    ev_ebitda: float | None
    ev_ebit: float | None
    p_fcf: float | None
    roe: float | None
    roa: float | None
    marge_ebit: float | None
    marge_ebitda: float | None
    marge_nette: float | None
    dette_cp: float | None
    dn_ebitda: float | None
    mkt_cap: float
    ev: float
    prix: float
    annee_fiscale: int


def _to_dataframe(rows: list[ExportRow]) -> pd.DataFrame:
    records = [asdict(r) for r in rows]
    return pd.DataFrame(records)


def to_csv(rows: list[ExportRow], path: Path) -> None:
    _to_dataframe(rows).to_csv(path, index=False, encoding="utf-8-sig")


def to_excel(rows: list[ExportRow], path: Path) -> None:
    df = _to_dataframe(rows)
    with pd.ExcelWriter(path, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Screening")
        worksheet = writer.sheets["Screening"]
        for i, col in enumerate(df.columns):
            width = max(len(str(col)), df[col].astype(str).str.len().max()) + 2
            worksheet.set_column(i, i, width)
