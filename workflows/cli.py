#!/usr/bin/env python3
"""SEO Agency 2026 - Rich CLI Interface.

Interactive command-line interface for non-technical users.
Run with: python -m workflows.cli
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.markdown import Markdown
from rich import print as rprint

from core.wp_api import get_credentials, fetch_post, quick_fetch
from modules.geo.auditor import GEOAuditor, audit_content


console = Console()


def show_header():
    """Display the application header."""
    console.print()
    console.print(Panel.fit(
        "[bold blue]🎯 SEO Agency 2026[/bold blue]\n"
        "[dim]Automated GEO/Technical SEO for WordPress[/dim]",
        border_style="blue"
    ))
    console.print()


def check_credentials() -> bool:
    """Check if WordPress credentials are configured."""
    try:
        site_url, username, _ = get_credentials()
        console.print(f"[green]✓[/green] Connected to: [cyan]{site_url}[/cyan]")
        console.print(f"[green]✓[/green] User: [cyan]{username}[/cyan]")
        return True
    except ValueError as e:
        console.print(f"[red]✗[/red] {e}")
        console.print()
        console.print("[yellow]To configure credentials:[/yellow]")
        console.print("  1. Copy [cyan].env.example[/cyan] to [cyan].env[/cyan]")
        console.print("  2. Edit [cyan].env[/cyan] with your WordPress credentials")
        console.print("  3. Run this command again")
        return False


def show_main_menu() -> str:
    """Display the main menu and get user choice."""
    console.print()
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="cyan bold")
    table.add_column()
    
    table.add_row("[1]", "📊 Audit a post - Check GEO score and issues")
    table.add_row("[2]", "🔄 Transform a post - Apply GEO optimization")
    table.add_row("[3]", "🔧 Fix technical issues - 404s, orphans, redirects")
    table.add_row("[4]", "📋 Batch audit - Audit multiple posts")
    table.add_row("[5]", "⚙️  Configure - View/update settings")
    table.add_row("[q]", "🚪 Quit")
    
    console.print(table)
    console.print()
    
    choice = Prompt.ask(
        "Select an option",
        choices=["1", "2", "3", "4", "5", "q"],
        default="1"
    )
    return choice


def audit_single_post():
    """Audit a single post for GEO compliance."""
    console.print()
    console.print("[bold]📊 Single Post Audit[/bold]")
    console.print()
    
    post_id = IntPrompt.ask("Enter post ID to audit")
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            # Fetch post
            task = progress.add_task("Fetching post from WordPress...", total=None)
            post_data = quick_fetch(post_id)
            progress.update(task, description="[green]✓ Post fetched[/green]")
            
            # Get content
            content = post_data.get("content", {}).get("rendered", "")
            title = post_data.get("title", {}).get("rendered", "Untitled")
            
            # Run audit
            progress.update(task, description="Running GEO audit...")
            result = audit_content(content, title)
            progress.update(task, description="[green]✓ Audit complete[/green]")
        
        # Display results
        display_audit_results(post_id, title, result)
        
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")


def display_audit_results(post_id: int, title: str, result):
    """Display audit results in a formatted table."""
    console.print()
    
    # Overall score with color coding
    score = result.overall_score
    if score >= 80:
        score_color = "green"
        score_emoji = "🌟"
    elif score >= 60:
        score_color = "yellow"
        score_emoji = "⚡"
    elif score >= 40:
        score_color = "orange1"
        score_emoji = "⚠️"
    else:
        score_color = "red"
        score_emoji = "🔴"
    
    console.print(Panel(
        f"[bold]{title}[/bold]\n"
        f"Post ID: {post_id}\n\n"
        f"[{score_color}]{score_emoji} Overall GEO Score: {score}/100[/{score_color}]",
        title="Audit Results",
        border_style=score_color
    ))
    
    # Category scores table
    console.print()
    console.print("[bold]Category Scores[/bold]")
    
    score_table = Table(show_header=True)
    score_table.add_column("Category", style="cyan")
    score_table.add_column("Score", justify="right")
    score_table.add_column("Status")
    
    for category, cat_score in result.category_scores.items():
        if cat_score >= 70:
            status = "[green]✓ Good[/green]"
        elif cat_score >= 40:
            status = "[yellow]⚠ Needs work[/yellow]"
        else:
            status = "[red]✗ Critical[/red]"
        
        score_table.add_row(
            category.replace("_", " ").title(),
            f"{cat_score}",
            status
        )
    
    console.print(score_table)
    
    # Issues
    if result.issues:
        console.print()
        console.print("[bold]Issues Found[/bold]")
        
        issues_table = Table(show_header=True)
        issues_table.add_column("Severity", width=8)
        issues_table.add_column("Issue")
        issues_table.add_column("Suggestion", style="dim")
        
        for issue in result.issues:
            if issue.severity == "error":
                sev_display = "[red]ERROR[/red]"
            elif issue.severity == "warning":
                sev_display = "[yellow]WARN[/yellow]"
            else:
                sev_display = "[blue]INFO[/blue]"
            
            issues_table.add_row(
                sev_display,
                issue.message,
                issue.suggestion[:50] + "..." if len(issue.suggestion) > 50 else issue.suggestion
            )
        
        console.print(issues_table)
    
    # Passed checks
    if result.passed_checks:
        console.print()
        console.print("[bold green]Passed Checks[/bold green]")
        for check in result.passed_checks:
            console.print(f"  [green]✓[/green] {check}")
    
    console.print()
    
    # Offer next action
    if score < 80:
        if Confirm.ask("Would you like to transform this post to improve its score?"):
            transform_post_flow(post_id)


def transform_post_flow(post_id: int = None):
    """Transform a post with GEO optimization."""
    console.print()
    console.print("[bold]🔄 GEO Transformation[/bold]")
    console.print()
    
    if post_id is None:
        post_id = IntPrompt.ask("Enter post ID to transform")
    
    console.print("[yellow]⚠ GEO transformation module coming soon![/yellow]")
    console.print("This will:")
    console.print("  • Add an Answer Capsule (120-150 chars)")
    console.print("  • Restructure for Inverted Pyramid")
    console.print("  • Inject first-person experience signals")
    console.print("  • Generate JSON-LD schema")
    console.print()


def fix_technical_issues():
    """Fix technical SEO issues."""
    console.print()
    console.print("[bold]🔧 Technical SEO Fixes[/bold]")
    console.print()
    console.print("[yellow]⚠ Technical fix module coming soon![/yellow]")
    console.print("This will:")
    console.print("  • Fix broken links (404s) with 301 redirects")
    console.print("  • Link orphan pages to relevant parents")
    console.print("  • Flatten redirect chains")
    console.print("  • Submit fixed URLs to IndexNow")
    console.print()


def batch_audit():
    """Audit multiple posts."""
    console.print()
    console.print("[bold]📋 Batch Audit[/bold]")
    console.print()
    console.print("[yellow]⚠ Batch audit module coming soon![/yellow]")
    console.print("This will:")
    console.print("  • Audit all posts in a category")
    console.print("  • Generate CSV/JSON report")
    console.print("  • Prioritize posts by improvement potential")
    console.print()


def show_configure():
    """Show configuration options."""
    console.print()
    console.print("[bold]⚙️ Configuration[/bold]")
    console.print()
    
    try:
        site_url, username, _ = get_credentials()
        console.print(f"  Site URL: [cyan]{site_url}[/cyan]")
        console.print(f"  Username: [cyan]{username}[/cyan]")
        console.print(f"  Password: [dim]••••••••[/dim]")
    except ValueError:
        console.print("  [red]Not configured[/red]")
    
    console.print()
    console.print("[dim]Edit .env file to change credentials[/dim]")
    console.print()


def main():
    """Main entry point for the CLI."""
    show_header()
    
    # Check credentials
    if not check_credentials():
        console.print()
        return 1
    
    # Main loop
    while True:
        choice = show_main_menu()
        
        if choice == "1":
            audit_single_post()
        elif choice == "2":
            transform_post_flow()
        elif choice == "3":
            fix_technical_issues()
        elif choice == "4":
            batch_audit()
        elif choice == "5":
            show_configure()
        elif choice == "q":
            console.print()
            console.print("[dim]Goodbye! 👋[/dim]")
            break
        
        # Pause before showing menu again
        if choice != "q":
            console.print()
            Prompt.ask("[dim]Press Enter to continue[/dim]", default="")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
