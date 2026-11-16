"""Exporter module serializing synthetic datasets to CSV and JSON formats."""

import csv
import json
from pathlib import Path
from typing import Any

from app.generator.synthesizer import GeneratedDataset


class DatasetExporter:
    """Exports generated dataset into standardized CSV and JSON artifact files."""

    def __init__(self, output_dir: Path | str = "data/synthetic") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_all(self, dataset: GeneratedDataset) -> dict[str, Path]:
        """Serializes all operational domains into CSV and JSON files with manifest."""
        saved_paths: dict[str, Path] = {}

        # 1. Company
        company_path = self.output_dir / "company.json"
        with open(company_path, "w", encoding="utf-8") as f:
            json.dump(dataset.company, f, indent=2)
        saved_paths["company_json"] = company_path

        # 2. Collections mapping (name -> records)
        collections: dict[str, list[dict[str, Any]]] = {
            "customers": dataset.customers,
            "orders": dataset.orders,
            "order_items": dataset.order_items,
            "metrics": dataset.metrics,
            "events": dataset.system_events,
            "deployments": dataset.deployments,
            "support_tickets": dataset.support_tickets,
            "complaints": dataset.complaints,
        }

        for name, records in collections.items():
            # Export CSV
            csv_path = self.output_dir / f"{name}.csv"
            self._write_csv(csv_path, records)
            saved_paths[f"{name}_csv"] = csv_path

            # Export JSON
            json_path = self.output_dir / f"{name}.json"
            self._write_json(json_path, records)
            saved_paths[f"{name}_json"] = json_path

        # 3. Incident Scenarios
        scenario_path = self.output_dir / "incident_scenarios.json"
        with open(scenario_path, "w", encoding="utf-8") as f:
            json.dump([dataset.scenario_metadata], f, indent=2)
        saved_paths["incident_scenarios_json"] = scenario_path

        # 4. Manifest
        manifest = {
            "dataset_id": f"synthetic-{dataset.company['name'].lower()}-90d",
            "company_name": dataset.company["name"],
            "classification": dataset.company["metadata"].get("classification", "PUBLIC_DEMO"),
            "exported_at": dataset.company["created_at"],
            "stats": dataset.generation_stats,
            "files": {k: str(v.name) for k, v in saved_paths.items()},
        }
        manifest_path = self.output_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        saved_paths["manifest_json"] = manifest_path

        return saved_paths

    def _write_csv(self, path: Path, records: list[dict[str, Any]]) -> None:
        """Helper to write records to a CSV file."""
        if not records:
            path.write_text("", encoding="utf-8")
            return

        headers = list(records[0].keys())
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            for row in records:
                # Serialize any nested dict/json structures as JSON strings for CSV compatibility
                serialized_row = {}
                for k, v in row.items():
                    if isinstance(v, (dict, list)):
                        serialized_row[k] = json.dumps(v)
                    else:
                        serialized_row[k] = v
                writer.writerow(serialized_row)

    def _write_json(self, path: Path, records: list[dict[str, Any]]) -> None:
        """Helper to write records to a JSON file."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)
