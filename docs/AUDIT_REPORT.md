# Audit de l'Application Small Cap Screener

## 1. Diagnostic

### UI / UX
- **Affichage surchargé** : Le widget `CompanyDetailWidget` empile un très grand nombre de formulaires (`QFormLayout`), de graphiques et de champs de saisie dans une liste déroulante infinie. L'information n'est pas hiérarchisée efficacement.
- **Feedback asynchrone basique** : Les opérations de rafraîchissement (batch) utilisent des `Worker` mais le suivi global (barre de progression, temps restant) est absent, remplacé par un simple message de statut en fin de tâche.

### Ingestion Ticker / ISIN
- **ISIN non supporté par le provider** : L'ingestion par ISIN est implémentée dans le service (`TickerIngestionService`), mais elle fait appel à `YFinanceProvider.get_company_profile(isin)`. Or, la librairie `yfinance` ne supporte pas nativement la résolution des ISINs (elle attend un ticker de marché). Les requêtes ISIN échoueront systématiquement.
- **Format strict** : L'import manuel nécessite de connaître le suffixe exact de la place boursière (ex: `.PA` pour Paris) attendu par Yahoo Finance, ce qui complique l'ajout pour un utilisateur réel.

### Qualité et couverture des données
- **Fiabilité pour les small caps** : Le provider exclusif est `yfinance`. Les données fondamentales (états financiers) pour les small et micro caps européennes sont notoirement incomplètes, obsolètes ou absentes sur Yahoo Finance.
- **Blocage IP** : La fonction `batch_refresh_universe` rafraîchit toutes les sociétés de manière séquentielle rapide sans "pacing" (délai) entre chaque société. Face à un large univers, Yahoo Finance va bloquer l'IP de l'utilisateur (Rate Limiting HTTP 429).

### Utilité réelle pour analyse buy-side
- **Screener limité** : L'interface de screening (`FilterWidget`) ne permet de filtrer que par Secteur, Score global, et Qualité de données. Il manque tous les filtres fondamentaux classiques utilisés en buy-side (Capitalisation boursière, P/E, Croissance, Marge nette, etc.) bien que les données existent en base.
- **Gestion de la Watchlist pertinente** : La gestion analyste (thèses d'investissement, statuts, dates de revues) est bien modélisée.
- **Comparaison de pairs basique** : Basée sur les secteurs larges de Yahoo Finance, ce qui compare souvent des small caps à des mega caps de manière peu pertinente.

---

## 2. Classification et Causes des Problèmes

| Problème | Sévérité | Cause Principale | Description |
|---|---|---|---|
| **L'import par ISIN échoue toujours** | **Bloquant** | *Provider insuffisant* | `yfinance` ne sait pas résoudre un ISIN en ticker. |
| **Ban IP lors du batch refresh** | **Bloquant** | *Mauvaise orchestration* | Pas de rate-limiting ou délai global entre les appels dans le `UniverseDiscoveryService`. |
| **Absence de filtres fondamentaux** | **Important** | *UI mal pensée / features non intégrées* | Le modèle de données a les ratios, mais le screener UI ne propose que le score et le secteur. |
| **Données Small Caps vides/NA** | **Important** | *Données absentes ou inutilisables* | Yahoo Finance couvre très mal les small caps européennes (états financiers manquants). |
| **UI de détail indigeste** | **Secondaire** | *UI mal pensée* | La fiche société est un immense bloc vertical au lieu d'utiliser des onglets (Tabs). |

---

## 3. Plan de Correction

### Lot 1 : Rendre l’import et la donnée fiables
1. **Résolution ISIN** : Remplacer l'appel direct à `yfinance` pour les ISIN par un service tiers dédié (ex: OpenFIGI, ou mapping externe) permettant de trouver le bon ticker local.
2. **Rate-limiting** : Intégrer un système de délai asynchrone ("pacing") robuste dans `batch_refresh_universe` et `refresh_watchlist` pour éviter les blocages de l'API.
3. **Tolérance aux données vides** : Améliorer les services pour qu'une société s'importe même si certains états financiers manquent (éviter le rejet asymétrique).

### Lot 2 : Rendre le screener utile
1. **Filtres fondamentaux** : Câbler des champs de filtrage dans le `FilterWidget` pour le Market Cap, P/E, Croissance, et Marges. Connecter cela au `ScreeningService`.
2. **Export enrichi** : Étendre l'export CSV/Excel pour inclure toutes les métriques financières et pas uniquement les scores et notes de l'analyste.
3. **Secteurs granulaires** : Implémenter une classification sectorielle plus fine (ou personnalisable par l'analyste) pour que la comparaison de pairs ait du sens.

### Lot 3 : Refaire l’UX principale
1. **Fiche Société Tabulaire** : Découper `CompanyDetailWidget` en onglets distincts : *Vue d'ensemble*, *États Financiers*, *Notes Analyste*, *Analyse Graphique*, *Comparables*.
2. **Indicateurs Visuels (Badges)** : Utiliser des codes couleurs explicites (feux tricolores) dans le tableau de screening pour la *Data Quality* et la fraîcheur des données.
3. **Feedback Batch** : Mettre en place une fenêtre de progression modale détaillée lors d'un "Actualiser l'univers" (avec le compte exact des sociétés traitées / en erreur).
