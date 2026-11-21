from pathlib import Path

import gradio as gr

from src.router import route_request
from frontend.components import (
    create_header,
    create_hero,
    create_page_intro,
    create_stat_card,
    create_section_heading,
    create_action_card,
    create_employee_card,
    create_ai_banner,
    create_info_panel,
)


# --------------------------------------------------
# PATHS & STYLING
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
CSS_PATH = BASE_DIR / "frontend" / "styles.css"

base_css = (
    CSS_PATH.read_text(encoding="utf-8")
    if CSS_PATH.exists()
    else ""
)

# All layout + component styling now lives in frontend/styles.css
APP_CSS = ""


# --------------------------------------------------
# CHAT BACKEND — PRESERVED
# --------------------------------------------------

def chat_with_hr(message, employee_id, history):

    if not message or not message.strip():
        return history, history, ""

    try:
        history = history or []

        print("\n========== CHAT DEBUG ==========")
        print(f"Employee ID: {employee_id}")
        print(f"Current message: {message}")
        print(f"Previous messages: {len(history)}")

        response = route_request(
            user_message=message.strip(),
            employee_id=int(employee_id),
            history=history
        )

        response = str(response)

        updated_history = history + [
            {"role": "user", "content": message.strip()},
            {"role": "assistant", "content": response}
        ]

        print(f"[DEBUG] Updated history: {len(updated_history)} messages")
        print("================================\n")

        return updated_history, updated_history, ""

    except Exception as exc:
        print(f"[ERROR] HR assistant error: {exc}")

        error_message = (
            "I'm sorry, but I couldn't process your request right now. "
            "Please try again in a moment."
        )

        updated_history = (history or []) + [
            {"role": "user", "content": message.strip()},
            {"role": "assistant", "content": error_message}
        ]

        return updated_history, updated_history, ""


# --------------------------------------------------
# NAVIGATION
# --------------------------------------------------

def show_dashboard():
    return (
        gr.update(visible=True),
        gr.update(visible=False),
        gr.update(visible=False)
    )


def show_assistant():
    return (
        gr.update(visible=False),
        gr.update(visible=True),
        gr.update(visible=False)
    )


def show_employees():
    return (
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=True)
    )


# --------------------------------------------------
# EMPLOYEE DATA
# --------------------------------------------------

EMPLOYEES = [
    ("Arjun Desai", 4, "Employee"),
    ("Neha Joshi", 5, "Employee"),
    ("Rahul Mehta", 2, "Manager"),
    ("Sneha Patel", 3, "Manager"),
    ("Priya Sharma", 1, "HR Admin"),
    ("Karan Shah", 6, "Employee"),
    ("Aditi Kulkarni", 7, "Employee"),
]

EMPLOYEE_CHOICES = [
    (f"{name} — {role} (ID: {employee_id})", employee_id)
    for name, employee_id, role in EMPLOYEES
]


# --------------------------------------------------
# SUGGESTED PROMPTS
# --------------------------------------------------

import inspect

# Newer Gradio versions can show clickable example prompts inside the chat window.
SUPPORTS_CHAT_EXAMPLES = "examples" in inspect.signature(gr.Chatbot.__init__).parameters

SUGGESTED_PROMPTS = [
    "How many leaves do I have left?",
    "Explain the leave policy",
    "How do I claim a reimbursement?",
    "Apply for leave next Friday",
]


# --------------------------------------------------
# APPLICATION
# --------------------------------------------------

with gr.Blocks(
    title="HR-MAS | ASK QUESTIONS, UNDERSTAND COMPANY POLICIES AND ACCESS HR SERVICES.",
    css=base_css + "\n" + APP_CSS
) as demo:

    with gr.Row(elem_classes=["app-layout"]):

        # ==========================================
        # SIDEBAR  (navigation + "acting as" switcher)
        # ==========================================

        with gr.Column(scale=0, min_width=340, elem_classes=["sidebar"]):

            gr.HTML("""
                <div class="sidebar-brand">✦ HR-MAS</div>
                <div class="sidebar-caption">INTELLIGENT HR PLATFORM </div>
                <div class="sidebar-label">WORKSPACE</div>
            """)

            dashboard_btn = gr.Button("◈   Overview")
            assistant_btn = gr.Button("✦   AI Assistant")
            employees_btn = gr.Button("♙   Employees")

            gr.HTML('<div class="sidebar-label">ACTING AS</div>')

            employee_id = gr.Dropdown(
                show_label=False,
                container=False,
                choices=EMPLOYEE_CHOICES,
                value=4,
                type="value",
                interactive=True
            )

            gr.HTML("""
                <div class="sidebar-footer">
                    ● &nbsp; HR SYSTEM ACTIVE<br><br>
                    Intelligent HR operations<br>
                    Powered by AI
                </div>
            """)

        # ==========================================
        # MAIN CONTENT
        # ==========================================

        with gr.Column(scale=1, elem_classes=["main-content"]):

            create_header()

            # --------------------------------------
            # OVERVIEW PAGE
            # --------------------------------------

            with gr.Column(visible=True, elem_classes=["page-content"]) as dashboard_page:

                create_hero(
                    "Good day, welcome back.",
                    "Your intelligent workspace for streamlined HR operations.",
                    "WORKSPACE OVERVIEW",
                    chips=["07 PROFILES", "AI ASSISTANT READY", "POLICY WORKFLOWS"]
                )

                with gr.Row(elem_classes=["stat-grid"]):
                    create_stat_card("Employee Profiles", "07", "Demo employee records configured", "♙")
                    create_stat_card("AI Assistant", "Ready", "Available for HR queries", "✦")
                    create_stat_card("HR Workspace", "Active", "Policy and employee workflows", "◈")

                create_section_heading(
                    "Jump in",
                    "Open a tool to get started."
                )

                with gr.Row():

                    with gr.Column(scale=2):
                        create_action_card(
                            "AI HR Assistant",
                            "ASK QUESTIONS, UNDERSTAND COMPANY POLICIES AND ACCESS HR SERVICES.",
                            "✦"
                        )
                        open_assistant_btn = gr.Button(
                            "Open AI Assistant →",
                            elem_classes=["primary-action"]
                        )

                        create_action_card(
                            "Employee Directory",
                            "Explore the employee profiles configured in the system.",
                            "♙"
                        )
                        view_employees_btn = gr.Button(
                            "View Employees →",
                            elem_classes=["secondary-action"]
                        )

                    with gr.Column(scale=1):
                        create_info_panel(
                            "What you can ask",
                            [
                                ("Leave", "Balances, requests and approvals", "◈"),
                                ("Policies", "Company rules explained simply", "✦"),
                                ("Reimbursement", "Claims and how to file them", "♙"),
                            ]
                        )

            # --------------------------------------
            # AI ASSISTANT PAGE
            # --------------------------------------

            with gr.Column(visible=False, elem_classes=["page-content"]) as assistant_page:

                with gr.Column(elem_classes=["chat-panel"]):

                    chatbot_kwargs = dict(
                        show_label=False,
                        height=400,
                        elem_classes=["chatbot"]
                    )

                    # Suggestions live INSIDE the chat window (shown while it is empty)
                    if SUPPORTS_CHAT_EXAMPLES:
                        chatbot_kwargs["examples"] = [
                            {"text": p} for p in SUGGESTED_PROMPTS
                        ]

                    chatbot = gr.Chatbot(**chatbot_kwargs)

                    conversation_state = gr.State([])

                    # Fallback for older Gradio: chips directly under the chat window
                    prompt_btns = []
                    if not SUPPORTS_CHAT_EXAMPLES:
                        with gr.Row(elem_classes=["chip-row"]):
                            prompt_btns = [
                                gr.Button(p, elem_classes=["prompt-chip"])
                                for p in SUGGESTED_PROMPTS
                            ]

                    message = gr.Textbox(
                        placeholder="Ask something about leave, policies, reimbursement...",
                        label="Your message",
                        lines=1,
                        max_lines=4
                    )

                    with gr.Row(elem_classes=["chat-input-row"]):
                        send_btn = gr.Button(
                            "Send message →",
                            variant="primary",
                            elem_classes=["primary-action"],
                            scale=4
                        )
                        clear_btn = gr.Button(
                            "Clear",
                            elem_classes=["secondary-action"],
                            scale=1
                        )

            # --------------------------------------
            # EMPLOYEES PAGE  (3-column card grid)
            # --------------------------------------

            with gr.Column(visible=False, elem_classes=["page-content"]) as employees_page:

                create_page_intro(
                    "Employee directory.",
                    "View the employee profiles configured in your HR system.",
                    "PEOPLE & ORGANIZATION"
                )

                create_section_heading(
                    "Registered employees",
                    "Select a profile to use the AI assistant as that employee."
                )

                use_profile_btns = []

                for i in range(0, len(EMPLOYEES), 3):
                    with gr.Row():
                        for name, emp_id, role in EMPLOYEES[i:i + 3]:
                            with gr.Column(min_width=260, elem_classes=["employee-col"]):
                                create_employee_card(name, emp_id, role)
                                btn = gr.Button(
                                    "Use profile →",
                                    size="sm",
                                    elem_classes=["secondary-action"]
                                )
                                use_profile_btns.append((btn, emp_id))

                        # pad the last row so its cards keep the same width
                        for _ in range(3 - len(EMPLOYEES[i:i + 3])):
                            gr.Column(min_width=260)

    # ==========================================
    # EVENTS
    # ==========================================

    pages = [dashboard_page, assistant_page, employees_page]

    # Navigation
    dashboard_btn.click(fn=show_dashboard, outputs=pages)
    assistant_btn.click(fn=show_assistant, outputs=pages)
    employees_btn.click(fn=show_employees, outputs=pages)
    open_assistant_btn.click(fn=show_assistant, outputs=pages)
    view_employees_btn.click(fn=show_employees, outputs=pages)

    # Chat
    chat_inputs = [message, employee_id, conversation_state]
    chat_outputs = [chatbot, conversation_state, message]

    message.submit(fn=chat_with_hr, inputs=chat_inputs, outputs=chat_outputs)
    send_btn.click(fn=chat_with_hr, inputs=chat_inputs, outputs=chat_outputs)

    clear_btn.click(fn=lambda: ([], []), outputs=[chatbot, conversation_state])

    # Avoid mixing one employee's chat with another's.
    employee_id.change(fn=lambda: ([], []), outputs=[chatbot, conversation_state])

    # Suggested prompts fill the message box
    if SUPPORTS_CHAT_EXAMPLES:
        def fill_from_example(evt: gr.SelectData):
            value = evt.value
            return value.get("text", "") if isinstance(value, dict) else str(value)

        chatbot.example_select(fn=fill_from_example, outputs=message)
    else:
        for btn, text in zip(prompt_btns, SUGGESTED_PROMPTS):
            btn.click(fn=lambda t=text: t, outputs=message)

    # "Use profile" -> set employee and jump to the assistant
    for btn, emp_id in use_profile_btns:
        btn.click(
            fn=lambda eid=emp_id: (eid, *show_assistant()),
            outputs=[employee_id, *pages]
        )


# --------------------------------------------------
# LAUNCH
# --------------------------------------------------

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=8501)