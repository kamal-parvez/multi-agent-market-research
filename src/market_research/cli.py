"""CLI entry point for the summer sunglasses campaign pipeline."""
import typer
from rich.console import Console

from market_research.graph import run_campaign_pipeline

app = typer.Typer(add_completion=False, no_args_is_help=True)
console = Console()


@app.command()
def run(
    skip_image: bool = typer.Option(False, "--skip-image", help="Skip image generation (faster/cheaper dev iteration)."),
) -> None:
    """Run the full campaign pipeline: research, image, quote, report."""
    console.print("[bold blue]:mag: Running market research...[/bold blue]")
    result = run_campaign_pipeline(skip_image=skip_image)

    console.print("\n[bold green]Pipeline complete.[/bold green]")
    if result.get("image_path"):
        console.print(f"[bold]Image:[/bold] {result.get('image_path')}")
    console.print(f"[bold]Quote:[/bold] {result.get('quote', '')}")
    console.print(f"[bold]Report:[/bold] {result.get('report_path', '')}")


if __name__ == "__main__":
    app()
