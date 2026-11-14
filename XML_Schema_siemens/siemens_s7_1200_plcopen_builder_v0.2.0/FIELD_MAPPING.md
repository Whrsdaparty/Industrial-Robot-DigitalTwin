# PLCopen and Siemens Field Mapping

## Standard PLCopen content

The application emits the supplied PLCopen TC6 XML 2.01 namespace:

```text
http://www.plcopen.org/xml/tc6_0201
```

### `project/fileHeader`

The Project tab records the required company name, exporting product name, exporting product version, and creation timestamp. It also supports company URL, product release, and content description.

### `project/contentHeader`

The application records project name, project version, modification timestamp, organization, author, documentation language, project comment, page size, and FBD/LD/SFC scaling.

`contentHeader/addDataInfo` declares the Siemens hardware extension URI and vendor.

### `project/types/dataTypes`

The data-type editor currently supports:

- Elementary or derived aliases
- Enumerations
- Structures
- One-dimensional arrays
- Simple initial values
- Documentation

### `project/types/pous`

The POU editor supports `program`, `functionBlock`, and `function` objects.

ST and IL bodies are exported as formatted text. LD, FBD, and SFC bodies are emitted as schema-valid graphical body containers. Any text entered for a graphical body is retained in an extension note rather than being misrepresented as graphical network data.

### Variables

Configuration globals are exported under the configuration. Resource globals are exported under their resource. POU variables are exported into the corresponding interface list.

Variable-list attributes supported:

- `constant`
- `retain`
- `nonretain`
- `persistent`
- `nonpersistent`

Variable-level fields supported:

- Name
- Data type
- Direct address
- Simple initial value
- Documentation

### `project/instances`

The first release supports one configuration with multiple resources. Resources are created from the resource names used by tasks.

Each task supports:

- Name
- Periodic interval
- Single-trigger variable
- Priority
- Program instance name
- Program type name
- Documentation

## Siemens S7-1200 extension

Hardware is stored at project level:

```xml
<addData>
  <data
      name="https://integracad-open.org/addData/siemens-s7-1200-hardware/v1"
      handleUnknown="preserve">
    <s7:hardwareConfiguration>...</s7:hardwareConfiguration>
  </data>
</addData>
```

Each device can record:

- Manufacturer and product family
- Category, product name, and Siemens article number / MLFB
- Quantity
- Catalog year, page, description, and structured catalog properties
- Device tag
- Rack and slot
- PROFINET station name
- IP address, subnet mask, and gateway
- Firmware and hardware version
- Lifecycle status
- Product, support, datasheet, manual, and CAx URLs
- Width, height, depth, and weight
- Operating-temperature information
- Approvals
- Website verification date
- Engineering notes

## CSV handoffs

The BOM export produces one row per hardware line item with product, placement, network, lifecycle, and source fields.

The website checklist isolates fields that should be verified against current Siemens sources. It is intended for controlled enrichment rather than unattended scraping.

## Why hardware is not stored as a PLCopen resource

PLCopen configurations and resources describe IEC 61131 execution. They do not define physical rack construction. Treating a signal module as an IEC resource would corrupt the meaning of the standard model.

The application therefore preserves the hardware domain separately. A later internal engineering model or AutomationML export can provide richer physical topology without changing the PLCopen software representation.
