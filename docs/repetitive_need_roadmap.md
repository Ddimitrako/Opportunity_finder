# Opportunity Finder: Repetitive Need Roadmap

## Product thesis

Το Opportunity Finder πρέπει να μετακινηθεί από "βρίσκω διαγωνισμούς" σε
"αναγνωρίζω επαναλαμβανόμενες ανάγκες που μπορούν να γίνουν reusable product ή
service package".

Η αξία δεν είναι μόνο το σημερινό tender. Είναι το pattern πίσω από πολλά μικρά
έργα: ποιοι φορείς ζητούν παρόμοια πράγματα, σε τι budget, με ποια συχνότητα,
ποιοι τα παίρνουν, και αν η ανάγκη μπορεί να καλυφθεί με open-source based
product, implementation package ή managed service.

## Current implementation

Το app έχει ήδη καλή βάση για αυτό:

- `backend/app/sources/khmdhs.py`: ψάχνει ΚΗΜΔΗΣ requests με `title`,
  `cpvItems`, `dateFrom/dateTo`, `totalCostFrom/totalCostTo`, και κρατά
  `referenceNumber`, buyer, CPV, budget, dates, object details και source payload.
- `backend/app/sources/ted.py`: τραβά active TED notices για Ελλάδα με CPV και
  notice metadata.
- `backend/app/scoring.py`: δίνει fit score με βάση CPV, budget, keywords,
  buyer type, deadline, red flags και πιθανό package match.
- `backend/app/services/details.py`: εμπλουτίζει ΚΗΜΔΗΣ/TED records με documents
  και procurement lifecycle guidance. Για ΚΗΜΔΗΣ χρησιμοποιεί `adamChain`.
- `backend/app/services/buyer_intelligence.py`: κοιτά ιστορικό αγοραστή από
  ΚΗΜΔΗΣ και signals από Διαύγεια, συμπεριλαμβανομένων πιθανών αναδόχων,
  ποσών και παρόμοιων procurement signals.
- `backend/app/services/briefs.py`: διαβάζει έγγραφα/PDF και προαιρετικά παράγει
  AI brief με OpenAI.
- `frontend/src/App.tsx`: ήδη εμφανίζει search, source runs, details drawer,
  buyer intelligence graph, Diavgeia signals, bookmarks και AI brief.

Το κενό: το app αξιολογεί καλά μεμονωμένες ευκαιρίες, αλλά δεν παράγει ακόμα
first-class entities τύπου "Need Pattern", "Repeat Buyer", "Reusable Package",
"Competitor/Winner Pattern" και "Market Signal".

## API capabilities that matter

### ΚΗΜΔΗΣ

Primary docs:

- https://cerpp.eprocurement.gov.gr/khmdhs-opendata/help
- https://cerpp.eprocurement.gov.gr/khmdhs-opendata/swagger-ui/index.html

Χρήσιμα σημεία:

- Το API είναι JSON/REST και το base URL είναι `https://cerpp.eprocurement.gov.gr`.
- Το opendata API έχει rate limit 350 requests/minute και ενημέρωση δεδομένων
  περίπου κάθε 24 ώρες.
- `POST /khmdhs-opendata/request?page=0` υποστηρίζει φίλτρα `title`, `cpvItems`,
  `organizations`, `referenceNumber`, `contractType`, `dateFrom/dateTo`,
  `totalCostFrom/totalCostTo`, `cancelDateFrom/cancelDateTo`, `isInitial`,
  `isApproved`, `isApproval`.
- Το ΚΗΜΔΗΣ περιορίζει date windows σε 180 ημέρες, άρα historical mining πρέπει
  να κάνει chunked requests.
- Υπάρχουν endpoints για requests, notices, auctions, contracts, payments,
  attachments και `adamChain`.
- `GET /khmdhs-opendata/adamChain/{referenceNumber}` δίνει συνδεδεμένες πράξεις
  στο procurement lifecycle.
- Τα `objectDetails` έχουν quantity, costWithoutVAT, shortDescription και CPV,
  που είναι πολύτιμα για need clustering.

Live probe στις 2026-06-18 γύρισε ενδεικτικό μικρό software result:

- Buyer: Δήμος Θεσσαλονίκης
- Budget: 8.000 EUR χωρίς ΦΠΑ
- Need: συντήρηση/τεχνική υποστήριξη συστήματος ηλεκτρονικής διακίνησης εγγράφων,
  νέα dashboard λειτουργία, CPV 72267000-4 και 72262000-9
- Αυτό είναι ακριβώς candidate για repetitive need: document workflow +
  maintenance + dashboard extension.

### Διαύγεια

Primary/official references:

- https://diavgeia.gov.gr/api/help
- https://github.com/diavgeia/opendata-client-samples-python

Χρήσιμα σημεία:

- Το app base `https://diavgeia.gov.gr/opendata` δουλεύει για read calls.
- `GET /search` υποστηρίζει simple search με `ada`, `subject`, `protocol`,
  `term`, `org`, `unit`, `signer`, `type`, `tag`, date ranges, issue date
  ranges, `status`, `page`, `size`, `sort`.
- `GET /search/advanced` υποστηρίζει advanced query syntax.
- Υπάρχουν read endpoints για `/types`, `/types/{id}/details`,
  `/organizations`, `/organizations/{id}/details`, `/decisions/{ada}`,
  `/decisions/{ada}/versionlog`, `/search/terms`, `/types/{id}/terms`.
- Decisions περιέχουν `ada`, `subject`, `decisionTypeId`, `organizationId`,
  `publishTimestamp`, `issueDate`, `url`, `documentUrl`, `extraFieldValues`.
- Τα `extraFieldValues` μπορούν να περιέχουν ποσά, αναδόχους, related decisions
  ή πεδία ανά τύπο πράξης. Άρα πρέπει να γίνεται type-aware parsing.

## Recommended feature set

### 1. Need Pattern Explorer

Goal: να εμφανίζει clusters επαναλαμβανόμενων αναγκών, όχι μόνο opportunities.

Backend:

- Νέο entity `NeedPattern` με:
  - `pattern_id`
  - `label`
  - `need_category`
  - `keywords`
  - `cpv_families`
  - `sample_titles`
  - `buyers`
  - `buyer_count`
  - `opportunity_count`
  - `median_budget`
  - `budget_range`
  - `recency_score`
  - `repeat_score`
  - `productization_score`
  - `source_refs`
- Νέο endpoint:
  - `POST /api/patterns/discover`
- Inputs:
  - date range
  - CPV families
  - budget range
  - sources
  - minimum repeat count
- Data:
  - ΚΗΜΔΗΣ `request`, `notice`, `auction`, `contract`
  - Διαύγεια `/search` και optional `/search/advanced`

Logic:

- Normalize titles, object descriptions, CPV, buyer names.
- Extract need terms from `title`, `summary`, `objectDetails.shortDescription`,
  `document brief technical_requirements`.
- Cluster by CPV family + normalized terms + package match.
- Score repeatability by count, buyer diversity, recency and lifecycle evidence.

Frontend:

- New tab: `Patterns`
- Cards/table με:
  - pattern label
  - repeat count
  - median budget
  - sample buyers
  - productization score
  - "Open examples"

### 2. Productization Score

Goal: να απαντά "μπορεί αυτό να γίνει μικρό product/service package;".

Signals:

- Budget 5k-100k: θετικό για μικρή ομάδα.
- CPV 48/72, document management, dashboards, portals, monitoring, CMS:
  θετικό.
- Πολλοί διαφορετικοί buyers με παρόμοιο need: πολύ θετικό.
- Επαναλήψεις στον ίδιο buyer ανά έτος: θετικό για support/maintenance.
- Heavy compliance, mission-critical, μεγάλα ISO/turnover requirements:
  αρνητικό.
- Award/contract/payment chain exists: θετικό για market validation.
- Same winner repeatedly: διπλή ένδειξη. Υπάρχει αγορά, αλλά ίσως incumbent risk.

Implementation:

- Επέκταση `score_opportunity` ή νέο `pattern_scoring.py`.
- Να μη μπερδευτεί με `fit_score`: το `fit_score` απαντά "να το κυνηγήσω τώρα;",
  ενώ το `productization_score` απαντά "να χτίσω reusable λύση γύρω από αυτό;".

### 3. Buyer Repeat Map

Goal: να δείχνει ποιοι φορείς αγοράζουν συχνά μικρά software/services.

Backend:

- Επέκταση `BuyerIntelligenceResponse` ή νέο endpoint:
  - `GET /api/buyers/{buyer}/patterns`
- Χρήση ΚΗΜΔΗΣ `organizations` key όταν υπάρχει.
- Chunked historical lookup ανά 180 ημέρες.
- Διαύγεια lookup με `org` όταν μπορεί να γίνει mapping, αλλιώς `term`.

Metrics:

- recent small software count
- repeat categories
- median budget
- last purchase date
- common winners
- lifecycle conversion: request -> notice -> award -> contract -> payment

Frontend:

- Στο details drawer, ενότητα "Buyer repeats this need".
- Mini timeline ανά buyer.
- "This buyer buys: DMS support, dashboard extensions, website maintenance".

### 4. Winner / Incumbent Signals

Goal: να μάθουμε ποιοι κερδίζουν επαναλαμβανόμενες ανάγκες και σε τι ποσά.

Backend:

- Διαύγεια type-aware parsing από `extraFieldValues`.
- ΚΗΜΔΗΣ awards/contracts parsing για contractor/supplier fields.
- Νέο model `WinnerSignal`.

Outputs:

- winner name
- amount
- buyer
- need category
- CPV
- source document
- confidence

Use:

- Market validation.
- Incumbent risk.
- Price anchoring.
- Partner/acquisition candidates.

### 5. Need Lifecycle Tracker

Goal: να βρίσκει early signals πριν γίνει tender.

ΚΗΜΔΗΣ has enough for this through `request` + `adamChain`.

States:

- request / approved request: "watch"
- notice / invitation: "actionable"
- award / contract / payment: "market intelligence"

Feature:

- Watchlist for early requests that match target patterns.
- Alert when linked `PROC` notice appears in `adamChain`.
- Alert when award/contract appears, so the pattern gets winner and price data.

### 6. Pattern-backed AI Brief

Goal: το AI brief να μην απαντά μόνο στο συγκεκριμένο document, αλλά και στο
pattern γύρω του.

Prompt additions:

- Similar historical procurements.
- Typical budget range.
- Known red flags for this pattern.
- Suggested reusable package shape.
- "Build vs bid" recommendation.

Output additions:

- `reusable_solution_angle`
- `implementation_package`
- `open_source_candidates`
- `repeatability_rationale`
- `pricing_hint`
- `buyer_risk`

### 7. Opportunity-to-Package Library

Goal: να φτιάχνουμε κατάλογο reusable offerings.

Initial packages:

- Document workflow / DMS support and extensions
- Municipality dashboard / reporting layer
- Website / CMS maintenance
- Public application/workflow portal
- Field monitoring and reporting app
- Open-data / BI mini portal
- Cultural/museum digital experience

Each package should have:

- target CPV
- keywords
- typical buyers
- typical budget
- delivery skeleton
- open-source base options
- red flags
- sample opportunities

## Technical roadmap

### Phase 1: Data foundation

- Add `pattern_scoring.py`.
- Add models:
  - `NeedPattern`
  - `NeedPatternRequest`
  - `NeedPatternResponse`
  - `PatternOpportunitySample`
  - `WinnerSignal`
- Add a service:
  - `backend/app/services/patterns.py`
- Add endpoint:
  - `POST /api/patterns/discover`
- Use current search results first, then add historical KΗΜΔΗΣ backfill.

This can be implemented without a new database table initially.

### Phase 2: Persistence

- Store fetched opportunities and normalized pattern fingerprints in SQLite.
- Tables:
  - `opportunity_snapshots`
  - `need_patterns`
  - `pattern_members`
  - `winner_signals`
  - `buyer_profiles`
- Use daily refresh instead of re-querying every UI interaction.

### Phase 3: API depth

- Add KΗΜΔΗΣ endpoint coverage:
  - `notice`
  - `auction`
  - `contract`
  - `payment`
  - `adamChain`
- Add Διαύγεια endpoint coverage:
  - `/types`
  - `/types/{id}/details`
  - `/organizations`
  - `/organizations/{id}/details`
  - `/search/advanced`
  - `/decisions/{ada}`
- Add type-aware parser for awards/contracts and financial decisions.

### Phase 4: Product UI

- Add `Patterns` tab.
- Add pattern details drawer:
  - examples
  - buyers
  - winners
  - lifecycle
  - package recommendation
- Add "Save pattern" next to bookmarks.
- Add watchlist alerts for pattern changes.

## Suggested first build

Build `POST /api/patterns/discover` using already fetched opportunities plus
optional ΚΗΜΔΗΣ historical lookups by CPV/date chunks.

Why this first:

- It is aligned with the repetitive-need thesis.
- It reuses existing source clients, scoring and UI state.
- It creates a new product surface without requiring a full ingestion pipeline.
- It will quickly show whether the patterns are useful before we invest in
  persistence, alerts or deeper Διαύγεια parsing.

Minimum response shape:

```json
{
  "generated_at": "2026-06-18T00:00:00Z",
  "patterns": [
    {
      "pattern_id": "document-workflow-dashboard",
      "label": "Document workflow support + dashboard extensions",
      "need_category": "Document & Case Management",
      "opportunity_count": 12,
      "buyer_count": 8,
      "median_budget": 18000,
      "budget_range": "8.000 - 45.000 EUR",
      "repeat_score": 84,
      "productization_score": 91,
      "keywords": ["ΣΗΔΕ", "έγγραφα", "dashboard", "συντήρηση λογισμικού"],
      "cpv_families": ["722", "483"],
      "recommended_package": "DMS support and workflow dashboard package"
    }
  ]
}
```

## Risks / caveats

- ΚΗΜΔΗΣ has 180-day search windows, so historical analysis must be chunked.
- ΚΗΜΔΗΣ fields can evolve; normalization must tolerate unknown fields.
- Διαύγεια `term` search is noisy. Prefer `org` when organization mapping is
  known.
- Διαύγεια extra fields vary by decision type. Type-aware parsers are needed.
- Greek text normalization matters: accents, casing, mojibake from terminal
  display, and synonyms can affect clustering.
- Do not overfit to CPV alone. Many useful needs hide in `shortDescription` and
  PDF text.
