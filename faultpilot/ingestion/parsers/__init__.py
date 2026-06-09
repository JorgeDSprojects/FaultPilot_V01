"""Parsers for manufacturer-specific manuals."""

from faultpilot.ingestion.parsers.bosch import parse_bosch_pdf
from faultpilot.ingestion.parsers.fanuc import parse_fanuc_pdf

__all__ = ["parse_bosch_pdf", "parse_fanuc_pdf"]
