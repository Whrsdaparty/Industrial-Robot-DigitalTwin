# Siemens S7-1200 PLCopen XML Builder

Version **0.2.0**

A Python/Tkinter desktop application for creating and validating **PLCopen TC6 XML 2.01** projects while carrying a selected Siemens SIMATIC S7-1200 hardware set in a preserved PLCopen `addData` extension.

The application is the first vendor adapter for a planned family of controls-engineering catalog applications. The shared approach is:

1. Keep IEC 61131 software and project structure in standard PLCopen XML.
2. Keep manufacturer hardware and project installation data in a versioned, preserved extension.
3. Save editable working state as JSON.
4. Validate the standard PLCopen document and the Siemens extension independently.
5. Preserve source provenance so a catalog snapshot is not mistaken for current manufacturer data.

## What the application does

The Project tab prompts for the PLCopen file header, content header, drawing scale information, configuration name, project comment, and project documentation.

The Hardware tab contains **104 Siemens S7-1200 products** transcribed from the supplied 2017 Siemens brochure. It supports catalog search, category filtering, quantities, device tags, rack/slot placement, PROFINET station and IP data, firmware and hardware revision, lifecycle status, dimensions, approvals, Siemens URLs, manuals, CAx links, source-check dates, and engineering notes.

The remaining tabs support:

- User-defined aliases, enumerations, structures, and one-dimensional arrays
- Configuration, resource, and POU variables
- `program`, `functionBlock`, and `function` POUs
- ST and legacy IL formatted-text bodies
- Schema-valid LD, FBD, and SFC bodies with preserved engineering notes
- Resources, periodic or triggered tasks, and program instances
- XML preview, export, and validation

The Tools menu provides:

- Engineering consistency report
- Hardware BOM CSV export
- Siemens website-enrichment checklist CSV export
- TIA Selection Tool launch

## Why the Siemens hardware is an extension

PLCopen TC6 XML represents IEC 61131 software and execution structure. A PLCopen `configuration` and `resource` are not equivalent to a physical PLC rack, signal module, terminal connector, or catalog item.

The application therefore uses the standards-defined software hierarchy for software and stores physical hardware under:

```xml
<addData>
  <data
      name="https://integracad-open.org/addData/siemens-s7-1200-hardware/v1"
      handleUnknown="preserve">
    <s7:hardwareConfiguration>...</s7:hardwareConfiguration>
  </data>
</addData>
```

This prevents the physical and software models from being conflated while allowing another PLCopen-aware tool to preserve the manufacturer data.

## Siemens catalog and website workflow

The embedded catalog is an **offline 2017 brochure snapshot**. It provides article numbers and concise product properties for CPUs, fail-safe CPUs, starter kits, communication modules, digital and analog I/O, fail-safe I/O, technology modules, signal boards, software, power supply, memory cards, accessories, and Basic Panels.

For every selected item, the application can generate official Siemens entry-point URLs for:

- SiePortal product details
- Siemens technical datasheet PDF
- TIA Selection Tool

The application deliberately does not scrape dynamic Siemens pages. Instead, it prompts the engineer to review and record current information such as lifecycle status, firmware, dimensions, approvals, manuals, CAx data, and the date checked. This avoids silently importing localized, stale, login-dependent, or incorrectly matched data.

## Ubuntu installation

```bash
sudo apt update
sudo apt install -y python3 python3-tk python3-venv

cd siemens_s7_1200_plcopen_builder_v0.2.0
python3 -m venv .venv
source .venv/bin/activate.fish
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
./run.sh
```

For Bash or Zsh:

```bash
source .venv/bin/activate
```

The GUI uses the Python standard library and Tkinter. `lxml` is used for XSD validation.

An optional user-level desktop launcher can be installed after the virtual environment is created:

```bash
./install_desktop_launcher.sh
```

The launcher calls `run.sh`, which automatically uses `.venv/bin/python` when that environment exists.

## Recommended workflow

1. Create a new project and complete the Project tab.
2. Search the Siemens catalog by CPU name or article number.
3. Add the CPU and required modules.
4. Edit every hardware item to assign a unique device tag, rack, slot, and project network data.
5. Open the Siemens product and datasheet pages.
6. Record current website information and the checked date.
7. Add application data types and variables.
8. Add or edit programs, functions, and function blocks.
9. Configure the resources and tasks.
10. Run the engineering consistency report.
11. Export the BOM and website checklist for project review.
12. Export the PLCopen XML. The application validates both XSDs before reporting success.

## Command-line operations

Generate and validate an example:

```bash
python siemens_s7_1200_plcopen_app.py --example examples/generated_example.xml
```

Validate an existing export:

```bash
python siemens_s7_1200_plcopen_app.py --validate examples/generated_example.xml
```

Display the catalog summary:

```bash
python siemens_s7_1200_plcopen_app.py --catalog-summary
```

Display the version:

```bash
python siemens_s7_1200_plcopen_app.py --version
```

## Project JSON

Use **Save Project** to create a `.plcproj.json` working file. The JSON preserves the editable application state. It is not a substitute for PLCopen XML and should not be imported directly into a PLC engineering environment.

## Data type formats

```text
Alias:       BOOL
Alias:       MyExistingType
Enumeration: Idle=0,Starting=1,Running=2,Faulted=3
Structure:   Ready:BOOL;Count:DINT;Temperature:REAL
Array:       1..16:BOOL
```

## Variable scopes

```text
configuration_global
resource_global
pou_local
pou_temp
pou_input
pou_output
pou_inout
pou_external
pou_global
```

A POU variable owner must match a POU name. A resource-global variable owner should match a resource name.

## Validation and tests

Run all automated tests:

```bash
python -m unittest discover -s tests -v
```

The tests cover:

- Catalog completeness and article-number lookup
- Catalog text search
- PLCopen XSD validation
- Siemens hardware-extension XSD validation
- ST, IL, LD, FBD, and SFC body export
- Quantity-weighted I/O summaries
- Engineering consistency checks
- BOM and website-checklist CSV exports
- Project JSON round-trip behavior

## Important limitations

This is a first vendor-specific application, not a replacement for TIA Portal or TIA Selection Tool.

It does not yet:

- Import or export TIA Portal projects
- Generate graphical LD, FBD, or SFC networks
- Enforce all legal S7-1200 module combinations
- Calculate power budgets or connector requirements
- Automatically allocate I/O addresses
- Import GSDML, AutomationML, EPLAN, or Siemens CAx packages
- Generate terminal plans, panel layouts, or wiring diagrams
- Scrape or continuously synchronize Siemens websites
- Model multiple PLC stations as separate physical racks

The project model is intentionally structured so later versions can add these functions without changing the PLCopen software model.

## Project contents

```text
siemens_s7_1200_plcopen_app.py
engineering.py
catalog/
  siemens_s7_1200_2017.json
schemas/
  tc6_xml_v201.xsd
  siemens_s7_1200_hardware_v1.xsd
references/
  Siemens_SIMATIC_S7-1200_Brochure_2017.pdf
examples/
  example_s7_1200_project.plcproj.json
  example_s7_1200_project.xml
  example_hardware_bom.csv
  example_website_checklist.csv
tests/
  test_export.py
requirements.txt
run.sh
install_desktop_launcher.sh
README.md
FIELD_MAPPING.md
SCHEMA_COVERAGE.md
VENDOR_APP_ROADMAP.md
CHANGELOG.md
THIRD_PARTY_NOTICES.md
LICENSE
```
