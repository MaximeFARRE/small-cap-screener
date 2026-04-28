from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.services.settings_service import AppSettings, SettingsService, validate_app_settings

_WEIGHT_DECIMALS: int = 2
_WEIGHT_STEP: float = 0.05
_WEIGHT_MIN: float = 0.0
_WEIGHT_MAX: float = 1.0


class SettingsDialog(QDialog):
    """Dialog for editing and persisting application settings.

    Emits settings_saved when the user confirms valid changes.
    The caller is responsible for applying the new settings to running services.
    """

    settings_saved = Signal(AppSettings)

    def __init__(self, settings_service: SettingsService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings_service = settings_service
        self._current = settings_service.load()
        self.setWindowTitle("Paramètres")
        self.setMinimumWidth(380)
        self._setup_ui()
        self._load_into_widgets(self._current)

    # --- UI construction ---

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(self._build_connectivity_group())
        layout.addWidget(self._build_scoring_group())
        layout.addWidget(self._build_weight_sum_label())
        layout.addWidget(self._build_reset_button())
        layout.addWidget(self._build_button_box())

    def _build_connectivity_group(self) -> QGroupBox:
        group = QGroupBox("Connectivité")
        form = QFormLayout(group)

        self._offline_mode_check = QCheckBox("Mode hors ligne (désactive les appels fournisseur)")
        form.addRow(self._offline_mode_check)

        self._retry_spin = QSpinBox()
        self._retry_spin.setRange(1, 10)
        self._retry_spin.setSuffix(" tentative(s)")
        form.addRow("Tentatives fournisseur :", self._retry_spin)

        return group

    def _build_scoring_group(self) -> QGroupBox:
        group = QGroupBox("Pondération du score (somme = 1.00)")
        form = QFormLayout(group)

        self._quality_spin = self._make_weight_spinbox()
        self._value_spin = self._make_weight_spinbox()
        self._growth_spin = self._make_weight_spinbox()
        self._risk_spin = self._make_weight_spinbox()

        form.addRow("Qualité :", self._quality_spin)
        form.addRow("Valeur :", self._value_spin)
        form.addRow("Croissance :", self._growth_spin)
        form.addRow("Risque :", self._risk_spin)

        for spin in (self._quality_spin, self._value_spin, self._growth_spin, self._risk_spin):
            spin.valueChanged.connect(self._refresh_weight_sum)

        return group

    def _build_weight_sum_label(self) -> QLabel:
        self._weight_sum_label = QLabel()
        self._weight_sum_label.setObjectName("weightSumLabel")
        return self._weight_sum_label

    def _build_reset_button(self) -> QPushButton:
        btn = QPushButton("Réinitialiser les valeurs par défaut")
        btn.clicked.connect(self._on_reset)
        return btn

    def _build_button_box(self) -> QDialogButtonBox:
        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        box.accepted.connect(self._on_accept)
        box.rejected.connect(self.reject)
        return box

    @staticmethod
    def _make_weight_spinbox() -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(_WEIGHT_MIN, _WEIGHT_MAX)
        spin.setDecimals(_WEIGHT_DECIMALS)
        spin.setSingleStep(_WEIGHT_STEP)
        return spin

    # --- State management ---

    def _load_into_widgets(self, settings: AppSettings) -> None:
        self._offline_mode_check.setChecked(settings.offline_mode)
        self._retry_spin.setValue(settings.provider_retry_attempts)
        self._quality_spin.setValue(settings.scoring_quality_weight)
        self._value_spin.setValue(settings.scoring_value_weight)
        self._growth_spin.setValue(settings.scoring_growth_weight)
        self._risk_spin.setValue(settings.scoring_risk_weight)
        self._refresh_weight_sum()

    def _collect_settings(self) -> AppSettings:
        return AppSettings(
            offline_mode=self._offline_mode_check.isChecked(),
            provider_retry_attempts=self._retry_spin.value(),
            scoring_quality_weight=self._quality_spin.value(),
            scoring_value_weight=self._value_spin.value(),
            scoring_growth_weight=self._growth_spin.value(),
            scoring_risk_weight=self._risk_spin.value(),
        )

    def _refresh_weight_sum(self) -> None:
        total = (
            self._quality_spin.value() + self._value_spin.value() + self._growth_spin.value() + self._risk_spin.value()
        )
        label = f"Somme des poids : {total:.2f}"
        if abs(total - 1.0) < 1e-6:
            self._weight_sum_label.setText(f"✓ {label}")
            self._weight_sum_label.setStyleSheet("color: green;")
        else:
            self._weight_sum_label.setText(f"✗ {label}  (doit être égal à 1.00)")
            self._weight_sum_label.setStyleSheet("color: red;")

    # --- Slot handlers ---

    def _on_accept(self) -> None:
        candidate = self._collect_settings()
        errors = validate_app_settings(candidate)
        if errors:
            QMessageBox.warning(
                self,
                "Paramètres invalides",
                "\n".join(errors),
            )
            return
        self._settings_service.save(candidate)
        self._current = candidate
        self.settings_saved.emit(candidate)
        self.accept()

    def _on_reset(self) -> None:
        confirm = QMessageBox.question(
            self,
            "Réinitialiser",
            "Réinitialiser tous les paramètres aux valeurs par défaut ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        defaults = self._settings_service.reset_to_defaults()
        self._load_into_widgets(defaults)
