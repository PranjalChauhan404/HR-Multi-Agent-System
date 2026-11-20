import json
import re
import time
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from crewai import Agent, LLM, Task, Crew, Process

from src.config import OPENAI_API_KEY, OPENAI_MODEL

from src.agents import (
    policy_agent,
    create_leave_agent,
    onboarding_agent,
)

from src.tools import (
    apply_for_leave,
    check_leave_balance,
    view_leave_requests,
    view_team_pending_requests,
    view_team_leave_balances,
    view_team_members,
    view_team_members_without_leave_requests,
)

from src.observability import trace_function


# ============================================================
# 1. LLM CONFIGURATION
# ============================================================

llm = LLM(
    model=f"openai/{OPENAI_MODEL}",
    api_key=OPENAI_API_KEY,
    temperature=0,
)


# ============================================================
# 2. INTENT CLASSIFICATION SCHEMA
# ============================================================

class HRIntent(str, Enum):

    LEAVE_BALANCE = "leave_balance"

    TEAM_LEAVE_BALANCE = "team_leave_balance"

    LEAVE_REQUEST_STATUS = "leave_request_status"

    TEAM_PENDING_REQUESTS = "team_pending_requests"

    APPLY_LEAVE = "apply_leave"

    LEAVE_MANAGEMENT = "leave_management"

    ONBOARDING = "onboarding"

    POLICY = "policy"

    GENERAL = "general"


class RoutingDecision(BaseModel):

    intent: HRIntent = Field(
        description="The primary intent of the employee's request."
    )

    leave_type: Optional[str] = Field(
        default=None,
        description="Leave category if explicitly mentioned."
    )

    request_id: Optional[int] = Field(
        default=None,
        description="Leave request ID if explicitly mentioned."
    )

    reasoning: str = Field(
        description="Brief explanation of the classification."
    )


# ============================================================
# 3. SUPERVISOR AGENT
# ============================================================

supervisor_agent = Agent(
    role="HR Intent Classification Supervisor",

    goal=(
        "Understand employee requests and identify their "
        "underlying HR intent accurately."
    ),

    backstory=(
        "You are an intelligent HR request classifier. "

        "You understand natural language, paraphrasing, "
        "implicit requests, conversational context, and "
        "different ways employees express the same intent. "

        "You do not depend on exact keywords. "

        "You identify what the employee wants to accomplish "
        "rather than merely matching words in their message."
    ),

    llm=llm,

    verbose=False,

    allow_delegation=False,
)


# ============================================================
# 4. CONVERSATION HISTORY
# ============================================================

def format_conversation_history(history, max_messages=10):

    if not history:
        return "No previous conversation."

    messages = []

    for item in history[-max_messages:]:

        if isinstance(item, dict):

            role = item.get("role", "user")
            content = item.get("content", "")

            if isinstance(content, str) and content.strip():

                messages.append(
                    f"{role.capitalize()}: {content}"
                )

        elif isinstance(item, (tuple, list)) and len(item) == 2:

            user_message, assistant_message = item

            if user_message:
                messages.append(f"User: {user_message}")

            if assistant_message:
                messages.append(
                    f"Assistant: {assistant_message}"
                )

    return "\n".join(messages) or "No previous conversation."


# ============================================================
# 5. LEAVE DETAIL EXTRACTION
# ============================================================

def extract_leave_details(user_message, history=None):

    user_messages = []

    if history:

        for item in history:

            if isinstance(item, dict):

                if item.get("role") == "user":

                    content = item.get("content", "")

                    if isinstance(content, str):
                        user_messages.append(content)

            elif isinstance(item, (tuple, list)) and len(item) == 2:

                if item[0]:
                    user_messages.append(str(item[0]))

    user_messages.append(user_message)

    details = {
        "leave_type": None,
        "start_date": None,
        "end_date": None,
    }

    patterns = {

        "leave_type": re.compile(
            r"leave\s*type\s*:\s*"
            r"(casual\s*leave|sick\s*leave|earned\s*leave|"
            r"annual\s*leave|casual|sick|earned|annual)",
            re.IGNORECASE,
        ),

        "start_date": re.compile(
            r"start\s*date\s*:\s*(\d{4}-\d{2}-\d{2})",
            re.IGNORECASE,
        ),

        "end_date": re.compile(
            r"end\s*date\s*:\s*(\d{4}-\d{2}-\d{2})",
            re.IGNORECASE,
        ),
    }

    for message in user_messages:

        for key, pattern in patterns.items():

            match = pattern.search(message)

            if not match:
                continue

            value = match.group(1).strip().lower()

            if key == "leave_type":

                value = re.sub(r"\s+", " ", value)

                if value.endswith(" leave"):
                    value = value[:-6].strip()

            details[key] = value

    return details


# ============================================================
# 6. INTENT CLASSIFICATION
# ============================================================

def classify_intent(user_message, history=None):

    conversation_history = format_conversation_history(history)

    classification_task = Task(

        description=f"""
You are classifying an employee's HR request.

CONVERSATION HISTORY:
{conversation_history}

CURRENT EMPLOYEE REQUEST:
{user_message}

Identify the employee's actual intent.

AVAILABLE INTENTS:

1. leave_balance:
   Employee wants their own leave balance, remaining leaves,
   available days off, or leave entitlement from their records.

2. team_leave_balance:
   Employee wants leave balances belonging to their team.

3. leave_request_status:
   Employee wants to know the status or details of an
   existing leave application.

4. team_pending_requests:
   Employee wants to see pending leave requests from their team.

5. apply_leave:
   Employee wants to apply for, submit, or request leave.

6. leave_management:
   Employee asks another leave-related question or wants
   assistance with leave management.

7. onboarding:
   Employee asks about onboarding, joining procedures,
   new employee processes, or onboarding documentation.

8. policy:
   Employee asks about company policies, rules, benefits,
   reimbursements, work-from-home, or HR guidelines.

9. general:
   General HR questions that do not fit the categories above.

IMPORTANT CLASSIFICATION RULES:

- Understand meaning, not exact keywords.
- "How many days off do I have left?" means leave_balance.
- "What's left in my leave allowance?" means leave_balance.
- "Can you check how much sick leave I have?" means leave_balance.
- "How much leave does my team have?" means team_leave_balance.
- "Has my leave been approved?" means leave_request_status.
- "I need a day off next Monday" means apply_leave.
- "How do I apply for leave?" means leave_management.
- A question about leave policy is policy, not leave_balance.
- Use conversation history to understand follow-up questions.
- Prefer the current message when the employee clearly changes topics.
- Do not classify an employee's personal balance request as a
  team balance request.
- Do not confuse policy entitlements with actual database balances.

If a leave type is explicitly mentioned, extract it.

If a leave request ID is explicitly mentioned, extract it.

Return ONLY the structured classification.
""",

        expected_output=(
            "A structured RoutingDecision containing the intent, "
            "optional leave type, optional request ID, and reasoning."
        ),

        agent=supervisor_agent,

        output_pydantic=RoutingDecision,
    )

    crew = Crew(
        agents=[supervisor_agent],
        tasks=[classification_task],
        process=Process.sequential,
        verbose=False,
    )

    result = crew.kickoff()

    decision = getattr(result, "pydantic", None)

    if isinstance(decision, RoutingDecision):
        return decision

    if isinstance(decision, dict):
        return RoutingDecision(**decision)

    # Compatibility fallback for models/framework versions
    # that return structured JSON as text.

    raw_output = str(result)

    json_match = re.search(
        r"\{[\s\S]*\}",
        raw_output,
    )

    if not json_match:
        raise ValueError(
            "The intent classifier returned an invalid response."
        )

    data = json.loads(json_match.group())

    return RoutingDecision(**data)


# ============================================================
# 7. DIRECT DATABASE EXECUTION
# ============================================================

def get_personal_leave_balance(employee_id, leave_type=None):

    result = check_leave_balance(
        employee_id=employee_id,
        current_user_id=employee_id,
    )

    if not result.get("success"):

        return result.get(
            "message",
            "Unable to retrieve your leave balance."
        )

    balances = result.get("balances", {})

    if leave_type:

        leave_type = leave_type.lower()

        if leave_type not in ("casual", "earned", "sick"):

            return (
                "I couldn't identify a supported leave category. "
                "Please specify casual, earned, or sick leave."
            )

        return (
            f"Your current {leave_type.title()} Leave balance "
            f"is {balances.get(leave_type, 0)} days."
        )

    return (
        "Here is your current leave balance:\n\n"
        f"- Casual Leave: {balances.get('casual', 0)} days\n"
        f"- Earned Leave: {balances.get('earned', 0)} days\n"
        f"- Sick Leave: {balances.get('sick', 0)} days"
    )


def get_team_members_without_leave_requests(manager_id):
    result = view_team_members_without_leave_requests(manager_id)
    if not result.get("success"):
        return result.get("message", "Unable to retrieve team leave history.")
    members = result.get("members", [])
    if not members:
        return "All your direct reports have submitted at least one leave request."
    return "**Team members with no leave requests on record**\n" + "\n".join(
        f"- {m['name']} (ID: {m['employee_id']})" for m in members
    )


def get_team_members(manager_id):
    result = view_team_members(manager_id=manager_id)
    if not result.get("success"):
        return result.get("message", "Unable to retrieve your team members.")
    members = result.get("members", [])
    if not members:
        return "No direct reports are currently assigned to you."
    lines = ["**Your Team Members**"]
    for member in members:
        lines.append(
            f"- {member['name']} — ID: {member['employee_id']} | "
            f"{member.get('department') or 'Department not set'} | "
            f"{member.get('role') or 'Role not set'}"
        )
    return "\n".join(lines)


def get_team_leave_balance(manager_id):

    result = view_team_leave_balances(
        manager_id=manager_id
    )

    if not result.get("success"):
        return result.get("message", "Unable to retrieve team balances.")

    balances = result.get("balances", [])

    if not balances:
        return "No leave balances were found for your team."

    lines = ["**Team Leave Balances**"]

    for item in balances:

        lines.append(
            f"- Employee ID {item['employee_id']}: "
            f"{item['leave_type']} leave — "
            f"{item['remaining']} days remaining"
        )

    return "\n".join(lines)


def get_team_pending_requests(manager_id):

    result = view_team_pending_requests(
        manager_id=manager_id
    )

    if not result.get("success"):
        return result.get("message", "Unable to retrieve team requests.")

    requests = result.get("requests", [])

    if not requests:
        return "There are no pending leave requests for your team."

    lines = ["**Pending Team Leave Requests**"]

    for request in requests:

        lines.append(
            f"- Request #{request['request_id']} | "
            f"Employee ID: {request['employee_id']} | "
            f"Type: {request['leave_type']} | "
            f"Dates: {request['start_date']} to "
            f"{request['end_date']} | "
            f"Status: {request['status']}"
        )

    return "\n".join(lines)


def get_leave_request_status(employee_id, request_id):

    result = view_leave_requests(
        employee_id=employee_id,
        current_user_id=employee_id,
    )

    if not result.get("success"):
        return result.get("message", "Unable to retrieve leave requests.")

    requests = result.get("requests", [])
    if not request_id:
        if not requests:
            return "You don't have any leave requests on record."
        lines = ["**Your Recent Leave Requests**"]
        for request in requests[:5]:
            lines.append(
                f"- Request #{request['request_id']} | "
                f"{request['leave_type'].title()} leave | "
                f"{request['start_date']} to {request['end_date']} | "
                f"{request['status'].upper()}"
            )
        lines.append("Tell me which request you'd like details about.")
        return "\n".join(lines)

    for request in requests:
        if request["request_id"] == request_id:
            return (
                f"Leave request #{request_id} status: "
                f"{request['status'].upper()}.\n\n"
                f"Leave type: {request['leave_type']}\n"
                f"Start date: {request['start_date']}\n"
                f"End date: {request['end_date']}"
            )
    return f"Leave request #{request_id} was not found among your leave requests."


# ============================================================
# 8. LEAVE APPLICATION EXECUTION
# ============================================================

def handle_leave_application(employee_id, user_message, history):

    details = extract_leave_details(
        user_message,
        history,
    )

    leave_type = details["leave_type"]
    start_date = details["start_date"]
    end_date = details["end_date"]

    # Check whether the application is ready for submission.

    if not all([leave_type, start_date, end_date]):

        leave_agent = create_leave_agent(employee_id)

        task = Task(

            description=f"""
The employee wants to apply for leave.

Conversation:
{format_conversation_history(history)}

Current request:
{user_message}

Employee ID:
{employee_id}

Help the employee complete their leave application.

Collect any missing information:
- Leave type
- Start date
- End date

Do not submit an incomplete application.
Do not claim that a request was submitted.
""",

            expected_output=(
                "A response that guides the employee through "
                "the missing leave application information."
            ),

            agent=leave_agent,
        )

        crew = Crew(
            agents=[leave_agent],
            tasks=[task],
            process=Process.sequential,
            verbose=False,
        )

        return str(crew.kickoff())

    if leave_type == "annual":

        return (
            "Annual leave is not supported in this system. "
            "Please choose casual, sick, or earned leave."
        )

    result = apply_for_leave(

        employee_id=employee_id,

        leave_type=leave_type,

        start_date=start_date,

        end_date=end_date,

        current_user_id=employee_id,
    )

    if not result.get("success"):

        return (
            "I couldn't submit your leave request: "
            + result.get("message", "Unknown error.")
        )

    return (
        "Leave request submitted successfully!\n"
        f"Request ID: #{result['request_id']}\n"
        "Status: Pending manager approval."
    )


# ============================================================
# 9. SPECIALIST AGENT EXECUTION
# ============================================================

def execute_specialist(
    agent,
    employee_id,
    user_message,
    history,
):

    task = Task(

        description=f"""
You are handling an employee's HR request.

EMPLOYEE ID:
{employee_id}

CONVERSATION HISTORY:
{format_conversation_history(history)}

CURRENT REQUEST:
{user_message}

INSTRUCTIONS:

- Understand the current request in its conversational context.
- Answer accurately and concisely.
- Use available tools when necessary.
- Never invent employee records or policy information.
- Never claim a database action succeeded unless a tool confirms it.
- Do not ask for information already provided in the conversation.
- If a leave application requires missing information, collect it.
""",

        expected_output=(
            "A clear, accurate response to the employee's request."
        ),

        agent=agent,
    )

    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )

    return str(crew.kickoff())


# ============================================================
# 10. MAIN REQUEST ROUTER
# ============================================================

@trace_function("hr-request-routing")

def route_request(
    user_message: str,
    employee_id: int,
    history=None,
) -> str:

    if not user_message or not user_message.strip():

        return "Please enter an HR-related question."

    request_started = time.perf_counter()
    print("\n========== HR ROUTER ==========")

    print(f"Employee ID: {employee_id}")
    print(f"Request: {user_message}")

    try:
        message = user_message.strip().lower()

        # Fast, deterministic routes for unambiguous, identity-bound team queries.
        no_leave_query = (
            re.search(r"\b(never|haven't|have not|hasn't|has not|no)\b", message)
            and re.search(r"\b(submitted|applied|made|raised)\b", message)
            and re.search(r"\b(leave|time off)\b", message)
            and re.search(r"\b(team|employees|members|people|staff)\b", message)
        )
        if no_leave_query:
            print("[ROUTER] Fast path: team members without leave requests")
            return get_team_members_without_leave_requests(employee_id)

        directory_intent = (
            re.search(r"\b(my team|team members?|team roster|team directory|direct reports?|employees reporting to me|people reporting to me|employees under me|my staff)\b", message)
            or re.search(r"\b(who reports to me|who is on my team|who are in my team)\b", message)
        )
        directory_action = re.search(
            r"\b(list|show|display|give|find|who|names?|directory|roster|reports?)\b",
            message,
        )
        # Do not steal team-balance or pending-request questions from their routes.
        is_other_team_workflow = re.search(
            r"\b(balance|balances|pending|leave requests?|approv(?:e|al)|reject(?:ion)?)\b",
            message,
        )
        if directory_intent and directory_action and not is_other_team_workflow:
            print("[ROUTER] Fast path: team directory")
            return get_team_members(employee_id)

        # Never allow an employee/manager to approve their own request.
        history_text = format_conversation_history(history).lower()
        self_approval_context = ("leave request submitted successfully" in history_text or "i submitted" in history_text or "apply for a sick leave" in history_text)
        explicit_self_approval = re.search(r"\b(approve|accept)\b", message) and re.search(r"\b(my own|my|own)\b", message) and re.search(r"\b(leave|request)\b", message)
        contextual_self_approval = self_approval_context and re.fullmatch(r"(please\s+)?(approve|accept)(\s+it)?[.! ]*", message)
        if explicit_self_approval or contextual_self_approval:
            return "You cannot approve your own leave request. It must be reviewed by your assigned manager."

        # A general question about rejection is a policy question, not a request lookup.
        if re.search(r"\b(what happens|what if|if)\b", message) and re.search(r"\b(manager|leave)\b", message) and re.search(r"\b(reject|rejected|denied)\b", message) and not re.search(r"#?\d+", message):
            return execute_specialist(policy_agent, employee_id, user_message, history)

        # Asking to find/remember a request without an ID should retrieve recent history.
        if re.search(r"\b(don't remember|do not remember|forgot|don't know|find my|my recent)\b", message) and re.search(r"\b(request|leave)\b", message):
            return get_leave_request_status(employee_id, None)

        # -----------------------------------------------
        # STEP 1: UNDERSTAND EMPLOYEE INTENT
        # -----------------------------------------------

        classification_started = time.perf_counter()
        decision = classify_intent(
            user_message=user_message,
            history=history,
        )
        print(
            f"[TIMING] Intent classification: "
            f"{time.perf_counter() - classification_started:.2f}s"
        )

        intent = decision.intent

        print(f"[ROUTER] Intent: {intent.value}")
        print(f"[ROUTER] Reasoning: {decision.reasoning}")

        # -----------------------------------------------
        # STEP 2: EXECUTE DETERMINISTIC OPERATIONS
        # -----------------------------------------------

        if intent == HRIntent.LEAVE_BALANCE:

            return get_personal_leave_balance(
                employee_id=employee_id,
                leave_type=decision.leave_type,
            )

        if intent == HRIntent.TEAM_LEAVE_BALANCE:

            return get_team_leave_balance(
                manager_id=employee_id,
            )

        if intent == HRIntent.LEAVE_REQUEST_STATUS:

            return get_leave_request_status(
                employee_id=employee_id,
                request_id=decision.request_id,
            )

        if intent == HRIntent.TEAM_PENDING_REQUESTS:

            return get_team_pending_requests(
                manager_id=employee_id,
            )

        if intent == HRIntent.APPLY_LEAVE:

            return handle_leave_application(
                employee_id=employee_id,
                user_message=user_message,
                history=history,
            )

        # -----------------------------------------------
        # STEP 3: DELEGATE TO SPECIALIST AGENTS
        # -----------------------------------------------

        if intent == HRIntent.LEAVE_MANAGEMENT:

            agent = create_leave_agent(employee_id)

        elif intent == HRIntent.ONBOARDING:

            agent = onboarding_agent

        elif intent == HRIntent.POLICY:

            agent = policy_agent

        else:

            # General HR questions go through the policy
            # specialist rather than being treated as a
            # database operation.

            agent = policy_agent

        specialist_started = time.perf_counter()
        answer = execute_specialist(
            agent=agent,
            employee_id=employee_id,
            user_message=user_message,
            history=history,
        )
        print(
            f"[TIMING] Specialist execution: "
            f"{time.perf_counter() - specialist_started:.2f}s"
        )
        return answer

    except Exception as exc:

        print(f"[ROUTER ERROR] {type(exc).__name__}: {exc}")

        raise

    finally:

        print(f"[TIMING] Total route_request: {time.perf_counter() - request_started:.2f}s")
        print("================================\n")


# ============================================================
# 11. DIRECT TEST
# ============================================================

if __name__ == "__main__":

    test_queries = [

        "Show me my remaining leaves",

        "How many days off do I have left?",

        "What's my current leave balance?",

        "Check my sick leave availability",

        "How much leave does my team have?",

        "Show me pending leave requests",

        "What is the work from home policy?",

        "How do I apply for leave?",

        "What should a new employee complete during onboarding?",
    ]

    for query in test_queries:

        print(f"\nTEST QUERY: {query}")

        decision = classify_intent(query)

        print("CLASSIFIED INTENT:", decision.intent.value)