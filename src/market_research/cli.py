"""CLI entry point for the campaign pipeline."""
import typer
from rich.console import Console
from rich.prompt import Prompt

from market_research import catalog_builder
from market_research.graph import run_campaign_pipeline

app = typer.Typer(add_completion=False, no_args_is_help=False)
console = Console()


@app.command()
def run(
    product: str = typer.Option(
        None, "--product", "-p", help="Product category to research (e.g. Sunglasses, Shoes, T-Shirts)."
    ),
    skip_image: bool = typer.Option(False, "--skip-image", help="Skip image generation (faster/cheaper dev iteration)."),
) -> None:
    """Run the full campaign pipeline: research, image, quote, report."""
    if not product:
        top = catalog_builder.top_categories(30)
        if top:
            console.print(f"[bold]Popular categories:[/bold] {', '.join(name for name, _ in top)}")
            console.print("[dim](You can also enter any other product -- if it's not recognized, "
                          "web research still runs without a catalog match.)[/dim]")
        product = Prompt.ask("\n[bold]What product should we research?[/bold]") or "Sunglasses"

    with console.status(f"[bold blue]Preparing catalog for '{product}'...[/bold blue]"):
        found = catalog_builder.ensure_category_in_catalog(product)
    if not found:
        console.print(f"[yellow]No catalog match for '{product}' -- proceeding with web research only.[/yellow]")

    console.print(f"[bold blue]:mag: Running market research on '{product}'...[/bold blue]")
    result = run_campaign_pipeline(product_category=product, skip_image=skip_image)

    console.print("\n[bold green]Pipeline complete.[/bold green]")
    if result.get("image_path"):
        console.print(f"[bold]Image:[/bold] {result.get('image_path')}")
    console.print(f"[bold]Quote:[/bold] {result.get('quote', '')}")
    console.print(f"[bold]Report:[/bold] {result.get('report_path', '')}")


if __name__ == "__main__":
    app()
