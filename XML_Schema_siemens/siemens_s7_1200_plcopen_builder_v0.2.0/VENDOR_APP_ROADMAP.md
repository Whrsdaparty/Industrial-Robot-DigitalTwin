# Vendor Application Roadmap

The Siemens S7-1200 builder is the first vendor adapter. Future vendor applications should share the same internal project records and PLCopen exporter while replacing the manufacturer catalog and hardware-rule layer.

## Stable shared core

The following behavior should remain manufacturer-independent:

- PLCopen file and content headers
- Custom data types
- Variable scopes and attributes
- POU source and documentation
- Configurations, resources, tasks, and program instances
- PLCopen XML generation
- PLCopen XSD validation
- Project JSON persistence
- Engineering consistency reporting
- BOM and source-enrichment CSV handoffs
- Common hardware identity, placement, network, source, and lifecycle fields

## Vendor adapter contract

Each adapter should eventually define:

1. Manufacturer name and product-family identifiers
2. Catalog schema and source provenance
3. Product search and display labels
4. Official manufacturer URL generation
5. Hardware categories and article-number normalization
6. Rack, backplane, slot, and side-module rules
7. Compatible module relationships
8. Power-budget and current-consumption rules
9. I/O channel definitions and address widths
10. Automatic I/O address allocation
11. Required connectors and terminal accessories
12. Firmware and engineering-tool compatibility
13. Lifecycle, successor, and replacement relationships
14. CAx, EPLAN, AutomationML, GSDML, EDS, or device-description references
15. Vendor-specific extension fields and XSD

## Recommended project architecture

```text
plcopen_builder_core/
  models.py
  plcopen_exporter.py
  validation.py
  handoffs.py
  ui_common.py
vendors/
  siemens_s7_1200/
    adapter.py
    catalog.json
    hardware_extension.xsd
  siemens_s7_1500/
  rockwell_compactlogix/
  rockwell_controllogix/
  beckhoff_ethercat/
```

The current release remains a self-contained application for ease of use. The next major refactor should extract the tested data model, exporter, validation, and CSV handoffs into the shared package before adding a second manufacturer.

## Proposed adapter sequence

1. Siemens S7-1200
2. Siemens S7-1500 and ET 200SP
3. Rockwell CompactLogix
4. Rockwell ControlLogix
5. Beckhoff TwinCAT controllers and EtherCAT terminals
6. Schneider Modicon M241/M251 and M580
7. Omron NX/NJ
8. Mitsubishi iQ-F and iQ-R

## Source hierarchy

Use the highest-quality available source in this order:

1. Structured manufacturer data, CAx package, or official API/export
2. Current manufacturer product page
3. Current manufacturer technical manual or datasheet
4. Manufacturer catalog PDF
5. Deliberate user-entered project data

Every imported or entered property should preserve its source and checked date. Catalog PDFs should remain traceable import sources, not the final source of truth.

## Long-term engineering outputs

The internal project should eventually generate separate purpose-specific outputs:

- PLCopen XML or IEC 61131-10 software exchange
- AutomationML hardware, physical topology, and engineering-object exchange
- OPC UA NodeSet information models
- CAD panel-layout metadata
- Device manifest and approved vendor list
- Terminal plan and terminal-strip model
- Signal registry and I/O map
- Network topology
- Alarm and event definitions
- Revision and package manifest

No single interchange format should be forced to serve as the master engineering model. A strict internal project schema should own the complete engineering data and generate each external format deliberately.
