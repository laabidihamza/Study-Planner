# app.py - Streamlit Application
import streamlit as st
from streamlit_mermaid import st_mermaid
import uuid
import os
import re
from dotenv import load_dotenv
from backend.gemini_client import GeminiClient

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), 'backend', '.env')
load_dotenv(env_path)

# Page configuration
st.set_page_config(
    page_title="AI Study Planner",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "gemini_client" not in st.session_state:
    try:
        st.session_state.gemini_client = GeminiClient()
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.session_state.settings = {
            "duration": "3 weeks",
            "current_level": "Beginner",
            "study_field": ""
        }
        # Check if database is initialized
        st.session_state.db_initialized = st.session_state.gemini_client.use_database
    except Exception as e:
        st.error(f"Error initializing AI client: {str(e)}")
        st.stop()

# Show database status warning if needed (only once per session)
if not st.session_state.get("db_initialized", False) and not st.session_state.get("db_warning_shown", False):
    st.warning(
        "⚠️ **Database not connected**: Conversation history won't be saved between sessions. "
        "To enable persistence, set up your Supabase database by running the SQL script "
        "from `supabase_schema.sql` in your Supabase SQL Editor. See README.md for details."
    )
    st.session_state.db_warning_shown = True

# Sidebar for settings
with st.sidebar:
    st.header("⚙️ Study Settings")
    
    # Study Field
    study_field = st.text_input(
        "Study Field/Topic",
        value=st.session_state.settings.get("study_field", ""),
        placeholder="e.g., Java Programming, Python, Machine Learning",
        help="Enter the subject or topic you want to study"
    )
    
    # Current Level
    current_level = st.selectbox(
        "Current Level",
        ["Beginner", "Intermediate", "Advanced"],
        index=["Beginner", "Intermediate", "Advanced"].index(
            st.session_state.settings.get("current_level", "Beginner")
        ),
        help="Select your current proficiency level"
    )
    
    # Duration
    duration = st.selectbox(
        "Study Duration",
        ["1 week", "2 weeks", "3 weeks", "1 month", "2 months", "3 months", "6 months", "Custom"],
        index=["1 week", "2 weeks", "3 weeks", "1 month", "2 months", "3 months", "6 months", "Custom"].index(
            st.session_state.settings.get("duration", "3 weeks")
        ) if st.session_state.settings.get("duration", "3 weeks") in ["1 week", "2 weeks", "3 weeks", "1 month", "2 months", "3 months", "6 months"] else 7,
        help="Select your desired study timeline"
    )
    
    # Custom duration input
    if duration == "Custom":
        custom_duration = st.text_input(
            "Custom Duration",
            placeholder="e.g., 5 weeks, 10 days",
            help="Enter a custom duration"
        )
        if custom_duration:
            duration = custom_duration
    
    # Update settings
    st.session_state.settings = {
        "duration": duration,
        "current_level": current_level,
        "study_field": study_field
    }
    
    st.divider()
    
    # Reset conversation button
    if st.button("🔄 Reset Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.gemini_client.reset_conversation()
        st.rerun()
    
    st.divider()
    st.caption("💡 **Tip:** Adjust your settings before asking for a study plan to get personalized recommendations!")

# Main chat interface
st.title("📚 AI Study Planner")
st.markdown("Your intelligent study planning assistant powered by Gemini 2.5 Flash")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask for a study plan or ask questions about your learning journey..."):
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                # Get response with user settings
                response = st.session_state.gemini_client.chat(
                    prompt,
                    session_id=st.session_state.session_id,
                    user_settings=st.session_state.settings
                )
                
                # Process response to handle Mermaid diagrams
                # Extract Mermaid diagrams - handle multiple formats
                mermaid_pattern = r'```mermaid\s*\n(.*?)\n```'
                mermaid_diagrams = re.findall(mermaid_pattern, response, re.DOTALL)
                
                # Also try alternative format with space
                if not mermaid_diagrams:
                    mermaid_pattern = r'```\s*mermaid\s*\n(.*?)\n```'
                    mermaid_diagrams = re.findall(mermaid_pattern, response, re.DOTALL)
                
                # Save roadmap if one was generated
                if mermaid_diagrams and st. session_state.gemini_client.use_database:
                  try:
                    # Extract title from user message or use default
                    roadmap_title = prompt[: 50] + "..." if len(prompt) > 50 else prompt
                    st.session_state. gemini_client.save_roadmap(roadmap_title, mermaid_diagrams[0])
                  except Exception as e: 
                    st.warning(f"Could not save roadmap: {e}")
                
                # Remove Mermaid code blocks from response for cleaner display
                response_without_mermaid = re.sub(r'```\s*mermaid\s*\n.*?\n```', '', response, flags=re.DOTALL)
                
                # Display Mermaid diagrams first if any exist
                if mermaid_diagrams:
                    st.subheader("📊 Study Roadmap Diagram")
                    st.markdown("---")
                    for idx, diagram in enumerate(mermaid_diagrams):
                        # Clean up the diagram code
                        diagram_clean = diagram.strip()
                        
                        # Display the Mermaid diagram using st_mermaid
                        try:
                            st_mermaid(diagram_clean, height=500)
                        except Exception as e:
                            st.warning(f"Could not render diagram {idx+1}. Showing code instead.")
                            st.code(diagram_clean, language="mermaid")
                        
                        # Also show the code for reference
                        with st.expander(f"📝 View Diagram Code {idx+1}"):
                            st.code(diagram_clean, language="mermaid")
                    
                    st.markdown("---")
                
                # Display response text after diagrams
                st.markdown(response_without_mermaid)
                
                # Add assistant response to messages
                st.session_state.messages.append({"role": "assistant", "content": response})
                
            except Exception as e:
                error_message = f"Error: {str(e)}"
                st.error(error_message)
                st.session_state.messages.append({"role": "assistant", "content": error_message})

# Progress Tracking Section
if st.session_state.get("db_initialized", False):
    st.divider()
    st.header("📈 Learning Progress Tracker")
    
    try:
        roadmaps = st.session_state.gemini_client.get_roadmaps()
        
        if roadmaps:
            # Roadmap selector
            roadmap_options = {rm["id"]: rm["title"] for rm in roadmaps}
            selected_roadmap_id = st.selectbox(
                "Select a roadmap to track progress:",
                options=list(roadmap_options.keys()),
                format_func=lambda x: roadmap_options[x],
                key="roadmap_selector"
            )
            
            if selected_roadmap_id:
                # Get progress data
                progress_data = st.session_state.gemini_client.get_roadmap_progress(selected_roadmap_id)
                
                # Progress overview
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Items", progress_data["total_items"])
                with col2:
                    st.metric("Completed", progress_data["completed_items"])
                with col3:
                    st.metric("Progress", f"{progress_data['progress_percentage']:.1f}%")
                
                # Progress bar
                st.progress(progress_data["progress_percentage"] / 100)
                
                # Items checklist
                st.subheader("📝 Roadmap Items")
                for item in progress_data["items"]:
                    completed = item.get("completed", False)
                    item_title = item.get("title", "Unknown")
                    
                    # Checkbox for completion
                    new_completed = st.checkbox(
                        item_title,
                        value=completed,
                        key=f"item_{item['id']}"
                    )
                    
                    # Update progress if changed
                    if new_completed != completed:
                        success = st.session_state.gemini_client.update_item_progress(item["id"], new_completed)
                        if success:
                            st.success(f"✅ Updated: {item_title}")
                            st.rerun()  # Refresh to show updated progress
                        else:
                            st.error(f"❌ Failed to update: {item_title}")
        else:
            st.info("📚 No roadmaps found. Generate a study plan to start tracking progress!")
            
    except Exception as e:
        st.error(f"Error loading progress tracker: {e}")

# Footer
st.divider()
st.caption("🔍 Use 'search:' or '/search' prefix to search the web for resources")

