"""CLI entry point and global options for intervals-icu-tools."""

import click

from ..config import load_config


@click.group()
@click.option(
    "--output-dir",
    "-o",
    default=".",
    show_default=True,
    help="Directory to save output files, or a full file path to set the filename too.",
)
@click.option(
    "--format",
    "-f",
    "fmt",
    type=click.Choice(["json", "csv"]),
    default="json",
    show_default=True,
    help="Output format for saved files.",
)
@click.pass_context
def cli(ctx: click.Context, output_dir: str, fmt: str) -> None:
    """intervals-icu-tools — CLI for the Intervals.ICU fitness tracking API."""
    ctx.ensure_object(dict)
    ctx.obj["output_dir"] = output_dir
    ctx.obj["format"] = fmt
    ctx.obj["config"] = load_config()
