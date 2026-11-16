"""Parsers and readers for CSV and JSON synthetic datasets."""

import csv
import json
from pathlib import Path
from typing import Any


class DatasetParser:
    """Parses tabular CSV or hierarchical JSON dataset files into normalized Python dictionaries."""

    @staticmethod
    def read_dataset(
        source_dir: Path | str, file_format: str = "csv"
    ) -> dict[str, list[dict[str, Any]]]:
        """Reads all dataset files from directory based on format ('csv' or 'json')."""
        path = Path(source_dir)
        if not path.exists():
            raise FileNotFoundError(f"Source directory not found: {source_dir}")

        result: dict[str, list[dict[str, Any]]] = {}

        # Company file (always JSON)
        company_file = path / "company.json"
        if company_file.exists():
            with open(company_file, encoding="utf-8") as f:
                result["company"] = [json.load(f)]
        else:
            result["company"] = []

        entities = [
            "customers",
            "orders",
            "order_items",
            "metrics",
            "events",
            "deployments",
            "support_tickets",
            "complaints",
        ]

        for entity in entities:
            if file_format.lower() == "csv":
                csv_path = path / f"{entity}.csv"
                if csv_path.exists():
                    result[entity] = DatasetParser._parse_csv(csv_path)
                else:
                    result[entity] = []
            elif file_format.lower() == "json":
                json_path = path / f"{entity}.json"
                if json_path.exists():
                    result[entity] = DatasetParser._parse_json(json_path)
                else:
                    result[entity] = []
            else:
                raise ValueError(f"Unsupported format: {file_format}. Expected 'csv' or 'json'.")

        return result

    @staticmethod
    def _parse_csv(file_path: Path) -> list[dict[str, Any]]:
        """Parses a CSV file and converts serialized JSON string columns into dictionaries."""
        records: list[dict[str, Any]] = []
        json_fields = {
            "dimension_data",
            "event_metadata",
            "deployment_metadata",
            "ticket_metadata",
            "complaint_metadata",
            "metadata",
        }

        with open(file_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                parsed_row: dict[str, Any] = {}
                for k, v in row.items():
                    if k in json_fields and v:
                        try:
                            parsed_row[k] = json.loads(v)
                        except (json.JSONDecodeError, TypeError):
                            parsed_row[k] = {}
                    else:
                        parsed_row[k] = v
                records.append(parsed_row)
        return records

    @staticmethod
    def _parse_json(file_path: Path) -> list[dict[str, Any]]:
        """Parses a JSON file containing a list of records."""
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return [data]
            return []
