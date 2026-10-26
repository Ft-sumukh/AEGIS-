"""Command-line interface for Aegis synthetic data generation and ingestion."""

import sys
from pathlib import Path

import click
from sqlalchemy import select

from app.core.logging import get_logger, setup_logging
from app.database.session import get_session_factory
from app.generator.config import GeneratorConfig
from app.generator.exporter import DatasetExporter
from app.generator.synthesizer import EnterpriseDataSynthesizer
from app.ingestion.parsers import DatasetParser
from app.ingestion.service import IngestionPipeline
from app.ingestion.validator import DataValidator
from app.models.company import Company

logger = get_logger("aegis.cli")


@click.group()
def cli() -> None:
    """Aegis Operations Intelligence CLI - Synthetic Data & Ingestion Tools."""
    setup_logging(log_level="INFO")


@cli.command("generate-data")
@click.option("--days", default=90, type=int, help="Number of simulation days (default: 90).")
@click.option("--seed", default=42, type=int, help="Random seed for reproducibility (default: 42).")
@click.option(
    "--customers", default=1500, type=int, help="Customer population count (default: 1500)."
)
@click.option("--output-dir", default="data/synthetic", type=str, help="Target output directory.")
@click.option("--company", default="NovaCart", type=str, help="Fictional company name.")
def generate_data(days: int, seed: int, customers: int, output_dir: str, company: str) -> None:
    """Generates synthetic enterprise operational telemetry (CSV + JSON)."""
    click.echo("[*] Initializing Aegis Synthetic Enterprise Generator...")
    click.echo(f"    - Company: {company}")
    click.echo(f"    - Timeline: {days} days ({days * 24} hours)")
    click.echo(f"    - Customers: {customers}")
    click.echo(f"    - Seed: {seed}")
    click.echo(f"    - Output: {output_dir}")

    config = GeneratorConfig(
        company_name=company,
        days=days,
        seed=seed,
        customer_count=customers,
        output_dir=Path(output_dir),
    )

    synthesizer = EnterpriseDataSynthesizer(config)
    click.echo("[*] Simulating operational causal timeline and incident injection...")
    dataset = synthesizer.synthesize()

    click.echo("[*] Exporting datasets to CSV and JSON formats...")
    exporter = DatasetExporter(output_dir)
    exporter.export_all(dataset)

    click.echo("[+] Synthetic generation complete!")
    click.echo(f"    - Metrics recorded: {len(dataset.metrics):,}")
    click.echo(f"    - Orders simulated: {len(dataset.orders):,}")
    click.echo(f"    - System events: {len(dataset.system_events):,}")
    click.echo(f"    - Deployments: {len(dataset.deployments):,}")
    click.echo(f"    - Support tickets: {len(dataset.support_tickets):,}")
    click.echo(f"    - Customer complaints: {len(dataset.complaints):,}")
    click.echo(f"    - Artifacts written to: {Path(output_dir).resolve()}")


@cli.command("validate-data")
@click.option(
    "--source", default="data/synthetic", type=str, help="Source directory containing dataset."
)
@click.option(
    "--format",
    "file_format",
    default="csv",
    type=click.Choice(["csv", "json"], case_sensitive=False),
    help="Dataset format to validate.",
)
def validate_data(source: str, file_format: str) -> None:
    """Validates schema, ranges, enums, duplicates, and integrity of dataset."""
    click.echo(f"[*] Validating dataset at: {source} (format: {file_format})...")
    src_path = Path(source)
    if not src_path.exists():
        click.secho(f"[!] Error: Source directory does not exist: {source}", fg="red")
        sys.exit(1)

    try:
        raw_data = DatasetParser.read_dataset(source, file_format=file_format)
    except Exception as exc:
        click.secho(f"[!] Parsing failed: {exc}", fg="red")
        sys.exit(1)

    from app.ingestion.models import EntityIngestionSummary

    validator = DataValidator()
    all_summaries = {}

    entity_validators = [
        ("company", validator.validate_company),
        ("customers", validator.validate_customers),
        ("deployments", validator.validate_deployments),
        ("metrics", validator.validate_metrics),
        ("events", validator.validate_events),
        ("orders", validator.validate_orders),
        ("order_items", validator.validate_order_items),
        ("support_tickets", validator.validate_support_tickets),
        ("complaints", validator.validate_complaints),
    ]

    total_valid = 0
    total_errors = 0
    total_duplicates = 0

    for entity_name, val_fn in entity_validators:
        records = raw_data.get(entity_name, [])
        summary = EntityIngestionSummary(entity_name=entity_name)
        val_fn(records, summary)
        all_summaries[entity_name] = summary

        total_valid += summary.received - summary.rejected
        total_errors += len(summary.validation_errors)
        total_duplicates += summary.duplicates

        status_color = "green" if summary.rejected == 0 else "yellow"
        click.secho(
            f"    - {entity_name:16}: {summary.received:6d} received, "
            f"{summary.received - summary.rejected:6d} valid, "
            f"{summary.rejected:4d} rejected ({len(summary.validation_errors)} errors, {summary.duplicates} duplicates)",
            fg=status_color,
        )

    click.echo("[*] Dataset Validation Summary:")
    click.echo(f"    - Total Records Validated: {total_valid:,}")
    click.echo(f"    - Total Validation Errors: {total_errors:,}")
    click.echo(f"    - Total Duplicates Detected: {total_duplicates:,}")

    if total_errors > 0:
        click.secho(
            f"[!] Note: Controlled data quality flaws detected ({total_errors} errors). Ingestion pipeline will safely trap these.",
            fg="yellow",
        )
    else:
        click.secho("[+] All records 100% clean and compliant!", fg="green")


@cli.command("ingest-data")
@click.option(
    "--source", default="data/synthetic", type=str, help="Source directory containing dataset."
)
@click.option(
    "--format",
    "file_format",
    default="csv",
    type=click.Choice(["csv", "json"], case_sensitive=False),
    help="File format to ingest.",
)
@click.option("--batch-size", default=1000, type=int, help="Database batch insert size.")
@click.option("--db-url", default=None, type=str, help="Target database connection URL.")
def ingest_data(source: str, file_format: str, batch_size: int, db_url: str | None) -> None:
    """Ingests dataset into PostgreSQL database with batching and idempotency."""
    click.echo(
        f"[*] Ingesting dataset from {source} (format: {file_format}, batch_size: {batch_size})..."
    )
    if db_url:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from app.database.base import Base

        engine = create_engine(db_url)
        if db_url.startswith("sqlite"):
            Base.metadata.create_all(bind=engine)
        session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    else:
        session_factory = get_session_factory()

    with session_factory() as session:
        pipeline = IngestionPipeline(session, batch_size=batch_size)
        report = pipeline.run(source, file_format=file_format)

    click.echo("[+] Ingestion Completed:")
    click.echo(f"    - Duration: {report.duration_seconds:.2f} seconds")
    click.echo(f"    - Records Received: {report.total_records_received:,}")
    click.echo(f"    - Records Inserted: {report.total_records_inserted:,}")
    click.echo(f"    - Records Rejected: {report.total_records_rejected:,}")
    click.echo(
        f"    - Duplicates Detected (Idempotent skips): {report.total_duplicates_detected:,}"
    )

    for name, summary in report.entity_summaries.items():
        click.echo(
            f"      * {name:16}: {summary.inserted:6d} inserted, {summary.duplicates:4d} duplicates"
        )


@cli.command("reset-demo-data")
@click.option("--company-slug", default="novacart", help="Company slug to purge.")
@click.option(
    "--source", default="data/synthetic", type=str, help="Source directory for re-ingestion."
)
@click.option(
    "--format",
    "file_format",
    default="csv",
    type=click.Choice(["csv", "json"], case_sensitive=False),
    help="Format for re-ingestion.",
)
@click.option("--db-url", default=None, type=str, help="Target database connection URL.")
def reset_demo_data(company_slug: str, source: str, file_format: str, db_url: str | None) -> None:
    """Purges demo company data and performs a clean re-ingestion."""
    click.echo(f"[*] Resetting demo company '{company_slug}'...")
    if db_url:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from app.database.base import Base

        engine = create_engine(db_url)
        if db_url.startswith("sqlite"):
            Base.metadata.create_all(bind=engine)
        session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    else:
        session_factory = get_session_factory()

    with session_factory() as session:
        company = session.scalar(select(Company).where(Company.slug == company_slug))
        if company:
            click.echo(f"[*] Cascading delete for company {company.name} ({company.id})...")
            session.delete(company)
            session.commit()
            click.echo("[+] Prior demo data purged successfully.")
        else:
            click.echo(
                f"[*] Company '{company_slug}' not found in database. Proceeding to fresh ingest."
            )

    # Re-ingest
    click.echo(f"[*] Re-ingesting dataset from {source}...")
    with session_factory() as session:
        pipeline = IngestionPipeline(session, batch_size=1000)
        report = pipeline.run(source, file_format=file_format)

    click.echo(f"[+] Demo data reset complete: {report.total_records_inserted:,} records inserted.")


if __name__ == "__main__":
    cli()
