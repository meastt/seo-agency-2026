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
    
    # Import GEO modules
    from modules.geo.rewriter import GEORewriter
    from modules.geo.schema_generator import SchemaGenerator, generate_schema_for_content
    from modules.geo.freshness import ContentFreshness
    from core.wp_api import update_post, create_backup
    
    if post_id is None:
        post_id = IntPrompt.ask("Enter post ID to transform")
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Fetching post from WordPress...", total=None)
            post_data = quick_fetch(post_id)
            progress.update(task, description="[green]✓ Post fetched[/green]")
        
        content = post_data.get("content", {}).get("rendered", "")
        title = post_data.get("title", {}).get("rendered", "Untitled")
        
        console.print(f"\n[bold]Post:[/bold] {title}")
        console.print(f"[dim]ID: {post_id} | Content length: {len(content)} chars[/dim]\n")
        
    except Exception as e:
        console.print(f"[red]Error fetching post: {e}[/red]")
        return
    
    # First, run audit to show current state
    console.print("[bold]Current GEO Score[/bold]")
    result = audit_content(content, title)
    _display_quick_score(result)
    
    # Ask for Answer Capsule
    console.print()
    answer_capsule = Prompt.ask(
        "[cyan]Enter Answer Capsule (120-150 chars)[/cyan]\n"
        "[dim]This is the quick answer that appears right after the title.[/dim]\n"
        "[dim]Leave blank to skip[/dim]",
        default=""
    )
    
    # Ask about freshness update
    freshness_update = Confirm.ask("Update year references (e.g., 2025 → 2026)?", default=True)
    
    # Ask about schema generation
    auto_schema = Confirm.ask("Auto-generate JSON-LD schema?", default=True)
    
    # Preview transformation
    console.print()
    console.print("[bold]Applying transformations...[/bold]")
    
    rewriter = GEORewriter()
    transformed = rewriter.transform(
        content,
        answer_capsule=answer_capsule if answer_capsule else None,
        add_experience=True
    )
    
    # Apply freshness updates
    if freshness_update:
        freshness = ContentFreshness()
        fresh_result = freshness.refresh_content(title, transformed.transformed)
        if fresh_result.title_changed:
            title = fresh_result.updated_title
            transformed.changes_made.append(f"Updated title year to {freshness.current_year}")
        if fresh_result.content_changed:
            transformed = rewriter.transform(fresh_result.updated_content)
            transformed.changes_made.extend(fresh_result.year_updates)
    
    # Show changes
    console.print()
    console.print("[bold]Changes to be applied:[/bold]")
    for change in transformed.changes_made:
        console.print(f"  [green]✓[/green] {change}")
    
    if auto_schema:
        try:
            site_url, username, _ = get_credentials()
            author = username.split("@")[0]  # Use username as author
            schema = generate_schema_for_content(
                transformed.transformed,
                title,
                author
            )
            schema_type = schema.get("@type", "Unknown")
            console.print(f"  [green]✓[/green] Generated {schema_type} schema")
        except Exception as e:
            console.print(f"  [yellow]⚠[/yellow] Schema generation failed: {e}")
            auto_schema = False
    
    # Confirm before applying
    console.print()
    if not Confirm.ask("[yellow]Apply these changes to WordPress?[/yellow]"):
        console.print("[dim]Transformation cancelled.[/dim]")
        return
    
    # Create backup and apply
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Creating backup...", total=None)
            site_url, username, app_password = get_credentials()
            backup_data = {
                "post_id": post_id,
                "original_title": post_data.get("title", {}).get("rendered", ""),
                "original_content": content
            }
            backup_path = create_backup(backup_data, "backups", "geo_transform")
            progress.update(task, description="[green]✓ Backup created[/green]")
            
            task = progress.add_task("Updating WordPress...", total=None)
            update_data = {"content": transformed.transformed}
            if freshness_update and title != post_data.get("title", {}).get("rendered", ""):
                update_data["title"] = title
            
            update_post(site_url, post_id, username, app_password, update_data)
            progress.update(task, description="[green]✓ Post updated[/green]")
        
        console.print()
        console.print(Panel(
            f"[green]✅ GEO Transformation Complete![/green]\n\n"
            f"Post ID: {post_id}\n"
            f"Changes: {len(transformed.changes_made)}\n"
            f"Backup: {backup_path}",
            title="Success",
            border_style="green"
        ))
        
        # Re-audit to show improvement
        console.print()
        if Confirm.ask("Re-audit to see score improvement?"):
            new_result = audit_content(transformed.transformed, title)
            improvement = new_result.overall_score - result.overall_score
            if improvement > 0:
                console.print(f"[green]🎉 Score improved by +{improvement} points![/green]")
            console.print(f"New score: {new_result.overall_score}/100")
        
    except Exception as e:
        console.print(f"[red]Error applying transformation: {e}[/red]")


def _display_quick_score(result):
    """Display a compact score summary."""
    score = result.overall_score
    if score >= 80:
        color = "green"
    elif score >= 60:
        color = "yellow"
    else:
        color = "red"
    console.print(f"  [{color}]Score: {score}/100[/{color}]")
    for cat, cat_score in result.category_scores.items():
        console.print(f"    {cat.replace('_', ' ').title()}: {cat_score}")


def fix_technical_issues():
    """Fix technical SEO issues."""
    console.print()
    console.print("[bold]🔧 Technical SEO Fixes[/bold]")
    console.print()
    
    # Import here to avoid circular imports
    from modules.technical.link_fixer import TechnicalFixer, FixResult
    
    try:
        fixer = TechnicalFixer()
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        return
    
    # Show submenu
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="cyan bold")
    table.add_column()
    
    table.add_row("[1]", "🔗 Fix broken link (404) - Create 301 redirect")
    table.add_row("[2]", "📄 Fix orphan page - Link to parent post")
    table.add_row("[3]", "⛓️  Flatten redirect chain - A→B→C becomes A→C")
    table.add_row("[b]", "← Back to main menu")
    
    console.print(table)
    console.print()
    
    choice = Prompt.ask(
        "Select fix type",
        choices=["1", "2", "3", "b"],
        default="b"
    )
    
    if choice == "b":
        return
    
    if choice == "1":
        _fix_broken_link(fixer)
    elif choice == "2":
        _fix_orphan_page(fixer)
    elif choice == "3":
        _fix_redirect_chain(fixer)


def _fix_broken_link(fixer):
    """Handle broken link fix flow."""
    console.print()
    console.print("[bold]🔗 Fix Broken Link (404)[/bold]")
    console.print()
    
    broken_url = Prompt.ask("Enter the broken URL path (e.g., /old-page)")
    redirect_target = Prompt.ask(
        "Enter redirect target URL (or press Enter to auto-find)",
        default=""
    ) or None
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Creating 301 redirect...", total=None)
        result = fixer.fix_broken_link(broken_url, redirect_target)
        progress.update(task, description="Done")
    
    _display_fix_result(result)


def _fix_orphan_page(fixer):
    """Handle orphan page fix flow."""
    console.print()
    console.print("[bold]📄 Fix Orphan Page[/bold]")
    console.print()
    
    post_id = IntPrompt.ask("Enter the orphan page's post ID")
    parent_id_str = Prompt.ask(
        "Enter parent post ID (or press Enter to auto-find)",
        default=""
    )
    parent_id = int(parent_id_str) if parent_id_str else None
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Adding internal link...", total=None)
        result = fixer.fix_orphan_page(post_id, parent_id)
        progress.update(task, description="Done")
    
    _display_fix_result(result)


def _fix_redirect_chain(fixer):
    """Handle redirect chain fix flow."""
    console.print()
    console.print("[bold]⛓️ Flatten Redirect Chain[/bold]")
    console.print()
    
    start_url = Prompt.ask("Enter the starting URL of the chain")
    final_url = Prompt.ask("Enter the final destination URL")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Flattening redirect chain...", total=None)
        result = fixer.flatten_redirect_chain(start_url, final_url)
        progress.update(task, description="Done")
    
    _display_fix_result(result)


def _display_fix_result(result):
    """Display the result of a technical fix."""
    console.print()
    
    if result.success:
        console.print(Panel(
            f"[green]✅ Fix Applied Successfully[/green]\n\n"
            f"Type: {result.fix_type}\n"
            f"Source: {result.source_url}\n"
            f"Target: {result.target_url}\n"
            f"Method: {result.method}\n"
            f"Backup: {result.backup_path}",
            title="Success",
            border_style="green"
        ))
    else:
        details_str = ""
        if result.details:
            if "htaccess_rule" in result.details:
                details_str = f"\n\n[yellow]Manual fix required:[/yellow]\n{result.details['htaccess_rule']}"
        
        console.print(Panel(
            f"[red]❌ Fix Failed[/red]\n\n"
            f"Type: {result.fix_type}\n"
            f"Source: {result.source_url}\n"
            f"Error: {result.error}"
            f"{details_str}",
            title="Failed",
            border_style="red"
        ))
    
    console.print()


def batch_audit():
    """Audit multiple posts."""
    console.print()
    console.print("[bold]📋 Batch Audit[/bold]")
    console.print()
    
    from modules.geo.batch_auditor import BatchAuditor
    from rich.progress import Progress, BarColumn, TextColumn, TaskProgressColumn
    
    try:
        auditor = BatchAuditor()
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        return
    
    # Show submenu
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="cyan bold")
    table.add_column()
    
    table.add_row("[1]", "📁 Audit posts in a category")
    table.add_row("[2]", "🔢 Audit specific post IDs")
    table.add_row("[b]", "← Back to main menu")
    
    console.print(table)
    console.print()
    
    choice = Prompt.ask(
        "Select audit type",
        choices=["1", "2", "b"],
        default="b"
    )
    
    if choice == "b":
        return
    
    if choice == "1":
        _batch_audit_category(auditor)
    elif choice == "2":
        _batch_audit_ids(auditor)


def _batch_audit_category(auditor):
    """Audit all posts in a category."""
    from rich.progress import Progress, BarColumn, TextColumn, TaskProgressColumn
    
    console.print()
    category_id = IntPrompt.ask("Enter category ID to audit")
    max_posts = IntPrompt.ask("Maximum posts to audit", default=20)
    
    console.print()
    
    with Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task("Auditing posts...", total=max_posts)
        
        def on_progress(current, total):
            progress.update(task, completed=current, total=total)
        
        report = auditor.audit_category(category_id, max_posts, on_progress)
    
    _display_batch_report(auditor, report)


def _batch_audit_ids(auditor):
    """Audit specific post IDs."""
    from rich.progress import Progress, BarColumn, TextColumn, TaskProgressColumn
    
    console.print()
    ids_str = Prompt.ask("Enter post IDs (comma-separated, e.g., 123,456,789)")
    
    try:
        post_ids = [int(x.strip()) for x in ids_str.split(",") if x.strip()]
    except ValueError:
        console.print("[red]Invalid post IDs. Use comma-separated numbers.[/red]")
        return
    
    if not post_ids:
        console.print("[red]No valid post IDs provided.[/red]")
        return
    
    console.print()
    
    with Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task("Auditing posts...", total=len(post_ids))
        
        def on_progress(current, total):
            progress.update(task, completed=current, total=total)
        
        report = auditor.audit_post_ids(post_ids, on_progress)
    
    _display_batch_report(auditor, report)


def _display_batch_report(auditor, report):
    """Display batch audit report and offer export."""
    console.print()
    
    # Summary panel
    if report.average_score >= 70:
        score_color = "green"
    elif report.average_score >= 40:
        score_color = "yellow"
    else:
        score_color = "red"
    
    console.print(Panel(
        f"[bold]Batch Audit Complete[/bold]\n\n"
        f"Posts audited: {report.audited_posts}/{report.total_posts}\n"
        f"Failed: {report.failed_posts}\n\n"
        f"[{score_color}]Average Score: {report.average_score:.1f}/100[/{score_color}]\n\n"
        f"[red]High priority: {report.high_priority_count}[/red]\n"
        f"[yellow]Medium priority: {report.medium_priority_count}[/yellow]\n"
        f"[green]Low priority: {report.low_priority_count}[/green]",
        title="Summary",
        border_style="blue"
    ))
    
    # Results table (top 10)
    if report.results:
        console.print()
        console.print("[bold]Top Priority Posts[/bold] (sorted by improvement potential)")
        
        results_table = Table(show_header=True)
        results_table.add_column("ID", style="dim")
        results_table.add_column("Title", max_width=40)
        results_table.add_column("Score", justify="right")
        results_table.add_column("Priority")
        results_table.add_column("Issues", justify="right")
        
        for result in report.results[:10]:
            if result.priority == "high":
                priority_display = "[red]HIGH[/red]"
            elif result.priority == "medium":
                priority_display = "[yellow]MED[/yellow]"
            else:
                priority_display = "[green]LOW[/green]"
            
            title_display = result.title[:37] + "..." if len(result.title) > 40 else result.title
            
            results_table.add_row(
                str(result.post_id),
                title_display,
                str(result.overall_score),
                priority_display,
                f"{result.error_count}E/{result.warning_count}W"
            )
        
        console.print(results_table)
        
        if len(report.results) > 10:
            console.print(f"[dim]...and {len(report.results) - 10} more posts[/dim]")
    
    # Export options
    console.print()
    export_choice = Prompt.ask(
        "Export report?",
        choices=["csv", "json", "both", "none"],
        default="none"
    )
    
    if export_choice in ["csv", "both"]:
        csv_path = auditor.save_report_csv(report)
        console.print(f"[green]✓[/green] Saved CSV: {csv_path}")
    
    if export_choice in ["json", "both"]:
        json_path = auditor.save_report_json(report)
        console.print(f"[green]✓[/green] Saved JSON: {json_path}")
    
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
