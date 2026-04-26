from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from src.services.ticker_ingestion_service import TickerIngestionService, validate_ingestion_identifier
from src.ui.error_formatter import format_ingestion_error

_DIALOG_TITLE = "Ajouter un ticker ou un ISIN"
_DIALOG_MIN_WIDTH = 380
_PLACEHOLDER = "Exemple : MC.PA ou FR0000120271"
_STATUS_STYLE_ERROR = "color: #c0392b;"
_STATUS_STYLE_SUCCESS = "color: #27ae60;"
_STATUS_STYLE_PENDING = "color: #7f8c8d;"


class AddTickerDialog(QDialog):
    """Dialog allowing the analyst to ingest using ticker or ISIN."""

    ticker_ingested = Signal(int)

    def __init__(self, ingestion_service: TickerIngestionService, parent=None) -> None:
        super().__init__(parent)
        self._ingestion_service = ingestion_service
        self.setWindowTitle(_DIALOG_TITLE)
        self.setMinimumWidth(_DIALOG_MIN_WIDTH)
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        self._identifier_input = QLineEdit()
        self._identifier_input.setPlaceholderText(_PLACEHOLDER)
        self._identifier_input.textChanged.connect(self._on_text_changed)
        layout.addWidget(self._identifier_input)

        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self._status_label)

        self._buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self._ok_button = self._buttons.button(QDialogButtonBox.StandardButton.Ok)
        self._ok_button.setText("Importer")
        self._ok_button.setEnabled(False)
        self._buttons.accepted.connect(self._on_import)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

    def _on_text_changed(self, text: str) -> None:
        normalized = text.strip().upper()
        self._status_label.setText("")
        self._ok_button.setEnabled(bool(normalized) and validate_ingestion_identifier(normalized) is None)

    def _on_import(self) -> None:
        identifier = self._identifier_input.text().strip().upper()
        self._ok_button.setEnabled(False)
        self._status_label.setStyleSheet(_STATUS_STYLE_PENDING)
        self._status_label.setText(f"Importation de {identifier} en cours…")
        self.repaint()

        result = self._ingestion_service.ingest_identifier(identifier)

        if not result.success:
            self._ok_button.setEnabled(True)
            self._status_label.setStyleSheet(_STATUS_STYLE_ERROR)
            if result.stage == "validate" and result.error:
                error_text = result.error
            else:
                error_text = format_ingestion_error(identifier, result.error_kind, result.stage)
            self._status_label.setText(error_text)
            return

        resolved = result.resolved_ticker or identifier
        action = "créée" if result.created else "mise à jour"
        suffix_info = (
            f" (suffixe ajouté automatiquement : {resolved})"
            if result.resolved_ticker and result.resolved_ticker != identifier
            else ""
        )
        msg = f"Société {action} avec succès ({resolved}){suffix_info}."
        if result.warnings:
            msg += f"\nAvertissements : {'; '.join(result.warnings)}"
        self._status_label.setStyleSheet(_STATUS_STYLE_SUCCESS)
        self._status_label.setText(msg)

        if result.company_id is not None:
            self.ticker_ingested.emit(result.company_id)

        self.accept()
