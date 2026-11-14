# Changelog

## 0.2.0 — Validated engineering handoff release

- Added dual validation for PLCopen TC6 XML and the Siemens hardware extension.
- Added catalog search across product names, article numbers, descriptions, and properties.
- Added official Siemens product and datasheet URL generation.
- Added TIA Selection Tool launch.
- Added quantity-weighted CPU and I/O summaries.
- Added engineering consistency checks for required metadata, task/POU references, variable owners, conflicting flags, duplicate tags, occupied rack/slot pairs, missing CPUs, and website provenance.
- Added BOM CSV export.
- Added Siemens website-enrichment checklist CSV export.
- Added command-line validation, example generation, version display, and catalog summary.
- Expanded automated testing from two to eight tests.
- Added the supplied Siemens brochure as a source reference.
- Added schema-coverage, licensing, and third-party notices.

## 0.1.0 — Initial Siemens S7-1200 implementation

- Added Tkinter project wizard.
- Added PLCopen TC6 XML 2.01 exporter.
- Added XSD validation through `lxml`.
- Added 104-item Siemens S7-1200 2017 catalog snapshot.
- Added hardware installation and Siemens website enrichment prompts.
- Added custom data types, scoped variables, POUs, resources, and tasks.
- Added ST and IL formatted-text export.
- Added preserved notes for LD, FBD, and SFC bodies.
- Added project JSON save/load.
- Added Siemens hardware `addData` extension and extension XSD.
- Added initial automated tests.
