"""Engineering utilities for the Siemens S7-1200 PLCopen builder.

This module is intentionally independent of Tkinter.  It can be reused by later
vendor adapters and by command-line or test workflows.
"""

from __future__ import annotations

import csv
from datetime import date
import ipaddress
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote


@dataclass(frozen=True)
class SiemensUrls:
    """Official Siemens URL templates that do not require page scraping."""

    product: str
    datasheet_pdf: str
    tia_selection_tool: str = (
        "https://www.siemens.com/en-us/products/tia/selection-tool/"
    )


def siemens_urls(article_number: str) -> SiemensUrls:
    """Build stable official Siemens entry-point URLs for an MLFB/article number.

    Siemens pages remain the source of truth.  These links are entry points only;
    lifecycle, firmware, dimensions, approvals, manuals, and CAx data should be
    reviewed by the engineer and recorded with a checked date.
    """

    article = article_number.strip()
    encoded = quote(article)
    return SiemensUrls(
        product=(
            "https://sieportal.siemens.com/en-ww/products-services/detail/"
            f"{encoded}?tree=CatalogTree"
        ),
        datasheet_pdf=(
            "https://support.industry.siemens.com/teddatasheet/"
            f"?caller=SIOS&format=pdf&language=en&mlfbs={encoded}"
        ),
    )


def _number(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _is_identifier(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value.strip()))


def _valid_iso_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


def hardware_summary(hardware: Iterable[Any]) -> dict[str, int]:
    """Return quantity-weighted system counts from catalog properties."""

    totals = {
        "line_items": 0,
        "pieces": 0,
        "cpus": 0,
        "fail_safe_cpus": 0,
        "digital_inputs": 0,
        "digital_outputs": 0,
        "analog_inputs": 0,
        "analog_outputs": 0,
        "fail_safe_inputs": 0,
        "fail_safe_outputs": 0,
        "profinet_ports": 0,
    }
    for item in hardware:
        product = item.product
        quantity = max(1, _number(item.quantity))
        totals["line_items"] += 1
        totals["pieces"] += quantity
        if product.get("category") == "CPU":
            totals["cpus"] += quantity
            if product.get("fail_safe"):
                totals["fail_safe_cpus"] += quantity
        totals["digital_inputs"] += (
            _number(product.get("digital_inputs")) + _number(product.get("onboard_di"))
        ) * quantity
        totals["digital_outputs"] += (
            _number(product.get("digital_outputs")) + _number(product.get("onboard_dq"))
        ) * quantity
        totals["analog_inputs"] += (
            _number(product.get("analog_inputs")) + _number(product.get("onboard_ai"))
        ) * quantity
        totals["analog_outputs"] += (
            _number(product.get("analog_outputs")) + _number(product.get("onboard_aq"))
        ) * quantity
        for key in ("fail_safe_inputs", "fail_safe_outputs", "profinet_ports"):
            totals[key] += _number(product.get(key)) * quantity
    return totals


def format_hardware_summary(hardware: Iterable[Any]) -> str:
    totals = hardware_summary(hardware)
    return (
        f"{totals['line_items']} line items / {totals['pieces']} pieces | "
        f"CPU {totals['cpus']} (F-CPU {totals['fail_safe_cpus']}) | "
        f"DI {totals['digital_inputs']} | DQ {totals['digital_outputs']} | "
        f"AI {totals['analog_inputs']} | AQ {totals['analog_outputs']} | "
        f"F-DI {totals['fail_safe_inputs']} | F-DQ {totals['fail_safe_outputs']}"
    )


@dataclass
class QualityReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def text(self) -> str:
        lines: list[str] = []
        if self.errors:
            lines.append("Errors:")
            lines.extend(f"- {value}" for value in self.errors)
        if self.warnings:
            if lines:
                lines.append("")
            lines.append("Warnings:")
            lines.extend(f"- {value}" for value in self.warnings)
        if not lines:
            lines.append("No engineering consistency errors or warnings were found.")
        return "\n".join(lines)


def project_quality_report(state: Any) -> QualityReport:
    """Check semantic consistency not enforced by the PLCopen XSD."""

    report = QualityReport()
    required_header = {
        "companyName": "Company name",
        "productName": "Exporting product name",
        "productVersion": "Exporting product version",
        "creationDateTime": "Creation date/time",
    }
    for key, label in required_header.items():
        if not str(state.file_header.get(key, "")).strip():
            report.errors.append(f"{label} is blank.")
    if not str(state.content_header.get("name", "")).strip():
        report.errors.append("Project name is blank.")
    if not str(state.configuration_name).strip():
        report.errors.append("Configuration name is blank.")

    pou_names = [p.name for p in state.pous]
    duplicate_pous = sorted({name for name in pou_names if pou_names.count(name) > 1})
    for name in duplicate_pous:
        report.errors.append(f"Duplicate POU name: {name}.")
    for pou in state.pous:
        if not _is_identifier(pou.name):
            report.warnings.append(
                f"POU name {pou.name!r} is not a conservative IEC identifier."
            )

    program_pous = {p.name for p in state.pous if p.pou_type == "program"}
    for task in state.tasks:
        if task.program_type_name not in program_pous:
            report.errors.append(
                f"Task {task.name} references missing or non-program POU "
                f"{task.program_type_name}."
            )
        if task.interval.strip() and task.single_trigger.strip():
            report.warnings.append(
                f"Task {task.name} has both interval and single-trigger attributes. "
                "Confirm the target tool's intended scheduling semantics."
            )
        if not _is_identifier(task.name):
            report.warnings.append(
                f"Task name {task.name!r} is not a conservative IEC identifier."
            )

    resource_names = {task.resource_name or "PLC_1" for task in state.tasks}
    variable_keys = [(v.scope, v.owner, v.name) for v in state.variables]
    duplicate_variables = sorted(
        {key for key in variable_keys if variable_keys.count(key) > 1}
    )
    for scope, owner, name in duplicate_variables:
        report.errors.append(
            f"Duplicate variable {name} in scope {scope} owned by {owner or 'configuration'}."
        )
    for variable in state.variables:
        if not _is_identifier(variable.name):
            report.warnings.append(
                f"Variable name {variable.name!r} is not a conservative IEC identifier."
            )
        if variable.scope.startswith("pou_") and variable.owner not in set(pou_names):
            report.errors.append(
                f"Variable {variable.name} references unknown POU owner {variable.owner!r}."
            )
        if (
            variable.scope == "resource_global"
            and variable.owner
            and variable.owner not in resource_names
        ):
            report.errors.append(
                f"Resource-global variable {variable.name} references unknown resource "
                f"{variable.owner!r}."
            )
        if variable.retain and variable.nonretain:
            report.errors.append(
                f"Variable {variable.name} is both retain and nonretain."
            )
        if variable.persistent and variable.nonpersistent:
            report.errors.append(
                f"Variable {variable.name} is both persistent and nonpersistent."
            )

    tags = [
        item.device_tag.strip() for item in state.hardware if item.device_tag.strip()
    ]
    duplicate_tags = sorted({tag for tag in tags if tags.count(tag) > 1})
    for tag in duplicate_tags:
        report.errors.append(f"Duplicate hardware device tag: {tag}.")

    occupied: dict[tuple[str, str], str] = {}
    for item in state.hardware:
        rack_slot = (item.rack.strip(), item.slot.strip())
        if not all(rack_slot):
            continue
        existing = occupied.get(rack_slot)
        if existing:
            report.warnings.append(
                f"Rack {rack_slot[0]} slot {rack_slot[1]} is assigned to both "
                f"{existing} and {item.device_tag or item.product.get('product_name', 'hardware')}."
            )
        else:
            occupied[rack_slot] = item.device_tag or item.product.get(
                "product_name", "hardware"
            )

    cpu_count = hardware_summary(state.hardware)["cpus"]
    if cpu_count == 0:
        report.warnings.append("No CPU has been selected.")
    elif cpu_count > 1:
        report.warnings.append(
            "More than one CPU is selected. The first release does not model multiple stations "
            "or enforce separate rack ownership."
        )

    used_ips: dict[str, str] = {}
    for item in state.hardware:
        label = item.device_tag or item.product.get("article_number", "hardware")
        if not item.device_tag.strip():
            report.errors.append(
                f"Hardware item {item.product.get('article_number', '')} has no device tag."
            )
        if _number(item.quantity) < 1:
            report.errors.append(f"{label}: quantity must be at least 1.")
        if _number(item.quantity) > 1 and (item.rack.strip() or item.slot.strip()):
            report.warnings.append(
                f"{label}: quantity is greater than one but only one rack/slot placement is recorded. "
                "Use separate line items when each physical instance needs its own placement."
            )
        if item.ip_address.strip():
            try:
                ipaddress.ip_address(item.ip_address.strip())
            except ValueError:
                report.errors.append(
                    f"{label}: invalid IP address {item.ip_address!r}."
                )
            existing = used_ips.get(item.ip_address.strip())
            if existing:
                report.errors.append(
                    f"IP address {item.ip_address.strip()} is assigned to both {existing} and {label}."
                )
            else:
                used_ips[item.ip_address.strip()] = label
        for field_name, field_value in (
            ("subnet mask", item.subnet_mask),
            ("gateway", item.gateway),
        ):
            if field_value.strip():
                try:
                    ipaddress.ip_address(field_value.strip())
                except ValueError:
                    report.errors.append(
                        f"{label}: invalid {field_name} {field_value!r}."
                    )
        if item.station_name.strip() and not re.fullmatch(
            r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)*",
            item.station_name.strip(),
        ):
            report.warnings.append(
                f"{label}: PROFINET station name {item.station_name!r} is not a conservative "
                "lowercase DNS-style name."
            )
        if not item.website_checked_date:
            report.warnings.append(f"{label}: Siemens website checked date is blank.")
        elif not _valid_iso_date(item.website_checked_date):
            report.errors.append(f"{label}: website checked date must use YYYY-MM-DD.")
        if not item.lifecycle_status:
            report.warnings.append(f"{label}: lifecycle status has not been recorded.")
        if not item.product_url:
            report.warnings.append(f"{label}: product URL is blank.")

    return report


def export_bom_csv(state: Any, destination: Path) -> None:
    """Export a vendor-neutral-enough hardware BOM with Siemens source fields."""

    columns = [
        "DeviceTag",
        "Quantity",
        "Manufacturer",
        "Family",
        "Category",
        "ProductName",
        "ArticleNumber",
        "Rack",
        "Slot",
        "StationName",
        "IPAddress",
        "FirmwareVersion",
        "HardwareVersion",
        "LifecycleStatus",
        "ProductURL",
        "DatasheetURL",
        "ManualURL",
        "CAxURL",
        "WebsiteCheckedDate",
        "AdditionalWebsiteProperties",
        "Notes",
    ]
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for item in state.hardware:
            product = item.product
            writer.writerow(
                {
                    "DeviceTag": item.device_tag,
                    "Quantity": item.quantity,
                    "Manufacturer": product.get("manufacturer", "Siemens"),
                    "Family": product.get("family", "SIMATIC S7-1200"),
                    "Category": product.get("category", ""),
                    "ProductName": product.get("product_name", ""),
                    "ArticleNumber": product.get("article_number", ""),
                    "Rack": item.rack,
                    "Slot": item.slot,
                    "StationName": item.station_name,
                    "IPAddress": item.ip_address,
                    "FirmwareVersion": item.firmware_version,
                    "HardwareVersion": item.hardware_version,
                    "LifecycleStatus": item.lifecycle_status,
                    "ProductURL": item.product_url,
                    "DatasheetURL": item.datasheet_url,
                    "ManualURL": item.manual_url,
                    "CAxURL": item.cax_url,
                    "WebsiteCheckedDate": item.website_checked_date,
                    "AdditionalWebsiteProperties": json.dumps(
                        item.website_properties, sort_keys=True
                    ),
                    "Notes": item.notes,
                }
            )


def export_website_checklist_csv(state: Any, destination: Path) -> None:
    """Export fields that should be confirmed on current Siemens pages."""

    columns = [
        "DeviceTag",
        "ArticleNumber",
        "ProductName",
        "ProductURL",
        "DatasheetURL",
        "LifecycleStatus",
        "FirmwareVersion",
        "HardwareVersion",
        "Width_mm",
        "Height_mm",
        "Depth_mm",
        "Weight_kg",
        "OperatingTemperature",
        "Approvals",
        "ManualURL",
        "CAxURL",
        "WebsiteCheckedDate",
        "AdditionalWebsiteProperties",
        "ReviewerNotes",
    ]
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for item in state.hardware:
            product = item.product
            writer.writerow(
                {
                    "DeviceTag": item.device_tag,
                    "ArticleNumber": product.get("article_number", ""),
                    "ProductName": product.get("product_name", ""),
                    "ProductURL": item.product_url,
                    "DatasheetURL": item.datasheet_url,
                    "LifecycleStatus": item.lifecycle_status,
                    "FirmwareVersion": item.firmware_version,
                    "HardwareVersion": item.hardware_version,
                    "Width_mm": item.width_mm,
                    "Height_mm": item.height_mm,
                    "Depth_mm": item.depth_mm,
                    "Weight_kg": item.weight_kg,
                    "OperatingTemperature": item.operating_temperature,
                    "Approvals": item.approvals,
                    "ManualURL": item.manual_url,
                    "CAxURL": item.cax_url,
                    "WebsiteCheckedDate": item.website_checked_date,
                    "AdditionalWebsiteProperties": json.dumps(
                        item.website_properties, sort_keys=True
                    ),
                    "ReviewerNotes": item.notes,
                }
            )
