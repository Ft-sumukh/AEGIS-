"""Unit and integration tests for data ingestion pipeline and idempotency."""

import shutil
import tempfile
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.database.base import Base
from app.generator.config import GeneratorConfig
from app.generator.exporter import DatasetExporter
from app.generator.synthesizer import EnterpriseDataSynthesizer
from app.ingestion.models import EntityIngestionSummary, IngestionReport
from app.ingestion.parsers import DatasetParser
from app.ingestion.service import IngestionPipeline
from app.ingestion.validator import DataValidator
from app.models.customer import Customer


@pytest.fixture
def sqlite_session():
    """In-memory SQLite database session fixture."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    with session_factory() as session:
        yield session


@pytest.fixture
def sample_data_dir():
    """Generates a small temporary dataset on disk."""
    temp_dir = Path(tempfile.mkdtemp())
    cfg = GeneratorConfig(days=2, customer_count=30, output_dir=temp_dir)
    ds = EnterpriseDataSynthesizer(cfg).synthesize()
    DatasetExporter(temp_dir).export_all(ds)
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_validator_rejects_invalid_records() -> None:
    """Verifies that the validator rejects missing required fields and out-of-range values."""
    validator = DataValidator()
    summary = EntityIngestionSummary(entity_name="customers")

    # Missing name and ext_ref
    invalid_custs = [
        {"id": str(uuid.uuid4()), "name": "", "external_reference": ""},
        {"id": str(uuid.uuid4()), "name": "Valid Name", "external_reference": "CUST-001"},
        {
            "id": str(uuid.uuid4()),
            "name": "Valid Name 2",
            "external_reference": "CUST-001",
        },  # Duplicate
    ]

    valid = validator.validate_customers(invalid_custs, summary)
    assert len(valid) == 1
    assert summary.received == 3
    assert summary.rejected == 2
    assert summary.duplicates == 1


def test_validator_rejects_negative_order_amounts() -> None:
    """Verifies that orders with negative dollar amounts are rejected."""
    validator = DataValidator()
    # Mock valid customer
    cust_id = str(uuid.uuid4())
    validator.valid_customer_ids.add(cust_id)
    summary = EntityIngestionSummary(entity_name="orders")

    orders = [
        {
            "id": str(uuid.uuid4()),
            "customer_id": cust_id,
            "external_reference": "ORD-1",
            "total_amount": -50.0,
            "status": "COMPLETED",
        },
        {
            "id": str(uuid.uuid4()),
            "customer_id": cust_id,
            "external_reference": "ORD-2",
            "total_amount": 120.0,
            "status": "COMPLETED",
        },
        {
            "id": str(uuid.uuid4()),
            "customer_id": cust_id,
            "external_reference": "ORD-3",
            "total_amount": "invalid",
            "status": "COMPLETED",
        },
    ]

    valid = validator.validate_orders(orders, summary)
    assert len(valid) == 1
    assert summary.rejected == 2


def test_csv_and_json_parsing(sample_data_dir: Path) -> None:
    """Verifies that DatasetParser reads both CSV and JSON formats accurately."""
    csv_data = DatasetParser.read_dataset(sample_data_dir, file_format="csv")
    json_data = DatasetParser.read_dataset(sample_data_dir, file_format="json")

    assert len(csv_data["customers"]) == len(json_data["customers"])
    assert len(csv_data["metrics"]) == len(json_data["metrics"])
    assert len(csv_data["orders"]) == len(json_data["orders"])


def test_batch_ingestion_and_idempotency(sqlite_session: Session, sample_data_dir: Path) -> None:
    """Verifies that ingestion loads all records, and re-running produces zero new inserts."""
    pipeline = IngestionPipeline(sqlite_session, batch_size=50)

    # First run
    report1: IngestionReport = pipeline.run(sample_data_dir, file_format="csv")
    assert report1.total_records_inserted > 0
    assert report1.total_records_rejected == 0
    initial_inserted = report1.total_records_inserted

    # Verify counts in DB
    db_cust_count = (
        sqlite_session.scalar(select(Customer).count())
        if hasattr(select(Customer), "count")
        else len(sqlite_session.scalars(select(Customer)).all())
    )
    assert db_cust_count > 0

    # Second run (Idempotency check)
    report2: IngestionReport = pipeline.run(sample_data_dir, file_format="csv")
    assert report2.total_records_inserted == 0
    assert report2.total_duplicates_detected == initial_inserted
