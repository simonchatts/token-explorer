import asyncio
import html

from nicegui import ui
from nicegui.events import KeyEventArguments

from src.explorer import Explorer
from src.session import TokenSession


def run_gui(prompt, host, port, model_name, tokens_to_show):
    ui.add_head_html(
        """
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Fredoka:wght@400;600&family=Nunito:wght@400;600&display=swap" rel="stylesheet">
        <style>
            :root {
                --bg-1: #fff7d6;
                --bg-2: #e6f3ff;
                --bg-3: #e7ffe7;
                --panel: #ffffff;
                --ink: #172b4d;
                --accent: #ffb703;
                --accent-2: #00b4d8;
                --shadow: 0 12px 30px rgba(23, 43, 77, 0.12);
                --prob-bar: rgba(0, 180, 216, 0.25);
            }

            body {
                font-family: "Nunito", "Verdana", sans-serif;
                color: var(--ink);
                background: radial-gradient(circle at 10% 20%, var(--bg-1) 0%, transparent 45%),
                            radial-gradient(circle at 90% 10%, var(--bg-2) 0%, transparent 50%),
                            radial-gradient(circle at 50% 90%, var(--bg-3) 0%, transparent 55%),
                            #f7fbff;
            }

            .page {
                width: 100%;
                max-width: 1200px;
                margin: 0 auto;
                padding: 24px;
            }

            .banner {
                font-family: "Fredoka", "Trebuchet MS", sans-serif;
                font-size: 32px;
                letter-spacing: 0.5px;
                padding: 10px 18px;
                border-radius: 16px;
                background: linear-gradient(90deg, #fff3bf, #d0ebff);
                box-shadow: var(--shadow);
                margin-bottom: 18px;
            }

            .panel {
                background: var(--panel);
                border-radius: 16px;
                box-shadow: var(--shadow);
                padding: 16px;
            }

            .controls {
                width: 260px;
                flex-shrink: 0;
                gap: 12px;
            }

            .controls button {
                width: 100%;
            }

            .token-output {
                min-height: 140px;
                white-space: pre-wrap;
                font-size: 16px;
                line-height: 1.6;
            }

            .token-chip {
                border-radius: 6px;
                padding: 0 2px;
                box-decoration-break: clone;
                -webkit-box-decoration-break: clone;
            }

            .next-table {
                display: grid;
                grid-template-columns: 1fr 1.4fr;
                gap: 6px;
                margin-top: 8px;
            }

            .next-header {
                font-weight: 600;
                opacity: 0.8;
                padding: 6px 8px;
            }

            .next-row {
                display: contents;
            }

            .next-cell {
                padding: 8px;
                border-radius: 10px;
                background: #f8fafc;
                cursor: pointer;
                transition: transform 0.06s ease;
            }

            .next-cell:hover {
                transform: translateY(-1px);
                background: #eef6ff;
            }

            .prob-cell {
                position: relative;
                overflow: hidden;
            }

            .prob-bar {
                position: absolute;
                left: 0;
                top: 0;
                height: 100%;
                background: var(--prob-bar);
                border-radius: 10px;
            }

            .prob-text {
                position: relative;
                text-align: right;
                padding-right: 8px;
                font-variant-numeric: tabular-nums;
                display: block;
            }

            .legend-swatch {
                width: 24px;
                height: 18px;
                border-radius: 6px;
                display: inline-block;
                margin-right: 8px;
                border: 1px solid rgba(23, 43, 77, 0.1);
            }
        </style>
        """,
        shared=True,
    )

    @ui.page("/")
    def main_page():
        explorer = Explorer(model_name)
        session = TokenSession(explorer, prompt=prompt, tokens_to_show=tokens_to_show)

        base_prompt_text = prompt
        base_token_ids = list(session.get_prompt_tokens())
        base_token_count = len(base_token_ids)

        show_token_numbers = False
        show_probabilities = False
        continue_task = None
        continue_cancelled = False
        continue_active = False

        end_token_id = _resolve_end_token_id(explorer)

        def prob_to_color(probability):
            probability = max(0.0, min(1.0, probability))
            hue = 20 + (200 - 20) * probability
            return f"hsl({hue:.0f} 80% 85%)"

        def token_ids_to_text(token_ids):
            return " ".join(str(token_id) for token_id in token_ids)

        def sync_prompt_from_input():
            nonlocal base_prompt_text, base_token_ids, base_token_count
            if show_token_numbers:
                return
            current_text = input_area.value or ""
            if current_text == base_prompt_text:
                return
            base_prompt_text = current_text
            session.set_prompt_text(base_prompt_text)
            base_token_ids = list(session.get_prompt_tokens())
            base_token_count = len(base_token_ids)
            refresh_ui()

        def render_output():
            prompt_tokens = session.get_prompt_tokens()
            if not prompt_tokens:
                update_html(output_area, "")
                return

            if show_token_numbers:
                labels = [str(token_id) for token_id in prompt_tokens]
                if not show_probabilities:
                    update_html(output_area, html.escape(" ".join(labels)))
                    return
            else:
                labels = session.get_prompt_tokens_strings()
                if not show_probabilities:
                    update_html(output_area, html.escape(session.get_prompt()))
                    return

            probabilities = session.get_prompt_token_probabilities()
            pieces = []
            for idx, label in enumerate(labels):
                token_label = label
                if show_token_numbers and idx < len(labels) - 1:
                    token_label += " "
                safe_label = html.escape(token_label)
                bg = prob_to_color(probabilities[idx]) if show_probabilities else "transparent"
                pieces.append(f'<span class="token-chip" style="background:{bg}">{safe_label}</span>')
            update_html(output_area, "".join(pieces))

        def render_next_tokens():
            next_tokens_container.clear()
            displayed_tokens = session.displayed_tokens
            if not displayed_tokens:
                return
            with next_tokens_container:
                ui.label("Next").classes("next-header")
                ui.label("Probability").classes("next-header")
                for token in displayed_tokens:
                    token_label = str(token["token_id"]) if show_token_numbers else token["token"]
                    prob = max(0.0, min(1.0, token["probability"]))
                    percent = int(round(prob * 100))

                    row = ui.element("div").classes("next-row")
                    with row:
                        token_cell = ui.element("div").classes("next-cell")
                        token_cell.on("click", lambda _, token_id=token["token_id"]: append_token(token_id))
                        with token_cell:
                            ui.label(token_label).style("white-space: pre-wrap;")

                        prob_cell = ui.element("div").classes("next-cell prob-cell")
                        prob_cell.on("click", lambda _, token_id=token["token_id"]: append_token(token_id))
                        with prob_cell:
                            ui.element("div").classes("prob-bar").style(f"width: {prob * 100:.2f}%;")
                            ui.label(f"{percent}").classes("prob-text")

        def render_legend():
            legend_container.clear()
            if not show_probabilities:
                return
            with legend_container:
                ui.label("Probability legend").style("font-weight: 600; margin-bottom: 6px;")
                for percent in (0, 25, 50, 75, 100):
                    row = ui.row().style("align-items: center; gap: 6px;")
                    color = prob_to_color(percent / 100)
                    swatch = ui.element("span").classes("legend-swatch")
                    swatch.style(f"background: {color};")
                    ui.label(f"{percent}%")

        def refresh_ui():
            render_output()
            render_next_tokens()
            render_legend()
            update_edit_state()

        def set_show_token_numbers(value):
            nonlocal show_token_numbers
            show_token_numbers = value
            if show_token_numbers:
                input_area.disable()
                input_area.value = token_ids_to_text(base_token_ids)
            else:
                input_area.value = base_prompt_text
            refresh_ui()

        def set_show_probabilities(value):
            nonlocal show_probabilities
            show_probabilities = value
            refresh_ui()

        def append_token(token_id):
            sync_prompt_from_input()
            session.explorer.append_token(token_id)
            session.prompts[session.prompt_index] = session.explorer.get_prompt()
            session._refresh_tokens()
            refresh_ui()

        def append_weighted():
            sync_prompt_from_input()
            if session.append_weighted_token():
                refresh_ui()

        def delete_last():
            sync_prompt_from_input()
            if len(session.get_prompt_tokens()) > base_token_count:
                session.pop_token(min_tokens=base_token_count)
                refresh_ui()

        def delete_all():
            sync_prompt_from_input()
            session.set_prompt_text(base_prompt_text)
            refresh_ui()

        def is_end_token():
            if end_token_id is None:
                return False
            prompt_tokens = session.get_prompt_tokens()
            return bool(prompt_tokens and prompt_tokens[-1] == end_token_id)

        async def run_continue():
            nonlocal continue_cancelled, continue_task
            try:
                while not continue_cancelled and not is_end_token():
                    success = await asyncio.to_thread(session.append_weighted_token)
                    if not success:
                        break
                    refresh_ui()
                    await asyncio.sleep(0)
            finally:
                continue_cancelled = False
                continue_task = None
                set_continue_button(False)

        def toggle_continue():
            nonlocal continue_cancelled, continue_task
            sync_prompt_from_input()
            if continue_task is None:
                continue_cancelled = False
                set_continue_button(True)
                continue_task = asyncio.create_task(run_continue())
            else:
                continue_cancelled = True

        def handle_key(event: KeyEventArguments):
            nonlocal continue_cancelled, continue_task
            if event.key in ("Escape", "Esc") and continue_task is not None:
                continue_cancelled = True

        def on_input_blur():
            sync_prompt_from_input()

        def on_input_change(value):
            nonlocal base_prompt_text, base_token_ids, base_token_count
            if show_token_numbers:
                return
            current_text = value or ""
            if current_text == base_prompt_text:
                return
            base_prompt_text = current_text
            session.set_prompt_text(base_prompt_text)
            base_token_ids = list(session.get_prompt_tokens())
            base_token_count = len(base_token_ids)
            refresh_ui()

        def set_continue_button(active):
            nonlocal continue_active
            continue_active = active
            if active:
                continue_button.text = "Cancel"
                continue_button.classes(add="bg-red-600 text-white")
                continue_button.props(remove="outline")
                next_button.disable()
                delete_button.disable()
                delete_all_button.disable()
            else:
                continue_button.text = "Continue"
                continue_button.classes(remove="bg-red-600 text-white")
                continue_button.props(add="outline")
                delete_button.enable()
                delete_all_button.enable()
                # next_button and continue_button enabled state handled by update_edit_state
            continue_button.update()
            update_edit_state()

        def update_edit_state():
            completion_empty = len(session.get_prompt_tokens()) == base_token_count
            if completion_empty:
                edit_button.disable()
            else:
                edit_button.enable()

            can_edit = completion_empty and not show_token_numbers and not continue_active
            if can_edit:
                input_area.enable()
            else:
                input_area.disable()

            # Disable Next and Continue when at end token (unless continue is active/cancelling)
            at_end = is_end_token()
            if not continue_active:
                if at_end or not session.get_prompt_tokens():
                    next_button.disable()
                    continue_button.disable()
                else:
                    next_button.enable()
                    continue_button.enable()

        def handle_edit():
            nonlocal continue_cancelled, continue_task, base_token_ids, base_token_count
            if continue_task is not None:
                continue_cancelled = True
                continue_task.cancel()
                set_continue_button(False)
            session.set_prompt_text(base_prompt_text)
            base_token_ids = list(session.get_prompt_tokens())
            base_token_count = len(base_token_ids)
            if show_token_numbers:
                input_area.value = token_ids_to_text(base_token_ids)
            refresh_ui()
            focus_prompt()

        def focus_prompt():
            ui.run_javascript(
                "const ta = document.querySelector('textarea');"
                "if (!ta) return;"
                "requestAnimationFrame(() => {"
                "  ta.focus({ preventScroll: true });"
                "  const pos = ta.value.length;"
                "  ta.setSelectionRange(pos, pos);"
                "});"
            )

        with ui.column().classes("page"):
            ui.label("AI Explorer").classes("banner")

            with ui.row().classes("items-start gap-6 w-full"):
                with ui.column().classes("gap-4 w-full").style("flex: 1 1 0; min-width: 0;"):
                    with ui.card().classes("panel w-full"):
                        ui.label("Prompt").style("font-weight: 600;")
                        input_area = ui.textarea(value=base_prompt_text, placeholder="Enter a prompt...",
                                                  on_change=lambda e: on_input_change(e.value))
                        input_area.props("rows=5")
                        input_area.style("width: 100%;")
                        input_area.on("blur", lambda _: on_input_blur())

                    with ui.card().classes("panel w-full"):
                        ui.label("Completion").style("font-weight: 600; margin-bottom: 6px;")
                        output_area = ui.html("", sanitize=False).classes("token-output")

                    with ui.card().classes("panel w-full"):
                        ui.label("Next tokens").style("font-weight: 600;")
                        next_tokens_container = ui.element("div").classes("next-table").style("width: 100%;")

                with ui.column().classes("panel controls"):
                    ui.label("Controls").style("font-weight: 600;")
                    edit_button = ui.button("Edit", on_click=lambda: handle_edit()).props("outline")
                    next_button = ui.button("Next", on_click=lambda: append_weighted()).props("outline")
                    delete_button = ui.button("Delete", on_click=lambda: delete_last()).props("outline")
                    delete_all_button = ui.button("Delete All", on_click=lambda: delete_all()).props("outline")
                    continue_button = ui.button("Continue", on_click=lambda: toggle_continue())
                    continue_button.props("outline")

                    token_numbers_checkbox = ui.checkbox("Show token numbers", value=False, on_change=lambda e: set_show_token_numbers(e.value))
                    probabilities_checkbox = ui.checkbox("Show probabilities", value=False, on_change=lambda e: set_show_probabilities(e.value))

                    legend_container = ui.column().classes("gap-2")

        ui.keyboard(on_key=handle_key)
        refresh_ui()

    ui.run(host=host, port=port, reload=False)


def _resolve_end_token_id(explorer):
    if explorer.tokenizer.eos_token_id is not None:
        return explorer.tokenizer.eos_token_id
    try:
        tokens = explorer.tokenizer.encode("<|endoftext|>")
        if len(tokens) == 1:
            return tokens[0]
    except Exception:
        return None
    return None


def update_html(element, content):
    try:
        element.set_content(content)
    except AttributeError:
        element.content = content
