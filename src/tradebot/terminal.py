"""Single-window, four-pane Textual application with nonblocking research and chat."""

import json

from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, VerticalScroll
from textual.widgets import DataTable, Footer, Header, Input, RichLog, Static

from tradebot.service import TradeService


class TradingTerminal(App):
    TITLE = "Agentic Trading"
    CSS = """
    Screen { background: #0b1220; }
    Header { background: #16243b; }
    #status { height: 1; padding: 0 1; background: #16243b; color: #9fcfff; }
    #panes { layout: grid; grid-size: 2 2; grid-columns: 1fr 1fr;
             grid-rows: 1fr 1fr; height: 1fr; grid-gutter: 0 1; }
    .pane { border: round #415a77; padding: 0 1; height: 100%; }
    .pane:focus-within { border: round #66c6ff; }
    #positions { height: 1fr; }
    #chat-log { height: 1fr; }
    #question { height: 3; }
    #detail-text, #performance-text { width: 1fr; height: auto; }
    Footer { background: #16243b; }
    """
    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+r", "research", "Research"),
        ("ctrl+u", "refresh_data", "Refresh"),
        ("f1", "focus_positions", "Positions"),
        ("f2", "focus_detail", "Focus"),
        ("f3", "focus_chat", "Chat"),
        ("f4", "focus_portfolio", "Portfolio"),
    ]

    def __init__(self, service: TradeService, automatic: bool = False):
        super().__init__()
        self.service, self.automatic = service, automatic
        self.selected: str | None = None
        self.last_status = "Starting"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("", id="status")
        with Container(id="panes"):
            with Vertical(classes="pane", id="positions-pane"):
                yield DataTable(id="positions", cursor_type="row", zebra_stripes=True)
            with VerticalScroll(classes="pane", id="detail-pane", can_focus=True):
                yield Static("Select a position", id="detail-text", markup=False)
            with Vertical(classes="pane", id="chat-pane"):
                yield RichLog(id="chat-log", wrap=True, markup=False, max_lines=500)
                yield Input(
                    placeholder="Ask about the selected holding or portfolio…", id="question"
                )
            with VerticalScroll(classes="pane", id="portfolio-pane", can_focus=True):
                yield Static("Loading portfolio", id="performance-text", markup=False)
        yield Footer()

    async def on_mount(self):
        titles = {
            "positions-pane": "1  OPEN POSITIONS",
            "detail-pane": "2  SELECTED POSITION",
            "chat-pane": "3  RESEARCH CHAT",
            "portfolio-pane": "4  PORTFOLIO / PERFORMANCE",
        }
        for widget_id, title in titles.items():
            self.query_one("#" + widget_id).border_title = title
        table = self.query_one("#positions", DataTable)
        table.add_columns("Symbol", "Qty", "Value $", "P/L $")
        for entry in self.service.store.chat_history():
            self.log_message(f"{entry['role']}: {entry['content']}")
        self.set_status(
            "DEMO / synthetic" if self.service.demo else "RESEARCH ONLY / orders disabled"
        )
        self.refresh_data()
        self.set_interval(30, self.refresh_data)
        if self.automatic:
            self.set_interval(self.service.policy.session_hours * 3600, self.research_session)
        table.focus()

    async def on_unmount(self):
        await self.service.close()

    def set_status(self, text: str):
        self.last_status = text
        mode = "DEMO" if self.service.demo else "RESEARCH ONLY"
        self.query_one("#status", Static).update(f"{mode} · ORDERS OFF · {text}")

    def log_message(self, text: str):
        self.query_one("#chat-log", RichLog).write(Text(text))

    @work(group="refresh", exclusive=True, exit_on_error=False)
    async def refresh_data(self):
        try:
            await self.service.refresh()
            self.render_portfolio()
        except (ValueError, RuntimeError) as exc:
            self.set_status(str(exc))
            self.render_portfolio()

    def render_portfolio(self):
        snapshot = self.service.store.snapshot()
        table = self.query_one("#positions", DataTable)
        previous = self.selected
        table.clear()
        if snapshot:
            for position in snapshot.positions:
                table.add_row(
                    position.symbol,
                    str(position.quantity),
                    f"{position.value:,.2f}",
                    f"{position.unrealized:+,.2f}",
                    key=position.symbol,
                )
            symbols = [p.symbol for p in snapshot.positions]
            self.selected = previous if previous in symbols else (symbols[0] if symbols else None)
            if self.selected:
                table.move_cursor(row=symbols.index(self.selected))
        else:
            self.selected = None
        self.render_detail()
        performance = self.service.performance()
        if "equity" not in performance:
            text = performance["status"]
        else:
            text = (
                f"{performance['source']}\n\nEquity       ${performance['equity']:,.2f}\n"
                f"Cash         ${performance['cash']:,.2f}\n"
                f"Pending buys ${performance['reserved']:,.2f}\n"
                f"Exposure     ${performance['gross']:,.2f}\n"
                f"Unrealized   ${performance['unrealized']:+,.2f}\n"
                f"Equity change since first snapshot: {performance['change_percent']:+.2f}%\n"
                f"Model spend this month: ${performance['model_spend']:.4f}\n"
                f"Snapshot: {performance['as_of'].isoformat()}\n"
                f"Reconciled: {performance['reconciled']}\n\n{performance['caveat']}\n"
                "Orders disabled; allocations are research previews."
            )
        self.query_one("#performance-text", Static).update(text)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted):
        symbol = event.row_key.value
        if symbol:
            self.selected = str(symbol)
            self.render_detail()

    def render_detail(self):
        snapshot = self.service.store.snapshot()
        position = snapshot.position(self.selected) if snapshot and self.selected else None
        if not position:
            self.query_one("#detail-text", Static).update(
                "No open position. Ctrl+R researches configured stocks; results appear in chat."
            )
            return
        stages = self.service.store.latest(position.symbol)
        text = (
            f"{position.symbol} · {position.sector}\n"
            f"Quantity: {position.quantity}   Average: ${position.average_price}\n"
            f"Mark: ${position.price}   Unrealized: ${position.unrealized:+.2f}\n\n"
            f"Entry thesis\n{position.thesis}\n"
        )
        initial = stages.get("initial_forecast", {}).get("output", {})
        verdict = stages.get("effective_verdict", {})
        research = stages.get("research", {})
        if initial:
            text += f"\nInitial confidence: {initial.get('probability')} (uncalibrated)\n"
        if verdict:
            text += (
                f"Final confidence: {verdict['forecast']['probability']} (uncalibrated)\n"
                f"Research verdict: {verdict['decision']}\n{verdict['rationale']}\n"
            )
        if research:
            text += "\nSource coverage\n" + "\n".join(
                f"{x['category']}/{x['source']}: {x['coverage']}" for x in research["coverage"]
            )
            text += "\n\nRecent evidence\n" + "\n".join(
                f"{x['id']}: {x['title']}" for x in research["evidence"][:4]
            )
        for stage in ("holding_review_preview", "allocation_preview"):
            if stage in stages:
                record = stages[stage]
                text += (
                    f"\n{stage.replace('_', ' ')}\n{record['allocation']['action']} · "
                    f"${record['validation']['notional']} · "
                    f"accepted: {record['validation']['accepted']}\n"
                    + "\n".join(record["validation"]["reasons"])
                    + "\n"
                )
        if "error" in stages:
            text += "\nResearch error: " + stages["error"]["reason"]
        self.query_one("#detail-text", Static).update(text)

    def action_refresh_data(self):
        self.refresh_data()

    def action_research(self):
        if self.service.session_lock.locked():
            self.set_status("Session already running")
        else:
            self.research_session()

    @work(group="research", exclusive=False, exit_on_error=False)
    async def research_session(self):
        try:
            result = await self.service.run_session(self.set_status)
            self.log_message("Research completed: " + json.dumps(result))
        except (ValueError, RuntimeError, TimeoutError) as exc:
            self.set_status("Research deferred: " + str(exc))
            self.log_message("Research deferred: " + str(exc))
        finally:
            self.render_portfolio()

    async def on_input_submitted(self, event: Input.Submitted):
        if not event.value.strip() or self.service.chat_lock.locked():
            return
        question, selected = event.value.strip(), self.selected
        event.input.value = ""
        self.log_message("You: " + question)
        self.answer_question(question, selected)

    @work(group="chat", exclusive=False, exit_on_error=False)
    async def answer_question(self, question, selected):
        field = self.query_one("#question", Input)
        field.disabled = True
        try:
            response = await self.service.ask(question, selected)
            self.log_message("Assistant: " + response)
        except (ValueError, RuntimeError) as exc:
            self.log_message("Chat unavailable: " + str(exc))
        finally:
            field.disabled = False
            field.focus()

    def action_focus_positions(self):
        self.query_one("#positions").focus()

    def action_focus_detail(self):
        self.query_one("#detail-pane").focus()

    def action_focus_chat(self):
        self.query_one("#question").focus()

    def action_focus_portfolio(self):
        self.query_one("#portfolio-pane").focus()
