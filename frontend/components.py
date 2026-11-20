import gradio as gr
from html import escape


# =====================================================
# BRAND HEADER
# =====================================================

def create_header():

    return gr.HTML("""
    <div class="app-header">
        <div class="brand-section">
            <div class="brand-icon">✦</div>
            <div>
                <div class="brand-name">HR-MAS</div>
                <div class="brand-subtitle">ASK QUESTIONS, UNDERSTAND COMPANY POLICIES AND ACCESS HR SERVICES.</div>
            </div>
        </div>

        <div class="header-right">
            <div class="system-status">
                <span class="status-dot"></span>
                Systems operational
            </div>
            <div class="header-user">
                <div class="header-user-name">Admin</div>
                <div class="header-user-role">HR workspace</div>
            </div>
            <div class="header-avatar">A</div>
        </div>
    </div>
    """)


# =====================================================
# PAGE INTRODUCTION
# =====================================================

def create_page_intro(title, subtitle, eyebrow="OVERVIEW"):

    return gr.HTML(f"""
    <div class="page-intro">
        <div class="eyebrow">{escape(eyebrow)}</div>
        <h1>{escape(title)}</h1>
        <p>{escape(subtitle)}</p>
    </div>
    """)


# =====================================================
# STATISTIC CARD
# =====================================================

def create_stat_card(title, value, description, icon="✦"):

    return gr.HTML(f"""
    <div class="stat-card">
        <div class="stat-card-top">
            <span class="stat-icon">{escape(icon)}</span>
            <span class="stat-label">{escape(title)}</span>
        </div>

        <div class="stat-value">{escape(str(value))}</div>

        <div class="stat-description">
            {escape(description)}
        </div>
    </div>
    """)


# =====================================================
# SECTION HEADING
# =====================================================

def create_section_heading(title, description=""):

    return gr.HTML(f"""
    <div class="section-heading">
        <h2>{escape(title)}</h2>
        <p>{escape(description)}</p>
    </div>
    """)


# =====================================================
# QUICK ACTION CARD
# =====================================================

def create_action_card(title, description, icon="✦"):

    return gr.HTML(f"""
    <div class="action-card">
        <div class="action-icon">{escape(icon)}</div>

        <div class="action-content">
            <h3>{escape(title)}</h3>
            <p>{escape(description)}</p>
        </div>

        <div class="action-arrow">↗</div>
    </div>
    """)


# =====================================================
# EMPLOYEE PROFILE CARD
# =====================================================

def create_employee_card(name, employee_id, role, department=""):

    return gr.HTML(f"""
    <div class="employee-card">

        <div class="employee-avatar">
            {escape(name[:1].upper())}
        </div>

        <div class="employee-details">
            <h3>{escape(name)}</h3>
            <p>{escape(role)}</p>
            <span>{(escape(department) + " · ") if department else ""}ID: {escape(str(employee_id))}</span>
        </div>

    </div>
    """)


# =====================================================
# STATUS BADGE
# =====================================================

def create_status_badge(status):

    status_class = status.lower().replace(" ", "-")

    allowed_classes = {
        "approved",
        "pending",
        "rejected",
        "active",
        "inactive",
    }

    if status_class not in allowed_classes:
        status_class = "pending"

    return gr.HTML(f"""
    <span class="status-badge {status_class}">
        {escape(status.title())}
    </span>
    """)


# =====================================================
# AI ASSISTANT BANNER
# =====================================================

def create_ai_banner(title="HR-MAS AI", subtitle="Your intelligent HR companion."):

    return gr.HTML(f"""
    <div class="ai-banner">
        <div class="ai-banner-icon">✦</div>
        <div>
            <div class="ai-banner-title">{escape(title)}</div>
            <div class="ai-banner-sub">{escape(subtitle)}</div>
        </div>
    </div>
    """)



# =====================================================
# HERO BANNER
# =====================================================

def create_hero(title, subtitle, eyebrow="WORKSPACE OVERVIEW", chips=()):

    chip_html = "".join(
        f'<span class="hero-chip">{escape(c)}</span>' for c in chips
    )

    return gr.HTML(f"""
    <div class="hero">
        <div class="eyebrow">{escape(eyebrow)}</div>
        <h1>{escape(title)}</h1>
        <p>{escape(subtitle)}</p>
        <div class="hero-chips">{chip_html}</div>
    </div>
    """)


# =====================================================
# INFO PANEL (list of short items)
# =====================================================

def create_info_panel(title, items):
    """items: list of (heading, detail, icon) tuples."""

    rows = "".join(
        f"""
        <div class="info-item">
            <div class="info-item-icon">{escape(icon)}</div>
            <div><b>{escape(h)}</b><span>{escape(d)}</span></div>
        </div>"""
        for h, d, icon in items
    )

    return gr.HTML(f"""
    <div class="info-panel">
        <h3>{escape(title)}</h3>
        {rows}
    </div>
    """)