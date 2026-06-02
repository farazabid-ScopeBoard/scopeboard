# -*- coding: utf-8 -*-
"""
ScopeBoard — Streamlit Prototype
---------------------------------
Run with:  streamlit run app.py
"""

import json
import streamlit as st
from scripts.scopeboard_extract import run_extraction
from scripts.scopeboard_suggest import run_suggestion

# ════════════════════════════════════════════════════════════════════
# CONFIG
# ════════════════════════════════════════════════════════════════════

INDUSTRIES = [
    "Financial Services",
    "Healthcare & Life Sciences",
    "Technology",
    "Telecommunications & Media",
    "Retail & Consumer",
    "Energy & Utilities",
    "Public Sector & Government",
]

ARCHETYPES = [
    "Digital Transformation & Modernisation",
    "Cost Reduction & Efficiency",
    "Risk Management",
    "Regulatory & Compliance",
    "Customer Experience & Engagement",
    "Market Growth & Revenue Expansion",
    "M&A Integration & Restructuring",
    "Sustainable Technology & ESG",
    "Workforce & Talent Transformation",
    "Data & Analytics",
    "AI Adoption & Transformation",
    "Cybersecurity & Information Security",
    "Infrastructure & Technology Modernisation",
]

st.set_page_config(
    page_title  = "ScopeBoard",
    page_icon   = "🎯",
    layout      = "wide",
    initial_sidebar_state = "expanded"
)

# ── Custom CSS ────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {font-size: 2rem; font-weight: 800; color: #1F497D; margin-bottom: 0;}
    .sub-header  {font-size: 1rem; color: #666; margin-top: 0; margin-bottom: 1.5rem;}
    .step-badge  {background: #1F497D; color: white; padding: 3px 10px;
                  border-radius: 12px; font-size: 0.75rem; font-weight: 600;}
    .benefit-card {border: 1px solid #e0e0e0; border-radius: 8px;
                   padding: 1rem; margin-bottom: 0.75rem; background: #fafafa;}
    .missing-card {border-left: 4px solid #C55A11; background: #FFF8F5;
                   padding: 1rem; border-radius: 0 8px 8px 0; margin-bottom: 1rem;}
    .matched-card {border-left: 4px solid #375E23; background: #F5FFF5;
                   padding: 0.75rem; border-radius: 0 8px 8px 0; margin-bottom: 0.5rem;}
    .flag-card    {border-left: 4px solid #C5A000; background: #FFFDE7;
                   padding: 0.75rem; border-radius: 0 8px 8px 0; margin-bottom: 0.5rem;}
    .section-title {color: #1F497D; font-weight: 700; font-size: 1.1rem; margin-bottom: 0.5rem;}
    .metric-pill  {display: inline-block; background: #E8F0FE; color: #1F497D;
                   padding: 2px 8px; border-radius: 10px; font-size: 0.78rem;
                   margin: 2px; font-weight: 500;}
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════
# SESSION STATE INIT
# ════════════════════════════════════════════════════════════════════

defaults = {
    "project_name":       "",
    "industry":           INDUSTRIES[0],
    "transcript":         "",
    "extraction":         None,
    "review":             {},      # entity_id -> {status, text}
    "archetypes_by_goal": {},      # goal_id -> archetype string
    "suggestion_results": None,
    "step":               1,       # 1=setup, 2=extract, 3=review, 4=suggest, 5=export
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ════════════════════════════════════════════════════════════════════
# SIDEBAR — Project Setup
# ════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("### 🎯 ScopeBoard")
    st.caption("Portfolio Intelligence Tool")
    st.divider()

    st.markdown("**Project Setup**")
    st.session_state.project_name = st.text_input(
        "Project / Initiative Name",
        value = st.session_state.project_name,
        placeholder = "e.g. 2025 Digital Transformation"
    )
    st.session_state.industry = st.selectbox(
        "Industry",
        options = INDUSTRIES,
        index   = INDUSTRIES.index(st.session_state.industry)
                  if st.session_state.industry in INDUSTRIES else 0
    )

    st.divider()

    # Progress tracker
    st.markdown("**Progress**")
    steps = [
        ("1", "Project Setup",      st.session_state.step >= 1),
        ("2", "Load Transcript",    st.session_state.step >= 2),
        ("3", "Review Extraction",  st.session_state.step >= 3),
        ("4", "Missing Benefits",   st.session_state.step >= 4),
        ("5", "Export Report",      st.session_state.step >= 5),
    ]
    for num, label, done in steps:
        icon = "✅" if done and st.session_state.step > int(num) else ("▶️" if st.session_state.step == int(num) else "⬜")
        st.markdown(f"{icon} **{num}.** {label}")

    st.divider()

    # Reset
    if st.button("🔄 Start New Project", use_container_width=True):
        for k, v in defaults.items():
            st.session_state[k] = v
        st.rerun()


# ════════════════════════════════════════════════════════════════════
# MAIN HEADER
# ════════════════════════════════════════════════════════════════════

st.markdown('<p class="main-header">ScopeBoard</p>', unsafe_allow_html=True)
project_display = st.session_state.project_name or "New Project"
st.markdown(
    f'<p class="sub-header">📁 {project_display} &nbsp;·&nbsp; 🏭 {st.session_state.industry}</p>',
    unsafe_allow_html=True
)

# ════════════════════════════════════════════════════════════════════
# STEP 2 — TRANSCRIPT INPUT & EXTRACTION
# ════════════════════════════════════════════════════════════════════

st.markdown("---")
st.markdown('<p class="section-title"><span class="step-badge">STEP 1</span>&nbsp; Load Executive Transcript</p>',
            unsafe_allow_html=True)

col_input, col_hint = st.columns([3, 1])
with col_input:
    transcript = st.text_area(
        "Paste the executive interview transcript here",
        value       = st.session_state.transcript,
        height      = 220,
        placeholder = "Paste interview transcript or meeting notes here...",
        label_visibility = "collapsed"
    )
    st.session_state.transcript = transcript

with col_hint:
    st.info(
        "**Tip:** Paste the full transcript from your Fathom, Fireflies, or Otter export. "
        "The AI will extract Vision, Goals, and Benefits automatically."
    )

extract_clicked = st.button(
    "🔍 Extract Vision, Goals & Benefits",
    disabled          = len(transcript.strip()) < 50,
    use_container_width = True,
    type              = "primary"
)

if extract_clicked:
    if not st.session_state.project_name.strip():
        st.warning("Please enter a project name in the sidebar before extracting.")
    else:
        with st.spinner("Analysing transcript... this takes 15–30 seconds"):
            try:
                extraction = run_extraction(transcript)
                st.session_state.extraction   = extraction
                st.session_state.review       = {}
                st.session_state.archetypes_by_goal = {}
                st.session_state.suggestion_results = None
                st.session_state.step         = 3
                st.rerun()
            except Exception as e:
                st.error(f"Extraction failed: {e}")

# ════════════════════════════════════════════════════════════════════
# STEP 3 — REVIEW EXTRACTION + ARCHETYPE ASSIGNMENT
# ════════════════════════════════════════════════════════════════════

if st.session_state.extraction:
    ext = st.session_state.extraction

    st.markdown("---")
    st.markdown('<p class="section-title"><span class="step-badge">STEP 2</span>&nbsp; Review Extracted Entities</p>',
                unsafe_allow_html=True)
    st.caption("Accept, edit, or reject each extracted item. Then assign an archetype to each goal.")

    # ── Vision ────────────────────────────────────────────────────────
    st.markdown("#### 🔭 Vision")
    vision_text = ext.get("vision", "")
    vision_key  = "vision_text"

    if vision_key not in st.session_state.review:
        st.session_state.review[vision_key] = {"status": "pending", "text": vision_text}

    vcol1, vcol2 = st.columns([5, 1])
    with vcol1:
        edited_vision = st.text_area(
            "Vision statement",
            value = st.session_state.review[vision_key]["text"],
            height = 80,
            key = "vision_edit",
            label_visibility = "collapsed"
        )
        st.session_state.review[vision_key]["text"] = edited_vision

    with vcol2:
        v_status = st.session_state.review[vision_key]["status"]
        if st.button("✅ Accept", key="v_accept"):
            st.session_state.review[vision_key]["status"] = "accepted"
        if st.button("❌ Reject", key="v_reject"):
            st.session_state.review[vision_key]["status"] = "rejected"
        status_colours = {"pending": "🔵", "accepted": "✅", "rejected": "❌"}
        st.caption(f"Status: {status_colours.get(v_status, '🔵')} {v_status.title()}")

    # ── Flags ─────────────────────────────────────────────────────────
    flags = ext.get("flags", [])
    if flags:
        st.markdown("#### ⚠️ Advisory Flags")
        for flag in flags:
            st.markdown(
                f'<div class="flag-card">⚠️ {flag}</div>',
                unsafe_allow_html=True
            )

    # ── Goals ─────────────────────────────────────────────────────────
    goals    = ext.get("goals", [])
    benefits = ext.get("benefits", [])

    if goals:
        st.markdown("#### 🎯 Goals & Archetypes")
        st.caption("Review each goal, assign an archetype, then link it to extracted benefits below.")

        for goal in goals:
            gid       = goal["id"]
            goal_text = goal["text"]
            gkey      = f"goal_{gid}"

            if gkey not in st.session_state.review:
                st.session_state.review[gkey] = {"status": "pending", "text": goal_text}

            with st.expander(f"**{gid}** — {goal_text[:80]}{'...' if len(goal_text) > 80 else ''}", expanded=True):
                gcol1, gcol2, gcol3 = st.columns([3, 2, 1])

                with gcol1:
                    edited_goal = st.text_area(
                        f"Goal text for {gid}",
                        value = st.session_state.review[gkey]["text"],
                        height = 80,
                        key = f"gedit_{gid}",
                        label_visibility = "collapsed"
                    )
                    st.session_state.review[gkey]["text"] = edited_goal

                with gcol2:
                    # Archetype selection
                    current_arch = st.session_state.archetypes_by_goal.get(gid, ARCHETYPES[0])
                    arch_options = ["(Not assigned)"] + ARCHETYPES
                    arch_idx     = arch_options.index(current_arch) if current_arch in arch_options else 0
                    selected_arch = st.selectbox(
                        f"Archetype for {gid}",
                        options = arch_options,
                        index   = arch_idx,
                        key     = f"arch_{gid}",
                        label_visibility = "collapsed"
                    )
                    if selected_arch != "(Not assigned)":
                        st.session_state.archetypes_by_goal[gid] = selected_arch
                    elif gid in st.session_state.archetypes_by_goal:
                        del st.session_state.archetypes_by_goal[gid]
                    st.caption("🏷️ Assign archetype")

                with gcol3:
                    g_status = st.session_state.review[gkey]["status"]
                    if st.button("✅", key=f"gaccept_{gid}", help="Accept"):
                        st.session_state.review[gkey]["status"] = "accepted"
                    if st.button("❌", key=f"greject_{gid}", help="Reject"):
                        st.session_state.review[gkey]["status"] = "rejected"
                    status_colours = {"pending": "🔵", "accepted": "✅", "rejected": "❌"}
                    st.caption(f"{status_colours.get(g_status, '🔵')} {g_status.title()}")

                # Show linked benefits
                linked = [b for b in benefits if gid in b.get("relation", "")]
                if linked:
                    st.markdown("**Extracted Benefits linked to this goal:**")
                    for b in linked:
                        bkey = f"benefit_{b['id']}"
                        if bkey not in st.session_state.review:
                            st.session_state.review[bkey] = {"status": "pending", "text": b["text"]}

                        bcol1, bcol2 = st.columns([5, 1])
                        with bcol1:
                            edited_b = st.text_input(
                                f"Benefit {b['id']}",
                                value = st.session_state.review[bkey]["text"],
                                key   = f"bedit_{b['id']}_{gid}",
                                label_visibility = "collapsed"
                            )
                            st.session_state.review[bkey]["text"] = edited_b
                        with bcol2:
                            b_status = st.session_state.review[bkey]["status"]
                            if st.button("✅", key=f"baccept_{b['id']}_{gid}", help="Accept"):
                                st.session_state.review[bkey]["status"] = "accepted"
                            if st.button("❌", key=f"breject_{b['id']}_{gid}", help="Reject"):
                                st.session_state.review[bkey]["status"] = "rejected"
                            b_colours = {"pending": "🔵", "accepted": "✅", "rejected": "❌"}
                            st.caption(f"{b_colours.get(b_status, '🔵')} {b_status.title()}")

    # ════════════════════════════════════════════════════════════════
    # STEP 4 — RUN MISSING BENEFITS ANALYSIS
    # ════════════════════════════════════════════════════════════════

    st.markdown("---")
    st.markdown('<p class="section-title"><span class="step-badge">STEP 3</span>&nbsp; Identify Missing Benefits</p>',
                unsafe_allow_html=True)

    # Check readiness
    goals_without_archetype = [
        g["id"] for g in goals
        if g["id"] not in st.session_state.archetypes_by_goal
        and st.session_state.review.get(f"goal_{g['id']}", {}).get("status") != "rejected"
    ]

    if goals_without_archetype:
        st.warning(
            f"Assign an archetype to goals: **{', '.join(goals_without_archetype)}** "
            "before running the analysis. This ensures the right benefit patterns are suggested."
        )

    suggest_clicked = st.button(
        "🔎 Find Missing Benefits",
        disabled = len(goals_without_archetype) > 0,
        use_container_width = True,
        type = "primary"
    )

    if suggest_clicked:
        # Build accepted-only extraction for suggestion engine
        accepted_goals = [
            {"id": g["id"],
             "text": st.session_state.review.get(f"goal_{g['id']}", {}).get("text", g["text"])}
            for g in goals
            if st.session_state.review.get(f"goal_{g['id']}", {}).get("status") != "rejected"
        ]
        accepted_benefits = [
            {"id": b["id"],
             "text": st.session_state.review.get(f"benefit_{b['id']}", {}).get("text", b["text"]),
             "relation": b["relation"]}
            for b in benefits
            if st.session_state.review.get(f"benefit_{b['id']}", {}).get("status") != "rejected"
        ]

        accepted_extraction = {
            "vision":   st.session_state.review.get("vision_text", {}).get("text", ext.get("vision", "")),
            "goals":    accepted_goals,
            "benefits": accepted_benefits,
            "flags":    flags
        }

        with st.spinner("Analysing benefit coverage across the portfolio... this takes 20–40 seconds"):
            try:
                results = run_suggestion(
                    extraction         = accepted_extraction,
                    industry           = st.session_state.industry,
                    archetypes_by_goal = st.session_state.archetypes_by_goal
                )
                st.session_state.suggestion_results = results
                st.session_state.step = 4
                st.rerun()
            except Exception as e:
                st.error(f"Suggestion engine failed: {e}")

# ════════════════════════════════════════════════════════════════════
# STEP 5 — DISPLAY RESULTS + EXPORT
# ════════════════════════════════════════════════════════════════════

if st.session_state.suggestion_results:
    results = st.session_state.suggestion_results
    summary = results["summary"]

    st.markdown("---")
    st.markdown('<p class="section-title"><span class="step-badge">STEP 4</span>&nbsp; Missing Benefits Analysis</p>',
                unsafe_allow_html=True)

    # Summary metrics
    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("Goals Analysed",           summary["total_goals"])
    mc2.metric("Goals with Missing Items", summary["goals_with_missing_benefits"])
    mc3.metric("Total Missing Benefits",   summary["total_missing_benefits"])

    st.markdown("")

    for gr in results["goal_results"]:
        missing = gr.get("missing_benefits", [])
        matched = gr.get("matched_library_benefits", [])

        with st.expander(
            f"**{gr['goal_id']}** — {gr['goal_text'][:70]}...  "
            f"({'⚠️ ' + str(len(missing)) + ' missing' if missing else '✅ fully covered'})",
            expanded = len(missing) > 0
        ):
            st.caption(f"🏷️ Archetype: **{gr['archetype']}**")

            if matched:
                st.markdown(f"**✅ Covered benefits ({len(matched)})**")
                for m in matched:
                    st.markdown(
                        f'<div class="matched-card">✅ <strong>{m["benefit_id"]}</strong> — {m["matched_to"]}</div>',
                        unsafe_allow_html=True
                    )

            if missing:
                st.markdown(f"**⚠️ Missing benefits ({len(missing)}) — consider raising these with the executive**")
                for mb in missing:
                    # Type badge
                    type_color = {
                        "Tangible":    "#375E23",
                        "Measurable":  "#1F497D",
                        "Intangible":  "#4B297C"
                    }.get(mb["benefit_type"], "#666")

                    st.markdown(
                        f"""<div class="missing-card">
                        <strong>[{mb['benefit_id']}] {mb['title']}</strong>
                        &nbsp;<span style="background:{type_color};color:white;padding:2px 8px;
                        border-radius:10px;font-size:0.72rem;">{mb['benefit_type']}</span>
                        &nbsp;<span style="color:#888;font-size:0.82rem;">
                        {mb['difficulty_to_realize']} difficulty · {mb['typical_time_horizon']}</span>
                        <br/><br/>
                        <em>{mb['relevance']}</em>
                        </div>""",
                        unsafe_allow_html=True
                    )

                    tab_details, tab_metrics, tab_followup = st.tabs(["📋 Details", "📊 Metrics", "💬 Follow-up Question"])

                    with tab_details:
                        st.markdown(f"**Measurement approach:** {mb['measurement_approach']}")
                        if mb.get("qualitative_indicators"):
                            st.markdown("**Qualitative indicators:**")
                            for qi in mb["qualitative_indicators"]:
                                st.markdown(f"- {qi}")

                    with tab_metrics:
                        if mb.get("example_metrics"):
                            for m in mb["example_metrics"]:
                                st.markdown(
                                    f'<span class="metric-pill">📏 {m["unit"]}: {m["example"]}</span>',
                                    unsafe_allow_html=True
                                )
                        else:
                            st.caption("No quantitative benchmarks available for this benefit yet.")

                    with tab_followup:
                        fq = mb.get("follow_up_question", "")
                        st.markdown(f"**Suggested question for your next executive session:**")
                        st.info(f'💬 "{fq}"')
                        if st.button("📋 Copy", key=f"copy_{mb['benefit_id']}_{gr['goal_id']}"):
                            st.write(fq)

    # ── Export ──────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown('<p class="section-title"><span class="step-badge">STEP 5</span>&nbsp; Export</p>',
                unsafe_allow_html=True)

    export_data = {
        "project":  st.session_state.project_name,
        "industry": st.session_state.industry,
        "extraction": st.session_state.extraction,
        "review":   st.session_state.review,
        "archetypes_by_goal": st.session_state.archetypes_by_goal,
        "suggestion_results": st.session_state.suggestion_results
    }

    col_exp1, col_exp2 = st.columns(2)
    with col_exp1:
        st.download_button(
            label     = "⬇️ Download Full Session (JSON)",
            data      = json.dumps(export_data, indent=2),
            file_name = f"scopeboard_{st.session_state.project_name.replace(' ','_')}.json",
            mime      = "application/json",
            use_container_width = True
        )
    with col_exp2:
        st.info(
            "📄 **Word/PDF report export** coming in the next prototype sprint. "
            "For now, use the JSON export to share session data with your team."
        )

    st.session_state.step = 5
