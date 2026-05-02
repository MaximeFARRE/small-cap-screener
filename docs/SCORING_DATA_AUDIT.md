# Scoring Data Audit

**Date:** 2026-05-02
**Branche:** `feat/scoring`
**Périmètre:** Audit data-first avant refonte du scoring fondamental.
**Objectif:** Recenser précisément ce qui existe, ce qui est calculable, et ce qui manque — sans modifier l'algorithme.

---

## 1. Données stockées en base

### 1.1 `Company` (`src/models/company.py`)

Données de profil et de marché par société.

| Champ | Type | Nullable | Usage scoring actuel |
|-------|------|----------|----------------------|
| `id` | int | Non (PK) | — |
| `ticker` | str(20) | Oui | Identifiant |
| `isin` | str(12) | Oui, unique | Identifiant |
| `name` | str(200) | Non | — |
| `sector` | str(100) | Oui | Ranking sectoriel |
| `industry` | str(200) | Oui | — |
| `market` | str(100) | Oui | — |
| `country` | str(100) | Oui | — |
| `currency` | str(3) | Non, défaut EUR | — |
| `market_cap` | float | Non | Ratios value |
| `enterprise_value_yahoo` | float | Oui | EV (fallback) |
| `beta` | float | Oui | Stocké dans KPI JSON |
| `shares_outstanding` | float | Oui | Calcul EPS, P/E |
| `float_shares` | float | Oui | Non utilisé scoring |
| `gross_margins` | float | Oui | Dupliqué depuis yfinance |
| `operating_margins` | float | Oui | Dupliqué depuis yfinance |
| `profit_margins` | float | Oui | Dupliqué depuis yfinance |
| `roe` | float | Oui | Dupliqué depuis yfinance |
| `roa` | float | Oui | Dupliqué depuis yfinance |
| `current_ratio` | float | Oui | Dupliqué depuis yfinance |
| `quick_ratio` | float | Oui | Non utilisé scoring |
| `payout_ratio` | float | Oui | Non utilisé scoring |
| `dividend_rate` | float | Oui | — |
| `dividend_yield` | float | Oui | Non utilisé scoring |
| `five_year_avg_dividend_yield` | float | Oui | Non utilisé scoring |
| `ex_dividend_date` | datetime | Oui | — |
| `analyst_target_price` | float | Oui | Stocké dans KPI JSON |
| `analyst_recommendation` | str(20) | Oui | Stocké dans KPI JSON |
| `analyst_count` | int | Oui | Stocké dans KPI JSON |
| `forward_pe` | float | Oui | Stocké dans KPI JSON |
| `average_daily_volume` | float | Oui | Filtre liquidité |
| `business_summary` | str(5000) | Oui | — |
| `full_time_employees` | int | Oui | Non utilisé scoring |
| `website`, `city`, `phone` | str | Oui | — |
| `source_origin` | str(20) | Oui | — |
| `last_universe_refresh_at` | datetime | Oui | Fraîcheur data |
| `is_active` | bool | Non | Filtre univers |

**Remarques :**
- Les champs `gross_margins`, `operating_margins`, `roe`, `roa`, `current_ratio` sont redondants avec ce qui est recalculé dans `RatioService` depuis `FinancialStatement`. Ils proviennent directement de yfinance (TTM ou LTM, sans contrôle sur la période).
- `enterprise_value_yahoo` est un fallback ; l'EV utilisée dans le scoring est recalculée (`market_cap + net_debt` depuis `FinancialStatement`).

---

### 1.2 `FinancialStatement` (`src/models/financial_statement.py`)

Un enregistrement par société et par exercice fiscal.

| Champ | Type | Nullable | Source yfinance |
|-------|------|----------|-----------------|
| `company_id` | int (FK) | Non | — |
| `fiscal_year` | int | Non | Colonne annuelle |
| `period_type` | str(20) | Non, défaut "annual" | — |
| `revenue` | float | Oui | `Total Revenue` |
| `ebit` | float | Oui | `EBIT` |
| `ebitda` | float | Oui | `EBITDA` (calculé si absent) |
| `net_income` | float | Oui | `Net Income` |
| `gross_profit` | float | Oui | `Gross Profit` (calculé si absent) |
| `total_assets` | float | Oui | `Total Assets` |
| `total_equity` | float | Oui | `Stockholders Equity` |
| `total_debt` | float | Oui | `Total Debt` |
| `net_debt` | float | Oui | `Total Debt - Cash` |
| `free_cash_flow` | float | Oui | `Free Cash Flow` |
| `shares_outstanding` | float | Oui | `Ordinary Shares Number` |
| `current_assets` | float | Oui | `Current Assets` |
| `current_liabilities` | float | Oui | `Current Liabilities` |
| `interest_expense` | float | Oui | `Interest Expense` |

**Données absentes du modèle mais présentes dans les états financiers standards :**
- `capex` (investissements) — non persisté
- `depreciation_amortization` — non persisté (EBITDA = EBIT + D&A, mais D&A seul n'est pas stocké)
- `operating_cash_flow` — non persisté
- `working_capital` — non persisté (calculable : `current_assets - current_liabilities`)
- `retained_earnings` — non persisté
- `goodwill` — non persisté
- `intangible_assets` — non persisté
- `cash_and_equivalents` — non persisté en propre (intégré dans `net_debt`)

---

### 1.3 `PriceHistory` (`src/models/price_history.py`)

Un enregistrement par date de cotation.

| Champ | Type | Nullable |
|-------|------|----------|
| `company_id` | int (FK) | Non |
| `date` | date | Non |
| `open` | float | Oui |
| `high` | float | Oui |
| `low` | float | Oui |
| `close` | float | Non |
| `adjusted_close` | float | Oui |
| `volume` | int | Oui |

**Données absentes :**
- Prix 52 semaines haut/bas — calculable depuis la table mais non pré-calculé
- Volume moyen sur N jours — calculable mais non pré-calculé
- Momentum (rendement 1M, 3M, 6M, 12M) — calculable mais non stocké
- Volatilité historique — calculable mais non stockée

---

### 1.4 `KpiSnapshot` (`src/models/kpi_snapshot.py`)

Point-in-time de tous les ratios et scores calculés, stocké sous forme de JSON dans `metrics`.

| Clé JSON | Type | Produit par |
|----------|------|-------------|
| `fiscal_year` | int | `KpiSnapshotService` |
| `price` | float | `KpiSnapshotService` |
| `market_cap` | float | `KpiSnapshotService` |
| `enterprise_value` | float | `KpiSnapshotService` |
| `pe_ratio` | float\|null | `RatioService` |
| `pb_ratio` | float\|null | `RatioService` |
| `ev_ebitda` | float\|null | `RatioService` |
| `ev_ebit` | float\|null | `RatioService` |
| `fcf_yield` | float\|null | `RatioService` |
| `roe` | float\|null | `RatioService` |
| `roic` | float\|null | `RatioService` |
| `roce` | float\|null | `RatioService` |
| `gross_margin` | float\|null | `RatioService` |
| `operating_margin` | float\|null | `RatioService` |
| `ebitda_margin` | float\|null | `RatioService` |
| `revenue_growth` | float\|null | `RatioService` (YoY N vs N-1) |
| `ebitda_growth` | float\|null | `RatioService` (YoY N vs N-1) |
| `net_debt_to_ebitda` | float\|null | `RatioService` |
| `current_ratio` | float\|null | `RatioService` |
| `interest_coverage` | float\|null | `RatioService` |
| `beta` | float\|null | Depuis `Company.beta` |
| `analyst_target_price` | float\|null | Depuis `Company` |
| `analyst_recommendation` | str\|null | Depuis `Company` |
| `analyst_count` | int\|null | Depuis `Company` |
| `forward_pe` | float\|null | Depuis `Company` |
| `data_quality_score` | float (0–100) | `KpiSnapshotService` |
| `quality_score` | float | `ScoringService` |
| `value_score` | float | `ScoringService` |
| `growth_score` | float | `ScoringService` |
| `risk_score` | float | `ScoringService` |
| `total_score` | float | `ScoringService` |
| `score_weight_quality` | float | `ScoringService` |
| `score_weight_value` | float | `ScoringService` |
| `score_weight_growth` | float | `ScoringService` |
| `score_weight_risk` | float | `ScoringService` |

---

### 1.5 Autres modèles

| Modèle | Contenu | Usage scoring actuel |
|--------|---------|----------------------|
| `Dividend` | Historique des dividendes (ex_date, amount, currency) | Non utilisé |
| `Split` | Historique des splits (date, ratio_from, ratio_to) | Non utilisé |
| `CompanyExecutive` | Dirigeants (nom, titre, âge, rémunération totale) | Non utilisé |
| `CompanyHolder` | Actionnariat (type, nom, % détenu, nb actions) | Non utilisé |
| `CompanyInsiderTransaction` | Transactions d'initiés (nom, relation, montant, date) | Non utilisé |
| `ScreeningSnapshot` | Snapshot filtré (filters, company_ids, scores JSON) | Snapshot uniquement |
| `WatchlistEntry` | Suivi analyste (statut, notes, thèse, exclusion) | Non utilisé dans scoring |

---

## 2. Données récupérées par les providers externes

### 2.1 `YFinanceProvider` (`src/repositories/providers/yfinance_provider.py`)

#### Champs récupérés ET persistés

| Source yfinance | Champ modèle | Notes |
|-----------------|-------------|-------|
| `info.sector` | `Company.sector` | |
| `info.industry` | `Company.industry` | |
| `info.marketCap` | `Company.market_cap` | |
| `info.enterpriseValue` | `Company.enterprise_value_yahoo` | Pas utilisé dans scoring (EV recalculée) |
| `info.beta` | `Company.beta` | |
| `info.forwardPE` | `Company.forward_pe` | |
| `info.targetMeanPrice` | `Company.analyst_target_price` | |
| `info.recommendationKey` | `Company.analyst_recommendation` | |
| `info.numberOfAnalystOpinions` | `Company.analyst_count` | |
| `info.grossMargins` | `Company.gross_margins` | TTM, non dédupliqué |
| `info.operatingMargins` | `Company.operating_margins` | TTM, non dédupliqué |
| `info.profitMargins` | `Company.profit_margins` | TTM, non dédupliqué |
| `info.returnOnEquity` | `Company.roe` | TTM, non dédupliqué |
| `info.returnOnAssets` | `Company.roa` | TTM, non dédupliqué |
| `info.currentRatio` | `Company.current_ratio` | TTM, non dédupliqué |
| `info.quickRatio` | `Company.quick_ratio` | |
| `info.payoutRatio` | `Company.payout_ratio` | |
| `info.sharesOutstanding` | `Company.shares_outstanding` | |
| `info.floatShares` | `Company.float_shares` | |
| `info.averageVolume` | `Company.average_daily_volume` | |
| `info.dividendRate` | `Company.dividend_rate` | |
| `info.dividendYield` | `Company.dividend_yield` | |
| `info.exDividendDate` | `Company.ex_dividend_date` | |
| `info.fiveYearAvgDividendYield` | `Company.five_year_avg_dividend_yield` | |
| Income Statement (annual) | `FinancialStatement.revenue/ebit/ebitda/...` | Jusqu'à 4 exercices |
| Balance Sheet (annual) | `FinancialStatement.total_assets/equity/debt/...` | |
| Cash Flow (annual) | `FinancialStatement.free_cash_flow` | |
| OHLCV daily | `PriceHistory` | Toute l'historique disponible |
| Dividends | `Dividend` | |
| Splits | `Split` | |
| Major holders | `CompanyHolder` (type=major) | |
| Institutional holders | `CompanyHolder` (type=institutional) | |
| Mutual fund holders | `CompanyHolder` (type=mutual_fund) | |
| Insider transactions | `CompanyInsiderTransaction` | |
| Key executives | `CompanyExecutive` | |

#### Champs récupérés par yfinance mais NON persistés

| Champ yfinance | Raison de non-persistance | Utile pour scoring avancé |
|----------------|--------------------------|--------------------------|
| `info.trailingPE` | Redondant avec P/E calculé | Non |
| `info.priceToBook` | Redondant avec P/B calculé | Non |
| `info.pegRatio` | Non implémenté | **Oui — PEG ratio** |
| `info.priceToSalesTrailing12Months` | Non implémenté | **Oui — P/S ratio** |
| `info.evToRevenue` | Non implémenté | **Oui — EV/Sales** |
| `info.evToEbitda` | Non persisté (EV/EBITDA recalculé) | Non (déjà calculé) |
| `info.revenueGrowth` | Non persisté (recalculé) | Non (déjà calculé) |
| `info.earningsGrowth` | Non persisté | **Oui — croissance BN TTM** |
| `info.earningsQuarterlyGrowth` | Non persisté | **Oui — croissance trimestrielle** |
| `info.revenuePerShare` | Non persisté | Non |
| `info.bookValue` | Non persisté (dérivable) | Non |
| `info.heldPercentInsiders` | Non persisté | **Oui — % détenu initiés** |
| `info.heldPercentInstitutions` | Non persisté | **Oui — % détenu institutionnels** |
| `info.shortRatio` | Non persisté | Oui — indicateur short interest |
| `info.shortPercentOfFloat` | Non persisté | Oui — indicateur short interest |
| `info.52WeekHigh` / `52WeekLow` | Non persisté (calculable) | Oui — momentum |
| `info.50DayAverage` / `200DayAverage` | Non persisté | Oui — momentum technique |
| Quarterly income statements | Non persisté | **Oui — tendances récentes** |
| Quarterly balance sheets | Non persisté | Oui |
| `info.debtToEquity` | Non persisté (calculé) | Non |

---

## 3. Ratios déjà calculés dans les services

### 3.1 `RatioService` (`src/services/ratio_service.py`)

| Ratio | Formule | Inputs |
|-------|---------|--------|
| `pe_ratio` | prix / (net_income / shares_outstanding) | price, net_income, shares_outstanding |
| `pb_ratio` | market_cap / total_equity | market_cap, total_equity |
| `ev_ebitda` | EV / ebitda | EV, ebitda |
| `ev_ebit` | EV / ebit | EV, ebit |
| `price_to_fcf` | market_cap / free_cash_flow | market_cap, free_cash_flow |
| `fcf_yield` | free_cash_flow / market_cap | free_cash_flow, market_cap |
| `roe` | net_income / total_equity | net_income, total_equity |
| `roic` | EBIT*(1-t) / (equity + net_debt) | ebit, total_equity, net_debt, tax_rate=0.25 |
| `roce` | ebit / (total_assets - current_liabilities) | ebit, total_assets, current_liabilities |
| `gross_margin` | gross_profit / revenue | gross_profit, revenue |
| `operating_margin` | ebit / revenue | ebit, revenue |
| `ebitda_margin` | ebitda / revenue | ebitda, revenue |
| `net_margin` | net_income / revenue | net_income, revenue |
| `roa` | net_income / total_assets | net_income, total_assets |
| `revenue_growth` | (rev_N - rev_N-1) / rev_N-1 | revenue (N), revenue (N-1) |
| `ebitda_growth` | (ebitda_N - ebitda_N-1) / ebitda_N-1 | ebitda (N), ebitda (N-1) |
| `net_debt_to_ebitda` | net_debt / ebitda | net_debt, ebitda |
| `current_ratio` | current_assets / current_liabilities | current_assets, current_liabilities |
| `interest_coverage` | ebit / interest_expense | ebit, interest_expense |
| `debt_to_equity` | total_debt / total_equity | total_debt, total_equity |
| `market_cap` | price * shares_outstanding | price, shares_outstanding |
| `enterprise_value` | market_cap + net_debt | market_cap, net_debt |

### 3.2 `ScoringService` (`src/services/scoring_service.py`)

Modèle multi-facteurs 4 piliers. Chaque métrique est scorée de 0 à 100 par interpolation linéaire entre `bad_threshold` (0) et `good_threshold` (100).

| Pilier | Poids total | Métriques incluses | Poids métrique |
|--------|------------|-------------------|----------------|
| **Quality** | 35% | roe | 35% |
| | | roic | 25% |
| | | operating_margin | 25% |
| | | gross_margin | 15% |
| **Value** | 30% | pe_ratio | 30% |
| | | ev_ebitda | 30% |
| | | pb_ratio | 20% |
| | | fcf_yield | 20% |
| **Growth** | 20% | revenue_growth | 60% |
| | | ebitda_growth | 40% |
| **Risk** | 15% | net_debt_to_ebitda | 50% |
| | | current_ratio | 25% |
| | | interest_coverage | 25% |

### 3.3 `KpiSnapshotService` — `data_quality_score`

Score de complétude des données (0–100), stocké dans `KpiSnapshot.metrics`.

| Composante | Poids | Critère |
|-----------|-------|---------|
| Complétude financière | 40% | 10 champs FS présents : revenue, ebit, ebitda, net_income, total_assets, total_equity, total_debt, net_debt, free_cash_flow, shares_outstanding |
| Disponibilité du prix | 20% | 100% si PriceHistory ; 60% si market_cap fallback |
| Qualité du market cap | 20% | 100% si > 0, sinon 0% |
| Complétude des ratios | 20% | pe, pb, ev_ebitda, ev_ebit, fcf_yield, roe, roic, operating_margin, net_debt_to_ebitda ; + growth si N-1 disponible |

---

## 4. Ratios calculables immédiatement avec les données existantes

Ces ratios ne sont pas dans le scoring actuel mais sont calculables sans nouvelle donnée.

| Ratio | Formule | Inputs existants | Pertinence scoring |
|-------|---------|-----------------|-------------------|
| `ps_ratio` | market_cap / revenue | market_cap (Company), revenue (FS) | Élevée — valorisation croissance |
| `ev_sales` | EV / revenue | EV (calculé), revenue (FS) | Élevée — valorisation croissance |
| `net_income_growth` | (NI_N - NI_N-1) / NI_N-1 | net_income (FS N et N-1) | Élevée — croissance bénéfice |
| `fcf_growth` | (FCF_N - FCF_N-1) / FCF_N-1 | free_cash_flow (FS N et N-1) | Élevée — croissance cash |
| `gross_profit_growth` | (GP_N - GP_N-1) / GP_N-1 | gross_profit (FS N et N-1) | Moyenne |
| `revenue_cagr_3y` | (rev_N / rev_N-3)^(1/3) - 1 | revenue (FS ≥ 3 exercices) | Très élevée — CAGR 3 ans |
| `ebitda_cagr_3y` | (ebitda_N / ebitda_N-3)^(1/3) - 1 | ebitda (FS ≥ 3 exercices) | Très élevée — CAGR 3 ans |
| `working_capital` | current_assets - current_liabilities | current_assets, current_liabilities (FS) | Moyenne — santé BFR |
| `asset_turnover` | revenue / total_assets | revenue, total_assets (FS) | Moyenne — efficacité |
| `equity_multiplier` | total_assets / total_equity | total_assets, total_equity (FS) | Moyenne — levier |
| `cash_conversion_ratio` | FCF / net_income | free_cash_flow, net_income (FS) | Élevée — qualité bénéfice |
| `capex_intensity` | Non calculable (capex non persisté) | — | — |
| `dividend_payout_ratio` | dividends / net_income | Dividend (table), net_income (FS) | Moyenne |
| `price_52w_high_pct` | (price - 52w_high) / 52w_high | PriceHistory (1 an) | Moyenne — momentum |
| `price_52w_low_pct` | (price - 52w_low) / 52w_low | PriceHistory (1 an) | Moyenne — momentum |
| `price_momentum_6m` | (price_today / price_6m_ago) - 1 | PriceHistory | Élevée — momentum |
| `price_momentum_12m` | (price_today / price_12m_ago) - 1 | PriceHistory | Élevée — momentum |
| `insider_ownership_pct` | CompanyHolder.weight (type=major) | CompanyHolder | Moyenne — alignement |
| `net_debt_growth` | (nd_N - nd_N-1) / |nd_N-1| | net_debt (FS N et N-1) | Élevée — tendance endettement |
| `interest_burden` | net_income / ebit | net_income, ebit (FS) | Moyenne — DuPont |
| `tax_burden` | net_income / pretax_income | Non calculable (pretax absent) | — |

---

## 5. Ratios non calculables — données manquantes

Ces ratios nécessitent des données non présentes dans les modèles actuels.

### 5.1 Données manquantes dans `FinancialStatement`

| Ratio manquant | Données absentes | Impact |
|----------------|-----------------|--------|
| `capex_to_revenue` | `capex` non persisté | Impossible — mesure investissement |
| `maintenance_capex` | `capex` non persisté | Impossible — FCF normalisé |
| `d_and_a` | D&A non persisté seul | Impossible — analyse cash conversion |
| `operating_cash_flow` | OCF non persisté | Impossible (FCF seul stocké) |
| `ocf_to_net_income` | OCF absent | Impossible — accrual quality |
| `retained_earnings` | Non persisté | Impossible — capacité d'autofinancement |
| `goodwill_to_assets` | goodwill non persisté | Impossible — risque impairment |
| `intangibles_to_assets` | intangibles non persisté | Impossible — tangible book value |
| `tangible_book_value` | goodwill + intangibles absents | Impossible — P/TBV |
| `pretax_income` | Non persisté | Impossible — tax burden |
| `tax_rate_effective` | Non persisté | Approximé à 25% fixe dans ROIC |
| `minority_interest` | Non persisté | Impossible — NOPAT précis |

### 5.2 Données de marché manquantes

| Donnée manquante | Source possible | Impact scoring |
|-----------------|-----------------|----------------|
| `short_interest` / `short_ratio` | yfinance (non persisté) | Indicateur sentiment |
| `short_percent_of_float` | yfinance (non persisté) | Indicateur squeeze |
| `52_week_high` / `52_week_low` | Calculable depuis PriceHistory | Momentum techniquement absent |
| `50_day_avg` / `200_day_avg` | Calculable depuis PriceHistory | Momentum MA |
| Données trimestrielles (quarterly FS) | yfinance (non persisté) | Tendances récentes, earnings momentum |

### 5.3 Données inexistantes dans yfinance (pour petites caps françaises)

| Donnée | Pourquoi absente | Alternative |
|--------|-----------------|-------------|
| `ESG score` | Non couvert Euronext Growth/Access | Source tierce requise |
| `consensus estimates` | Faible couverture analyste | Partiellement via `analyst_count` |
| `earnings surprise` | Non disponible | Non implémentable |
| `insider transactions valorisées` | Partiellement via `CompanyInsiderTransaction` | Données incomplètes yfinance FR |
| Prix d'options / volatilité implicite | Non pertinent small caps FR | Non applicable |
| `revenue by segment` | Rare pour small caps | Non disponible |

---

## 6. Données critiques manquantes pour un scoring professionnel

Classées par priorité d'impact sur la qualité du scoring.

### Priorité 1 — Impact immédiat sur la fiabilité

| Donnée | Problème actuel | Solution |
|--------|----------------|---------|
| **ROIC avec tax rate effectif** | Tax rate figé à 25% pour toutes les sociétés | Persister `pretax_income` pour calculer le taux réel |
| **Croissance multi-années (CAGR 3 ans)** | Croissance calculée uniquement sur N vs N-1 | Déjà calculable avec ≥ 3 exercices en base ; ajouter `revenue_cagr_3y`, `ebitda_cagr_3y` dans `RatioService` |
| **FCF margin** | Non calculé (FCF / revenue) | Calculable immédiatement |
| **Trend score** | Pas de détection de tendance sur 3 ans (amélioration/dégradation margins) | Calculable depuis FS historiques |

### Priorité 2 — Qualité du scoring value/growth

| Donnée | Problème actuel | Solution |
|--------|----------------|---------|
| **P/S ratio** | Non dans le scoring malgré données disponibles | Ajouter `ps_ratio` dans `RatioService` et scoring Value |
| **EV/Sales** | Non dans le scoring | Calculable immédiatement |
| **Net income growth** | Non dans le scoring Growth | Calculable depuis FS |
| **FCF growth** | Non dans le scoring Growth | Calculable depuis FS |
| **Cash conversion ratio** | Non calculé | Calculable : FCF / net_income |

### Priorité 3 — Données à enrichir (fetch + persist)

| Donnée | Provenance | Changement requis |
|--------|-----------|------------------|
| **Operating cash flow** | yfinance cash flow statement | Ajouter `operating_cash_flow` à `FinancialStatement` |
| **Capex** | yfinance cash flow statement | Ajouter `capex` à `FinancialStatement` |
| **D&A** | yfinance income/cash flow | Ajouter `depreciation_amortization` à `FinancialStatement` |
| **Résultat trimestriel (TTM)** | yfinance quarterly | Ajouter période `quarterly` ou TTM dans `FinancialStatement` |
| **% détenu par initiés** | yfinance `heldPercentInsiders` | Persister depuis provider (disponible, non stocké) |
| **% détenu institutionnels** | yfinance `heldPercentInstitutions` | Persister depuis provider (disponible, non stocké) |
| **PEG ratio** | yfinance `pegRatio` | Persister ou calculer (forward earnings growth manquant) |
| **Goodwill / intangibles** | yfinance balance sheet | Ajouter à `FinancialStatement` |

### Priorité 4 — `confidence_score` (scoring de confiance)

Pour implémenter un `confidence_score` robuste, les composantes suivantes doivent être explicitement disponibles :

| Composante confidence | Données requises | Statut |
|-----------------------|-----------------|--------|
| Ancienneté des données | `last_universe_refresh_at` | ✅ Disponible |
| Nb d'exercices en base | Requête sur `FinancialStatement` | ✅ Calculable |
| Présence du prix actuel | `PriceHistory.date` | ✅ Disponible |
| Couverture analyste | `analyst_count` | ✅ Disponible |
| Complétude des champs FS | Via `data_quality_score` partiel | ✅ Partiellement fait |
| Cohérence cross-field | `DataValidationService` | ✅ Existe |
| Nb de ratios calculables vs total | Ratio calculé / ratio attendu | ⚠️ Non formalisé |
| Qualité de la source | `source_origin`, `Company.source` | ✅ Disponible |
| Trimestres disponibles | Non stocké | ❌ Manquant |
| Révisions récentes | Non disponible | ❌ Manquant |

---

## Synthèse

### Ce qui fonctionne bien

- Pipeline de persistance complet : profil, états financiers (4 exercices), prix quotidien, dividendes, splits, actionnariat, dirigeants.
- 22 ratios calculés dans `RatioService`, tous traçables à leurs inputs.
- Scoring V1 4-piliers déterministe et explicable ; poids configurables.
- `data_quality_score` opérationnel comme proxy de confiance.

### Lacunes pour un scoring professionnel

1. **Capex et OCF absents** — empêche le calcul de FCF normalisé, capex intensity, cash conversion fiable.
2. **Croissance sur 1 an seulement** dans le scoring Growth — ignorer les CAGR 3 ans déjà calculables.
3. **P/S et EV/Sales absents** du scoring Value — données disponibles, non utilisées.
4. **Net income growth et FCF growth absents** du scoring Growth — calculables immédiatement.
5. **Données trimestrielles non persistées** — impossible de capter les tendances récentes (T-1 vs T-5).
6. **Tax rate figé à 25%** — biais sur ROIC pour sociétés bénéficiant d'avantages fiscaux.
7. **`confidence_score` non formalisé** — `data_quality_score` existe mais ne couvre pas la fiabilité temporelle.
8. **% actionnariat initiés/institutionnels non persisté** — disponible chez yfinance, non stocké.
