from __future__ import annotations

import copy
import csv
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SPEC = importlib.util.spec_from_file_location(
    "builder", ROOT / "siemens_s7_1200_plcopen_app.py"
)
assert SPEC and SPEC.loader
builder = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = builder
SPEC.loader.exec_module(builder)

from engineering import (  # noqa: E402
    export_bom_csv,
    export_website_checklist_csv,
    hardware_summary,
    project_quality_report,
    siemens_urls,
)


class ExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = builder.CatalogRepository(
            ROOT / "catalog" / "siemens_s7_1200_2017.json"
        )
        self.exporter = builder.PlcOpenExporter(
            ROOT / "schemas" / "tc6_xml_v201.xsd",
            ROOT / "schemas" / "siemens_s7_1200_hardware_v1.xsd",
        )

    def base_state(self) -> builder.ProjectState:
        state = builder.ProjectState()
        state.file_header["companyName"] = "Test Company"
        product = copy.deepcopy(self.catalog.by_article["6ES7214-1AG40-0XB0"])
        urls = siemens_urls(product["article_number"])
        state.hardware.append(
            builder.HardwareItem(
                product=product,
                device_tag="PLC1",
                rack="0",
                slot="1",
                station_name="plc1",
                ip_address="192.168.0.10",
                subnet_mask="255.255.255.0",
                product_url=urls.product,
                datasheet_url=urls.datasheet_pdf,
                lifecycle_status="PM300: Active Product",
                website_checked_date="2026-07-18",
                website_properties={
                    "CurrentProgramMemoryKB": "150",
                    "EAN": "4047623402787",
                },
            )
        )
        return state

    def test_catalog_has_brochure_products(self) -> None:
        self.assertEqual(len(self.catalog.products), 104)
        self.assertIn("6ES7214-1AG40-0XB0", self.catalog.by_article)
        self.assertIn("6ES7226-6BA32-0XB0", self.catalog.by_article)
        self.assertIn("6AV2123-2GB03-0AX0", self.catalog.by_article)
        self.assertGreaterEqual(len(self.catalog.categories()), 10)

    def test_catalog_search(self) -> None:
        results = self.catalog.search("1214C DC/DC/DC")
        articles = {item["article_number"] for item in results}
        self.assertIn("6ES7214-1AG40-0XB0", articles)
        filtered = self.catalog.search("relay", "CPU")
        self.assertTrue(filtered)
        self.assertTrue(all(item["category"] == "CPU" for item in filtered))

    def test_schema_valid_export(self) -> None:
        state = self.base_state()
        state.data_types.extend(
            [
                builder.DataTypeRecord("E_State", "enum", "Idle=0,Running=1,Faulted=2"),
                builder.DataTypeRecord("ST_Status", "struct", "Ready:BOOL;Count:DINT"),
                builder.DataTypeRecord("A_Temperatures", "array", "1..8:REAL"),
            ]
        )
        state.variables.extend(
            [
                builder.VariableRecord(
                    "StartPB",
                    "BOOL",
                    "pou_input",
                    "MainProgram",
                    documentation="Start input",
                ),
                builder.VariableRecord(
                    "CycleCount", "DINT", "configuration_global", retain=True
                ),
            ]
        )
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "project.xml"
            self.exporter.write(state, destination)
            valid, message = self.exporter.validate_all(destination)
            self.assertTrue(valid, message)
            text = destination.read_text(encoding="utf-8")
            self.assertIn("6ES7214-1AG40-0XB0", text)
            self.assertIn("hardwareConfiguration", text)
            self.assertIn("websiteProperties", text)
            self.assertIn("CurrentProgramMemoryKB", text)
            self.assertIn("MainProgram", text)

    def test_all_pou_language_bodies_validate(self) -> None:
        for language in ["ST", "IL", "LD", "FBD", "SFC"]:
            with self.subTest(language=language), tempfile.TemporaryDirectory() as tmp:
                state = self.base_state()
                state.pous = [
                    builder.POURecord(
                        name="Program1",
                        pou_type="program",
                        language=language,
                        source="Source or graphical engineering note",
                    )
                ]
                state.tasks = [builder.TaskRecord(program_type_name="Program1")]
                destination = Path(tmp) / f"{language}.xml"
                self.exporter.write(state, destination)
                valid, message = self.exporter.validate_all(destination)
                self.assertTrue(valid, message)

    def test_hardware_summary_is_quantity_weighted(self) -> None:
        state = self.base_state()
        module = copy.deepcopy(self.catalog.by_article["6ES7221-1BH32-0XB0"])
        state.hardware.append(
            builder.HardwareItem(product=module, quantity=2, device_tag="DI1")
        )
        totals = hardware_summary(state.hardware)
        self.assertEqual(totals["cpus"], 1)
        self.assertEqual(totals["digital_inputs"], 14 + 32)
        self.assertEqual(totals["pieces"], 3)

    def test_quality_report_detects_duplicate_tags_and_missing_program(self) -> None:
        state = self.base_state()
        state.hardware.append(copy.deepcopy(state.hardware[0]))
        state.tasks[0].program_type_name = "MissingProgram"
        report = project_quality_report(state)
        self.assertFalse(report.ok)
        text = report.text()
        self.assertIn("Duplicate hardware device tag", text)
        self.assertIn("MissingProgram", text)

    def test_csv_handoffs(self) -> None:
        state = self.base_state()
        with tempfile.TemporaryDirectory() as tmp:
            bom = Path(tmp) / "bom.csv"
            checklist = Path(tmp) / "website.csv"
            export_bom_csv(state, bom)
            export_website_checklist_csv(state, checklist)
            with bom.open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(rows[0]["ArticleNumber"], "6ES7214-1AG40-0XB0")
            with checklist.open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            self.assertIn("teddatasheet", rows[0]["DatasheetURL"])

    def test_every_catalog_product_can_be_exported_in_extension(self) -> None:
        state = builder.ProjectState()
        state.file_header["companyName"] = "Catalog Export Test"
        for index, product in enumerate(self.catalog.products, start=1):
            urls = siemens_urls(product["article_number"])
            state.hardware.append(
                builder.HardwareItem(
                    product=copy.deepcopy(product),
                    device_tag=f"HW{index}",
                    rack="CATALOG",
                    slot=str(index),
                    product_url=urls.product,
                    datasheet_url=urls.datasheet_pdf,
                    lifecycle_status="Not checked in catalog export test",
                    website_checked_date="2026-07-18",
                )
            )
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "all_catalog_products.xml"
            self.exporter.write(state, destination)
            valid, message = self.exporter.validate_all(destination)
            self.assertTrue(valid, message)

    def test_project_json_round_trip(self) -> None:
        original = self.base_state()
        restored = builder.ProjectState.from_dict(original.to_dict())
        self.assertEqual(restored.to_dict(), original.to_dict())


if __name__ == "__main__":
    unittest.main()
