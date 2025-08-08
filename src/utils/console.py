from __future__ import annotations

from typing import List, Dict, Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.box import ROUNDED
from rich.markdown import Markdown


class ConsoleUI:
    """Lightweight console UI utilities for clean, organized output."""

    def __init__(self) -> None:
        self.console = Console()

    # Basic structure
    def header(self, title: str, subtitle: str | None = None) -> None:
        self.console.rule(f"[bold cyan]{title}")
        if subtitle:
            self.console.print(subtitle, style="dim")

    def rule(self, text: str | None = None) -> None:
        self.console.rule(text or "")

    # Message helpers
    def info(self, msg: str) -> None:
        self.console.print(msg)

    def success(self, msg: str) -> None:
        self.console.print(f"[green]{msg}[/green]")

    def warn(self, msg: str) -> None:
        self.console.print(f"[yellow]{msg}[/yellow]")

    def error(self, msg: str) -> None:
        self.console.print(f"[red]{msg}[/red]")

    def ai_response(self, text: str, title: str = "AI Bistro") -> None:
        # Render markdown when useful
        if any(tok in text for tok in ("**", "# ", "- ", "\n-", "\n•", "`")):
            content = Markdown(text)
        else:
            content = text
        self.console.print(Panel.fit(content, title=title, border_style="cyan", box=ROUNDED))

    # Tables
    def order_table(self, items: List[Dict[str, Any]], totals: Dict[str, float]) -> None:
        """Render a table for order items and totals."""
        table = Table(show_header=True, header_style="bold", box=ROUNDED)
        table.add_column("Item", justify="left")
        table.add_column("Qty", justify="right")
        table.add_column("Price", justify="right")
        table.add_column("Line Total", justify="right")

        for item in items:
            name = str(item.get("name", "Item"))
            qty = int(item.get("quantity", 1))
            price = float(item.get("price", 0))
            line_total = price * qty
            table.add_row(
                name,
                str(qty),
                f"${price:.2f}",
                f"${line_total:.2f}",
            )

        self.console.print(table)

        # Totals summary
        totals_table = Table(show_header=False, box=ROUNDED)
        totals_table.add_column("Label", justify="left")
        totals_table.add_column("Amount", justify="right")
        subtotal = float(totals.get("subtotal", 0))
        tax = float(totals.get("tax", 0))
        total = float(totals.get("total", subtotal + tax))
        totals_table.add_row("Subtotal", f"${subtotal:.2f}")
        totals_table.add_row("Tax", f"${tax:.2f}")
        totals_table.add_row("Total", f"[bold]${total:.2f}[/bold]")
        self.console.print(totals_table)

    def debug_table(self, data: Dict[str, Any], title: str = "Debug Info") -> None:
        table = Table(title=title, show_header=False, box=ROUNDED)
        table.add_column("Key", style="dim")
        table.add_column("Value")
        for k, v in data.items():
            table.add_row(str(k), str(v))
        self.console.print(table)
