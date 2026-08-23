# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

This file starts at 0.28.0. Notes for earlier releases are on the
[GitHub releases page](https://github.com/dannymcc/may/releases).

## [0.31.0] - 2026-08-23

### Added

- Fuel level on trips. A trip can now record the fuel gauge reading at each
  end, as a percentage of a full tank, alongside the odometer readings. Where
  the vehicle has a tank capacity set, May works out the fuel used on the trip
  from the two readings and shows it on the trip list and while the trip is
  being logged, giving a per-trip picture of consumption rather than only one
  per fill-up. Both readings are optional, are carried in the API, CSV import
  and export, and the backup. ([#273](https://github.com/dannymcc/may/issues/273))

### Changed

- The README feature list now mentions trip logging, which was missing from it.

## [0.30.0] - 2026-08-23

### Added

- Restoring a May backup. Settings → Integrations → Import Data now has a
  "Restore May Backup" option that accepts both the JSON export and the full
  backup ZIP produced by the export page, so data can be moved from an old
  instance into a new one. Documents, attachments and vehicle images come
  across from a full backup ZIP; a JSON export carries the records only.
  The restore always merges into the signed-in account: nothing is deleted or
  overwritten, and records already present are skipped rather than duplicated.
  A preview showing exactly what will be added is displayed before anything is
  written. ([#265](https://github.com/dannymcc/may/issues/265))
- A photo gallery for vehicles. The vehicle page has a "Photos" section that
  takes as many photos as you like, several at a time; any of them can be made
  the main photo shown on the dashboard and vehicle list, and the header image
  steps through the rest with left and right arrows. Photos are stored as
  attachments against the vehicle, so they are already covered by the full
  backup export. Deleting a vehicle removes its photos; deleting the main one
  falls back to another photo, or clears the image if none are left.
  ([#147](https://github.com/dannymcc/may/issues/147))

### Changed

- Saved fuel stations now remember which forecourt a live price feed matched
  them to, rather than re-deriving it from postcode and address on every
  refresh. A station therefore keeps reporting the same forecourt after its
  postcode is edited, and a forecourt that drops out of the feed is reported as
  unmatched instead of quietly resolving to a different one. This is
  groundwork for the Tankerkönig integration; live German prices are not
  available yet. ([#155](https://github.com/dannymcc/may/issues/155))

### Fixed

- Hybrid fill-ups no longer appear as a "hybrid" series in the fuel station
  price charts. Hybrid is how a vehicle is driven, not what goes in the tank,
  so a fill-up is now recorded against petrol by default; the fuel type
  selector on the fuel form is offered for hybrids and plug-in hybrids so
  diesel hybrid owners can pick diesel instead. Changing a saved log's fuel
  type now moves its price history row to match. Existing price history is
  left as it stands. ([#268](https://github.com/dannymcc/may/issues/268))

## [0.29.0] - 2026-08-23

### Added

- UK fuel prices. Admins can switch on the government fuel price feeds in
  Settings → Integrations → UK Fuel Prices; saved stations are then matched to
  forecourts by postcode and their prices recorded, feeding the existing price
  history and Cheapest Fuel screens. Refreshes run every six hours in the
  background, or on demand with the "Update UK Prices" button on the Fuel
  Stations page or a station's price history. No API key is needed, and the
  retailer feed list can be overridden.
  ([#258](https://github.com/dannymcc/may/issues/258))
- The vehicle PDF report lists the vehicle's parts and consumables, with type,
  specification, quantity and part number, alongside the existing
  specifications, fuel logs and expenses. Vehicles with no parts recorded are
  unchanged. ([#235](https://github.com/dannymcc/may/issues/235))

## [0.28.0] - 2026-08-23

### Added

- Vehicle PDF reports can now include receipt images. The vehicle page has a
  "PDF + Receipts" button alongside the existing "PDF" one; it appends the
  images attached to the fuel logs and expenses in the report. Anything that
  cannot be inlined — a PDF scan, a missing file, or one that would push the
  report past the 20 MB image budget — is listed at the end of the report
  rather than dropped silently.
  ([#219](https://github.com/dannymcc/may/issues/219))
- Expenses accept more than one receipt. Select several files when adding or
  editing an expense, and the expandable row in the expense list links to each
  one. Files rejected for an unsupported extension are now reported rather than
  dropped silently. ([#234](https://github.com/dannymcc/may/issues/234))
- API v1 endpoints for trips and charging sessions: list, create, read, update
  and delete under `/api/v1/vehicles/{id}/trips`, `/api/v1/trips/{id}`,
  `/api/v1/vehicles/{id}/charging` and `/api/v1/charging/{id}`, plus
  `/api/v1/trip-purposes` and `/api/v1/charger-types`. Documented at `/api/docs`.
  ([#295](https://github.com/dannymcc/may/issues/295))
- Dashboard charts label their value axis with your currency, and tooltips show
  it too. ([#289](https://github.com/dannymcc/may/issues/289))
- Initial Hungarian translation files, contributed by
  [@burgatshow](https://github.com/burgatshow). Hungarian is not yet offered in
  the language picker while the remaining strings are filled in.
  ([#290](https://github.com/dannymcc/may/pull/290))

### Fixed

- `.env` settings were silently ignored. `config.py` now loads the `.env` file
  sitting next to it before reading the environment. Real environment variables
  still take precedence, so Docker deployments are unaffected.
  ([#297](https://github.com/dannymcc/may/issues/297))
- Deleting an entry from the fuel log bounced you to the vehicle page; it now
  leaves you where you were. ([#298](https://github.com/dannymcc/may/issues/298))

### Changed

- The expense list loads attachments in a single query rather than one per row.
- README and `.env.example` corrected: the real defaults for `DATABASE_URL` and
  `UPLOAD_FOLDER` are inside the application directory, the `sqlite:///` versus
  `sqlite:////` distinction is spelled out, and there is a note that `.env` does
  not drive those two keys under Docker Compose.
- The supported languages table in the README now lists Arabic, Czech, Russian
  and Turkish, which were already available in the app.
- Dependencies: `psycopg2-binary` >= 2.9.12
  ([#280](https://github.com/dannymcc/may/pull/280)), `coverage` >= 7.15.4
  ([#288](https://github.com/dannymcc/may/pull/288)), and `actions/setup-python`
  bumped from 6 to 7 in CI ([#263](https://github.com/dannymcc/may/pull/263)).
