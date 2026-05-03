"""
Hook Mining Engine — Streamlit Dashboard
Run: streamlit run dashboard.py
"""

import traceback
import streamlit as st
import pandas as pd
import plotly.express as px
from database import get_stats, get_all_patterns, get_all_generated_posts, get_pipeline_runs
from generator import generate_posts
from pipeline import run_pipeline
from ai_client import active_provider

st.set_page_config(page_title="Hook Mining Engine", page_icon="🪝", layout="wide")

st.title("🪝 Hook Mining Engine")
st.caption("Crawl viral posts → Extract hook patterns → Generate posts for Pixii")

# --- Sidebar ---
with st.sidebar:
    st.header("Controls")

    # Show active AI provider
    provider = active_provider()
    if provider == "None":
        st.error("⚠️ No AI API key found. Add GROQ_API_KEY or GEMINI_API_KEY to Secrets.")
    else:
        st.success(f"✅ AI: {provider}")

    if st.button("🚀 Run Full Pipeline", use_container_width=True):
        try:
            from crawler import crawl_all
            from analyzer import analyze_hooks
            from database import save_viral_posts, save_hook_patterns, start_pipeline_run, finish_pipeline_run, clear_patterns

            clear_patterns()
            run_id = start_pipeline_run()

            with st.spinner("Step 1/3: Crawling posts..."):
                posts = crawl_all()
                saved = save_viral_posts(posts)
            st.info(f"✅ Crawled {len(posts)} posts")

            with st.spinner("Step 2/3: Analyzing hooks with AI..."):
                patterns = analyze_hooks(posts)
                post_ids = [p["id"] for p in posts[:30]]
                new_p = save_hook_patterns(patterns, post_ids)
            st.info(f"✅ Found {len(patterns)} patterns ({new_p} new)")

            with st.spinner("Step 3/3: Generating Pixii posts..."):
                gen_twitter = generate_posts(count=5, platform="twitter")
                gen_linkedin = generate_posts(count=3, platform="linkedin")
            total_generated = len(gen_twitter) + len(gen_linkedin)

            finish_pipeline_run(run_id, saved, len(patterns), total_generated)
            st.success(f"🎉 Done! {saved} posts crawled, {len(patterns)} patterns, {total_generated} posts generated.")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Failed at this step: {e}")
            st.code(traceback.format_exc())

    st.divider()
    st.subheader("Quick Generate")
    platform = st.selectbox("Platform", ["twitter", "linkedin", "instagram"])
    count = st.slider("Number of posts", 1, 10, 5)
    if st.button("✍️ Generate Posts", use_container_width=True):
        try:
            with st.spinner("Generating..."):
                posts = generate_posts(count=count, platform=platform)
            st.success(f"Generated {len(posts)} posts!")
            st.rerun()
        except Exception as e:
            st.error(f"Generation failed: {e}")
            st.code(traceback.format_exc())

# --- Stats ---
stats = get_stats()
col1, col2, col3, col4 = st.columns(4)
col1.metric("Posts Crawled", stats["total_posts_crawled"])
col2.metric("Hook Patterns", stats["total_patterns"])
col3.metric("Posts Generated", stats["total_generated"])
col4.metric("Pipeline Runs", stats["total_runs"])

# --- Tabs ---
tab1, tab2, tab3, tab4 = st.tabs(["📚 Hook Library", "✍️ Generated Posts", "📊 Analytics", "🔄 Pipeline Runs"])

with tab1:
    st.subheader("Hook Pattern Library")
    patterns = get_all_patterns()
    if patterns:
        df = pd.DataFrame(patterns)
        display_cols = ["pattern_name", "category", "description", "example", "frequency", "first_seen", "last_seen"]
        available_cols = [c for c in display_cols if c in df.columns]
        st.dataframe(df[available_cols], use_container_width=True, hide_index=True)

        categories = df["category"].value_counts()
        fig = px.pie(values=categories.values, names=categories.index, title="Patterns by Category")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No patterns yet. Run the pipeline to start mining hooks!")

with tab2:
    st.subheader("Generated Pixii Posts")
    posts = get_all_generated_posts()
    if posts:
        for post in posts:
            with st.container(border=True):
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    st.markdown(post["content"])
                with col_b:
                    st.caption(f"Hook: {post.get('pattern_name', 'N/A')}")
                    st.caption(f"Platform: {post.get('platform', 'N/A')}")
                    st.caption(f"Created: {post.get('created_at', '')[:10]}")
    else:
        st.info("No posts generated yet. Use the sidebar to generate some!")

with tab3:
    st.subheader("Analytics")
    patterns = get_all_patterns()
    if patterns:
        df = pd.DataFrame(patterns)

        fig_freq = px.bar(
            df.nlargest(15, "frequency"),
            x="pattern_name", y="frequency",
            title="Top 15 Hook Patterns by Frequency",
            color="category",
        )
        fig_freq.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_freq, use_container_width=True)

        fig_cat = px.histogram(df, x="category", title="Pattern Distribution by Category", color="category")
        st.plotly_chart(fig_cat, use_container_width=True)
    else:
        st.info("Run the pipeline to see analytics.")

with tab4:
    st.subheader("Pipeline Run History")
    runs = get_pipeline_runs()
    if runs:
        df_runs = pd.DataFrame(runs)
        st.dataframe(df_runs, use_container_width=True, hide_index=True)
    else:
        st.info("No pipeline runs yet.")
