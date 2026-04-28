from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

MODE_DISCOVERY_ONLY = "discovery_only"
MODE_DISCOVERY_AND_ENRICH = "discovery_and_enrich"
MODE_RESUME_LAST_FAILURES = "resume_last_failures"


@dataclass(frozen=True)
class UniverseImportOptions:
    mode: str
    batch_size: int
    pacing_seconds: float


class UniverseImportDialog(QDialog):
    def __init__(self, *, can_resume: bool, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._can_resume = can_resume
        self._options: UniverseImportOptions | None = None
        self.setWindowTitle("Importer univers France")
        self.setMinimumWidth(460)
        self._setup_ui()

    @property
    def options(self) -> UniverseImportOptions | None:
        return self._options

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Choisissez le mode d'import.\n"
                "Le mode enrichissement déclenche un rafraîchissement Yahoo potentiellement long."
            )
        )

        mode_group = QGroupBox("Mode")
        mode_layout = QVBoxLayout(mode_group)
        self._mode_discovery_only = QRadioButton("Discovery only (sans enrichissement Yahoo)")
        self._mode_discovery_and_enrich = QRadioButton("Discovery + enrichissement Yahoo")
        self._mode_resume_failures = QRadioButton("Reprendre les derniers échecs d'enrichissement")

        self._mode_discovery_only.setChecked(True)
        self._mode_resume_failures.setEnabled(self._can_resume)
        if not self._can_resume:
            self._mode_resume_failures.setToolTip("Aucun échec précédent disponible dans cette session.")
        mode_layout.addWidget(self._mode_discovery_only)
        mode_layout.addWidget(self._mode_discovery_and_enrich)
        mode_layout.addWidget(self._mode_resume_failures)
        layout.addWidget(mode_group)

        execution_group = QGroupBox("Exécution batch")
        execution_form = QFormLayout(execution_group)
        self._batch_size = QSpinBox()
        self._batch_size.setRange(1, 200)
        self._batch_size.setValue(25)
        self._batch_size.setSuffix(" société(s)")
        execution_form.addRow("Taille des lots:", self._batch_size)

        self._pacing_seconds = QSpinBox()
        self._pacing_seconds.setRange(0, 10)
        self._pacing_seconds.setValue(2)
        self._pacing_seconds.setSuffix(" s")
        execution_form.addRow("Pause entre sociétés:", self._pacing_seconds)
        layout.addWidget(execution_group)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Lancer")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self) -> None:
        mode = MODE_DISCOVERY_ONLY
        if self._mode_discovery_and_enrich.isChecked():
            mode = MODE_DISCOVERY_AND_ENRICH
        elif self._mode_resume_failures.isChecked():
            mode = MODE_RESUME_LAST_FAILURES

        self._options = UniverseImportOptions(
            mode=mode,
            batch_size=self._batch_size.value(),
            pacing_seconds=float(self._pacing_seconds.value()),
        )
        self.accept()
