"""Ingestion pipeline coordinator orchestrating reading, validation, and loading."""

import time
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.ingestion.loader import BatchDataLoader
from app.ingestion.models import EntityIngestionSummary, IngestionReport
from app.ingestion.parsers import DatasetParser
from app.ingestion.validator import DataValidator

logger = get_logger("aegis.ingestion")


class IngestionPipeline:
    """End-to-end ingestion pipeline executing validation, transformation, batch insertion, and reporting."""

    def __init__(self, session: Session, batch_size: int = 1000) -> None:
        self.session = session
        self.batch_size = batch_size
        self.validator = DataValidator()
        self.loader = BatchDataLoader(session, batch_size=batch_size)

    def run(
        self,
        source_dir: Path | str,
        file_format: str = "csv",
        dataset_id: str = "synthetic-demo-001",
    ) -> IngestionReport:
        """Executes complete ingestion process from source directory."""
        start_time = datetime.now(UTC)
        t0 = time.perf_counter()

        report = IngestionReport(
            dataset_id=dataset_id,
            data_source=f"filesystem:{source_dir}",
            classification="PUBLIC_DEMO",
            started_at=start_time,
            completed_at=start_time,
            duration_seconds=0.0,
        )

        logger.info(f"Starting ingestion pipeline from {source_dir} (format: {file_format})...")

        # Step 1: Parse dataset
        try:
            raw_data = DatasetParser.read_dataset(source_dir, file_format=file_format)
        except Exception as exc:
            logger.error(f"Failed to read dataset from {source_dir}: {exc}")
            report.errors.append(f"Parsing error: {exc}")
            report.completed_at = datetime.now(UTC)
            report.duration_seconds = time.perf_counter() - t0
            return report

        # Step 2: Validate & Load in dependency order (Company -> Customers -> Deployments -> Metrics -> Events -> Orders -> OrderItems -> Tickets -> Complaints)
        self._process_company(raw_data.get("company", []), report)
        self._process_customers(raw_data.get("customers", []), report)
        self._process_deployments(raw_data.get("deployments", []), report)
        self._process_metrics(raw_data.get("metrics", []), report)
        self._process_events(raw_data.get("events", []), report)
        self._process_orders(raw_data.get("orders", []), report)
        self._process_order_items(raw_data.get("order_items", []), report)
        self._process_tickets(raw_data.get("support_tickets", []), report)
        self._process_complaints(raw_data.get("complaints", []), report)

        # Aggregate overall statistics
        for summary in report.entity_summaries.values():
            report.total_records_received += summary.received
            report.total_records_inserted += summary.inserted
            report.total_records_rejected += summary.rejected
            report.total_duplicates_detected += summary.duplicates

        report.completed_at = datetime.now(UTC)
        report.duration_seconds = time.perf_counter() - t0

        logger.info(
            f"Ingestion finished: {report.total_records_received} received, "
            f"{report.total_records_inserted} inserted, "
            f"{report.total_records_rejected} rejected, "
            f"{report.total_duplicates_detected} duplicates in {report.duration_seconds:.2f}s"
        )

        return report

    def _process_company(self, records: list, report: IngestionReport) -> None:
        summary = EntityIngestionSummary(entity_name="company")
        valid = self.validator.validate_company(records, summary)
        if valid:
            self.loader.load_company(valid, summary)
        report.entity_summaries["company"] = summary

    def _process_customers(self, records: list, report: IngestionReport) -> None:
        summary = EntityIngestionSummary(entity_name="customers")
        valid = self.validator.validate_customers(records, summary)
        if valid:
            self.loader.load_customers(valid, summary)
        report.entity_summaries["customers"] = summary

    def _process_deployments(self, records: list, report: IngestionReport) -> None:
        summary = EntityIngestionSummary(entity_name="deployments")
        valid = self.validator.validate_deployments(records, summary)
        if valid:
            self.loader.load_deployments(valid, summary)
        report.entity_summaries["deployments"] = summary

    def _process_metrics(self, records: list, report: IngestionReport) -> None:
        summary = EntityIngestionSummary(entity_name="metrics")
        valid = self.validator.validate_metrics(records, summary)
        if valid:
            self.loader.load_metrics(valid, summary)
        report.entity_summaries["metrics"] = summary

    def _process_events(self, records: list, report: IngestionReport) -> None:
        summary = EntityIngestionSummary(entity_name="events")
        valid = self.validator.validate_events(records, summary)
        if valid:
            self.loader.load_events(valid, summary)
        report.entity_summaries["events"] = summary

    def _process_orders(self, records: list, report: IngestionReport) -> None:
        summary = EntityIngestionSummary(entity_name="orders")
        valid = self.validator.validate_orders(records, summary)
        if valid:
            self.loader.load_orders(valid, summary)
        report.entity_summaries["orders"] = summary

    def _process_order_items(self, records: list, report: IngestionReport) -> None:
        summary = EntityIngestionSummary(entity_name="order_items")
        valid = self.validator.validate_order_items(records, summary)
        if valid:
            self.loader.load_order_items(valid, summary)
        report.entity_summaries["order_items"] = summary

    def _process_tickets(self, records: list, report: IngestionReport) -> None:
        summary = EntityIngestionSummary(entity_name="support_tickets")
        valid = self.validator.validate_support_tickets(records, summary)
        if valid:
            self.loader.load_support_tickets(valid, summary)
        report.entity_summaries["support_tickets"] = summary

    def _process_complaints(self, records: list, report: IngestionReport) -> None:
        summary = EntityIngestionSummary(entity_name="complaints")
        valid = self.validator.validate_complaints(records, summary)
        if valid:
            self.loader.load_complaints(valid, summary)
        report.entity_summaries["complaints"] = summary
