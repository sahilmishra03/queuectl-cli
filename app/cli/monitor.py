import os
import time
from datetime import datetime
from typing import Optional

import psutil
import typer
from rich.align import Align
from rich.columns import Columns
from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Table
from rich.text import Text

from app.db.database import SessionLocal
from app.db.redis import redis_client
from app.models.job import JobState
from app.repositories.job import JobRepository
from app.services.queue import QueueService

app = typer.Typer(invoke_without_command=True)


@app.callback(invoke_without_command=True)
def monitor_callback(
    ctx: typer.Context,
    refresh_interval: float = typer.Option(1.0, "--refresh-interval", "-r", help="Refresh interval in seconds"),
    iterations: Optional[int] = typer.Option(None, "--iterations", "-i", help="Number of refresh iterations before exiting"),
    auto_scroll: bool = typer.Option(False, "--auto-scroll", "-a", help="Automatically scroll through the job list"),
    max_rows: Optional[int] = typer.Option(None, "--max-rows", "-m", help="Fixed number of visible job rows"),
    screen: Optional[bool] = typer.Option(None, "--screen/--no-screen", help="Use alternate full-screen buffer (default: true)"),
):
    """Real-time Terminal UI (TUI) monitor displaying live progress bars, queue sizes, and memory usage."""
    if ctx.invoked_subcommand is None:
        run_monitor(
            refresh_interval=refresh_interval,
            iterations=iterations,
            auto_scroll=auto_scroll,
            max_rows=max_rows,
            use_screen=screen,
        )


def get_system_metrics() -> dict:
    try:
        mem = psutil.virtual_memory()
        total_gb = round(mem.total / (1024**3), 2)
        used_gb = round(mem.used / (1024**3), 2)
        mem_percent = mem.percent
    except Exception:
        total_gb, used_gb, mem_percent = 0.0, 0.0, 0.0

    worker_count = 0
    worker_mem_mb = 0.0
    try:
        if os.path.exists(".worker_pids"):
            with open(".worker_pids", "r") as f:
                pids = [int(p) for p in f.read().splitlines() if p.strip().isdigit()]
            for pid in pids:
                try:
                    proc = psutil.Process(pid)
                    worker_count += 1
                    worker_mem_mb += proc.memory_info().rss / (1024**2)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        else:
            proc = psutil.Process()
            worker_mem_mb = proc.memory_info().rss / (1024**2)
    except Exception:
        pass

    return {
        "mem_total_gb": total_gb,
        "mem_used_gb": used_gb,
        "mem_percent": mem_percent,
        "worker_count": worker_count,
        "worker_mem_mb": round(worker_mem_mb, 2),
    }


def build_header() -> Panel:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    title_text = Text.from_markup("[bold cyan]QueueCTL Live Terminal Monitor[/bold cyan]")
    status_text = Text.from_markup(f"[bold green]LIVE[/bold green] | [dim]{now}[/dim]")
    
    table = Table.grid(expand=True)
    table.add_column(justify="left", ratio=1)
    table.add_column(justify="right", ratio=1)
    table.add_row(title_text, status_text)
    
    return Panel(table, style="bold blue")


def build_system_panel(metrics: dict, queue_size: int, redis_ok: bool) -> Panel:
    mem_bar = Progress(
        TextColumn("[bold white]System RAM: [/bold white]"),
        BarColumn(bar_width=25, style="black", complete_style="green", finished_style="green"),
        TextColumn("[bold cyan]{task.percentage:>3.1f}%[/bold cyan] ({task.fields[used]}GB / {task.fields[mem_total]}GB)"),
        expand=False,
    )
    mem_bar.add_task("ram", total=100, completed=metrics["mem_percent"], used=metrics["mem_used_gb"], mem_total=metrics["mem_total_gb"])

    redis_status = "[bold green]ACTIVE[/bold green]" if redis_ok else "[bold red]UNAVAILABLE[/bold red]"
    worker_str = f"[bold yellow]{metrics['worker_count']}[/bold yellow] running ([cyan]{metrics['worker_mem_mb']} MB[/cyan] RAM)" if metrics['worker_count'] > 0 else f"[dim]No active worker file ([cyan]{metrics['worker_mem_mb']} MB[/cyan] local RAM)[/dim]"

    info_table = Table.grid(padding=(0, 3))
    info_table.add_column()
    info_table.add_column()
    info_table.add_row(
        Text.from_markup(f"[bold white]Redis Status:[/bold white] {redis_status}"),
        Text.from_markup(f"[bold white]Redis Queue Size:[/bold white] [bold magenta]{queue_size}[/bold magenta] jobs")
    )
    info_table.add_row(
        Text.from_markup(f"[bold white]Workers:[/bold white] {worker_str}"),
        mem_bar
    )

    return Panel(
        info_table,
        title="[bold yellow]System & Memory Statistics[/bold yellow]",
        border_style="yellow",
        padding=(0, 1),
    )


def build_job_stats_panel(stats: dict) -> Panel:
    counts = stats["counts"]
    total = stats["total_jobs"]

    state_colors = {
        "pending": "cyan",
        "processing": "yellow",
        "completed": "green",
        "failed": "red",
        "dead": "magenta",
        "timed_out": "bright_yellow",
    }

    progress_table = Table.grid(padding=(0, 1))
    progress_table.add_column(width=14)
    progress_table.add_column(width=32)
    progress_table.add_column(justify="right")

    try:
        import sys
        "█".encode(sys.stdout.encoding or "utf-8")
        fill_char, empty_char = "█", "█"
        empty_style = "[bold black]"
    except (UnicodeEncodeError, LookupError, AttributeError):
        fill_char, empty_char = "#", "-"
        empty_style = "[dim]"

    for state_name, count in counts.items():
        color = state_colors.get(state_name, "white")
        pct = (count / max(total, 1)) * 100
        bar_len = int((pct / 100) * 30)
        bar_str = f"[{color}]" + fill_char * bar_len + "[/]" + empty_style + empty_char * (30 - bar_len) + "[/]"
        desc_str = f"[bold {color}]{state_name.upper()}[/]"
        text_str = f"[bold white]{count:>4}[/bold white] / [dim]{total}[/dim] ([bold {color}]{pct:>5.1f}%[/])"
        progress_table.add_row(Text.from_markup(desc_str), Text.from_markup(bar_str), Text.from_markup(text_str))

    avg_dur = f"{stats['avg_duration_ms']}ms" if stats['avg_duration_ms'] else "N/A"
    success_rate = stats['success_rate']
    rate_color = "green" if success_rate >= 90 else ("yellow" if success_rate >= 70 else "red")

    metrics_table = Table.grid(padding=(0, 2))
    metrics_table.add_column(style="bold white")
    metrics_table.add_column(justify="right")
    metrics_table.add_row("Total Jobs:", f"[bold cyan]{total}[/bold cyan]")
    metrics_table.add_row("Avg Duration:", f"[bold white]{avg_dur}[/bold white]")
    metrics_table.add_row("Success Rate:", f"[bold {rate_color}]{success_rate}%[/bold {rate_color}]")
    metrics_table.add_row("Timed Out:", f"[bold red]{stats['timed_out']}[/bold red]")

    grid = Table.grid(expand=True, padding=(0, 2))
    grid.add_column(ratio=3)
    grid.add_column(ratio=2)
    grid.add_row(progress_table, Align.center(metrics_table, vertical="middle"))

    return Panel(
        grid,
        title="[bold cyan]Job States & Execution Progress[/bold cyan]",
        border_style="cyan",
        padding=(1, 1),
    )


def build_jobs_table_panel(
    jobs: list,
    offset: int = 0,
    max_visible_rows: int = 12,
    auto_scroll: bool = False,
) -> Panel:
    table = Table(
        show_header=True,
        header_style="bold white on dark_blue",
        expand=True,
        box=None,
    )
    table.add_column("ID", style="dim", width=12)
    table.add_column("Command", style="bold white")
    table.add_column("State", justify="center", width=12)
    table.add_column("Pri", justify="right", width=5)
    table.add_column("Att", justify="right", width=5)
    table.add_column("Duration", justify="right", width=10)
    table.add_column("Error", style="red", overflow="ellipsis")

    state_markup = {
        JobState.PENDING: "[bold cyan]PENDING[/bold cyan]",
        JobState.PROCESSING: "[bold yellow]PROCESSING[/bold yellow]",
        JobState.COMPLETED: "[bold green]COMPLETED[/bold green]",
        JobState.FAILED: "[bold red]FAILED[/bold red]",
        JobState.DEAD: "[bold magenta]DEAD (DLQ)[/bold magenta]",
        JobState.TIMED_OUT: "[bold bright_yellow]TIMED_OUT[/bold bright_yellow]",
    }

    def job_sort_key(j):
        priority_state = {
            JobState.PROCESSING: 0,
            JobState.PENDING: 1,
            JobState.DEAD: 2,
            JobState.FAILED: 2,
            JobState.TIMED_OUT: 2,
            JobState.COMPLETED: 3,
        }
        ts = (j.updated_at or j.created_at).timestamp() if (j.updated_at or j.created_at) else 0
        return (priority_state.get(j.state, 10), -j.priority, -ts)

    sorted_jobs = sorted(jobs, key=job_sort_key)
    total_jobs = len(sorted_jobs)

    if total_jobs > max_visible_rows:
        offset = min(offset, max(0, total_jobs - max_visible_rows))
        visible_jobs = sorted_jobs[offset : offset + max_visible_rows]
        scroll_indicator = " [AUTO-SCROLL ON]" if auto_scroll else ""
        title = (
            f"[bold green]Recent & Active Jobs ({offset + 1}-{min(offset + max_visible_rows, total_jobs)} of {total_jobs})"
            f"{scroll_indicator}[/bold green] [yellow]| Up/Down (j/k) to scroll | 'a' toggle auto-scroll[/yellow]"
        )
    else:
        visible_jobs = sorted_jobs
        title = f"[bold green]Recent & Active Jobs ({total_jobs} total)[/bold green]"

    if not visible_jobs:
        table.add_row("-", "No jobs in database", "-", "-", "-", "-", "-")
    else:
        for job in visible_jobs:
            short_id = job.id.split("-")[0] + "..." if "-" in job.id else job.id[:8]
            state_str = state_markup.get(job.state, str(job.state.value))
            duration_str = f"{job.duration_ms}ms" if job.duration_ms is not None else "-"
            err_str = (job.last_error or "").strip().split("\n")[0][:30]
            table.add_row(
                short_id,
                job.command[:35],
                state_str,
                str(job.priority),
                str(job.attempts),
                duration_str,
                err_str,
            )

    return Panel(
        table,
        title=title,
        border_style="green",
        padding=(0, 1),
    )


def build_dashboard_layout(
    repository: JobRepository,
    queue_service: QueueService,
    console: Optional[Console] = None,
    offset: int = 0,
    max_visible_rows: int = 12,
    auto_scroll: bool = False,
) -> Group:
    stats = repository.get_stats()
    jobs = repository.list_all()
    
    redis_ok = False
    try:
        redis_ok = redis_client.ping()
        queue_size = queue_service.size()
    except Exception:
        queue_size = 0

    metrics = get_system_metrics()

    header = build_header()
    system_panel = build_system_panel(metrics, queue_size, redis_ok)
    stats_panel = build_job_stats_panel(stats)
    table_panel = build_jobs_table_panel(
        jobs,
        offset=offset,
        max_visible_rows=max_visible_rows,
        auto_scroll=auto_scroll,
    )
    footer = Align.center(
        Text.from_markup("[dim white]Press [bold red]Ctrl+C[/bold red] exit | [bold yellow]Up/Down[/bold yellow] (or [yellow]j/k[/yellow]) scroll | [bold yellow]'a'[/bold yellow] auto-scroll[/dim white]")
    )

    return Group(
        header,
        system_panel,
        stats_panel,
        table_panel,
        footer,
    )


def run_monitor(
    refresh_interval: float = 1.0,
    iterations: Optional[int] = None,
    auto_scroll: bool = False,
    max_rows: Optional[int] = None,
    use_screen: Optional[bool] = None,
):
    import os
    import sys
    db = SessionLocal()
    repository = JobRepository(db)
    queue_service = QueueService()
    console = Console()
    if use_screen is None:
        use_screen = True if iterations is None and console.is_terminal else False

    offset = 0

    def get_max_rows():
        if max_rows is not None:
            return max_rows
        height = getattr(console.size, "height", 30)
        return max(5, height - 18)

    def check_keys():
        nonlocal offset, auto_scroll
        changed = False
        if os.name == "nt":
            import msvcrt
            while msvcrt.kbhit():
                ch = msvcrt.getch()
                if ch in (b'\x00', b'\xe0'):
                    ch2 = msvcrt.getch()
                    if ch2 == b'H':  # Up arrow
                        offset = max(0, offset - 1)
                        auto_scroll = False
                        changed = True
                    elif ch2 == b'P':  # Down arrow
                        offset += 1
                        auto_scroll = False
                        changed = True
                    elif ch2 == b'I':  # Page Up
                        offset = max(0, offset - 10)
                        auto_scroll = False
                        changed = True
                    elif ch2 == b'Q':  # Page Down
                        offset += 10
                        auto_scroll = False
                        changed = True
                elif ch in (b'k', b'K'):
                    offset = max(0, offset - 1)
                    auto_scroll = False
                    changed = True
                elif ch in (b'j', b'J'):
                    offset += 1
                    auto_scroll = False
                    changed = True
                elif ch in (b'a', b'A'):
                    auto_scroll = not auto_scroll
                    changed = True
                elif ch in (b'q', b'Q', b'\x03'):
                    raise KeyboardInterrupt
        else:
            import select
            while select.select([sys.stdin], [], [], 0)[0]:
                ch = sys.stdin.read(1)
                if ch == '\033':
                    if select.select([sys.stdin], [], [], 0)[0]:
                        ch2 = sys.stdin.read(1)
                        if ch2 == '[' and select.select([sys.stdin], [], [], 0)[0]:
                            ch3 = sys.stdin.read(1)
                            if ch3 == 'A':
                                offset = max(0, offset - 1)
                                auto_scroll = False
                                changed = True
                            elif ch3 == 'B':
                                offset += 1
                                auto_scroll = False
                                changed = True
                            elif ch3 == '5':
                                sys.stdin.read(1)
                                offset = max(0, offset - 10)
                                auto_scroll = False
                                changed = True
                            elif ch3 == '6':
                                sys.stdin.read(1)
                                offset += 10
                                auto_scroll = False
                                changed = True
                elif ch in ('k', 'K'):
                    offset = max(0, offset - 1)
                    auto_scroll = False
                    changed = True
                elif ch in ('j', 'J'):
                    offset += 1
                    auto_scroll = False
                    changed = True
                elif ch in ('a', 'A'):
                    auto_scroll = not auto_scroll
                    changed = True
                elif ch in ('q', 'Q', '\x03'):
                    raise KeyboardInterrupt
        return changed

    try:
        with Live(
            build_dashboard_layout(repository, queue_service, console=console, offset=offset, max_visible_rows=get_max_rows(), auto_scroll=auto_scroll),
            console=console,
            refresh_per_second=max(1, int(1 / max(refresh_interval, 0.1))),
            screen=use_screen,
        ) as live:
            count = 0
            while True:
                db.expire_all()
                total_jobs = len(repository.list_all())
                current_max_rows = get_max_rows()
                if auto_scroll and total_jobs > current_max_rows:
                    offset = (offset + 1) % max(1, total_jobs - current_max_rows + 1)

                live.update(
                    build_dashboard_layout(
                        repository,
                        queue_service,
                        console=console,
                        offset=offset,
                        max_visible_rows=current_max_rows,
                        auto_scroll=auto_scroll,
                    )
                )
                count += 1
                if iterations is not None and count >= iterations:
                    break

                elapsed = 0.0
                step = 0.05
                while elapsed < refresh_interval:
                    if check_keys():
                        db.expire_all()
                        live.update(
                            build_dashboard_layout(
                                repository,
                                queue_service,
                                console=console,
                                offset=offset,
                                max_visible_rows=get_max_rows(),
                                auto_scroll=auto_scroll,
                            )
                        )
                    time.sleep(step)
                    elapsed += step
    except KeyboardInterrupt:
        pass
    finally:
        db.close()


@app.command()
def start(
    refresh_interval: float = typer.Option(1.0, "--refresh-interval", "-r", help="Refresh interval in seconds"),
    iterations: Optional[int] = typer.Option(None, "--iterations", "-i", help="Number of refresh iterations before exiting"),
    auto_scroll: bool = typer.Option(False, "--auto-scroll", "-a", help="Automatically scroll through the job list"),
    max_rows: Optional[int] = typer.Option(None, "--max-rows", "-m", help="Fixed number of visible job rows"),
    screen: Optional[bool] = typer.Option(None, "--screen/--no-screen", help="Use alternate full-screen buffer (default: true)"),
):
    """Start the live terminal UI monitor."""
    run_monitor(
        refresh_interval=refresh_interval,
        iterations=iterations,
        auto_scroll=auto_scroll,
        max_rows=max_rows,
        use_screen=screen,
    )


if __name__ == "__main__":
    app()
