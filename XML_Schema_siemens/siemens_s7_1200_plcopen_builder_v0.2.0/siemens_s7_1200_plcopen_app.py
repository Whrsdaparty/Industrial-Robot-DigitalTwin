#!/usr/bin/env python3
"""Siemens S7-1200 PLCopen XML Builder.

A Tkinter application for creating PLCopen TC6 XML 2.01 files. The PLCopen
schema represents software/project exchange. Siemens hardware configuration is
stored in a preserved project-level addData extension so the resulting XML can
carry manufacturer product metadata without pretending that TC6 is a hardware
configuration schema.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import webbrowser
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from engineering import (
    export_bom_csv,
    export_website_checklist_csv,
    format_hardware_summary,
    project_quality_report,
    siemens_urls,
)
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from xml.etree import ElementTree as ET

APP_VERSION = "0.2.0"
PLCOPEN_NS = "http://www.plcopen.org/xml/tc6_0201"
XHTML_NS = "http://www.w3.org/1999/xhtml"
HARDWARE_NS = "https://integracad-open.org/xml/hardware/siemens/s7-1200/v1"
HARDWARE_DATA_URI = "https://integracad-open.org/addData/siemens-s7-1200-hardware/v1"
VENDOR_URI = "https://www.siemens.com/"

ET.register_namespace("", PLCOPEN_NS)
ET.register_namespace("xhtml", XHTML_NS)
ET.register_namespace("s7", HARDWARE_NS)

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CATALOG = BASE_DIR / "catalog" / "siemens_s7_1200_2017.json"
DEFAULT_XSD = BASE_DIR / "schemas" / "tc6_xml_v201.xsd"
DEFAULT_HARDWARE_XSD = BASE_DIR / "schemas" / "siemens_s7_1200_hardware_v1.xsd"

ELEMENTARY_TYPES = [
    "BOOL",
    "BYTE",
    "WORD",
    "DWORD",
    "LWORD",
    "SINT",
    "INT",
    "DINT",
    "LINT",
    "USINT",
    "UINT",
    "UDINT",
    "ULINT",
    "REAL",
    "LREAL",
    "TIME",
    "DATE",
    "DT",
    "TOD",
    "STRING",
    "WSTRING",
]
VAR_SCOPES = [
    "configuration_global",
    "resource_global",
    "pou_local",
    "pou_temp",
    "pou_input",
    "pou_output",
    "pou_inout",
    "pou_external",
    "pou_global",
]


def qn(namespace: str, local: str) -> str:
    return f"{{{namespace}}}{local}"


def utc_now_text() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def bool_text(value: Any) -> str:
    return "true" if bool(value) else "false"


def safe_id(value: str, fallback: str = "id") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    if not cleaned:
        cleaned = fallback
    if not re.match(r"[A-Za-z_]", cleaned):
        cleaned = f"_{cleaned}"
    return cleaned


def parse_property_text(value: str) -> dict[str, str]:
    """Parse `Name=Value` entries separated by semicolons or new lines."""
    result: dict[str, str] = {}
    for token in re.split(r"[;\n]+", value):
        token = token.strip()
        if not token:
            continue
        name, separator, property_value = token.partition("=")
        if not separator or not name.strip():
            raise ValueError(
                f"Invalid property entry {token!r}. Use Name=Value entries separated "
                "by semicolons or new lines."
            )
        result[name.strip()] = property_value.strip()
    return result


def format_property_text(properties: dict[str, str]) -> str:
    return "; ".join(f"{name}={value}" for name, value in sorted(properties.items()))


@dataclass
class HardwareItem:
    product: dict[str, Any]
    quantity: int = 1
    device_tag: str = ""
    rack: str = "0"
    slot: str = ""
    station_name: str = ""
    ip_address: str = ""
    subnet_mask: str = ""
    gateway: str = ""
    firmware_version: str = ""
    hardware_version: str = ""
    lifecycle_status: str = ""
    product_url: str = ""
    support_url: str = ""
    datasheet_url: str = ""
    manual_url: str = ""
    cax_url: str = ""
    width_mm: str = ""
    height_mm: str = ""
    depth_mm: str = ""
    weight_kg: str = ""
    operating_temperature: str = ""
    approvals: str = ""
    website_checked_date: str = ""
    notes: str = ""
    website_properties: dict[str, str] = field(default_factory=dict)


@dataclass
class DataTypeRecord:
    name: str
    kind: str = "alias"  # alias, enum, struct, array
    definition: str = "BOOL"
    initial_value: str = ""
    documentation: str = ""


@dataclass
class VariableRecord:
    name: str
    data_type: str = "BOOL"
    scope: str = "configuration_global"
    owner: str = ""
    address: str = ""
    initial_value: str = ""
    constant: bool = False
    retain: bool = False
    nonretain: bool = False
    persistent: bool = False
    nonpersistent: bool = False
    documentation: str = ""


@dataclass
class POURecord:
    name: str
    pou_type: str = "program"
    language: str = "ST"
    return_type: str = ""
    source: str = ""
    documentation: str = ""


@dataclass
class TaskRecord:
    resource_name: str = "PLC_1"
    name: str = "MainTask"
    interval: str = "T#100ms"
    priority: int = 1
    program_instance_name: str = "MainInstance"
    program_type_name: str = "MainProgram"
    single_trigger: str = ""
    documentation: str = ""


@dataclass
class ProjectState:
    file_header: dict[str, str] = field(
        default_factory=lambda: {
            "companyName": "",
            "companyURL": "",
            "productName": "Siemens S7-1200 PLCopen Builder",
            "productVersion": APP_VERSION,
            "productRelease": "",
            "creationDateTime": utc_now_text(),
            "contentDescription": "PLCopen project with Siemens S7-1200 hardware extension",
        }
    )
    content_header: dict[str, str] = field(
        default_factory=lambda: {
            "name": "S7_1200_Project",
            "version": "1.0.0",
            "modificationDateTime": utc_now_text(),
            "organization": "",
            "author": "",
            "language": "en-US",
            "comment": "",
            "pageSizeX": "210",
            "pageSizeY": "297",
            "fbdScaleX": "1",
            "fbdScaleY": "1",
            "ldScaleX": "1",
            "ldScaleY": "1",
            "sfcScaleX": "1",
            "sfcScaleY": "1",
        }
    )
    configuration_name: str = "Config_1"
    hardware: list[HardwareItem] = field(default_factory=list)
    data_types: list[DataTypeRecord] = field(default_factory=list)
    variables: list[VariableRecord] = field(default_factory=list)
    pous: list[POURecord] = field(
        default_factory=lambda: [
            POURecord(
                name="MainProgram",
                pou_type="program",
                language="ST",
                source="(* Main program *)\n",
                documentation="Primary cyclic application program.",
            )
        ]
    )
    tasks: list[TaskRecord] = field(default_factory=lambda: [TaskRecord()])
    project_documentation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ProjectState":
        state = cls()
        state.file_header.update(raw.get("file_header", {}))
        state.content_header.update(raw.get("content_header", {}))
        state.configuration_name = raw.get(
            "configuration_name", state.configuration_name
        )
        state.hardware = [HardwareItem(**item) for item in raw.get("hardware", [])]
        state.data_types = [
            DataTypeRecord(**item) for item in raw.get("data_types", [])
        ]
        state.variables = [VariableRecord(**item) for item in raw.get("variables", [])]
        state.pous = [POURecord(**item) for item in raw.get("pous", [])]
        state.tasks = [TaskRecord(**item) for item in raw.get("tasks", [])]
        state.project_documentation = raw.get("project_documentation", "")
        return state


class CatalogRepository:
    def __init__(self, path: Path = DEFAULT_CATALOG) -> None:
        raw = json.loads(path.read_text(encoding="utf-8"))
        self.metadata = raw["catalog"]
        self.products: list[dict[str, Any]] = raw["products"]
        self.by_article = {p["article_number"]: p for p in self.products}

    def categories(self) -> list[str]:
        return sorted({str(p["category"]) for p in self.products})

    def products_in(self, category: str) -> list[dict[str, Any]]:
        return [p for p in self.products if p["category"] == category]

    def search(self, query: str, category: str = "") -> list[dict[str, Any]]:
        terms = [term.casefold() for term in query.split() if term.strip()]
        candidates = self.products_in(category) if category else self.products
        if not terms:
            return candidates
        results: list[dict[str, Any]] = []
        for product in candidates:
            haystack = " ".join(str(value) for value in product.values()).casefold()
            if all(term in haystack for term in terms):
                results.append(product)
        return results

    def product_label(self, product: dict[str, Any]) -> str:
        return f"{product['product_name']} — {product['article_number']}"


class PlcOpenExporter:
    def __init__(
        self,
        xsd_path: Path = DEFAULT_XSD,
        hardware_xsd_path: Path = DEFAULT_HARDWARE_XSD,
    ) -> None:
        self.xsd_path = xsd_path
        self.hardware_xsd_path = hardware_xsd_path

    def build(self, state: ProjectState) -> ET.Element:
        root = ET.Element(qn(PLCOPEN_NS, "project"))
        self._file_header(root, state.file_header)
        self._content_header(root, state.content_header)
        self._types(root, state)
        self._instances(root, state)
        self._hardware_add_data(root, state.hardware)
        self._documentation(root, state.project_documentation)
        return root

    def write(self, state: ProjectState, destination: Path) -> None:
        root = self.build(state)
        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ")
        destination.parent.mkdir(parents=True, exist_ok=True)
        tree.write(destination, encoding="utf-8", xml_declaration=True)

    def to_string(self, state: ProjectState) -> str:
        root = self.build(state)
        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ")
        return ET.tostring(root, encoding="unicode", xml_declaration=False)

    def validate(self, xml_path: Path) -> tuple[bool, str]:
        try:
            from lxml import etree  # type: ignore
        except ImportError:
            return (
                False,
                "Validation requires lxml. Install with: python -m pip install lxml",
            )
        try:
            schema_doc = etree.parse(str(self.xsd_path))
            schema = etree.XMLSchema(schema_doc)
            document = etree.parse(str(xml_path))
            schema.assertValid(document)
            return True, "XML is valid against tc6_xml_v201.xsd."
        except Exception as exc:  # lxml produces detailed exceptions
            return False, str(exc)

    def validate_hardware_extension(self, xml_path: Path) -> tuple[bool, str]:
        try:
            from lxml import etree  # type: ignore
        except ImportError:
            return (
                False,
                "Validation requires lxml. Install with: python -m pip install lxml",
            )
        try:
            document = etree.parse(str(xml_path))
            nodes = document.xpath(
                "//s7:hardwareConfiguration",
                namespaces={"s7": HARDWARE_NS},
            )
            if not nodes:
                return True, "No Siemens hardware extension is present."
            schema = etree.XMLSchema(etree.parse(str(self.hardware_xsd_path)))
            for node in nodes:
                schema.assertValid(etree.ElementTree(node))
            return (
                True,
                "Siemens hardware extension is valid against siemens_s7_1200_hardware_v1.xsd.",
            )
        except Exception as exc:
            return False, str(exc)

    def validate_all(self, xml_path: Path) -> tuple[bool, str]:
        plcopen_ok, plcopen_message = self.validate(xml_path)
        if not plcopen_ok:
            return False, f"PLCopen validation failed:\n{plcopen_message}"
        hardware_ok, hardware_message = self.validate_hardware_extension(xml_path)
        if not hardware_ok:
            return False, f"Hardware-extension validation failed:\n{hardware_message}"
        return True, f"{plcopen_message}\n{hardware_message}"

    @staticmethod
    def _file_header(root: ET.Element, data: dict[str, str]) -> None:
        required = ["companyName", "productName", "productVersion", "creationDateTime"]
        attrs = {key: data.get(key, "") for key in required}
        for key in ["companyURL", "productRelease", "contentDescription"]:
            if data.get(key, "").strip():
                attrs[key] = data[key].strip()
        ET.SubElement(root, qn(PLCOPEN_NS, "fileHeader"), attrs)

    @staticmethod
    def _content_header(root: ET.Element, data: dict[str, str]) -> None:
        attrs = {"name": data.get("name", "Untitled") or "Untitled"}
        for key in [
            "version",
            "modificationDateTime",
            "organization",
            "author",
            "language",
        ]:
            if data.get(key, "").strip():
                attrs[key] = data[key].strip()
        ch = ET.SubElement(root, qn(PLCOPEN_NS, "contentHeader"), attrs)
        if data.get("comment", "").strip():
            ET.SubElement(ch, qn(PLCOPEN_NS, "Comment")).text = data["comment"]
        coordinate = ET.SubElement(ch, qn(PLCOPEN_NS, "coordinateInfo"))
        if data.get("pageSizeX", "") and data.get("pageSizeY", ""):
            ET.SubElement(
                coordinate,
                qn(PLCOPEN_NS, "pageSize"),
                {"x": data["pageSizeX"], "y": data["pageSizeY"]},
            )
        for language in ["fbd", "ld", "sfc"]:
            wrapper = ET.SubElement(coordinate, qn(PLCOPEN_NS, language))
            ET.SubElement(
                wrapper,
                qn(PLCOPEN_NS, "scaling"),
                {
                    "x": data.get(f"{language}ScaleX", "1") or "1",
                    "y": data.get(f"{language}ScaleY", "1") or "1",
                },
            )
        adi = ET.SubElement(ch, qn(PLCOPEN_NS, "addDataInfo"))
        info = ET.SubElement(
            adi,
            qn(PLCOPEN_NS, "info"),
            {
                "name": HARDWARE_DATA_URI,
                "version": "1.0",
                "vendor": VENDOR_URI,
            },
        )
        description = ET.SubElement(info, qn(PLCOPEN_NS, "description"))
        ET.SubElement(description, qn(XHTML_NS, "xhtml")).text = (
            "Siemens S7-1200 hardware configuration and manufacturer product metadata."
        )

    def _types(self, root: ET.Element, state: ProjectState) -> None:
        types = ET.SubElement(root, qn(PLCOPEN_NS, "types"))
        data_types = ET.SubElement(types, qn(PLCOPEN_NS, "dataTypes"))
        for record in state.data_types:
            dt = ET.SubElement(
                data_types, qn(PLCOPEN_NS, "dataType"), {"name": record.name}
            )
            base = ET.SubElement(dt, qn(PLCOPEN_NS, "baseType"))
            self._data_type_definition(base, record)
            if record.initial_value:
                init = ET.SubElement(dt, qn(PLCOPEN_NS, "initialValue"))
                ET.SubElement(
                    init, qn(PLCOPEN_NS, "simpleValue"), {"value": record.initial_value}
                )
            self._documentation(dt, record.documentation)

        pous_el = ET.SubElement(types, qn(PLCOPEN_NS, "pous"))
        for pou in state.pous:
            pou_el = ET.SubElement(
                pous_el,
                qn(PLCOPEN_NS, "pou"),
                {
                    "name": pou.name,
                    "pouType": pou.pou_type,
                },
            )
            related = [
                v
                for v in state.variables
                if v.owner == pou.name and v.scope.startswith("pou_")
            ]
            if related or pou.return_type.strip():
                interface = ET.SubElement(pou_el, qn(PLCOPEN_NS, "interface"))
                if pou.return_type.strip():
                    return_type = ET.SubElement(interface, qn(PLCOPEN_NS, "returnType"))
                    self._append_type(return_type, pou.return_type.strip())
                group_names = {
                    "pou_local": "localVars",
                    "pou_temp": "tempVars",
                    "pou_input": "inputVars",
                    "pou_output": "outputVars",
                    "pou_inout": "inOutVars",
                    "pou_external": "externalVars",
                    "pou_global": "globalVars",
                }
                for scope, element_name in group_names.items():
                    vars_for_scope = [v for v in related if v.scope == scope]
                    if vars_for_scope:
                        self._variable_list(interface, element_name, vars_for_scope)
            body = ET.SubElement(pou_el, qn(PLCOPEN_NS, "body"))
            language = pou.language.upper()
            if language in {"ST", "IL"}:
                text_el = ET.SubElement(body, qn(PLCOPEN_NS, language))
                ET.SubElement(text_el, qn(XHTML_NS, "xhtml")).text = pou.source
            elif language in {"LD", "FBD", "SFC"}:
                graphical = ET.SubElement(body, qn(PLCOPEN_NS, language))
                if pou.source.strip():
                    add_data = ET.SubElement(body, qn(PLCOPEN_NS, "addData"))
                    data = ET.SubElement(
                        add_data,
                        qn(PLCOPEN_NS, "data"),
                        {
                            "name": "https://integracad-open.org/addData/graphical-source-note/v1",
                            "handleUnknown": "preserve",
                        },
                    )
                    note = ET.SubElement(data, qn(HARDWARE_NS, "graphicalSourceNote"))
                    note.text = pou.source
            else:
                raise ValueError(f"Unsupported POU language: {pou.language}")
            self._documentation(pou_el, pou.documentation)

    def _instances(self, root: ET.Element, state: ProjectState) -> None:
        instances = ET.SubElement(root, qn(PLCOPEN_NS, "instances"))
        configurations = ET.SubElement(instances, qn(PLCOPEN_NS, "configurations"))
        config = ET.SubElement(
            configurations,
            qn(PLCOPEN_NS, "configuration"),
            {"name": state.configuration_name or "Config_1"},
        )

        grouped: dict[str, list[TaskRecord]] = {}
        for task in state.tasks:
            grouped.setdefault(task.resource_name or "PLC_1", []).append(task)
        resource_vars = [v for v in state.variables if v.scope == "resource_global"]
        config_vars = [v for v in state.variables if v.scope == "configuration_global"]

        for resource_name, tasks in grouped.items():
            resource = ET.SubElement(
                config, qn(PLCOPEN_NS, "resource"), {"name": resource_name}
            )
            for task in tasks:
                attrs = {"name": task.name, "priority": str(task.priority)}
                if task.interval.strip():
                    attrs["interval"] = task.interval.strip()
                if task.single_trigger.strip():
                    attrs["single"] = task.single_trigger.strip()
                task_el = ET.SubElement(resource, qn(PLCOPEN_NS, "task"), attrs)
                ET.SubElement(
                    task_el,
                    qn(PLCOPEN_NS, "pouInstance"),
                    {
                        "name": task.program_instance_name,
                        "typeName": task.program_type_name,
                    },
                )
                self._documentation(task_el, task.documentation)
            matching_resource_vars = [
                v
                for v in resource_vars
                if not v.owner.strip() or v.owner == resource_name
            ]
            for variable_group in self._group_variable_attributes(
                matching_resource_vars
            ):
                self._variable_list(resource, "globalVars", variable_group)

        for variable_group in self._group_variable_attributes(config_vars):
            self._variable_list(config, "globalVars", variable_group)

    def _hardware_add_data(
        self, root: ET.Element, hardware: list[HardwareItem]
    ) -> None:
        if not hardware:
            return
        add_data = ET.SubElement(root, qn(PLCOPEN_NS, "addData"))
        data = ET.SubElement(
            add_data,
            qn(PLCOPEN_NS, "data"),
            {
                "name": HARDWARE_DATA_URI,
                "handleUnknown": "preserve",
            },
        )
        config = ET.SubElement(
            data,
            qn(HARDWARE_NS, "hardwareConfiguration"),
            {
                "manufacturer": "Siemens",
                "family": "SIMATIC S7-1200",
                "generatedBy": f"Siemens S7-1200 PLCopen Builder {APP_VERSION}",
                "generatedAt": utc_now_text(),
            },
        )
        for index, item in enumerate(hardware, start=1):
            product = item.product
            attrs = {
                "id": safe_id(f"{item.device_tag or 'HW'}_{index}"),
                "deviceTag": item.device_tag or f"HW{index}",
                "quantity": str(max(1, int(item.quantity))),
                "manufacturer": str(product.get("manufacturer", "Siemens")),
                "family": str(product.get("family", "SIMATIC S7-1200")),
                "category": str(product.get("category", "")),
                "productName": str(product.get("product_name", "")),
                "articleNumber": str(product.get("article_number", "")),
                "catalogYear": str(product.get("catalog_year", "")),
                "catalogPage": str(product.get("source_page", "") or ""),
            }
            device = ET.SubElement(config, qn(HARDWARE_NS, "device"), attrs)
            ET.SubElement(device, qn(HARDWARE_NS, "catalogSummary")).text = str(
                product.get("summary", "")
            )
            if str(product.get("catalog_source", "")).strip():
                ET.SubElement(device, qn(HARDWARE_NS, "catalogSource")).text = str(
                    product.get("catalog_source", "")
                )
            catalog_props = ET.SubElement(device, qn(HARDWARE_NS, "catalogProperties"))
            ignored = {
                "manufacturer",
                "family",
                "category",
                "product_name",
                "article_number",
                "summary",
                "catalog_source",
                "catalog_year",
                "source_page",
            }
            for key, value in sorted(product.items()):
                if key in ignored or value in (None, "", [], {}):
                    continue
                prop = ET.SubElement(
                    catalog_props, qn(HARDWARE_NS, "property"), {"name": key}
                )
                prop.text = bool_text(value) if isinstance(value, bool) else str(value)
            installation = ET.SubElement(
                device,
                qn(HARDWARE_NS, "installation"),
                {
                    "rack": item.rack,
                    "slot": item.slot,
                    "stationName": item.station_name,
                },
            )
            network = ET.SubElement(installation, qn(HARDWARE_NS, "network"))
            for tag, value in [
                ("ipAddress", item.ip_address),
                ("subnetMask", item.subnet_mask),
                ("gateway", item.gateway),
            ]:
                if value.strip():
                    ET.SubElement(network, qn(HARDWARE_NS, tag)).text = value.strip()
            website = ET.SubElement(
                device,
                qn(HARDWARE_NS, "websiteData"),
                {
                    "checkedDate": item.website_checked_date,
                    "lifecycleStatus": item.lifecycle_status,
                    "firmwareVersion": item.firmware_version,
                    "hardwareVersion": item.hardware_version,
                },
            )
            for tag, value in [
                ("productUrl", item.product_url),
                ("supportUrl", item.support_url),
                ("datasheetUrl", item.datasheet_url),
                ("manualUrl", item.manual_url),
                ("caxUrl", item.cax_url),
                ("operatingTemperature", item.operating_temperature),
                ("approvals", item.approvals),
                ("notes", item.notes),
            ]:
                if value.strip():
                    ET.SubElement(website, qn(HARDWARE_NS, tag)).text = value.strip()
            if item.website_properties:
                properties = ET.SubElement(
                    website, qn(HARDWARE_NS, "websiteProperties")
                )
                for name, value in sorted(item.website_properties.items()):
                    prop = ET.SubElement(
                        properties, qn(HARDWARE_NS, "property"), {"name": name}
                    )
                    prop.text = value
            dimensions = ET.SubElement(
                website,
                qn(HARDWARE_NS, "dimensions"),
                {
                    "widthMm": item.width_mm,
                    "heightMm": item.height_mm,
                    "depthMm": item.depth_mm,
                    "weightKg": item.weight_kg,
                },
            )
            if not any([item.width_mm, item.height_mm, item.depth_mm, item.weight_kg]):
                website.remove(dimensions)

    def _data_type_definition(self, parent: ET.Element, record: DataTypeRecord) -> None:
        kind = record.kind.lower()
        definition = record.definition.strip()
        if kind == "alias":
            self._append_type(parent, definition or "BOOL")
        elif kind == "enum":
            enum = ET.SubElement(parent, qn(PLCOPEN_NS, "enum"))
            values = ET.SubElement(enum, qn(PLCOPEN_NS, "values"))
            for token in [x.strip() for x in definition.split(",") if x.strip()]:
                name, sep, value = token.partition("=")
                attrs = {"name": name.strip()}
                if sep and value.strip():
                    attrs["value"] = value.strip()
                ET.SubElement(values, qn(PLCOPEN_NS, "value"), attrs)
        elif kind == "struct":
            struct = ET.SubElement(parent, qn(PLCOPEN_NS, "struct"))
            for token in [x.strip() for x in definition.split(";") if x.strip()]:
                name, sep, dtype = token.partition(":")
                if not sep:
                    raise ValueError(
                        f"Invalid struct member '{token}'. Use Name:TYPE;Name2:TYPE"
                    )
                variable = ET.SubElement(
                    struct, qn(PLCOPEN_NS, "variable"), {"name": name.strip()}
                )
                type_el = ET.SubElement(variable, qn(PLCOPEN_NS, "type"))
                self._append_type(type_el, dtype.strip())
        elif kind == "array":
            match = re.fullmatch(
                r"\s*(-?\d+)\s*\.\.\s*(-?\d+)\s*:\s*([A-Za-z_][\w.]*)\s*", definition
            )
            if not match:
                raise ValueError("Array definition must be: lower..upper:TYPE")
            array = ET.SubElement(parent, qn(PLCOPEN_NS, "array"))
            ET.SubElement(
                array,
                qn(PLCOPEN_NS, "dimension"),
                {"lower": match.group(1), "upper": match.group(2)},
            )
            base = ET.SubElement(array, qn(PLCOPEN_NS, "baseType"))
            self._append_type(base, match.group(3))
        else:
            raise ValueError(f"Unsupported data type kind: {record.kind}")

    @staticmethod
    def _append_type(parent: ET.Element, data_type: str) -> None:
        normalized = data_type.strip()
        upper = normalized.upper()
        if upper.startswith("STRING[") and upper.endswith("]"):
            ET.SubElement(
                parent, qn(PLCOPEN_NS, "string"), {"length": normalized[7:-1]}
            )
        elif upper.startswith("WSTRING[") and upper.endswith("]"):
            ET.SubElement(
                parent, qn(PLCOPEN_NS, "wstring"), {"length": normalized[8:-1]}
            )
        elif upper == "STRING":
            ET.SubElement(parent, qn(PLCOPEN_NS, "string"))
        elif upper == "WSTRING":
            ET.SubElement(parent, qn(PLCOPEN_NS, "wstring"))
        elif upper in ELEMENTARY_TYPES:
            ET.SubElement(parent, qn(PLCOPEN_NS, upper))
        else:
            ET.SubElement(parent, qn(PLCOPEN_NS, "derived"), {"name": normalized})

    def _variable_list(
        self, parent: ET.Element, name: str, variables: list[VariableRecord]
    ) -> ET.Element:
        attrs = self._variable_list_attrs(variables[0]) if variables else {}
        list_el = ET.SubElement(parent, qn(PLCOPEN_NS, name), attrs)
        for record in variables:
            var_attrs = {"name": record.name}
            if record.address.strip():
                var_attrs["address"] = record.address.strip()
            variable = ET.SubElement(list_el, qn(PLCOPEN_NS, "variable"), var_attrs)
            type_el = ET.SubElement(variable, qn(PLCOPEN_NS, "type"))
            self._append_type(type_el, record.data_type)
            if record.initial_value.strip():
                initial = ET.SubElement(variable, qn(PLCOPEN_NS, "initialValue"))
                ET.SubElement(
                    initial,
                    qn(PLCOPEN_NS, "simpleValue"),
                    {"value": record.initial_value},
                )
            self._documentation(variable, record.documentation)
        return list_el

    @staticmethod
    def _variable_list_attrs(record: VariableRecord) -> dict[str, str]:
        attrs: dict[str, str] = {}
        for key in ["constant", "retain", "nonretain", "persistent", "nonpersistent"]:
            if getattr(record, key):
                attrs[key] = "true"
        return attrs

    @staticmethod
    def _group_variable_attributes(
        variables: list[VariableRecord],
    ) -> list[list[VariableRecord]]:
        grouped: dict[tuple[bool, bool, bool, bool, bool], list[VariableRecord]] = {}
        for record in variables:
            key = (
                record.constant,
                record.retain,
                record.nonretain,
                record.persistent,
                record.nonpersistent,
            )
            grouped.setdefault(key, []).append(record)
        return list(grouped.values())

    @staticmethod
    def _documentation(parent: ET.Element, text: str) -> None:
        if not text or not text.strip():
            return
        documentation = ET.SubElement(parent, qn(PLCOPEN_NS, "documentation"))
        ET.SubElement(documentation, qn(XHTML_NS, "xhtml")).text = text


class RecordDialog(simpledialog.Dialog):
    """Scrollable form dialog used by the compact record editors."""

    MULTILINE_KEYS = {"documentation", "notes", "summary"}

    def __init__(
        self,
        parent: tk.Misc,
        title: str,
        fields: list[tuple[str, str, str]],
        initial: dict[str, Any] | None = None,
    ) -> None:
        self.fields = fields
        self.initial = initial or {}
        self.vars: dict[str, tk.StringVar] = {}
        self.text_widgets: dict[str, tk.Text] = {}
        self.result: dict[str, str] | None = None
        super().__init__(parent, title)

    def body(self, master: tk.Misc) -> tk.Widget | None:
        canvas = tk.Canvas(master, highlightthickness=0, width=660, height=520)
        scrollbar = ttk.Scrollbar(master, orient="vertical", command=canvas.yview)
        form = ttk.Frame(canvas)
        window = canvas.create_window((0, 0), window=form, anchor="nw")

        def update_scrollregion(_: tk.Event[Any] | None = None) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def resize_form(event: tk.Event[Any]) -> None:
            canvas.itemconfigure(window, width=event.width)

        form.bind("<Configure>", update_scrollregion)
        canvas.bind("<Configure>", resize_form)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        master.rowconfigure(0, weight=1)
        master.columnconfigure(0, weight=1)

        first: tk.Widget | None = None
        for row, (key, label, default) in enumerate(self.fields):
            ttk.Label(form, text=label).grid(
                row=row, column=0, sticky="nw", padx=5, pady=3
            )
            value = str(self.initial.get(key, default))
            if key in self.MULTILINE_KEYS:
                widget = tk.Text(form, width=58, height=4, wrap="word")
                widget.insert("1.0", value)
                widget.grid(row=row, column=1, sticky="ew", padx=5, pady=3)
                self.text_widgets[key] = widget
            else:
                var = tk.StringVar(value=value)
                self.vars[key] = var
                widget = ttk.Entry(form, textvariable=var, width=58)
                widget.grid(row=row, column=1, sticky="ew", padx=5, pady=3)
            if first is None:
                first = widget
        form.columnconfigure(1, weight=1)
        update_scrollregion()
        return first

    def apply(self) -> None:
        result = {key: var.get().strip() for key, var in self.vars.items()}
        for key, widget in self.text_widgets.items():
            result[key] = widget.get("1.0", "end-1c").strip()
        self.result = result


class SiemensS1200App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"Siemens S7-1200 PLCopen XML Builder {APP_VERSION}")
        self.geometry("1220x820")
        self.minsize(1020, 680)
        self.catalog = CatalogRepository()
        self.exporter = PlcOpenExporter()
        self.state = ProjectState()
        self.current_project_path: Path | None = None
        self.meta_vars: dict[str, tk.StringVar] = {}
        self._build_menu()
        self._build_ui()
        self._load_state_into_ui()

    def _build_menu(self) -> None:
        menu = tk.Menu(self)
        file_menu = tk.Menu(menu, tearoff=False)
        file_menu.add_command(label="New", command=self.new_project)
        file_menu.add_command(label="Open Project JSON…", command=self.open_project)
        file_menu.add_command(label="Save Project", command=self.save_project)
        file_menu.add_command(label="Save Project As…", command=self.save_project_as)
        file_menu.add_separator()
        file_menu.add_command(label="Export PLCopen XML…", command=self.export_xml)
        file_menu.add_command(label="Validate Last Export…", command=self.validate_xml)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)
        menu.add_cascade(label="File", menu=file_menu)
        tools_menu = tk.Menu(menu, tearoff=False)
        tools_menu.add_command(
            label="Engineering consistency report", command=self.show_quality_report
        )
        tools_menu.add_command(
            label="Export hardware BOM CSV…", command=self.export_bom
        )
        tools_menu.add_command(
            label="Export Siemens website checklist…",
            command=self.export_website_checklist,
        )
        tools_menu.add_separator()
        tools_menu.add_command(
            label="Open TIA Selection Tool", command=self.open_tia_selection_tool
        )
        menu.add_cascade(label="Tools", menu=tools_menu)
        help_menu = tk.Menu(menu, tearoff=False)
        help_menu.add_command(
            label="About",
            command=lambda: messagebox.showinfo(
                "About",
                f"Siemens S7-1200 PLCopen XML Builder {APP_VERSION}\n"
                "PLCopen TC6 XML 2.01 with preserved Siemens hardware addData.",
            ),
        )
        menu.add_cascade(label="Help", menu=help_menu)
        self.config(menu=menu)

    def _build_ui(self) -> None:
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=8)
        self.tabs: dict[str, ttk.Frame] = {}
        for key, label in [
            ("project", "1. Project"),
            ("hardware", "2. Hardware"),
            ("types", "3. Data Types"),
            ("variables", "4. Variables"),
            ("pous", "5. POUs"),
            ("tasks", "6. Tasks"),
            ("preview", "7. Preview / Export"),
        ]:
            frame = ttk.Frame(self.notebook)
            self.notebook.add(frame, text=label)
            self.tabs[key] = frame
        self._build_project_tab()
        self._build_hardware_tab()
        self._build_types_tab()
        self._build_variables_tab()
        self._build_pous_tab()
        self._build_tasks_tab()
        self._build_preview_tab()

    def _build_project_tab(self) -> None:
        frame = self.tabs["project"]
        canvas = tk.Canvas(frame, highlightthickness=0)
        scroll = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas)
        inner.bind(
            "<Configure>", lambda _: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        fields = [
            ("fh.companyName", "Company name *"),
            ("fh.companyURL", "Company URL"),
            ("fh.productName", "Exporting product name *"),
            ("fh.productVersion", "Product version *"),
            ("fh.productRelease", "Product release"),
            ("fh.creationDateTime", "Creation date/time *"),
            ("fh.contentDescription", "Content description"),
            ("ch.name", "Project name *"),
            ("ch.version", "Project version"),
            ("ch.modificationDateTime", "Modification date/time"),
            ("ch.organization", "Organization"),
            ("ch.author", "Author"),
            ("ch.language", "Documentation language"),
            ("configuration_name", "Configuration name *"),
            ("ch.pageSizeX", "Page size X"),
            ("ch.pageSizeY", "Page size Y"),
            ("ch.fbdScaleX", "FBD scale X"),
            ("ch.fbdScaleY", "FBD scale Y"),
            ("ch.ldScaleX", "LD scale X"),
            ("ch.ldScaleY", "LD scale Y"),
            ("ch.sfcScaleX", "SFC scale X"),
            ("ch.sfcScaleY", "SFC scale Y"),
        ]
        for row, (key, label) in enumerate(fields):
            ttk.Label(inner, text=label).grid(
                row=row, column=0, sticky="w", padx=8, pady=4
            )
            var = tk.StringVar()
            self.meta_vars[key] = var
            ttk.Entry(inner, textvariable=var, width=85).grid(
                row=row, column=1, sticky="ew", padx=8, pady=4
            )
        row = len(fields)
        ttk.Label(inner, text="Project comment").grid(
            row=row, column=0, sticky="nw", padx=8, pady=4
        )
        self.project_comment = tk.Text(inner, height=5, width=85)
        self.project_comment.grid(row=row, column=1, sticky="ew", padx=8, pady=4)
        row += 1
        ttk.Label(inner, text="Project documentation").grid(
            row=row, column=0, sticky="nw", padx=8, pady=4
        )
        self.project_documentation = tk.Text(inner, height=8, width=85)
        self.project_documentation.grid(row=row, column=1, sticky="ew", padx=8, pady=4)
        inner.columnconfigure(1, weight=1)

    def _build_hardware_tab(self) -> None:
        frame = self.tabs["hardware"]
        selection = ttk.LabelFrame(frame, text="Siemens 2017 brochure catalog")
        selection.pack(fill="x", padx=6, pady=6)
        ttk.Label(selection, text="Category").grid(
            row=0, column=0, padx=5, pady=5, sticky="w"
        )
        self.category_var = tk.StringVar()
        self.category_combo = ttk.Combobox(
            selection, textvariable=self.category_var, state="readonly", width=28
        )
        self.category_combo["values"] = ["All categories", *self.catalog.categories()]
        self.category_combo.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.category_combo.bind("<<ComboboxSelected>>", self._category_changed)
        ttk.Label(selection, text="Search").grid(
            row=0, column=2, padx=5, pady=5, sticky="w"
        )
        self.catalog_search_var = tk.StringVar()
        search_entry = ttk.Entry(
            selection, textvariable=self.catalog_search_var, width=42
        )
        search_entry.grid(row=0, column=3, padx=5, pady=5, sticky="ew")
        search_entry.bind("<KeyRelease>", self._catalog_search_changed)
        ttk.Label(selection, text="Product").grid(
            row=1, column=0, padx=5, pady=5, sticky="w"
        )
        self.product_var = tk.StringVar()
        self.product_combo = ttk.Combobox(
            selection, textvariable=self.product_var, state="readonly", width=72
        )
        self.product_combo.grid(
            row=1, column=1, columnspan=3, padx=5, pady=5, sticky="ew"
        )
        self.product_combo.bind("<<ComboboxSelected>>", self._product_changed)
        ttk.Label(selection, text="Quantity").grid(
            row=2, column=0, padx=5, pady=5, sticky="w"
        )
        self.quantity_var = tk.StringVar(value="1")
        ttk.Spinbox(
            selection, textvariable=self.quantity_var, from_=1, to=999, width=8
        ).grid(row=2, column=1, padx=5, pady=5, sticky="w")
        ttk.Button(
            selection, text="Add selected hardware", command=self.add_hardware
        ).grid(row=2, column=3, padx=5, pady=5, sticky="e")
        self.product_summary = tk.StringVar(value="Select a product.")
        ttk.Label(selection, textvariable=self.product_summary, wraplength=1000).grid(
            row=3, column=0, columnspan=4, padx=5, pady=5, sticky="w"
        )
        selection.columnconfigure(3, weight=1)

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", padx=6)
        ttk.Button(
            buttons, text="Edit installation / website data", command=self.edit_hardware
        ).pack(side="left", padx=3)
        ttk.Button(
            buttons, text="Fill official Siemens URLs", command=self.fill_siemens_urls
        ).pack(side="left", padx=3)
        ttk.Button(
            buttons, text="Open product page", command=self.open_product_page
        ).pack(side="left", padx=3)
        ttk.Button(
            buttons, text="Open datasheet", command=self.open_datasheet_page
        ).pack(side="left", padx=3)
        ttk.Button(buttons, text="Duplicate", command=self.duplicate_hardware).pack(
            side="left", padx=3
        )
        ttk.Button(buttons, text="Remove", command=self.remove_hardware).pack(
            side="left", padx=3
        )
        ttk.Button(
            buttons, text="Add custom product", command=self.add_custom_product
        ).pack(side="left", padx=3)

        columns = (
            "tag",
            "qty",
            "category",
            "product",
            "article",
            "rack",
            "slot",
            "ip",
            "status",
        )
        self.hardware_tree = ttk.Treeview(
            frame, columns=columns, show="headings", selectmode="browse"
        )
        headings = {
            "tag": "Tag",
            "qty": "Qty",
            "category": "Category",
            "product": "Product",
            "article": "Article No.",
            "rack": "Rack",
            "slot": "Slot",
            "ip": "IP address",
            "status": "Lifecycle",
        }
        widths = {
            "tag": 90,
            "qty": 45,
            "category": 130,
            "product": 250,
            "article": 165,
            "rack": 55,
            "slot": 55,
            "ip": 120,
            "status": 110,
        }
        for col in columns:
            self.hardware_tree.heading(col, text=headings[col])
            self.hardware_tree.column(col, width=widths[col], anchor="w")
        self.hardware_tree.pack(fill="both", expand=True, padx=6, pady=6)
        self.hardware_summary_var = tk.StringVar(value="No hardware selected.")
        ttk.Label(frame, textvariable=self.hardware_summary_var, anchor="w").pack(
            fill="x", padx=9, pady=(0, 6)
        )
        if self.catalog.categories():
            self.category_var.set("All categories")
            self._category_changed()

    def _build_types_tab(self) -> None:
        frame = self.tabs["types"]
        note = "Alias definition: BOOL or MyType | Enum: Idle=0,Running=1 | Struct: Ready:BOOL;Count:DINT | Array: 1..10:REAL"
        ttk.Label(frame, text=note, wraplength=1100).pack(fill="x", padx=6, pady=6)
        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", padx=6)
        ttk.Button(buttons, text="Add", command=self.add_data_type).pack(
            side="left", padx=3
        )
        ttk.Button(buttons, text="Edit", command=self.edit_data_type).pack(
            side="left", padx=3
        )
        ttk.Button(buttons, text="Remove", command=self.remove_data_type).pack(
            side="left", padx=3
        )
        cols = ("name", "kind", "definition", "initial", "documentation")
        self.types_tree = ttk.Treeview(frame, columns=cols, show="headings")
        for col, title, width in [
            ("name", "Name", 180),
            ("kind", "Kind", 90),
            ("definition", "Definition", 430),
            ("initial", "Initial", 120),
            ("documentation", "Documentation", 350),
        ]:
            self.types_tree.heading(col, text=title)
            self.types_tree.column(col, width=width, anchor="w")
        self.types_tree.pack(fill="both", expand=True, padx=6, pady=6)

    def _build_variables_tab(self) -> None:
        frame = self.tabs["variables"]
        ttk.Label(
            frame,
            text="Owner is required for POU and resource scopes. For resource globals, owner is the resource name.",
        ).pack(fill="x", padx=6, pady=6)
        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", padx=6)
        ttk.Button(buttons, text="Add", command=self.add_variable).pack(
            side="left", padx=3
        )
        ttk.Button(buttons, text="Edit", command=self.edit_variable).pack(
            side="left", padx=3
        )
        ttk.Button(buttons, text="Remove", command=self.remove_variable).pack(
            side="left", padx=3
        )
        cols = (
            "name",
            "type",
            "scope",
            "owner",
            "address",
            "initial",
            "flags",
            "documentation",
        )
        self.variables_tree = ttk.Treeview(frame, columns=cols, show="headings")
        specs = [
            ("name", "Name", 130),
            ("type", "Type", 110),
            ("scope", "Scope", 150),
            ("owner", "Owner", 130),
            ("address", "Address", 100),
            ("initial", "Initial", 100),
            ("flags", "Attributes", 160),
            ("documentation", "Documentation", 320),
        ]
        for col, title, width in specs:
            self.variables_tree.heading(col, text=title)
            self.variables_tree.column(col, width=width, anchor="w")
        self.variables_tree.pack(fill="both", expand=True, padx=6, pady=6)

    def _build_pous_tab(self) -> None:
        frame = self.tabs["pous"]
        left = ttk.Frame(frame)
        left.pack(side="left", fill="y", padx=6, pady=6)
        right = ttk.Frame(frame)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ttk.Button(left, text="Add", command=self.add_pou).pack(fill="x", pady=2)
        ttk.Button(left, text="Rename / properties", command=self.edit_pou).pack(
            fill="x", pady=2
        )
        ttk.Button(left, text="Remove", command=self.remove_pou).pack(fill="x", pady=2)
        self.pou_list = tk.Listbox(left, width=34, exportselection=False)
        self.pou_list.pack(fill="both", expand=True, pady=6)
        self.pou_list.bind("<<ListboxSelect>>", self._pou_selected)
        ttk.Label(
            right,
            text="POU source (ST/IL). For LD/FBD/SFC this is preserved as a source note; use an engineering tool for graphical networks.",
        ).pack(anchor="w")
        self.pou_source = tk.Text(
            right, wrap="none", undo=True, font=("TkFixedFont", 10)
        )
        self.pou_source.pack(fill="both", expand=True, pady=4)
        ttk.Label(right, text="Documentation").pack(anchor="w")
        self.pou_documentation = tk.Text(right, height=5, wrap="word")
        self.pou_documentation.pack(fill="x", pady=4)
        ttk.Button(
            right, text="Apply source and documentation", command=self.apply_pou_text
        ).pack(anchor="e")

    def _build_tasks_tab(self) -> None:
        frame = self.tabs["tasks"]
        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", padx=6, pady=6)
        ttk.Button(buttons, text="Add", command=self.add_task).pack(side="left", padx=3)
        ttk.Button(buttons, text="Edit", command=self.edit_task).pack(
            side="left", padx=3
        )
        ttk.Button(buttons, text="Remove", command=self.remove_task).pack(
            side="left", padx=3
        )
        cols = (
            "resource",
            "task",
            "interval",
            "priority",
            "instance",
            "program",
            "trigger",
            "documentation",
        )
        self.tasks_tree = ttk.Treeview(frame, columns=cols, show="headings")
        specs = [
            ("resource", "Resource", 130),
            ("task", "Task", 120),
            ("interval", "Interval", 100),
            ("priority", "Priority", 70),
            ("instance", "Instance", 140),
            ("program", "Program type", 150),
            ("trigger", "Single trigger", 110),
            ("documentation", "Documentation", 300),
        ]
        for col, title, width in specs:
            self.tasks_tree.heading(col, text=title)
            self.tasks_tree.column(col, width=width, anchor="w")
        self.tasks_tree.pack(fill="both", expand=True, padx=6, pady=6)

    def _build_preview_tab(self) -> None:
        frame = self.tabs["preview"]
        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", padx=6, pady=6)
        ttk.Button(buttons, text="Refresh preview", command=self.refresh_preview).pack(
            side="left", padx=3
        )
        ttk.Button(buttons, text="Export XML", command=self.export_xml).pack(
            side="left", padx=3
        )
        ttk.Button(buttons, text="Validate XML file", command=self.validate_xml).pack(
            side="left", padx=3
        )
        ttk.Button(buttons, text="Save project JSON", command=self.save_project).pack(
            side="left", padx=3
        )
        self.preview_text = tk.Text(frame, wrap="none", font=("TkFixedFont", 9))
        self.preview_text.pack(fill="both", expand=True, padx=6, pady=6)

    def _load_state_into_ui(self) -> None:
        for key, var in self.meta_vars.items():
            if key.startswith("fh."):
                var.set(self.state.file_header.get(key[3:], ""))
            elif key.startswith("ch."):
                var.set(self.state.content_header.get(key[3:], ""))
            elif key == "configuration_name":
                var.set(self.state.configuration_name)
        self.project_comment.delete("1.0", "end")
        self.project_comment.insert("1.0", self.state.content_header.get("comment", ""))
        self.project_documentation.delete("1.0", "end")
        self.project_documentation.insert("1.0", self.state.project_documentation)
        self.refresh_all_lists()

    def _sync_state_from_ui(self) -> None:
        self.apply_pou_text(silent=True)
        for key, var in self.meta_vars.items():
            if key.startswith("fh."):
                self.state.file_header[key[3:]] = var.get().strip()
            elif key.startswith("ch."):
                self.state.content_header[key[3:]] = var.get().strip()
            elif key == "configuration_name":
                self.state.configuration_name = var.get().strip()
        self.state.content_header["comment"] = self.project_comment.get("1.0", "end-1c")
        self.state.project_documentation = self.project_documentation.get(
            "1.0", "end-1c"
        )
        self.state.content_header["modificationDateTime"] = utc_now_text()

    def refresh_all_lists(self) -> None:
        self._refresh_hardware()
        self._refresh_types()
        self._refresh_variables()
        self._refresh_pous()
        self._refresh_tasks()

    def _filtered_catalog_products(self) -> list[dict[str, Any]]:
        category = self.category_var.get()
        if category == "All categories":
            category = ""
        return self.catalog.search(self.catalog_search_var.get(), category)

    def _category_changed(self, *_: Any) -> None:
        products = self._filtered_catalog_products()
        labels = [self.catalog.product_label(product) for product in products]
        self.product_combo["values"] = labels
        if labels:
            self.product_var.set(labels[0])
            self._product_changed()
        else:
            self.product_var.set("")
            self.product_summary.set(
                "No catalog product matches the category and search text."
            )

    def _catalog_search_changed(self, *_: Any) -> None:
        self._category_changed()

    def _selected_catalog_product(self) -> dict[str, Any] | None:
        label = self.product_var.get()
        for product in self._filtered_catalog_products():
            if self.catalog.product_label(product) == label:
                return product
        return None

    def _product_changed(self, *_: Any) -> None:
        product = self._selected_catalog_product()
        if product:
            self.product_summary.set(product.get("summary", ""))

    def add_hardware(self) -> None:
        product = self._selected_catalog_product()
        if not product:
            return
        try:
            qty = max(1, int(self.quantity_var.get()))
        except ValueError:
            messagebox.showerror("Quantity", "Quantity must be an integer.")
            return
        tag = f"{self._tag_prefix(product.get('category','HW'))}{len(self.state.hardware)+1}"
        urls = siemens_urls(product["article_number"])
        self.state.hardware.append(
            HardwareItem(
                product=copy.deepcopy(product),
                quantity=qty,
                device_tag=tag,
                slot=str(len(self.state.hardware)),
                product_url=urls.product,
                datasheet_url=urls.datasheet_pdf,
            )
        )
        self._refresh_hardware()

    @staticmethod
    def _tag_prefix(category: str) -> str:
        mapping = {
            "CPU": "PLC",
            "Digital Signal Module": "DIOM",
            "Analog Signal Module": "AIOM",
            "Fail-safe Signal Module": "FIOM",
            "Communication Module": "CM",
            "Technology Module": "TM",
            "Signal Board": "SB",
            "Power Supply": "PS",
            "HMI": "HMI",
            "Memory Card": "MC",
        }
        return mapping.get(category, "HW")

    @staticmethod
    def _siemens_product_url(article: str) -> str:
        return siemens_urls(article).product

    @staticmethod
    def _siemens_datasheet_url(article: str) -> str:
        return siemens_urls(article).datasheet_pdf

    def _selected_index(self, tree: ttk.Treeview) -> int | None:
        selected = tree.selection()
        if not selected:
            return None
        return int(selected[0])

    def _refresh_hardware(self) -> None:
        self.hardware_tree.delete(*self.hardware_tree.get_children())
        for i, item in enumerate(self.state.hardware):
            p = item.product
            self.hardware_tree.insert(
                "",
                "end",
                iid=str(i),
                values=(
                    item.device_tag,
                    item.quantity,
                    p.get("category", ""),
                    p.get("product_name", ""),
                    p.get("article_number", ""),
                    item.rack,
                    item.slot,
                    item.ip_address,
                    item.lifecycle_status,
                ),
            )
        if hasattr(self, "hardware_summary_var"):
            self.hardware_summary_var.set(format_hardware_summary(self.state.hardware))

    def edit_hardware(self) -> None:
        idx = self._selected_index(self.hardware_tree)
        if idx is None:
            messagebox.showinfo("Hardware", "Select a hardware row.")
            return
        item = self.state.hardware[idx]
        fields = [
            ("device_tag", "Device tag", item.device_tag),
            ("quantity", "Quantity", str(item.quantity)),
            ("rack", "Rack", item.rack),
            ("slot", "Slot", item.slot),
            ("station_name", "PROFINET station name", item.station_name),
            ("ip_address", "IP address", item.ip_address),
            ("subnet_mask", "Subnet mask", item.subnet_mask),
            ("gateway", "Gateway", item.gateway),
            ("firmware_version", "Firmware version", item.firmware_version),
            ("hardware_version", "Hardware version", item.hardware_version),
            ("lifecycle_status", "Lifecycle status", item.lifecycle_status),
            ("product_url", "Siemens product URL", item.product_url),
            ("support_url", "Support URL", item.support_url),
            ("datasheet_url", "Datasheet URL", item.datasheet_url),
            ("manual_url", "Manual URL", item.manual_url),
            ("cax_url", "CAx/CAD URL", item.cax_url),
            ("width_mm", "Width mm", item.width_mm),
            ("height_mm", "Height mm", item.height_mm),
            ("depth_mm", "Depth mm", item.depth_mm),
            ("weight_kg", "Weight kg", item.weight_kg),
            (
                "operating_temperature",
                "Operating temperature",
                item.operating_temperature,
            ),
            ("approvals", "Approvals", item.approvals),
            ("website_checked_date", "Website checked date", item.website_checked_date),
            (
                "website_properties",
                "Additional website properties (Name=Value; ...)",
                format_property_text(item.website_properties),
            ),
            ("notes", "Notes", item.notes),
        ]
        dialog = RecordDialog(self, "Installation and Siemens website data", fields)
        if dialog.result:
            for key, value in dialog.result.items():
                if key == "quantity":
                    try:
                        item.quantity = max(1, int(value))
                    except ValueError:
                        messagebox.showerror("Quantity", "Quantity must be an integer.")
                elif key == "website_properties":
                    try:
                        item.website_properties = parse_property_text(value)
                    except ValueError as exc:
                        messagebox.showerror("Additional website properties", str(exc))
                        return
                else:
                    setattr(item, key, value)
            self._refresh_hardware()

    def open_product_page(self) -> None:
        idx = self._selected_index(self.hardware_tree)
        if idx is None:
            return
        item = self.state.hardware[idx]
        url = item.product_url or self._siemens_product_url(
            item.product.get("article_number", "")
        )
        webbrowser.open(url)

    def open_datasheet_page(self) -> None:
        idx = self._selected_index(self.hardware_tree)
        if idx is None:
            return
        item = self.state.hardware[idx]
        article = item.product.get("article_number", "")
        url = item.datasheet_url or self._siemens_datasheet_url(article)
        webbrowser.open(url)

    def open_tia_selection_tool(self) -> None:
        webbrowser.open(siemens_urls("").tia_selection_tool)

    def fill_siemens_urls(self) -> None:
        idx = self._selected_index(self.hardware_tree)
        if idx is None:
            messagebox.showinfo("Hardware", "Select a hardware row.")
            return
        item = self.state.hardware[idx]
        article = item.product.get("article_number", "")
        if not article:
            messagebox.showwarning(
                "Siemens URLs", "The selected item has no Siemens article number."
            )
            return
        urls = siemens_urls(article)
        item.product_url = item.product_url or urls.product
        item.datasheet_url = item.datasheet_url or urls.datasheet_pdf
        self._refresh_hardware()
        messagebox.showinfo(
            "Siemens URLs",
            "Official Siemens product and datasheet entry-point URLs were filled. "
            "Review the pages and record lifecycle, firmware, dimensions, approvals, "
            "manuals, CAx data, and the checked date.",
        )

    def duplicate_hardware(self) -> None:
        idx = self._selected_index(self.hardware_tree)
        if idx is None:
            return
        item = copy.deepcopy(self.state.hardware[idx])
        item.device_tag = f"{item.device_tag}_COPY"
        self.state.hardware.append(item)
        self._refresh_hardware()

    def remove_hardware(self) -> None:
        idx = self._selected_index(self.hardware_tree)
        if idx is not None:
            del self.state.hardware[idx]
            self._refresh_hardware()

    def add_custom_product(self) -> None:
        fields = [
            ("category", "Category", "Custom Hardware"),
            ("product_name", "Product name", ""),
            ("article_number", "Article number", ""),
            ("summary", "Description", ""),
            ("manufacturer", "Manufacturer", "Siemens"),
            ("family", "Family", "SIMATIC S7-1200"),
        ]
        dialog = RecordDialog(self, "Add custom product", fields)
        if dialog.result:
            product = {
                **dialog.result,
                "catalog_source": "User entry / manufacturer website",
                "catalog_year": "",
                "source_page": "",
            }
            urls = (
                siemens_urls(product["article_number"])
                if product["article_number"]
                else None
            )
            self.state.hardware.append(
                HardwareItem(
                    product=product,
                    device_tag=f"HW{len(self.state.hardware)+1}",
                    product_url=urls.product if urls else "",
                    datasheet_url=urls.datasheet_pdf if urls else "",
                )
            )
            self._refresh_hardware()

    def _refresh_types(self) -> None:
        self.types_tree.delete(*self.types_tree.get_children())
        for i, r in enumerate(self.state.data_types):
            self.types_tree.insert(
                "",
                "end",
                iid=str(i),
                values=(r.name, r.kind, r.definition, r.initial_value, r.documentation),
            )

    def add_data_type(self) -> None:
        self._data_type_dialog(None)

    def edit_data_type(self) -> None:
        idx = self._selected_index(self.types_tree)
        if idx is not None:
            self._data_type_dialog(idx)

    def _data_type_dialog(self, idx: int | None) -> None:
        initial = asdict(self.state.data_types[idx]) if idx is not None else {}
        fields = [
            ("name", "Name", ""),
            ("kind", "Kind: alias, enum, struct, array", "alias"),
            ("definition", "Definition", "BOOL"),
            ("initial_value", "Initial value", ""),
            ("documentation", "Documentation", ""),
        ]
        dialog = RecordDialog(self, "Data type", fields, initial)
        if dialog.result:
            record = DataTypeRecord(**dialog.result)
            if idx is None:
                self.state.data_types.append(record)
            else:
                self.state.data_types[idx] = record
            self._refresh_types()

    def remove_data_type(self) -> None:
        idx = self._selected_index(self.types_tree)
        if idx is not None:
            del self.state.data_types[idx]
            self._refresh_types()

    def _refresh_variables(self) -> None:
        self.variables_tree.delete(*self.variables_tree.get_children())
        for i, r in enumerate(self.state.variables):
            flags = ",".join(
                k
                for k in [
                    "constant",
                    "retain",
                    "nonretain",
                    "persistent",
                    "nonpersistent",
                ]
                if getattr(r, k)
            )
            self.variables_tree.insert(
                "",
                "end",
                iid=str(i),
                values=(
                    r.name,
                    r.data_type,
                    r.scope,
                    r.owner,
                    r.address,
                    r.initial_value,
                    flags,
                    r.documentation,
                ),
            )

    def add_variable(self) -> None:
        self._variable_dialog(None)

    def edit_variable(self) -> None:
        idx = self._selected_index(self.variables_tree)
        if idx is not None:
            self._variable_dialog(idx)

    def _variable_dialog(self, idx: int | None) -> None:
        initial = asdict(self.state.variables[idx]) if idx is not None else {}
        fields = [
            ("name", "Name", ""),
            ("data_type", "Data type", "BOOL"),
            ("scope", f"Scope: {', '.join(VAR_SCOPES)}", "configuration_global"),
            ("owner", "Owner POU/resource", ""),
            ("address", "Direct address", ""),
            ("initial_value", "Initial value", ""),
            ("constant", "Constant true/false", "false"),
            ("retain", "Retain true/false", "false"),
            ("nonretain", "Nonretain true/false", "false"),
            ("persistent", "Persistent true/false", "false"),
            ("nonpersistent", "Nonpersistent true/false", "false"),
            ("documentation", "Documentation", ""),
        ]
        if initial:
            for key in [
                "constant",
                "retain",
                "nonretain",
                "persistent",
                "nonpersistent",
            ]:
                initial[key] = bool_text(initial[key])
        dialog = RecordDialog(self, "Variable", fields, initial)
        if dialog.result:
            raw = dialog.result
            for key in [
                "constant",
                "retain",
                "nonretain",
                "persistent",
                "nonpersistent",
            ]:
                raw[key] = raw[key].lower() in {"true", "1", "yes", "y"}
            record = VariableRecord(**raw)
            if record.scope not in VAR_SCOPES:
                messagebox.showerror(
                    "Scope", f"Scope must be one of: {', '.join(VAR_SCOPES)}"
                )
                return
            if idx is None:
                self.state.variables.append(record)
            else:
                self.state.variables[idx] = record
            self._refresh_variables()

    def remove_variable(self) -> None:
        idx = self._selected_index(self.variables_tree)
        if idx is not None:
            del self.state.variables[idx]
            self._refresh_variables()

    def _refresh_pous(self) -> None:
        selected = self.pou_list.curselection()
        selected_index = selected[0] if selected else 0
        self.pou_list.delete(0, "end")
        for r in self.state.pous:
            self.pou_list.insert("end", f"{r.name} [{r.pou_type}/{r.language}]")
        if self.state.pous:
            selected_index = min(selected_index, len(self.state.pous) - 1)
            self.pou_list.selection_set(selected_index)
            self._pou_selected()
        else:
            self.pou_source.delete("1.0", "end")
            self.pou_documentation.delete("1.0", "end")

    def _pou_index(self) -> int | None:
        sel = self.pou_list.curselection()
        return sel[0] if sel else None

    def _pou_selected(self, *_: Any) -> None:
        idx = self._pou_index()
        if idx is None:
            return
        r = self.state.pous[idx]
        self.pou_source.delete("1.0", "end")
        self.pou_source.insert("1.0", r.source)
        self.pou_documentation.delete("1.0", "end")
        self.pou_documentation.insert("1.0", r.documentation)

    def apply_pou_text(self, silent: bool = False) -> None:
        idx = self._pou_index()
        if idx is None:
            return
        self.state.pous[idx].source = self.pou_source.get("1.0", "end-1c")
        self.state.pous[idx].documentation = self.pou_documentation.get("1.0", "end-1c")
        if not silent:
            messagebox.showinfo("POU", "Source and documentation applied.")

    def add_pou(self) -> None:
        self._pou_dialog(None)

    def edit_pou(self) -> None:
        idx = self._pou_index()
        if idx is not None:
            self._pou_dialog(idx)

    def _pou_dialog(self, idx: int | None) -> None:
        initial = (
            asdict(self.state.pous[idx])
            if idx is not None
            else {"pou_type": "program", "language": "ST"}
        )
        fields = [
            ("name", "POU name", ""),
            ("pou_type", "POU type: program, functionBlock, function", "program"),
            ("language", "Language: ST, IL, LD, FBD, SFC", "ST"),
            ("return_type", "Function return type (blank for program/FB)", ""),
        ]
        dialog = RecordDialog(self, "POU properties", fields, initial)
        if dialog.result:
            if dialog.result["pou_type"] not in {
                "program",
                "functionBlock",
                "function",
            }:
                messagebox.showerror(
                    "POU type", "Use program, functionBlock, or function."
                )
                return
            if dialog.result["language"].upper() not in {
                "ST",
                "IL",
                "LD",
                "FBD",
                "SFC",
            }:
                messagebox.showerror("Language", "Use ST, IL, LD, FBD, or SFC.")
                return
            if idx is None:
                self.state.pous.append(
                    POURecord(
                        name=dialog.result["name"],
                        pou_type=dialog.result["pou_type"],
                        language=dialog.result["language"].upper(),
                        return_type=dialog.result["return_type"],
                    )
                )
            else:
                old = self.state.pous[idx].name
                self.state.pous[idx].name = dialog.result["name"]
                self.state.pous[idx].pou_type = dialog.result["pou_type"]
                self.state.pous[idx].language = dialog.result["language"].upper()
                self.state.pous[idx].return_type = dialog.result["return_type"]
                for variable in self.state.variables:
                    if variable.owner == old and variable.scope.startswith("pou_"):
                        variable.owner = dialog.result["name"]
                for task in self.state.tasks:
                    if task.program_type_name == old:
                        task.program_type_name = dialog.result["name"]
            self._refresh_pous()
            self._refresh_variables()
            self._refresh_tasks()

    def remove_pou(self) -> None:
        idx = self._pou_index()
        if idx is not None:
            del self.state.pous[idx]
            self._refresh_pous()

    def _refresh_tasks(self) -> None:
        self.tasks_tree.delete(*self.tasks_tree.get_children())
        for i, r in enumerate(self.state.tasks):
            self.tasks_tree.insert(
                "",
                "end",
                iid=str(i),
                values=(
                    r.resource_name,
                    r.name,
                    r.interval,
                    r.priority,
                    r.program_instance_name,
                    r.program_type_name,
                    r.single_trigger,
                    r.documentation,
                ),
            )

    def add_task(self) -> None:
        self._task_dialog(None)

    def edit_task(self) -> None:
        idx = self._selected_index(self.tasks_tree)
        if idx is not None:
            self._task_dialog(idx)

    def _task_dialog(self, idx: int | None) -> None:
        initial = asdict(self.state.tasks[idx]) if idx is not None else {}
        fields = [
            ("resource_name", "Resource name", "PLC_1"),
            ("name", "Task name", "MainTask"),
            ("interval", "Interval, e.g. T#100ms", "T#100ms"),
            ("priority", "Priority 0-65535", "1"),
            ("program_instance_name", "Program instance name", "MainInstance"),
            ("program_type_name", "Program POU type name", "MainProgram"),
            ("single_trigger", "Single trigger variable", ""),
            ("documentation", "Documentation", ""),
        ]
        dialog = RecordDialog(self, "Resource task", fields, initial)
        if dialog.result:
            raw = dialog.result
            try:
                priority = int(raw["priority"])
                assert 0 <= priority <= 65535
            except Exception:
                messagebox.showerror(
                    "Priority", "Priority must be an integer from 0 to 65535."
                )
                return
            raw["priority"] = priority
            record = TaskRecord(**raw)
            if idx is None:
                self.state.tasks.append(record)
            else:
                self.state.tasks[idx] = record
            self._refresh_tasks()

    def remove_task(self) -> None:
        idx = self._selected_index(self.tasks_tree)
        if idx is not None:
            del self.state.tasks[idx]
            self._refresh_tasks()

    def show_quality_report(self) -> None:
        self._sync_state_from_ui()
        report = project_quality_report(self.state)
        if report.errors:
            messagebox.showerror("Engineering consistency report", report.text())
        elif report.warnings:
            messagebox.showwarning("Engineering consistency report", report.text())
        else:
            messagebox.showinfo("Engineering consistency report", report.text())

    def export_bom(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Export hardware BOM",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
        )
        if not path:
            return
        self._sync_state_from_ui()
        export_bom_csv(self.state, Path(path))
        messagebox.showinfo("Hardware BOM", f"Exported {path}")

    def export_website_checklist(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Export Siemens website checklist",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
        )
        if not path:
            return
        self._sync_state_from_ui()
        export_website_checklist_csv(self.state, Path(path))
        messagebox.showinfo("Website checklist", f"Exported {path}")

    def refresh_preview(self) -> None:
        try:
            self._sync_state_from_ui()
            text = self.exporter.to_string(self.state)
        except Exception as exc:
            messagebox.showerror("Preview error", str(exc))
            return
        self.preview_text.delete("1.0", "end")
        self.preview_text.insert("1.0", text)

    def new_project(self) -> None:
        if not messagebox.askyesno("New project", "Clear the current project?"):
            return
        self.state = ProjectState()
        self.current_project_path = None
        self._load_state_into_ui()

    def open_project(self) -> None:
        path = filedialog.askopenfilename(
            title="Open project JSON",
            filetypes=[
                ("PLC project JSON", "*.plcproj.json *.json"),
                ("All files", "*"),
            ],
        )
        if not path:
            return
        try:
            self.state = ProjectState.from_dict(
                json.loads(Path(path).read_text(encoding="utf-8"))
            )
            self.current_project_path = Path(path)
            self._load_state_into_ui()
        except Exception as exc:
            messagebox.showerror("Open project", str(exc))

    def save_project(self) -> None:
        if self.current_project_path is None:
            self.save_project_as()
            return
        self._sync_state_from_ui()
        self.current_project_path.write_text(
            json.dumps(self.state.to_dict(), indent=2), encoding="utf-8"
        )
        messagebox.showinfo("Project", f"Saved {self.current_project_path}")

    def save_project_as(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Save project JSON",
            defaultextension=".plcproj.json",
            filetypes=[("PLC project JSON", "*.plcproj.json"), ("JSON", "*.json")],
        )
        if not path:
            return
        self.current_project_path = Path(path)
        self.save_project()

    def export_xml(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Export PLCopen XML",
            defaultextension=".xml",
            filetypes=[("PLCopen XML", "*.xml")],
        )
        if not path:
            return
        try:
            self._sync_state_from_ui()
            report = project_quality_report(self.state)
            if report.errors:
                messagebox.showerror(
                    "Engineering consistency errors",
                    report.text() + "\n\nThe XML was not exported.",
                )
                return
            if report.warnings and not messagebox.askyesno(
                "Engineering consistency warnings",
                report.text() + "\n\nContinue with export?",
            ):
                return
            self.exporter.write(self.state, Path(path))
            valid, msg = self.exporter.validate_all(Path(path))
            if valid:
                messagebox.showinfo(
                    "Export complete", f"Exported and validated:\n{path}\n\n{msg}"
                )
            else:
                messagebox.showwarning(
                    "Export complete", f"Exported:\n{path}\n\nValidation status:\n{msg}"
                )
        except Exception as exc:
            messagebox.showerror("Export error", str(exc))

    def validate_xml(self) -> None:
        path = filedialog.askopenfilename(
            title="Validate PLCopen XML",
            filetypes=[("XML", "*.xml"), ("All files", "*")],
        )
        if not path:
            return
        valid, msg = self.exporter.validate_all(Path(path))
        (messagebox.showinfo if valid else messagebox.showerror)("Validation", msg)


def build_example_project(destination: Path) -> tuple[bool, str]:
    state = ProjectState()
    catalog = CatalogRepository()
    cpu = catalog.by_article["6ES7214-1AG40-0XB0"]
    urls = siemens_urls(cpu["article_number"])
    state.file_header["companyName"] = "Example Engineering Company"
    state.content_header["author"] = "Controls Engineer"
    state.hardware.append(
        HardwareItem(
            product=copy.deepcopy(cpu),
            device_tag="PLC1",
            rack="0",
            slot="1",
            station_name="plc1",
            ip_address="192.168.1.10",
            subnet_mask="255.255.255.0",
            product_url=urls.product,
            datasheet_url=urls.datasheet_pdf,
            lifecycle_status="Verify in SiePortal",
            website_checked_date=datetime.now().date().isoformat(),
        )
    )
    state.variables.append(
        VariableRecord(
            name="StartPB",
            data_type="BOOL",
            scope="pou_input",
            owner="MainProgram",
            documentation="Start pushbutton command.",
        )
    )
    exporter = PlcOpenExporter()
    exporter.write(state, destination)
    return exporter.validate_all(destination)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build and validate PLCopen TC6 XML with Siemens S7-1200 hardware metadata."
    )
    parser.add_argument("--version", action="version", version=APP_VERSION)
    parser.add_argument(
        "--example",
        nargs="?",
        const="example_s7_1200_project.xml",
        metavar="XML",
        help="Generate a schema-valid example XML file.",
    )
    parser.add_argument(
        "--validate",
        metavar="XML",
        help="Validate PLCopen and Siemens extension schemas.",
    )
    parser.add_argument(
        "--catalog-summary",
        action="store_true",
        help="Print catalog categories and counts.",
    )
    args = parser.parse_args()

    if args.catalog_summary:
        catalog = CatalogRepository()
        print(f"{catalog.metadata['manufacturer']} {catalog.metadata['family']}")
        print(
            f"Catalog: {catalog.metadata['edition']} ({len(catalog.products)} products)"
        )
        for category in catalog.categories():
            print(f"{category}: {len(catalog.products_in(category))}")
        return 0

    if args.validate:
        valid, message = PlcOpenExporter().validate_all(Path(args.validate))
        print(message)
        return 0 if valid else 1

    if args.example:
        destination = Path(args.example).resolve()
        valid, message = build_example_project(destination)
        print(destination)
        print(message)
        return 0 if valid else 1

    app = SiemensS1200App()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
