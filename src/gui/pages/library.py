"""
Library page — browse all saved highlight clips, filter, and compile best-of videos.
"""

from __future__ import annotations

import threading
from datetime import date, timedelta
from typing import Optional

from nicegui import ui

from src.gui.state import state


def library_page() -> None:
    with ui.column().classes("w-full gap-6"):

        # ── Filter bar ────────────────────────────────────────────────
        with ui.card().classes("w-full bg-grey-10 rounded-2xl"):
            with ui.card_section():
                ui.label("Clip Library").classes("text-h6 text-cyan")

            with ui.card_section().classes("flex flex-wrap gap-4 items-end"):
                game_filter = ui.input("Filter by game", placeholder="Valorant") \
                    .classes("flex-1 min-w-40")
                game_filter.props("outlined dense dark clearable")

                days_filter = ui.select(
                    {7: "Last 7 days", 30: "Last 30 days",
                     90: "Last 90 days", 0: "All time"},
                    value=7,
                    label="Time window",
                ).classes("flex-1 min-w-40")
                days_filter.props("outlined dense dark")

                score_filter = ui.select(
                    {5: "Score ≥ 5", 6: "Score ≥ 6",
                     7: "Score ≥ 7", 8: "Score ≥ 8", 9: "Score ≥ 9"},
                    value=6,
                    label="Min score",
                ).classes("flex-1 min-w-32")
                score_filter.props("outlined dense dark")

                search_btn = ui.button("Search", icon="search") \
                    .props("color=cyan dense")

        # ── Clips table ───────────────────────────────────────────────
        table_card = ui.card().classes("w-full bg-grey-10 rounded-2xl")

        columns = [
            {"name": "score",   "label": "Score",    "field": "score",    "sortable": True},
            {"name": "game",    "label": "Game",     "field": "game",     "sortable": True},
            {"name": "energy",  "label": "Energy",   "field": "energy",   "sortable": False},
            {"name": "cat",     "label": "Category", "field": "category", "sortable": True},
            {"name": "time",    "label": "Timestamp","field": "time",     "sortable": False},
            {"name": "desc",    "label": "Description", "field": "desc",  "sortable": False},
            {"name": "date",    "label": "Date",     "field": "date",     "sortable": True},
        ]

        rows_ref = {"rows": []}

        with table_card:
            with ui.card_section():
                count_label = ui.label("").classes("text-grey-5 text-caption")

            table = ui.table(columns=columns, rows=[], row_key="desc") \
                .classes("w-full")
            table.props("dark flat separator=cell dense")
            table.add_slot("body-cell-score", """
                <q-td :props="props">
                  <q-badge :color="props.value >= 9 ? 'positive' : props.value >= 7 ? 'cyan' : 'grey'"
                           :label="props.value + '/10'" />
                </q-td>
            """)
            table.add_slot("body-cell-energy", """
                <q-td :props="props">
                  <q-chip dense :color="{'peak':'negative','intense':'orange','medium':'cyan','calm':'grey'}[props.value] || 'grey'"
                          :label="props.value" />
                </q-td>
            """)

        def do_search():
            from src.modules.clip_library import get_library
            library = get_library()
            game = game_filter.value.strip() or None
            days = days_filter.value or None
            min_score = score_filter.value or 6

            clips = library.query(game=game, days=days, min_score=min_score, limit=100)
            rows = []
            for c in clips:
                rows.append({
                    "score":    c.highlight_score,
                    "game":     c.game,
                    "energy":   c.energy,
                    "category": c.category,
                    "time":     f"{int(c.timestamp_seconds // 60)}:{int(c.timestamp_seconds % 60):02d}",
                    "desc":     c.description[:70],
                    "date":     c.created_at[:10],
                    "_session": c.session_id,
                    "_screen":  c.screen_file,
                })
            table.rows = rows
            rows_ref["rows"] = clips
            count_label.set_text(f"{len(clips)} clips found")

        search_btn.on_click(do_search)
        do_search()  # initial load

        # ── Best-of section ───────────────────────────────────────────
        with ui.card().classes("w-full bg-grey-10 rounded-2xl"):
            with ui.card_section():
                ui.label("Build a best-of compilation").classes("text-h6 text-cyan")

            with ui.card_section().classes("flex flex-wrap gap-4 items-end"):
                bestof_game = ui.input("Game (optional)", placeholder="Valorant") \
                    .classes("flex-1 min-w-40")
                bestof_game.props("outlined dense dark clearable")

                bestof_days = ui.select(
                    {7: "Last 7 days", 30: "Last 30 days", 0: "All time"},
                    value=7,
                    label="Time window",
                ).classes("flex-1 min-w-40")
                bestof_days.props("outlined dense dark")

                bestof_minscore = ui.number(
                    label="Min score", value=7, min=1, max=10,
                ).classes("flex-1 min-w-28")
                bestof_minscore.props("outlined dense dark")

                channel_input = ui.input("Channel name", placeholder="My Gaming Channel") \
                    .classes("flex-1 min-w-48")
                channel_input.props("outlined dense dark")

            with ui.card_section():
                bestof_status = ui.label("").classes("text-grey-5 text-sm")
                bestof_btn = ui.button("Generate Best-Of Video", icon="auto_awesome") \
                    .classes("w-full py-3 rounded-xl")
                bestof_btn.props("color=cyan size=lg")

        def on_bestof():
            from src.agents.orchestrator import Pipeline
            game = bestof_game.value.strip() or None
            days = bestof_days.value or None
            min_score = int(bestof_minscore.value or 7)
            channel = channel_input.value.strip() or "My Gaming Channel"

            bestof_btn.props("disable")
            bestof_status.set_text("Building compilation… this may take a few minutes.")

            def run():
                pipeline = Pipeline()
                url = pipeline.run_best_of(game=game, days=days,
                                           channel_name=channel, min_score=min_score)
                if url:
                    bestof_status.set_text(f"Uploaded: {url}")
                    ui.notify(f"Best-of uploaded! {url}", type="positive")
                else:
                    bestof_status.set_text("Done — video saved locally.")
                bestof_btn.props(remove="disable")

            threading.Thread(target=run, daemon=True).start()

        bestof_btn.on_click(on_bestof)
