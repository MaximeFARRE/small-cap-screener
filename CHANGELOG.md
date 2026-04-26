# CHANGELOG

## v0.24.0 (2026-04-26)

### Feature

* feat: add provider_used to CompanyDataRefreshResult and use source_name in FinancialDataService ([`c9403eb`](https://github.com/MaximeFARRE/small-cap-screener/commit/c9403ebe1211d48e955d463fbcb368a38fc0f66f))

* feat: add ChainedProvider for primary/fallback provider orchestration ([`f1645a5`](https://github.com/MaximeFARRE/small-cap-screener/commit/f1645a566345eb0bcd480583bd37e90e2faf9d09))

* feat: add NoOpProvider as explicit provider failure sentinel ([`2cad6ef`](https://github.com/MaximeFARRE/small-cap-screener/commit/2cad6ef0dd3e3cd6c77009274682af0b12b68a41))

* feat: add source_name property to BaseProvider for provider identification ([`8e3b889`](https://github.com/MaximeFARRE/small-cap-screener/commit/8e3b889b6106babf2d01a06ba6cc2de15f2972e8))

### Test

* test: add ChainedProvider and NoOpProvider tests for provider redundancy ([`92eb4e1`](https://github.com/MaximeFARRE/small-cap-screener/commit/92eb4e1742b815a3883178d7daa5a453e3853e3c))

### Unknown

* Merge pull request #34 from MaximeFARRE/feat/phase29-provider-redundancy

Feat/phase29 provider redundancy ([`7bd1159`](https://github.com/MaximeFARRE/small-cap-screener/commit/7bd1159133967b9582fc4f8e0a7eae023b550c34))

## v0.23.0 (2026-04-26)

### Chore

* chore(release): 0.23.0 [skip ci] ([`84130c4`](https://github.com/MaximeFARRE/small-cap-screener/commit/84130c4353c94864964dcd677be739a9b1cd167a))

### Feature

* feat: add backtesting validation dialog ([`f15ef71`](https://github.com/MaximeFARRE/small-cap-screener/commit/f15ef71d89e67a55e794c8c4875a29fd0f87c6e7))

* feat: add ranking backtesting analysis service ([`5c3b5a7`](https://github.com/MaximeFARRE/small-cap-screener/commit/5c3b5a7a2204f2792aea50668d886031490b85f2))

### Test

* test: stub backtesting service in main window tests ([`153fdd5`](https://github.com/MaximeFARRE/small-cap-screener/commit/153fdd582dd24c46c72896d9c56bdc0d71517423))

* test: cover backtesting buckets and benchmark ([`7485603`](https://github.com/MaximeFARRE/small-cap-screener/commit/7485603dfc0df020d6708c925d90708b18526e23))

### Unknown

* Merge pull request #33 from MaximeFARRE/feat/phase28-backtesting-ranking-validation

Feat/phase28 backtesting ranking validation ([`3727df4`](https://github.com/MaximeFARRE/small-cap-screener/commit/3727df4579f0c825d22f8c6baec035750f1e94df))

## v0.22.0 (2026-04-26)

### Chore

* chore(release): 0.22.0 [skip ci] ([`24d0ade`](https://github.com/MaximeFARRE/small-cap-screener/commit/24d0adec3966ad795c1d00a6d0d1c87c9404aa4d))

* chore: rerun ci after black validation ([`e6b1446`](https://github.com/MaximeFARRE/small-cap-screener/commit/e6b14467f6885a5db59af075deb2107eec589f82))

### Feature

* feat: add peer comparison section in company detail ([`14e99ff`](https://github.com/MaximeFARRE/small-cap-screener/commit/14e99ff6e7b133cb1e04e39f3e1b88218726b4d7))

* feat: add sector peer comparison service ([`dceddc2`](https://github.com/MaximeFARRE/small-cap-screener/commit/dceddc259df6d18f9fe16921ad0402eee13ed5bc))

### Test

* test: stub peer comparison service in main window tests ([`80b1e9e`](https://github.com/MaximeFARRE/small-cap-screener/commit/80b1e9ee4b6506d54a56efb632ad109f634328a5))

* test: cover peer comparison selection and medians ([`3a66756`](https://github.com/MaximeFARRE/small-cap-screener/commit/3a66756a2a3f051e1d0dff5b91a02ea1e719a0eb))

### Unknown

* Merge pull request #32 from MaximeFARRE/feat/phase27-benchmark-relative-analysis

Feat/phase27 benchmark relative analysis ([`34de5b4`](https://github.com/MaximeFARRE/small-cap-screener/commit/34de5b42eb6a3f63e9eeec5b4dfa488f35e32a01))

## v0.21.0 (2026-04-26)

### Chore

* chore(release): 0.21.0 [skip ci] ([`bc94078`](https://github.com/MaximeFARRE/small-cap-screener/commit/bc940788f0e8e365b074bbcb84c5d42578b964b0))

### Feature

* feat: add company detail chart visualizations ([`d69094c`](https://github.com/MaximeFARRE/small-cap-screener/commit/d69094cd58b8627b1491b69a16bc2a58e7e15d78))

* feat: add company charts data service ([`bbd1328`](https://github.com/MaximeFARRE/small-cap-screener/commit/bbd132890a0e3fb0b90567b0d6caf1409330a1f8))

### Test

* test: stub chart service in main window tests ([`443a91a`](https://github.com/MaximeFARRE/small-cap-screener/commit/443a91aee79ab3a7dac15ac281ee1f36d501adb6))

* test: cover company charts data preparation ([`785250d`](https://github.com/MaximeFARRE/small-cap-screener/commit/785250d7db4dbd032a68698f536485500d992be3))

### Unknown

* Merge pull request #31 from MaximeFARRE/feat/phase26-charts-visual-analysis

Feat/phase26 charts visual analysis ([`586a0c4`](https://github.com/MaximeFARRE/small-cap-screener/commit/586a0c4e770b1a1bd8848096371cfc0729998c6b))

## v0.20.0 (2026-04-26)

### Chore

* chore(release): 0.20.0 [skip ci] ([`97b351a`](https://github.com/MaximeFARRE/small-cap-screener/commit/97b351a035ca2ea79427c7180035e976ed697d75))

### Feature

* feat: add excel and watchlist export actions ([`00257ec`](https://github.com/MaximeFARRE/small-cap-screener/commit/00257ec06c867e9efc3a8b31712c2b15a59bdde2))

* feat: enrich screening exports with metadata and scopes ([`ff541c0`](https://github.com/MaximeFARRE/small-cap-screener/commit/ff541c019ffbacea6c17c4d3f5b0f41a7112e3d5))

### Test

* test: cover enriched screening exports ([`c76e4c4`](https://github.com/MaximeFARRE/small-cap-screener/commit/c76e4c405d80d2d3b7a557fe10e8bbc2c230ee1c))

### Unknown

* Merge pull request #30 from MaximeFARRE/feat/phase25-export-polish

Feat/phase25 export polish ([`0645a8c`](https://github.com/MaximeFARRE/small-cap-screener/commit/0645a8cc247387309ebdba8979c5f4c0db61c319))

## v0.19.0 (2026-04-26)

### Chore

* chore(release): 0.19.0 [skip ci] ([`3665645`](https://github.com/MaximeFARRE/small-cap-screener/commit/3665645d6b46d01d8acde439b8bccd2b2ca8d3a2))

### Feature

* feat: allow ticker ingestion from ticker or isin input ([`b0d4492`](https://github.com/MaximeFARRE/small-cap-screener/commit/b0d4492b9e7969c414c43a4ea06ded1c481f1b1a))

### Fix

* fix: include companies without isin in investable universe ([`060f002`](https://github.com/MaximeFARRE/small-cap-screener/commit/060f002ada698ae22decdeefe464d235e595445e))

* fix: clean invalid existing isin during ticker ingestion ([`3305147`](https://github.com/MaximeFARRE/small-cap-screener/commit/3305147de8f92f0985e65e5434e695f3c62d4f39))

* fix: ignore invalid provider isin during ticker ingestion ([`46bdc7c`](https://github.com/MaximeFARRE/small-cap-screener/commit/46bdc7c0f43f220ed97e23d5fccf983fe9db3e06))

* fix: allow nullable company isin with sqlite migration ([`efa2516`](https://github.com/MaximeFARRE/small-cap-screener/commit/efa25160017362731a8189c70d5b858cbc89c304))

### Test

* test: cover ticker ingestion without valid isin ([`9a6e2c8`](https://github.com/MaximeFARRE/small-cap-screener/commit/9a6e2c8d96706c0c7bc122c9b3548bf974e929cb))

### Unknown

* Merge pull request #29 from MaximeFARRE/fix/isin-invalid-ticker-ingestion

Fix/isin invalid ticker ingestion ([`dd2c2ed`](https://github.com/MaximeFARRE/small-cap-screener/commit/dd2c2ed547feda7596e6e4426ff151dfeed8d7d5))

## v0.18.0 (2026-04-26)

### Chore

* chore(release): 0.18.0 [skip ci] ([`ab1fa21`](https://github.com/MaximeFARRE/small-cap-screener/commit/ab1fa2150e55f17b820d4730ed8275eb5db9490a))

### Feature

* feat: add screening snapshot browser actions ([`03b08b0`](https://github.com/MaximeFARRE/small-cap-screener/commit/03b08b06b28ad57f94285377d108c480a475812d))

* feat: add screening snapshot comparison views ([`082130c`](https://github.com/MaximeFARRE/small-cap-screener/commit/082130cdd8636ec1630e92b2df0e214eca1a01f8))

### Fix

* fix: add company column migration at startup ([`42c1917`](https://github.com/MaximeFARRE/small-cap-screener/commit/42c1917f73db6948d49b11236b69197ec0e4c5e6))

### Unknown

* Merge pull request #28 from MaximeFARRE/feat/phase24-screening-snapshots-v2

Feat/phase24 screening snapshots v2 ([`f972480`](https://github.com/MaximeFARRE/small-cap-screener/commit/f9724800cf04ce7f5b85ce3b3ab596f12e56c0a2))

## v0.17.0 (2026-04-26)

### Chore

* chore(release): 0.17.0 [skip ci] ([`68efa72`](https://github.com/MaximeFARRE/small-cap-screener/commit/68efa72196fc2244b7cabe7b29be369155e7144b))

### Feature

* feat: add next review date controls in company detail ([`ea80b70`](https://github.com/MaximeFARRE/small-cap-screener/commit/ea80b70bfc5fd6ad662db4594e0fc6e63727e99d))

* feat: add watchlist filters to screening workflow ([`f18137c`](https://github.com/MaximeFARRE/small-cap-screener/commit/f18137c1ba794b05572ccf36c3672099b7cdb4d2))

* feat: add watchlist workflow and next review scheduling ([`8308db1`](https://github.com/MaximeFARRE/small-cap-screener/commit/8308db1f2bf7d961e9964a4773b1f9240c6279fa))

### Unknown

* Merge pull request #27 from MaximeFARRE/feat/phase23-advanced-watchlist

Feat/phase23 advanced watchlist ([`cadef07`](https://github.com/MaximeFARRE/small-cap-screener/commit/cadef075610e73a10e88ca974df9ad919c7ea5c0))

## v0.16.0 (2026-04-26)

### Chore

* chore(release): 0.16.0 [skip ci] ([`cc82a96`](https://github.com/MaximeFARRE/small-cap-screener/commit/cc82a96bfbf3118e51e65c471490402d7386180c))

### Documentation

* docs: mention analyst memo workflow in features ([`70db6fe`](https://github.com/MaximeFARRE/small-cap-screener/commit/70db6fe01029e8197a88c3a7ceab7d0bc7129a4e))

### Feature

* feat: add analyst memo editing in company detail workflow ([`d0edfd1`](https://github.com/MaximeFARRE/small-cap-screener/commit/d0edfd1a344f91805405fa6e659844dd40426ee3))

* feat: add analyst memo fields to watchlist domain ([`86e7e80`](https://github.com/MaximeFARRE/small-cap-screener/commit/86e7e80b9ff5968e8dd47e32a74c42c7fa1f1397))

### Test

* test: add analyst memo service persistence scenarios ([`627618b`](https://github.com/MaximeFARRE/small-cap-screener/commit/627618bc6da99b06e9c9dda4523e79cde995ac5d))

### Unknown

* Merge pull request #26 from MaximeFARRE/feat/phase22-analyst-memo

Feat/phase22 analyst memo ([`4acf51f`](https://github.com/MaximeFARRE/small-cap-screener/commit/4acf51f07a74121e0acf4df2ca1f6133807b2945))

## v0.15.0 (2026-04-26)

### Chore

* chore(release): 0.15.0 [skip ci] ([`f31b423`](https://github.com/MaximeFARRE/small-cap-screener/commit/f31b4230252bbdbf7530f0cbde8057a86f1b75a4))

### Documentation

* docs: describe score transparency and weight configuration ([`16041cd`](https://github.com/MaximeFARRE/small-cap-screener/commit/16041cd158ea70ae494a0704ac6ee5eb00a8eb49))

### Feature

* feat: show score transparency details in company detail widget ([`df67b69`](https://github.com/MaximeFARRE/small-cap-screener/commit/df67b69a7fdf91de39ce4b13014c4959acf94ee7))

* feat: add configurable score weights and deterministic breakdown ([`a48b2b6`](https://github.com/MaximeFARRE/small-cap-screener/commit/a48b2b64d0fcd7a24ec4e8b5648eb4ef75938ad9))

### Test

* test: add score transparency and weight stability coverage ([`ac4b2c3`](https://github.com/MaximeFARRE/small-cap-screener/commit/ac4b2c313bf1e0128cfb9be88afe445dfc94a567))

### Unknown

* Merge pull request #25 from MaximeFARRE/feat/phase21-score-transparency

Feat/phase21 score transparency ([`4a916ae`](https://github.com/MaximeFARRE/small-cap-screener/commit/4a916ae4f6133589354e993d55d6e20074c9d5dc))

## v0.14.0 (2026-04-26)

### Chore

* chore(release): 0.14.0 [skip ci] ([`21646c7`](https://github.com/MaximeFARRE/small-cap-screener/commit/21646c7c191aaa22d412840eb62fe98761daa0b1))

### Documentation

* docs: mention historical fundamentals in feature list ([`9196b35`](https://github.com/MaximeFARRE/small-cap-screener/commit/9196b3503fdbf0c90a7ad000045f34235c21d4c5))

### Feature

* feat: add historical fundamentals section in detail widget ([`a89b945`](https://github.com/MaximeFARRE/small-cap-screener/commit/a89b945ad4aacc8063f756b1c77264cf3bf70921))

* feat: add historical fundamentals to company detail service ([`edd2dea`](https://github.com/MaximeFARRE/small-cap-screener/commit/edd2dea8fb2ad359c0bb5a90c9a50c5b2826d8fb))

### Test

* test: add historical fundamentals coverage for company detail ([`6e93295`](https://github.com/MaximeFARRE/small-cap-screener/commit/6e93295d504e6e56449dc16d45a6768ca6dc32e2))

### Unknown

* Merge pull request #24 from MaximeFARRE/feat/phase20-historical-fundamentals

Feat/phase20 historical fundamentals ([`a26f323`](https://github.com/MaximeFARRE/small-cap-screener/commit/a26f323be60cf3b962482402652e6d9c5b18f5ee))

## v0.13.0 (2026-04-26)

### Chore

* chore(release): 0.13.0 [skip ci] ([`17c758f`](https://github.com/MaximeFARRE/small-cap-screener/commit/17c758feeccd6484a81cd7506bc5eeb86520b91e))

### Feature

* feat: show freshness dates, quality badge and alert panel in CompanyDetailWidget ([`32fbb1e`](https://github.com/MaximeFARRE/small-cap-screener/commit/32fbb1e93c0b488e4d602284816c6f74f1f90e17))

* feat: add quality score and stale-only filter inputs to FilterWidget ([`0677a49`](https://github.com/MaximeFARRE/small-cap-screener/commit/0677a49d78f4d3c58f4027514d0a4694e44b3fa9))

* feat: add data_quality_score, freshness fields and quality/stale filters to screening service ([`e9b5db5`](https://github.com/MaximeFARRE/small-cap-screener/commit/e9b5db536f8e102154c038c57fe01e6d717615df))

### Test

* test: add quality score and freshness filter tests for ScreeningService ([`33e61b6`](https://github.com/MaximeFARRE/small-cap-screener/commit/33e61b69dbfcbf696ce7e197fc52f854665bb4e0))

### Unknown

* Merge pull request #23 from MaximeFARRE/feat/phase19-data-freshness-quality-ui

Feat/phase19 data freshness quality UI ([`9e5029a`](https://github.com/MaximeFARRE/small-cap-screener/commit/9e5029abe47117bec3c16caa12ed892f9f00163d))

## v0.12.0 (2026-04-26)

### Chore

* chore(release): 0.12.0 [skip ci] ([`ca4a0c2`](https://github.com/MaximeFARRE/small-cap-screener/commit/ca4a0c261989ca21ba8c9b145bf5da3a4f9d070f))

### Feature

* feat: wire refresh company/watchlist/universe actions with progress locking and detailed error feedback ([`4f32fae`](https://github.com/MaximeFARRE/small-cap-screener/commit/4f32faec60d689b99ce2ffea16bb6395ca566d45))

* feat: add Actualiser cette société button and refresh_company_requested signal to CompanyDetailWidget ([`6507316`](https://github.com/MaximeFARRE/small-cap-screener/commit/6507316619ccb4033acef9cdcc1eed7213d3f53f))

* feat: add refresh_watchlist method to UniverseDiscoveryService ([`169e4dc`](https://github.com/MaximeFARRE/small-cap-screener/commit/169e4dc21fbb74cd2f76141e53bd595f313c951a))

### Test

* test: add refresh_watchlist tests covering analyst data preservation and partial failures ([`f5df863`](https://github.com/MaximeFARRE/small-cap-screener/commit/f5df8636cd3edd5def78735fdaf60feb08fd4637))

### Unknown

* Merge pull request #22 from MaximeFARRE/feat/phase18-full-refresh-workflow

Feat/phase18 full refresh workflow ([`bc24283`](https://github.com/MaximeFARRE/small-cap-screener/commit/bc2428338ba935083f9319fd8b751e5ba60fa0da))

## v0.11.0 (2026-04-26)

### Chore

* chore(release): 0.11.0 [skip ci] ([`d67a0e9`](https://github.com/MaximeFARRE/small-cap-screener/commit/d67a0e9714fc8786ff24515c047c06f9de542c36))

### Feature

* feat: add Actualiser l&#39;univers menu action wired to UniverseDiscoveryService ([`150cba7`](https://github.com/MaximeFARRE/small-cap-screener/commit/150cba7b40ca98cb89816dd4ca4523070e83729b))

* feat: add UniverseDiscoveryService with refresh_company and batch_refresh_universe ([`12b63bc`](https://github.com/MaximeFARRE/small-cap-screener/commit/12b63bc608a83e22fc58dddcca4db475936334a4))

* feat: set source_origin on company creation and add get_all_active repository query ([`fcc1f86`](https://github.com/MaximeFARRE/small-cap-screener/commit/fcc1f8696cbed7c1bdeea72d377054e958206bd0))

* feat: add source_origin and last_universe_refresh_at to Company model ([`a15d6a4`](https://github.com/MaximeFARRE/small-cap-screener/commit/a15d6a46ca93fd964afefa6afbceec21fa84bab7))

### Test

* test: add unit tests for UniverseDiscoveryService and fix datetime deprecation warning ([`e3a3422`](https://github.com/MaximeFARRE/small-cap-screener/commit/e3a34220b3fdb6ab1a3de846d3a1e8da29f68204))

### Unknown

* Merge pull request #21 from MaximeFARRE/feat/phase17-universe-refresh

Feat/phase17 universe refresh ([`4d8a92b`](https://github.com/MaximeFARRE/small-cap-screener/commit/4d8a92bcc1d059ef87da4055bc867d83fb596d6f))

## v0.10.0 (2026-04-26)

### Chore

* chore(release): 0.10.0 [skip ci] ([`e999a14`](https://github.com/MaximeFARRE/small-cap-screener/commit/e999a1483b5b64fcdede07528c544fd083eb1b13))

### Feature

* feat: show resolved ticker and suffix hint in ingestion dialog success message ([`3dee5d4`](https://github.com/MaximeFARRE/small-cap-screener/commit/3dee5d40cd76fef31e91ba614aef4d2701cb7a54))

* feat: wire ticker resolver into ingestion service and expose resolved ticker in result ([`c59c73a`](https://github.com/MaximeFARRE/small-cap-screener/commit/c59c73a64ea54eb6a1a658cbce24959eb786b3a8))

* feat: add ticker resolver service with suffix fallback and provider error classification ([`c545089`](https://github.com/MaximeFARRE/small-cap-screener/commit/c545089b3378873588df1bcf6bd6cd4af3dd89d3))

* feat: add ticker resolution dto, error kind enum and normalization helpers ([`e138669`](https://github.com/MaximeFARRE/small-cap-screener/commit/e13866973469ed12a5390f43c709b75b28354fb3))

* feat: add provider data inconsistent error type ([`337acc8`](https://github.com/MaximeFARRE/small-cap-screener/commit/337acc8e873c9285d0cad043c7165ba5581428bf))

### Refactor

* refactor: return profile directly from probe to avoid double provider call ([`1254bb0`](https://github.com/MaximeFARRE/small-cap-screener/commit/1254bb0cf5ce02bf8ecef4336f3755c3bbc577c2))

### Test

* test: add resolver integration tests to ticker ingestion service ([`d287cb2`](https://github.com/MaximeFARRE/small-cap-screener/commit/d287cb2b0a55a6409207be42b2f3453c789f874a))

### Unknown

* Merge pull request #20 from MaximeFARRE/feat/phase16-ticker-resolution

Feat/phase16 ticker resolution ([`c3acb99`](https://github.com/MaximeFARRE/small-cap-screener/commit/c3acb991c18d45c0a07b0c975d0fddae12bc1565))

## v0.9.0 (2026-04-26)

### Chore

* chore(release): 0.9.0 [skip ci] ([`5edfbc1`](https://github.com/MaximeFARRE/small-cap-screener/commit/5edfbc1eed8a547758728bcc49caf7421ffc01b0))

### Feature

* feat: pass company financial detail to detail widget on row selection ([`87a6942`](https://github.com/MaximeFARRE/small-cap-screener/commit/87a6942bfbc654055adb889be71756026b0a246d))

* feat: enrich company detail widget with financial overview, valuation and quality sections ([`7783cd6`](https://github.com/MaximeFARRE/small-cap-screener/commit/7783cd66051cc05118a2db2f18ff1a8fb0b0d048))

* feat: add company detail service with financial detail dto ([`9cd7b3d`](https://github.com/MaximeFARRE/small-cap-screener/commit/9cd7b3dcdfa20ae08564d2d83fa02b0f8726ffbb))

### Test

* test: add coverage for company detail service ([`f5f40e4`](https://github.com/MaximeFARRE/small-cap-screener/commit/f5f40e48d0a95abdb3a67c5a72cc5aae687d5f24))

### Unknown

* Merge pull request #19 from MaximeFARRE/feat/phase15-company-financial-detail

Feat/phase15 company financial detail ([`6618cfe`](https://github.com/MaximeFARRE/small-cap-screener/commit/6618cfeb716841c2479e522aa5f30c3f4f30af07))

## v0.8.0 (2026-04-26)

### Chore

* chore(release): 0.8.0 [skip ci] ([`efba7dc`](https://github.com/MaximeFARRE/small-cap-screener/commit/efba7dc45377388aba73f29f577c293eef6a3d19))

### Feature

* feat: connect add ticker dialog to main window and refresh screener on import ([`c8776fa`](https://github.com/MaximeFARRE/small-cap-screener/commit/c8776fa392206915180c1dffb07c42f848707abd))

* feat: add ticker ingestion dialog with format validation and error display ([`46c92dc`](https://github.com/MaximeFARRE/small-cap-screener/commit/46c92dc40b90418a8146bfc08aa2fbe0c6313f26))

* feat: add ticker ingestion service with format validation and pipeline orchestration ([`ebaa293`](https://github.com/MaximeFARRE/small-cap-screener/commit/ebaa2937fdcfd57b1537e0e3d9237921116bc7c4))

* feat: add isin field to company profile dto and yfinance provider ([`d618984`](https://github.com/MaximeFARRE/small-cap-screener/commit/d6189846e40334f2d1a4119f5eaaec502325383c))

### Test

* test: add coverage for ticker ingestion service ([`baca0e4`](https://github.com/MaximeFARRE/small-cap-screener/commit/baca0e4a21ab0df2fbbed7b6951086f1b19d8549))

### Unknown

* Merge pull request #18 from MaximeFARRE/feat/phase14-ticker-ingestion

Feat/phase14 ticker ingestion ([`169e040`](https://github.com/MaximeFARRE/small-cap-screener/commit/169e04000293af774ad12f650ebf75ac3fe4faa9))

## v0.7.0 (2026-04-26)

### Chore

* chore(release): 0.7.0 [skip ci] ([`a8620e0`](https://github.com/MaximeFARRE/small-cap-screener/commit/a8620e090f0d65d508a7d98d645474b8f3d3e0ae))

* chore: add pyinstaller desktop build configuration ([`9f6b776`](https://github.com/MaximeFARRE/small-cap-screener/commit/9f6b7769219ad0d745a9bdb7cab94f72c491c3d2))

### Documentation

* docs:  improve project roadmap outlining future development phases ([`0e715e4`](https://github.com/MaximeFARRE/small-cap-screener/commit/0e715e443e02abd9430c256bfa23b7c3fab9f952))

* docs: add local demo dataset runbook ([`ccda902`](https://github.com/MaximeFARRE/small-cap-screener/commit/ccda902d1d90958e3908470d1c2e8f1d6f260219))

* docs: update known limitations for current v1 scope ([`b4a1dd4`](https://github.com/MaximeFARRE/small-cap-screener/commit/b4a1dd494d5b131b6db3f25d20c07f1ce6f4c9d5))

* docs: clarify layered architecture responsibilities ([`699ab3a`](https://github.com/MaximeFARRE/small-cap-screener/commit/699ab3ae4031f6535b719aec49c8d271ea56761c))

* docs: reframe roadmap with product milestones ([`a2b2ee4`](https://github.com/MaximeFARRE/small-cap-screener/commit/a2b2ee4041fca22305d80d8c07f5cca024081551))

* docs: improve readme for recruiter audience ([`0e338eb`](https://github.com/MaximeFARRE/small-cap-screener/commit/0e338eb6221d8a9e17988a90fc6203dd30c85172))

* docs: add desktop packaging build instructions ([`005a15d`](https://github.com/MaximeFARRE/small-cap-screener/commit/005a15d1d3dc8c0e180b2f90b3debbecc8568d7a))

* docs: align roadmap and features with current delivery ([`95a78c7`](https://github.com/MaximeFARRE/small-cap-screener/commit/95a78c71462f123900d4d3ab462f8eeef60c269e))

### Feature

* feat: add reproducible local demo dataset builder ([`deac4a4`](https://github.com/MaximeFARRE/small-cap-screener/commit/deac4a4a61e5772b3f468d4890821c741fd78dbb))

* feat: add french small-cap demo seed csv ([`d97295e`](https://github.com/MaximeFARRE/small-cap-screener/commit/d97295ef8479b5beb0083fb75cafaae8e0083f53))

* feat: move app storage initialization behind service layer ([`24033a9`](https://github.com/MaximeFARRE/small-cap-screener/commit/24033a969cba96487a53811426b210a710083b7c))

### Fix

* fix: keep orm objects usable after commit ([`dd8782d`](https://github.com/MaximeFARRE/small-cap-screener/commit/dd8782da6f2d61d4c3eb50dcdc6954a3a72c33a8))

* fix: exclude non-pyside qt bindings from pyinstaller build ([`135c4a1`](https://github.com/MaximeFARRE/small-cap-screener/commit/135c4a1eb288bc1201a1c2b0625db30af59e4681))

* fix: initialize database on desktop app startup ([`8cec14d`](https://github.com/MaximeFARRE/small-cap-screener/commit/8cec14de27c669a60e19f7e195fd4fb45b43aadf))

### Test

* test: add coverage for demo dataset builder ([`209c0ea`](https://github.com/MaximeFARRE/small-cap-screener/commit/209c0ea4de9cf65610fa912e30993eea4c204211))

### Unknown

* Merge pull request #17 from MaximeFARRE/feat/phase13-global-validation

Feat/phase13 global validation ([`c60f5e8`](https://github.com/MaximeFARRE/small-cap-screener/commit/c60f5e859d0a4cb43069a811a06ee6c7083247a8))

## v0.6.0 (2026-04-26)

### Chore

* chore(release): 0.6.0 [skip ci] ([`5ca50ea`](https://github.com/MaximeFARRE/small-cap-screener/commit/5ca50eabd7b8759cb0e1bdd85678cfb049f5842c))

* chore: harmonize kpi snapshot reliability logging ([`aeee6e9`](https://github.com/MaximeFARRE/small-cap-screener/commit/aeee6e94edaf77e4466af3c7c69355ebd21b4d3e))

* chore: structure reliability logs in financial data service ([`d6a9b9a`](https://github.com/MaximeFARRE/small-cap-screener/commit/d6a9b9ad44e7989a7a4216159c02c4d101deadcc))

### Feature

* feat: add data quality score to kpi snapshots ([`3016a6f`](https://github.com/MaximeFARRE/small-cap-screener/commit/3016a6f63943324164d99e6583f905fea831de43))

* feat: add offline mode path in financial data service ([`1ea28e0`](https://github.com/MaximeFARRE/small-cap-screener/commit/1ea28e07a8a12411ac2054df528b4619ab9f2aee))

* feat: add provider retry and fallback in ingestion service ([`8203979`](https://github.com/MaximeFARRE/small-cap-screener/commit/8203979e8357157c91656a44a83b958e6bfa1f10))

* feat: add ttl cache for yfinance provider calls ([`a3ef5d1`](https://github.com/MaximeFARRE/small-cap-screener/commit/a3ef5d17fe0f6ab361953aafa0fb7e9ae964027a))

### Fix

* fix: align data quality ratio coverage with snapshot metrics ([`af0f1b4`](https://github.com/MaximeFARRE/small-cap-screener/commit/af0f1b434246dd77a14ea2eec613a33a1b34674e))

### Test

* test: add data quality score checks for kpi snapshots ([`87dfeb3`](https://github.com/MaximeFARRE/small-cap-screener/commit/87dfeb3141259f9d98d755f274f2468606b0132c))

* test: add offline mode coverage for local data ([`48a4bf7`](https://github.com/MaximeFARRE/small-cap-screener/commit/48a4bf792cf11a6ce40980c3b3a39e78dcbd18af))

* test: cover ingestion retry success and fallback ([`e5f23eb`](https://github.com/MaximeFARRE/small-cap-screener/commit/e5f23eb12228fc9fcff42bc8832840ff4e72929d))

* test: add cache hit and miss coverage for provider ([`8b7bf0b`](https://github.com/MaximeFARRE/small-cap-screener/commit/8b7bf0b60171acbad42e9fde05350ba89562618f))

### Unknown

* Merge pull request #16 from MaximeFARRE/feat/phase12-cache-strategy

Feat/phase12 cache strategy ([`5aedca3`](https://github.com/MaximeFARRE/small-cap-screener/commit/5aedca3ca1d26b91b22e9ff16478ad794d605f4e))

## v0.5.0 (2026-04-26)

### Chore

* chore(release): 0.5.0 [skip ci] ([`8629bff`](https://github.com/MaximeFARRE/small-cap-screener/commit/8629bfff6f218415740a041783d6a206e8a24b2a))

### Documentation

* docs: update roadmap for phase 10 delivery ([`8dd1a13`](https://github.com/MaximeFARRE/small-cap-screener/commit/8dd1a13e4700db3dddd99800804007c4e59f05b1))

### Feature

* feat: wire analyst workflow actions in main window ([`b2b68cf`](https://github.com/MaximeFARRE/small-cap-screener/commit/b2b68cf05fad146b0630b5de5d652872d4a23051))

* feat: add analyst actions in company detail widget ([`a118377`](https://github.com/MaximeFARRE/small-cap-screener/commit/a118377ae93564fe6e352ace928db7446eb8f48a))

* feat: add include excluded filter control ([`a9fdfb1`](https://github.com/MaximeFARRE/small-cap-screener/commit/a9fdfb1c7b200141e7e4342722aad772d5e25449))

* feat: enrich analyst detail with scoring and ranks ([`fbe1def`](https://github.com/MaximeFARRE/small-cap-screener/commit/fbe1def5760e628d97069a621640f5662a47cc55))

* feat: add screening snapshot save and read methods ([`00295ea`](https://github.com/MaximeFARRE/small-cap-screener/commit/00295eaaf43ed62299353838c461e9fddec3785a))

* feat: add screening snapshot repository accessors ([`e0945ea`](https://github.com/MaximeFARRE/small-cap-screener/commit/e0945ea74dbec0b52edec3d9a080ee1036ac3763))

* feat: add excel export for filtered screening ([`8c63461`](https://github.com/MaximeFARRE/small-cap-screener/commit/8c63461495b5becf492fdedaaa09ff250b3b46f4))

* feat: exclude watchlist flagged companies from screening ([`fa2add8`](https://github.com/MaximeFARRE/small-cap-screener/commit/fa2add8d6d4a2ee11ffc7f164bfa5d2f963ea3dd))

* feat: expose watchlist exclusion update in service ([`05c3eaa`](https://github.com/MaximeFARRE/small-cap-screener/commit/05c3eaa0c032175b1da5c6eb37412e92ff79b78e))

* feat: add watchlist exclusion flag support ([`ca9b6b2`](https://github.com/MaximeFARRE/small-cap-screener/commit/ca9b6b2bbdcd20d334ab46dd1a9ab4000a9276ac))

### Test

* test: cover unified analyst detail scenarios ([`a14abaf`](https://github.com/MaximeFARRE/small-cap-screener/commit/a14abafc3a0257d5390bf05b4859097adc656fda))

* test: add coverage for screening snapshots ([`964eb6e`](https://github.com/MaximeFARRE/small-cap-screener/commit/964eb6e4135b678d147651f21f51b4303c45e8e9))

* test: add coverage for screening excel export ([`4514025`](https://github.com/MaximeFARRE/small-cap-screener/commit/4514025bba55c27c0287f2c2180600691c423f2f))

* test: cover excluded companies screening behavior ([`836b09d`](https://github.com/MaximeFARRE/small-cap-screener/commit/836b09d053ecbc9fb8f2c1215f9ffb9f372e69c8))

* test: add coverage for watchlist exclusion updates ([`a7ba480`](https://github.com/MaximeFARRE/small-cap-screener/commit/a7ba480d886af899cb4393c0a390c390813f8b6e))

### Unknown

* Merge pull request #15 from MaximeFARRE/feat/phase11-watchlist-exclusions

Feat/phase11 watchlist exclusions ([`228a6fb`](https://github.com/MaximeFARRE/small-cap-screener/commit/228a6fbee8aa5b6f9763785d531c50668f3d4732))

## v0.4.0 (2026-04-26)

### Chore

* chore(release): 0.4.0 [skip ci] ([`dec15cf`](https://github.com/MaximeFARRE/small-cap-screener/commit/dec15cf6532ff8a1e31ff8be3b7c2a4526d581a9))

### Feature

* feat: show analyst detail in company detail panel ([`d960bc5`](https://github.com/MaximeFARRE/small-cap-screener/commit/d960bc5a3f2ae6ff6d57e38f146aefad6847a54e))

* feat: add analyst detail accessor in watchlist service ([`b82e1ca`](https://github.com/MaximeFARRE/small-cap-screener/commit/b82e1ca33427582a793ef0943eccbfd167a2c49b))

* feat: add ui controls for screening sort options ([`72ddea4`](https://github.com/MaximeFARRE/small-cap-screener/commit/72ddea41d70f8ee804c5bcd81d576d88c7c6aefc))

* feat: apply ui filters through screening service ([`912281e`](https://github.com/MaximeFARRE/small-cap-screener/commit/912281e16b5fab41fa092ee9482d6446e44d4275))

* feat: add universe filter controls in filter widget ([`b6e5436`](https://github.com/MaximeFARRE/small-cap-screener/commit/b6e54368340f8c8e309c58fd17c8b87e509f0c3b))

* feat: load scored universe in main window ([`21a4e24`](https://github.com/MaximeFARRE/small-cap-screener/commit/21a4e247a8939922f54b459403854a1b701c6cbd))

* feat: adapt company detail panel to scoring fields ([`c2b96a8`](https://github.com/MaximeFARRE/small-cap-screener/commit/c2b96a846a824924dc6669026a37c2271c505673))

* feat: show scored universe columns in screener table ([`ced4d0a`](https://github.com/MaximeFARRE/small-cap-screener/commit/ced4d0a13cddeb3945a26de5a9e1fa148fec27ce))

### Test

* test: cover analyst detail access in watchlist service ([`3dc9579`](https://github.com/MaximeFARRE/small-cap-screener/commit/3dc9579b7667bfcb53043da4c121f67e77060200))

### Unknown

* Merge pull request #14 from MaximeFARRE/feat/phase10-screener-ui

Feat/phase10 screener UI ([`3ae5dea`](https://github.com/MaximeFARRE/small-cap-screener/commit/3ae5dea909d92bd6e3d299e79646e95c270a99cc))

## v0.3.0 (2026-04-25)

### Chore

* chore(release): 0.3.0 [skip ci] ([`2d6c595`](https://github.com/MaximeFARRE/small-cap-screener/commit/2d6c59513584d5d77a878e09148acb97e787082e))

### Feature

* feat: add csv export for filtered screening ([`81829da`](https://github.com/MaximeFARRE/small-cap-screener/commit/81829da5370192eda2af96c69876e1ea239ca1d7))

* feat: add configurable universe sorting ([`da1ff59`](https://github.com/MaximeFARRE/small-cap-screener/commit/da1ff596bac886d67352eb7116bbc50c8bec7a07))

* feat: add universe screening filters in service ([`c48c7b7`](https://github.com/MaximeFARRE/small-cap-screener/commit/c48c7b7d12b5e1583570f6b6c24d5a4ed2b60d2f))

* feat: add investable universe listing in screening service ([`dc2acf3`](https://github.com/MaximeFARRE/small-cap-screener/commit/dc2acf3c1b8bf2e2a0a8974d14a8153834d44c45))

### Test

* test: add coverage for screening csv export ([`0c2d07a`](https://github.com/MaximeFARRE/small-cap-screener/commit/0c2d07a485e8c58c58f85c5d274b86cfbe6cc67d))

* test: add coverage for configurable screening sort ([`6e55858`](https://github.com/MaximeFARRE/small-cap-screener/commit/6e558582d08c6b25418eb7fb6de5b6931c5f1634))

* test: add coverage for universe screening filters ([`8994f0a`](https://github.com/MaximeFARRE/small-cap-screener/commit/8994f0a6640fd615e7663e1f4118c1aa3538969e))

* test: add coverage for investable universe scoring view ([`a67868d`](https://github.com/MaximeFARRE/small-cap-screener/commit/a67868d08004f376a07ce8405377be80cb6a13a1))

### Unknown

* Merge pull request #13 from MaximeFARRE/feat/phase9-screening-service

Feat/phase9 screening service ([`d81cc29`](https://github.com/MaximeFARRE/small-cap-screener/commit/d81cc29c3b15fd1dd96d5d8cde31df4ec6997597))

## v0.2.0 (2026-04-25)

### Chore

* chore(release): 0.2.0 [skip ci] ([`4cdeb84`](https://github.com/MaximeFARRE/small-cap-screener/commit/4cdeb840faf7e3f62387f3c81201e0367aa9750e))

* chore: simplify semantic-release workflow on main ([`0740b25`](https://github.com/MaximeFARRE/small-cap-screener/commit/0740b25f7ce5e9da11949039c996e4820ab97457))

* chore: align semantic-release config with main branch ([`403d30f`](https://github.com/MaximeFARRE/small-cap-screener/commit/403d30f6270707bd39a9c207597e818fa0b901f2))

### Documentation

* docs: document semantic-release workflow ([`5ee1b49`](https://github.com/MaximeFARRE/small-cap-screener/commit/5ee1b49ec7d5b5ad794641a7f237db4e68b6ac0b))

* docs: document none and deduplication rules ([`2569e09`](https://github.com/MaximeFARRE/small-cap-screener/commit/2569e091812bea875a8f5e40bcd7a17a660acca7))

* docs: add normalization conventions overview ([`78edbd1`](https://github.com/MaximeFARRE/small-cap-screener/commit/78edbd11534e15023a7e348a357a2714f408afe0))

* docs: enforce micro-commit cadence during development ([`25251b8`](https://github.com/MaximeFARRE/small-cap-screener/commit/25251b8c2cbddee2b75acd0cece79b5a9bbb76e8))

* docs: replace limitations template with current state ([`c80c94e`](https://github.com/MaximeFARRE/small-cap-screener/commit/c80c94eefc6ff262c03a9c18725c203eb6d88847))

* docs: align development branch workflow ([`b17b655`](https://github.com/MaximeFARRE/small-cap-screener/commit/b17b6550c2f01432f7e410fa0dc8e42ae2ee570b))

* docs: add branch switch push rule ([`9d4c205`](https://github.com/MaximeFARRE/small-cap-screener/commit/9d4c20519a017b3139cf5922a9b03fe1c60c6e3b))

* docs: add project roadmap detailing development phases ([`93c5d3e`](https://github.com/MaximeFARRE/small-cap-screener/commit/93c5d3ebc74e00dfec2717bcf863cebf968c873e))

### Feature

* feat: add watchlist listing enriched with snapshot rankings ([`bb28157`](https://github.com/MaximeFARRE/small-cap-screener/commit/bb28157f8cd9d3199fde7a0c30d3b1240c137215))

* feat: expose watchlist status update via service ([`cc27188`](https://github.com/MaximeFARRE/small-cap-screener/commit/cc271886c2c5f2c6110de5e3da8b7ba8799ef8bf))

* feat: add watchlist status field and repository update ([`e8dca8d`](https://github.com/MaximeFARRE/small-cap-screener/commit/e8dca8d0a959acbebd1d1870592442b226ae5447))

* feat: expose watchlist note update via service ([`da6d08f`](https://github.com/MaximeFARRE/small-cap-screener/commit/da6d08f7497d894bd79e827d9f13d96fab18f5a4))

* feat: add watchlist note update repository method ([`9d8f68e`](https://github.com/MaximeFARRE/small-cap-screener/commit/9d8f68eca97a56c8598142fc357fcf01bef3c90c))

* feat: add watchlist repository and orchestration service ([`f96c5b8`](https://github.com/MaximeFARRE/small-cap-screener/commit/f96c5b8f9c3e57f8ee67e7a87775e276f532b266))

* feat: add watchlist entry model and base mapping ([`1263ada`](https://github.com/MaximeFARRE/small-cap-screener/commit/1263ada2a33553d54529cbbd5d401f6d3d237d06))

* feat: add deterministic score explanation in scoring service ([`b518b75`](https://github.com/MaximeFARRE/small-cap-screener/commit/b518b75a2407cc13007e0a5dc29c684ed716268a))

* feat: pass company sector to universe ranking ([`89deb23`](https://github.com/MaximeFARRE/small-cap-screener/commit/89deb239c3f871dc875cdbd56c93cc326b4889a1))

* feat: add sector rank in scoring ranking ([`5891d24`](https://github.com/MaximeFARRE/small-cap-screener/commit/5891d24a218f78025ee332cffa527981cf5af140))

* feat: add universe ranking from snapshot total scores ([`06edfba`](https://github.com/MaximeFARRE/small-cap-screener/commit/06edfbaccdcfa0e5bc5ab1915ca00d70d8f7fadc))

* feat: add deterministic total score ranking in scoring service ([`ae4bf83`](https://github.com/MaximeFARRE/small-cap-screener/commit/ae4bf837d17e63b068d3b5c5de0cd80d6fb0b65e))

* feat: apply scoring service in kpi snapshot pipeline ([`ba05d63`](https://github.com/MaximeFARRE/small-cap-screener/commit/ba05d63ba224524a65d5d7d743561b1e6e9be767))

* feat: add snapshot scoring service v1 ([`2214037`](https://github.com/MaximeFARRE/small-cap-screener/commit/2214037f67b0a37d5069cbef329479fc3ce8ebe9))

* feat: add resilient universe kpi refresh loop ([`e07434e`](https://github.com/MaximeFARRE/small-cap-screener/commit/e07434ece4d3ad9f3c3c6cda883b9b863f4de15c))

* feat: resolve investable universe for kpi refresh ([`7545940`](https://github.com/MaximeFARRE/small-cap-screener/commit/7545940942287c5e169cf20fff6ee4adb3fda555))

* feat: add universe kpi refresh result models ([`3963fdc`](https://github.com/MaximeFARRE/small-cap-screener/commit/3963fdcde9cb2db4f18f2f7afddc8906b98dc467))

* feat: compute and upsert kpi snapshots ([`b625315`](https://github.com/MaximeFARRE/small-cap-screener/commit/b6253156f5f24c4ff5f5ff817a7c196af9f058ad))

* feat: add kpi snapshot service scaffold ([`cce9572`](https://github.com/MaximeFARRE/small-cap-screener/commit/cce9572593c219bd1737b3b7658c4c1a2736b3c1))

* feat: centralize v1 ratios in ratio service ([`2c3da7b`](https://github.com/MaximeFARRE/small-cap-screener/commit/2c3da7b6529452d3c48d8c4d4f4113534da5dd57))

* feat: apply normalization before validation and storage ([`d3fcac2`](https://github.com/MaximeFARRE/small-cap-screener/commit/d3fcac2865e627142045e648e254546a757e8b29))

* feat: preserve full statement fields in normalization ([`6dbed82`](https://github.com/MaximeFARRE/small-cap-screener/commit/6dbed82f1ce7397638722af30ed1982e6252bae5))

* feat: normalize financial records and dates ([`8a031c4`](https://github.com/MaximeFARRE/small-cap-screener/commit/8a031c423f806a6719b36c7b61497a6932ba1347))

* feat: normalize company identifiers and core fields ([`196727f`](https://github.com/MaximeFARRE/small-cap-screener/commit/196727fc8531f1275482a605f42372e30b34b21c))

* feat: add normalization service contracts ([`4c25e8a`](https://github.com/MaximeFARRE/small-cap-screener/commit/4c25e8ab44026caf5e1c762813bc47b0ec982c28))

* feat: add ingestion lifecycle logging ([`19c7528`](https://github.com/MaximeFARRE/small-cap-screener/commit/19c752829dce2924cf1bf4a53a88808beb3751df))

* feat: log provider retries and final failure ([`fdbbe24`](https://github.com/MaximeFARRE/small-cap-screener/commit/fdbbe24fd8b5ca8e19c7cbb309f9630441d22a76))

* feat: validate financial payload before storage ([`9143208`](https://github.com/MaximeFARRE/small-cap-screener/commit/9143208a91b33962d04739b947746689c329a9a6))

* feat: add payload-based market data sync ([`f08c307`](https://github.com/MaximeFARRE/small-cap-screener/commit/f08c3072278ee7b702a63eced3ffa8602843d5ef))

* feat: add external data validation service ([`6842d28`](https://github.com/MaximeFARRE/small-cap-screener/commit/6842d28f5722e13233714e8d781271c029634a85))

* feat: add financial data refresh workflows ([`4f4e232`](https://github.com/MaximeFARRE/small-cap-screener/commit/4f4e232968b72b9a80753d164e6fea97ccca8c5f))

* feat: add financial data fetch orchestration service ([`54bd623`](https://github.com/MaximeFARRE/small-cap-screener/commit/54bd623735478e919cd22f09ac3655a986bd9428))

* feat: add stable universe summary metrics ([`c7af2ec`](https://github.com/MaximeFARRE/small-cap-screener/commit/c7af2ec98f031dcfcf2bc2783240eddce05745af))

* feat: add universe service seed load and refresh orchestration ([`d1d4fd0`](https://github.com/MaximeFARRE/small-cap-screener/commit/d1d4fd08e038c7b0e8211a8dd5e7eb0aba193aa1))

* feat: add investable universe filters in company repository ([`f072001`](https://github.com/MaximeFARRE/small-cap-screener/commit/f072001466dff10bddac563e687865da0c86030a))

* feat: add company metadata fields for investable filtering ([`7fe0d57`](https://github.com/MaximeFARRE/small-cap-screener/commit/7fe0d57663350611cc0293d0943275085350603b))

* feat: add bulk seed universe import for companies ([`6029fdd`](https://github.com/MaximeFARRE/small-cap-screener/commit/6029fdd17115e33c65f84184a80e9ec3ac43170a))

* feat: attach source and fetched timestamps to provider outputs ([`1276b44`](https://github.com/MaximeFARRE/small-cap-screener/commit/1276b449a8c859d176c684361be62cb02175a34d))

* feat: extend provider dto contract with source metadata ([`4fd1843`](https://github.com/MaximeFARRE/small-cap-screener/commit/4fd1843b1b07932d5ba756211cf29045f4d46c37))

* feat: map seed rows to validated universe entries ([`2ed8db1`](https://github.com/MaximeFARRE/small-cap-screener/commit/2ed8db1d5d808a9738bbd8976c9f3eae0d19fae9))

* feat: add seed csv loading and required column checks ([`1e7e6ed`](https://github.com/MaximeFARRE/small-cap-screener/commit/1e7e6ed910240660bc93feb150d7308b53f0dc4c))

* feat: add seed universe repository contracts ([`e164ae3`](https://github.com/MaximeFARRE/small-cap-screener/commit/e164ae39711c23a393b9da86ad527373715d9664))

* feat: add dividend and split retrieval in yfinance provider ([`297356b`](https://github.com/MaximeFARRE/small-cap-screener/commit/297356b0102b2a2080e0a2eea7bc4990cdc1633f))

* feat: add profile and current market data provider methods ([`9061609`](https://github.com/MaximeFARRE/small-cap-screener/commit/9061609a4429f3148fe8f5306b75f5c9fe209247))

* feat: add provider v1 data contracts ([`f504d82`](https://github.com/MaximeFARRE/small-cap-screener/commit/f504d825a6889dd3193ce8d417b51926ddd2c3f0))

* feat: add ingestion-ready repository upsert and lookup methods ([`e930eb9`](https://github.com/MaximeFARRE/small-cap-screener/commit/e930eb92e8ff39b7b6a806a1f376c2afb64c893c))

* feat: add repositories for kpi and corporate actions ([`de57589`](https://github.com/MaximeFARRE/small-cap-screener/commit/de5758967a35863e320d5f3dbea7082f583267c1))

* feat: add phase 1 financial data models ([`2e85d9d`](https://github.com/MaximeFARRE/small-cap-screener/commit/2e85d9d91b3a9b78562efb9891c674d49ff7e34e))

* feat: add launch.bat and __main__ entry point for one-click startup ([`d3ae1bd`](https://github.com/MaximeFARRE/small-cap-screener/commit/d3ae1bd23bf5367037f0bd5af9d8d383b67652bb))

* feat: add File menu with CSV and Excel export actions ([`0d0d1ad`](https://github.com/MaximeFARRE/small-cap-screener/commit/0d0d1ad7023de0b9f75a47e958899413cd6140b9))

* feat: add export_service with ExportRow, to_csv and to_excel ([`7effe49`](https://github.com/MaximeFARRE/small-cap-screener/commit/7effe4927b0820bec725dd338f66a104d4865063))

* feat: add filter dock widget (QDockWidget) to MainWindow left panel ([`dd109e2`](https://github.com/MaximeFARRE/small-cap-screener/commit/dd109e23befbd042a7df03573ee5f6d2243c62d6))

* feat: add FilterWidget with criteria inputs and filters_applied signal ([`b1eaa64`](https://github.com/MaximeFARRE/small-cap-screener/commit/b1eaa64f8a4bba07662664bc1b1c3885c43a451e))

* feat: split MainWindow into screener/detail panes with QSplitter ([`d9b018c`](https://github.com/MaximeFARRE/small-cap-screener/commit/d9b018c5b092ddcc8f68088301bff870472ee80a))

* feat: emit row_selected/selection_cleared signals on table selection change ([`f62c671`](https://github.com/MaximeFARRE/small-cap-screener/commit/f62c6711a44640e495962d08b74658420ad0305a))

* feat: add CompanyDetailWidget showing all ratios for selected company ([`4ff61ab`](https://github.com/MaximeFARRE/small-cap-screener/commit/4ff61abd5f9cf56895426abcad1023e8e47c592f))

* feat: wire ScreenerWidget into MainWindow as central widget ([`2ee6cf0`](https://github.com/MaximeFARRE/small-cap-screener/commit/2ee6cf0d59fe0d0e642f2e2eaa1e486d883e81ed))

* feat: add ScreenerWidget with QTableView wired to CompanyTableModel ([`23c7d40`](https://github.com/MaximeFARRE/small-cap-screener/commit/23c7d408513c885d6da493185d78c03b93fcd4cf))

* feat: add CompanyTableModel (QAbstractTableModel) wrapping ScreenerRow list ([`72462c9`](https://github.com/MaximeFARRE/small-cap-screener/commit/72462c9e19d58df9ea18d06f32c674925640a962))

* feat: add initial UI scaffold with MainWindow and app entry point ([`b44de97`](https://github.com/MaximeFARRE/small-cap-screener/commit/b44de977d2acce7ada25c961cfa8680d4a60c9f4))

### Fix

* fix: use semantic-release version instead of publish to trigger version bump and GitHub release creation ([`91a29c0`](https://github.com/MaximeFARRE/small-cap-screener/commit/91a29c0cbf5598a413f7d6007bb1d654b338be31))

* fix: deduplicate currency missing warnings ([`8f3df77`](https://github.com/MaximeFARRE/small-cap-screener/commit/8f3df77fde17c341a301daddbee56f9ca38321ce))

* fix: clarify snapshot roles and enforce stable uniqueness ([`ef8bc7f`](https://github.com/MaximeFARRE/small-cap-screener/commit/ef8bc7f447f8e032caa771aa199d20e962de0a7f))

* fix: handle semantic-release bootstrap without tags ([`2c217e5`](https://github.com/MaximeFARRE/small-cap-screener/commit/2c217e5cb2d37082b60cc39c2df5b825085aac56))

### Refactor

* refactor: centralize kpi context loading errors ([`e80f630`](https://github.com/MaximeFARRE/small-cap-screener/commit/e80f6309d3e02cc92af0d98d9b11fc0b104268a4))

### Test

* test: cover watchlist listing with score and rank data ([`34b2050`](https://github.com/MaximeFARRE/small-cap-screener/commit/34b2050b6d2507403b1485b47d218373c99c741a))

* test: add repository coverage for watchlist entries ([`bf0919c`](https://github.com/MaximeFARRE/small-cap-screener/commit/bf0919cec6fb986c764b9c8e4d0f21f43b40f900))

* test: add coverage for score explanation behavior ([`c553005`](https://github.com/MaximeFARRE/small-cap-screener/commit/c553005b12df6e712a0fe82de145c80f660fb96e))

* test: cover sector ranking with missing data ([`68a3096`](https://github.com/MaximeFARRE/small-cap-screener/commit/68a3096d44f6ad065f827c849358a2db00ab38ce))

* test: add coverage for universe ranking by total score ([`8795c2a`](https://github.com/MaximeFARRE/small-cap-screener/commit/8795c2a5acbb1b32bd396101bf0f718e2eb0e047))

* test: verify snapshot refresh persists scoring keys ([`8fb8824`](https://github.com/MaximeFARRE/small-cap-screener/commit/8fb8824b636c3432ffec63e4b3f9304eab1eb8ac))

* test: add coverage for snapshot scoring service ([`31fee59`](https://github.com/MaximeFARRE/small-cap-screener/commit/31fee59a140ff43e2938b4671059902578704159))

* test: add partial failure coverage for universe refresh ([`be27614`](https://github.com/MaximeFARRE/small-cap-screener/commit/be276143ee0672e28f954633bae26b461886eae9))

* test: add universe kpi refresh success path ([`b88fde1`](https://github.com/MaximeFARRE/small-cap-screener/commit/b88fde1d6ad2f4f58d93df6a258ca5f408b3a45e))

* test: cover kpi snapshot price fallback and growth ([`d153610`](https://github.com/MaximeFARRE/small-cap-screener/commit/d15361057b08ac5c0d514878f7bd8fdc3bb912c9))

* test: add kpi snapshot missing-data and consistency cases ([`aa46c5c`](https://github.com/MaximeFARRE/small-cap-screener/commit/aa46c5c13742c42a93f24e16a79b544988f8cdf2))

* test: add kpi snapshot create and update cases ([`bce4133`](https://github.com/MaximeFARRE/small-cap-screener/commit/bce41336c6d6dbdc023b4d6c42bdc481429c4c01))

* test: validate ratio service class behavior ([`8eab213`](https://github.com/MaximeFARRE/small-cap-screener/commit/8eab213c65d1ece962072bb62b18d4de09882ece))

* test: add v1 ratio calculations and edge cases ([`9d3dc3a`](https://github.com/MaximeFARRE/small-cap-screener/commit/9d3dc3a23420e351e6044f587900b10e459c08dc))

* test: cover normalization stage in ingestion pipeline ([`8b2a724`](https://github.com/MaximeFARRE/small-cap-screener/commit/8b2a7248a26cf8e1635f4085277f9dd0cd2edb7f))

* test: add invalid identifier normalization cases ([`45d14e2`](https://github.com/MaximeFARRE/small-cap-screener/commit/45d14e2bf7762d1fc37c206ddb0fbd25dc5371b5))

* test: add normalization coverage for dates and missing values ([`f84e7c4`](https://github.com/MaximeFARRE/small-cap-screener/commit/f84e7c460acfa3e96bfe9cb1504a629e6f8f9894))

* test: add normalization checks for identifiers ([`03d7251`](https://github.com/MaximeFARRE/small-cap-screener/commit/03d7251d68b39adc1095c56d2b2e701a3343bd06))

* test: add ingestion logging coverage ([`2def75e`](https://github.com/MaximeFARRE/small-cap-screener/commit/2def75e35c82f6823d0f84cf7d1aedfd950fbf34))

* test: add financial data service ingestion scenarios ([`133c753`](https://github.com/MaximeFARRE/small-cap-screener/commit/133c75314bb5f1592562a89892171c55bf5a8f98))

* test: add stable universe summary service scenario ([`85e4666`](https://github.com/MaximeFARRE/small-cap-screener/commit/85e46661e5b72163870c0d083898cea45c8149f7))

* test: cover seed loading and investable universe refresh ([`6917905`](https://github.com/MaximeFARRE/small-cap-screener/commit/691790576fb5962395e29692c1adc99098bb7d52))

* test: add company universe filtering scenarios ([`00f365a`](https://github.com/MaximeFARRE/small-cap-screener/commit/00f365aa6a23164dff4cd079d41cfdc9acd0d254))

* test: add dto contract coverage for provider base ([`2c871ee`](https://github.com/MaximeFARRE/small-cap-screener/commit/2c871eef7a410671cb84d131126cfa2e59eacb60))

* test: cover empty-file and invalid-row seed errors ([`ab11248`](https://github.com/MaximeFARRE/small-cap-screener/commit/ab11248f0b8e1100ed417b9522ef54c36e832bd4))

* test: add seed csv success and missing-column cases ([`c440236`](https://github.com/MaximeFARRE/small-cap-screener/commit/c440236be87c89271f71408eb80323b35877b60d))

* test: validate dividend and split provider behavior ([`07e197e`](https://github.com/MaximeFARRE/small-cap-screener/commit/07e197ef148259494eec41fa065e73801e5520df))

* test: cover company profile and market data methods ([`9ed85e4`](https://github.com/MaximeFARRE/small-cap-screener/commit/9ed85e4ccdd45b0fb2dd8a58e1916361a10e2d60))

* test: add coverage for phase 1 repositories ([`14d749a`](https://github.com/MaximeFARRE/small-cap-screener/commit/14d749a1b507d6adb829b1e54bb54e68e107ee9a))

### Unknown

* Merge pull request #12 from MaximeFARRE/feat/phase8-watchlist-service

Feat/phase8 watchlist service ([`80b0aa1`](https://github.com/MaximeFARRE/small-cap-screener/commit/80b0aa18364143dbb84692f6b6b240d1a34d9a33))

* Merge pull request #11 from MaximeFARRE/feat/phase7

Feat/phase7 ([`cbdbe0e`](https://github.com/MaximeFARRE/small-cap-screener/commit/cbdbe0e5e878bd878738f2ca57d4d3ed661b5e38))

* Merge pull request #10 from MaximeFARRE/feat/phase6-ratio-service

Feat/phase6 ratio service ([`bb88de4`](https://github.com/MaximeFARRE/small-cap-screener/commit/bb88de48dd228ecf4de9492ffb0d032d42d34290))

* Merge pull request #9 from MaximeFARRE/feat/phase5-normalization

Feat/phase5 normalization ([`433affd`](https://github.com/MaximeFARRE/small-cap-screener/commit/433affd1272700258affcb60a3a216cfeb8990c7))

* Merge pull request #8 from MaximeFARRE/feat/phase4-financial-ingestion

Feat/phase4 financial ingestion ([`5ebeefb`](https://github.com/MaximeFARRE/small-cap-screener/commit/5ebeefb5007f1f9311416e98d7bfde9f9e917d83))

* Merge pull request #7 from MaximeFARRE/feat/phase3-seed-import

Feat/phase3 seed import ([`f48213c`](https://github.com/MaximeFARRE/small-cap-screener/commit/f48213ce8ff8cf1f05929d8e7be86e5ddae054cf))

* Merge pull request #6 from MaximeFARRE/feat/phase2-provider-v1

Feat/phase2 provider v1 ([`90a365d`](https://github.com/MaximeFARRE/small-cap-screener/commit/90a365ded48b1763c12d5f1db0f8c31ffe45b8f5))

* Merge pull request #5 from MaximeFARRE/feat/phase1-data-models

Feat/phase1 data models ([`63aef9e`](https://github.com/MaximeFARRE/small-cap-screener/commit/63aef9ed3ae27b3e64ec6eef65538e1fa96f35ae))

* Merge pull request #4 from MaximeFARRE/docs/update-docs

docs: align phase 0 workflow and project limitations ([`5cd3f56`](https://github.com/MaximeFARRE/small-cap-screener/commit/5cd3f56f438648e97867cdbacddc1a90f6097ae1))

* Merge pull request #3 from MaximeFARRE/feat/ui-main-window

Feat/UI main window ([`32da6dc`](https://github.com/MaximeFARRE/small-cap-screener/commit/32da6dc735423b5e3e88515ac77a1eeaedeea4f0))

* Merge pull request #2 from MaximeFARRE/fix/ruff-up042-periodtype-strenum

fix: handle semantic-release bootstrap without tags ([`ab72e5c`](https://github.com/MaximeFARRE/small-cap-screener/commit/ab72e5c9125190efdf2552b9e264b47145790606))

## v0.1.0 (2026-04-24)

### Chore

* chore: reformat codebase with black ([`5323f49`](https://github.com/MaximeFARRE/small-cap-screener/commit/5323f495323f3541379d2553d27f8cb15ecdd3aa))

* chore: add yfinance&gt;=0.2 to requirements and fix file encoding (UTF-16→UTF-8) ([`f61c916`](https://github.com/MaximeFARRE/small-cap-screener/commit/f61c91699eed79cf91e92deac8b9c35247a6b1f9))

* chore: align project metadata and dependencies with STACK.md

- Fix pyproject.toml project name (was placeholder &#34;project-name&#34;)
- Replace bloated requirements.txt (200+ packages) with 8 STACK.md-defined deps
- Add __init__.py stubs to repositories/, services/, ui/ so they are proper packages
- Remove stale .gitkeep files from src/ subdirectories
- Strip .env.example to project-relevant variables only
- Remove Node.js/TypeScript/Rust/Java/C++ entries from .gitignore
- Simplify CODEX.md to a redirect to AGENTS.md (was a near-duplicate)
- Rewrite ROADMAP.md with concrete project phases replacing generic boilerplate
- Add first-time setup section to DEVELOPMENT.md (pre-commit install)
- Delete PROMPTS.md (scaffolding artifact, not project documentation)

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`d912afc`](https://github.com/MaximeFARRE/small-cap-screener/commit/d912afcf87f35056f217fb0476858de140ff19b8))

* chore: initialize CI/CD pipelines, pre-commit hooks, and dependency management configurations ([`c28b0eb`](https://github.com/MaximeFARRE/small-cap-screener/commit/c28b0eb237a60e77255c05ea0aeea7943b05ace1))

### Documentation

* docs: mark Phase 1 and Phase 2 as complete in ROADMAP ([`511b7a0`](https://github.com/MaximeFARRE/small-cap-screener/commit/511b7a026889bad34284427fe2488699a18e8e9c))

* docs: initialize project documentation and define architectural principles in README, STACK, and new ARCHITECTURE files. ([`f66af04`](https://github.com/MaximeFARRE/small-cap-screener/commit/f66af04736f8ec8d51f8d6b1a5d4bb4b0314566e))

### Feature

* feat: add market_data_repository with sync_company pipeline (upsert company, store prices, store financials) ([`61bc16c`](https://github.com/MaximeFARRE/small-cap-screener/commit/61bc16ca079b4ed94556c007914a3a8499950670))

* feat: add price_history_repository (create, get_by_company, get_by_company_and_date, get_latest, delete) ([`08358e0`](https://github.com/MaximeFARRE/small-cap-screener/commit/08358e076871e13fdd473b31b039cce9b66d2d78))

* feat: implement YFinanceProvider.get_current_price with currentPrice/regularMarketPrice fallback ([`4aba9f5`](https://github.com/MaximeFARRE/small-cap-screener/commit/4aba9f5b2962df391eb88907a3786812b60885ea))

* feat: implement YFinanceProvider.get_financial_statements with EBITDA fallback computation ([`87ae5ab`](https://github.com/MaximeFARRE/small-cap-screener/commit/87ae5ab2be1b2b852c250fcbf5816723eee02916))

* feat: implement YFinanceProvider.get_price_history with OHLCV parsing ([`15254dd`](https://github.com/MaximeFARRE/small-cap-screener/commit/15254ddc398135160f2e731a62e315c35283761c))

* feat: implement YFinanceProvider.get_company_info with retry logic ([`b5c4827`](https://github.com/MaximeFARRE/small-cap-screener/commit/b5c48275515cd95503b3e6e5093b838c80483962))

* feat: add BaseProvider abstract interface — implement to swap data source without changing any other layer ([`6c14dee`](https://github.com/MaximeFARRE/small-cap-screener/commit/6c14deea53ef874d2e38fc3a9019feb06be54bae))

* feat: add provider DTOs (CompanyInfo, PriceRecord, FinancialData) and exception types to base.py ([`51cb72c`](https://github.com/MaximeFARRE/small-cap-screener/commit/51cb72c5d11417e17261779db27ae59edad3e0c5))

* feat: add screening_service with ScreeningCriteria, apply_filters, and score-sorted ScreeningResult ([`469d421`](https://github.com/MaximeFARRE/small-cap-screener/commit/469d4217d06b222fdca54f21a47cd94144f8a102))

* feat: add scoring_service with weighted multi-factor score (0-100) for CompanyRatios ([`5a5f750`](https://github.com/MaximeFARRE/small-cap-screener/commit/5a5f750ada41b1188038b5a13fa73e8fbd95afea))

* feat: add CompanyRatios dataclass and compute_all to ratio_service ([`cdcbdd7`](https://github.com/MaximeFARRE/small-cap-screener/commit/cdcbdd76585c860e058131744cfb1413da61d8ff))

* feat: add leverage ratios to ratio_service (debt/equity, net_debt/EBITDA) ([`c36fd0d`](https://github.com/MaximeFARRE/small-cap-screener/commit/c36fd0d816a9f33b579f32d426091f300a34001f))

* feat: add profitability ratios to ratio_service (ROE, ROA, EBIT/EBITDA/net margin) ([`bef642d`](https://github.com/MaximeFARRE/small-cap-screener/commit/bef642da05e90be78172ea61808b68064bd57f5f))

* feat: add valuation ratios to ratio_service (P/E, P/B, EV/EBITDA, EV/EBIT, P/FCF) ([`1306637`](https://github.com/MaximeFARRE/small-cap-screener/commit/1306637e393a317f8e4f095964e269260b4abc2b))

* feat: add market_cap and enterprise_value helpers to ratio_service ([`03f410e`](https://github.com/MaximeFARRE/small-cap-screener/commit/03f410e9c7b50fd0ed6e20d94f3b31340cc928e0))

* feat: add Company and FinancialStatement repositories with full test coverage

- company_repository: create, get_by_id, get_by_isin, get_all, search_by_name,
  update, delete — all operations flush within the caller&#39;s session
- financial_statement_repository: create, get_by_id, get_by_company (desc),
  get_by_company_and_year (with PeriodType), delete
- tests/conftest.py: in-memory SQLite fixture shared across test modules
- 16 tests covering happy paths, empty results, and not-found cases
- Add src/__init__.py and pyproject.toml pythonpath so pytest resolves src.*

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`932e882`](https://github.com/MaximeFARRE/small-cap-screener/commit/932e88245859a3ab18d78abe3c5880f2abd3e094))

* feat: implement core data models and database session management

- database.py: DeclarativeBase, engine, SessionLocal, init_db(), get_session()
  context manager; auto-creates data/ directory for SQLite path
- Company: isin (unique), ticker, name, sector, market, currency, timestamps
- FinancialStatement: fiscal_year, PeriodType enum, 10 optional financial fields
- PriceHistory: OHLCV + adjusted_close, unique constraint on (company_id, date)
- ScreeningSnapshot: name, filters/company_ids/scores stored as JSON columns
- Add data/.gitkeep so SQLite directory exists in the working tree

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`9c5ca3e`](https://github.com/MaximeFARRE/small-cap-screener/commit/9c5ca3e29376de79c727ace39d8d7d3553b7c011))

* feat: implement core data models and database repository layer ([`6d91c34`](https://github.com/MaximeFARRE/small-cap-screener/commit/6d91c34020fe3a967de90da0f5453c798eaf284b))

### Fix

* fix: raise line length to 120 ([`a11c999`](https://github.com/MaximeFARRE/small-cap-screener/commit/a11c999b9ba972f49b9ef3e3c1acd66d76e55933))

* fix: resolve all ruff (E501, UP035, F401, I001) and black formatting violations ([`d55753d`](https://github.com/MaximeFARRE/small-cap-screener/commit/d55753d30d771292799a349808fdc7419eb93a9d))

### Test

* test: add 7 unit tests for market_data_repository (create, upsert, dedup prices/statements) ([`494aec6`](https://github.com/MaximeFARRE/small-cap-screener/commit/494aec680f93eac532d61214e4b005ecae86d5cb))

* test: add 7 unit tests for price_history_repository (CRUD, ordering, latest, not-found) ([`f1fe7c3`](https://github.com/MaximeFARRE/small-cap-screener/commit/f1fe7c316016de917a275d719c5d5c1272ffa3b0))

* test: add 10 unit tests for YFinanceProvider (all yfinance calls mocked, retry verified) ([`952f725`](https://github.com/MaximeFARRE/small-cap-screener/commit/952f725466f784c78754ccc0457405282637c408))

* test: add 8 unit tests for screening_service (filters, sorting, None passthrough, empty input) ([`94b469a`](https://github.com/MaximeFARRE/small-cap-screener/commit/94b469afb6d5ff4d343bf5ba712a8a14c3687e7d))

* test: add 7 unit tests for scoring_service (perfect/worst score, missing data, ordering) ([`d9fa441`](https://github.com/MaximeFARRE/small-cap-screener/commit/d9fa441d2c2b60516a3a1618b0a6dd2c4e46d18c))

* test: add 25 unit tests for ratio_service covering all ratios and edge cases ([`7144e43`](https://github.com/MaximeFARRE/small-cap-screener/commit/7144e437c40ebf78db47df34434e1ce9cfb7aad7))

### Unknown

* Merge pull request #1 from MaximeFARRE/fix/ruff-up042-periodtype-strenum

Fix Ruff and Black line length configuration ([`a533c50`](https://github.com/MaximeFARRE/small-cap-screener/commit/a533c50fce6a387c74faff4a5a73428faca58615))

* Initial commit ([`3c3d200`](https://github.com/MaximeFARRE/small-cap-screener/commit/3c3d2000a11901d6be7e33e85394d7cf6a3d91da))
