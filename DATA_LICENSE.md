# Data license and attribution

The **source code** in this repository is released under the MIT License (see `LICENSE`).

The **dataset** in `data/neurons.parquet` is derived from [NeuroMorpho.Org](https://neuromorpho.org),
which states that it is licensed under the
[Creative Commons Attribution 4.0 International License](https://creativecommons.org/licenses/by/4.0/).
That license continues to apply to the derived data.

## Please cite

1. The original paper(s) that describe each reconstruction. They are listed per row in the
   `reference_pmid` and `reference_doi` columns, and the contributing lab in `archive`.
2. NeuroMorpho.Org (RRID:SCR_002145).
3. Tecuatl C, Ljungquist B, Ascoli GA (2024) Accelerating the continuous community sharing of
   digital neuromorphology data. FASEB BioAdvances 6(7):207-221. doi:10.1096/fba.2024-00048

## Changes made

- Kept only species that downloaded successfully and had morphometry (52 of the 95 species in the archive).
- Selected and renamed columns; species names lower-cased.
- Added `trace_type`, derived from NeuroMorpho's `domain` field ("with axon", "dendrites only",
  "undifferentiated", "unknown").
- Joined each reconstruction's reference fields from the archive's metadata.
- No reconstruction (SWC) files are redistributed; only metadata and computed measurements.

This project is independent and is not affiliated with or endorsed by NeuroMorpho.Org or its contributors.
Use of the data is at your own risk.
