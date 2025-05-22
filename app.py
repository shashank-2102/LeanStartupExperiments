import streamlit as st
import os
import db_manager
import auth
import chat
import agent as agent_module
import admin
import rag_system
from models import setup_database
import traceback
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set page configuration
st.set_page_config(
    page_title="Multi-Agent Chatbot System",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state with all required variables
def initialize_session_state():
    """Initialize all session state variables to prevent KeyError"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "username" not in st.session_state:
        st.session_state.username = None
    if "role" not in st.session_state:
        st.session_state.role = None
    if "page" not in st.session_state:
        st.session_state.page = "chat"
    if "current_agent" not in st.session_state:
        st.session_state.current_agent = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = {}
    if "unified_chat_history" not in st.session_state:
        st.session_state.unified_chat_history = {}
    if "show_agent_recommendation" not in st.session_state:
        st.session_state.show_agent_recommendation = False
    if "show_api_key_panel" not in st.session_state:
        st.session_state.show_api_key_panel = False
    if "debug_mode" not in st.session_state:
        st.session_state.debug_mode = False
    if "waiting_for_response" not in st.session_state:
        st.session_state.waiting_for_response = False
    if "new_message" not in st.session_state:
        st.session_state.new_message = None
    if "current_conversation_id" not in st.session_state:
        st.session_state.current_conversation_id = {}
    if "agent_switch_suggestion" not in st.session_state:
        st.session_state.agent_switch_suggestion = None
    if "last_query" not in st.session_state:
        st.session_state.last_query = ""
    if "unified_conversation_id" not in st.session_state:
        st.session_state.unified_conversation_id = None

# Initialize session state
initialize_session_state()

# Initialize the database
try:
    setup_database()
except Exception as e:
    st.error(f"Error setting up database: {e}")
    st.info("Please make sure the database credentials are correctly set in the environment variables.")
    st.code(traceback.format_exc())

# Application header and sidebar
def render_sidebar():
    with st.sidebar:
        st.title("🤖 Multi-Agent Chat")
        
        if st.session_state.authenticated:
            st.write(f"Welcome, **{st.session_state.username}**!")
            
            # Navigation
            st.subheader("Navigation")
            nav_options = ["Chat"]
            
            # Add admin page for admin users
            if st.session_state.role == "admin":
                nav_options.append("Admin")
                
            selected_page = st.radio("Go to", nav_options)
            
            if selected_page == "Chat":
                st.session_state.page = "chat"
            elif selected_page == "Admin":
                st.session_state.page = "admin"
            
            # Agent selection and conversation management
            if st.session_state.page == "chat":
                st.subheader("Current Agent")
                agents = db_manager.get_agents()
                
                if agents:
                    agent_names = [agent["name"] for agent in agents]
                    
                    # Agent selection
                    current_agent = st.selectbox(
                        "Active Assistant:",
                        agent_names,
                        index=agent_names.index(st.session_state.current_agent) if st.session_state.current_agent in agent_names else 0,
                        help="Switch agents within the same conversation"
                    )
                    
                    if current_agent != st.session_state.current_agent:
                        st.session_state.current_agent = current_agent
                        st.rerun()
                    
                    # Display current agent info
                    selected_agent = next((a for a in agents if a["name"] == current_agent), None)
                    if selected_agent:
                        with st.expander("ℹ️ Agent Info", expanded=False):
                            st.write(f"**{selected_agent['description']}**")
                            try:
                                expertise = rag_system.get_agent_expertise_summary(current_agent)
                                st.caption(f"Expertise: {expertise}")
                            except:
                                st.caption("Specialized assistant")
                    
                    # Agent switch suggestion panel
                    if st.session_state.agent_switch_suggestion:
                        with st.container():
                            suggestion = st.session_state.agent_switch_suggestion
                            st.info(f"💡 **Agent Recommendation**\n\n"
                                   f"**{suggestion['recommended_agent']}** might be better suited for your query.\n\n"
                                   f"Confidence: {suggestion['confidence']:.1%}")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("🔄 Switch Agent", use_container_width=True):
                                    st.session_state.current_agent = suggestion['recommended_agent']
                                    st.session_state.agent_switch_suggestion = None
                                    st.success(f"Switched to {suggestion['recommended_agent']}")
                                    st.rerun()
                            with col2:
                                if st.button("❌ Keep Current", use_container_width=True):
                                    st.session_state.agent_switch_suggestion = None
                                    st.rerun()
                    
                    # Unified conversation management
                    st.subheader("Conversations")
                    
                    # New conversation button
                    if st.button("✨ New Conversation", use_container_width=True):
                        new_id = generate_conversation_id()
                        st.session_state.unified_conversation_id = new_id
                        st.session_state.unified_chat_history[new_id] = []
                        st.rerun()
                    
                    # List of existing conversations (unified across all agents)
                    try:
                        conversations = db_manager.get_unified_conversations(st.session_state.username)
                    except:
                        # Fallback to old method if new method not available
                        conversations = db_manager.get_conversations(st.session_state.username)

                    if conversations:
                        st.write("**Recent Conversations:**")
                        
                        for idx, conv in enumerate(conversations[:10]):  # Show latest 10 conversations
                            # Format date and show preview
                            created_date = conv.get('created_at', 'Unknown date')
                            if isinstance(created_date, str) and len(created_date) > 16:
                                try:
                                    from datetime import datetime
                                    dt = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                                    created_date = dt.strftime('%d-%m-%y %H:%M')
                                except:
                                    created_date = created_date[:16].replace('T', ' ')
                            
                            # Create conversation label with multi-agent indicator
                            msg_count = conv.get('message_count', 0)
                            preview = conv.get('preview', 'No preview')
                            agents_used = conv.get('agents_used', [])
                            is_multi_agent = conv.get('multi_agent', False) or len(agents_used) > 1
                            
                            # Multi-agent indicator
                            agent_indicator = "🔄" if is_multi_agent else "🤖"
                            agents_text = f" ({', '.join(agents_used[:2])}{'...' if len(agents_used) > 2 else ''})" if agents_used else ""
                            
                            conv_label = f"{agent_indicator} {created_date}"
                            conv_help = f"{preview}\n{msg_count} messages{agents_text}"
                            
                            if st.button(conv_label, key=f"conv_{idx}", help=conv_help, use_container_width=True):
                                st.session_state.unified_conversation_id = conv['conversation_id']
                                # Load the conversation
                                load_conversation(conv['conversation_id'])
                                st.rerun()
                        
                        # Show more button if there are more conversations
                        if len(conversations) > 10:
                            if st.button(f"📋 Show {len(conversations) - 10} more...", use_container_width=True):
                                # Could implement pagination here
                                pass
                        
                    # Agent recommendations toggle
                    st.session_state.show_agent_recommendation = st.toggle(
                        "🔄 Auto Agent Switching",
                        value=st.session_state.show_agent_recommendation,
                        help="Automatically switch to the best agent for each query"
                    )
                    
                    # Manual agent recommendations
                    if st.session_state.last_query and st.button("🔍 Find Best Agent", use_container_width=True):
                        try:
                            recommendations = rag_system.get_agent_recommendations(
                                st.session_state.last_query, 
                                top_n=3, 
                                exclude_current=st.session_state.current_agent
                            )
                            if recommendations:
                                st.write("**Recommended agents:**")
                                for i, agent in enumerate(recommendations[:3]):
                                    if st.button(f"🔄 Switch to {agent}", key=f"rec_{i}", use_container_width=True):
                                        st.session_state.current_agent = agent
                                        st.success(f"Switched to {agent}")
                                        st.rerun()
                        except Exception as e:
                            st.error(f"Error getting recommendations: {e}")
                else:
                    st.error("No agents found. Please contact an administrator.")
            
            # API Key Configuration Section
            st.subheader("⚙️ Configuration")
            api_key_button = st.button("🔑 OpenAI API Key", use_container_width=True)
            if api_key_button:
                st.session_state.show_api_key_panel = not st.session_state.show_api_key_panel
            
            # Debug mode toggle (for admins only)
            if st.session_state.role == "admin":
                st.session_state.debug_mode = st.toggle(
                    "🐛 Debug Mode", 
                    value=st.session_state.debug_mode,
                    help="Enable debug information"
                )
            
            # Logout button
            st.markdown("---")
            if st.button("🚪 Logout", use_container_width=True):
                auth.logout()
                st.rerun()
        else:
            st.info("Please login or register to continue.")

def load_conversation(conversation_id):
    """Load a specific conversation into the session state"""
    try:
        # Try new unified method first
        conversation_data = db_manager.load_conversation_by_id(
            st.session_state.username, 
            conversation_id
        )
        
        if conversation_data:
            st.session_state.unified_chat_history[conversation_id] = conversation_data['messages']
        else:
            st.session_state.unified_chat_history[conversation_id] = []
    except:
        # Fallback to old method
        try:
            chat_history = db_manager.load_chat_history(st.session_state.username)
            if conversation_id in chat_history:
                st.session_state.unified_chat_history[conversation_id] = chat_history[conversation_id].get('messages', [])
            else:
                st.session_state.unified_chat_history[conversation_id] = []
        except Exception as e:
            st.error(f"Error loading conversation: {e}")
            st.session_state.unified_chat_history[conversation_id] = []

def process_message_with_agent_switching(user_input, chat_history, conversation_id):
    """Process user input with intelligent agent switching"""
    
    # Store the query for potential agent recommendations
    st.session_state.last_query = user_input
    
    # Add user message to chat history first
    user_message = {"role": "user", "content": user_input}
    chat_history.append(user_message)
    
    try:
        # Check if we should automatically switch agents
        if st.session_state.show_agent_recommendation:
            try:
                should_switch, recommended_agent, confidence = rag_system.should_switch_agent(
                    user_input, 
                    st.session_state.current_agent,
                    threshold=0.10
                )
                
                # Automatically switch to the recommended agent if confidence is high enough
                if should_switch and recommended_agent != st.session_state.current_agent:
                    old_agent = st.session_state.current_agent
                    st.session_state.current_agent = recommended_agent
                    
                    # Add a system message to show the switch happened
                    system_message = {
                        "role": "system",
                        "content": f"🔄 **Automatically switched from {old_agent} to {recommended_agent}** (Confidence: {confidence:.1%})",
                        "agent": "System"
                    }
                    chat_history.append(system_message)
                    
                    # Optional: Show notification in the UI
                    if hasattr(st, 'toast'):
                        st.toast(f"🔄 Switched to {recommended_agent}", icon="🤖")
                    
            except Exception as e:
                if st.session_state.debug_mode:
                    st.warning(f"Auto-switch error: {e}")
        
        # Get current agent info (might have changed due to auto-switch)
        agents = db_manager.get_agents()
        agent_info = next((a for a in agents if a["name"] == st.session_state.current_agent), None)
        
        if agent_info:
            system_prompt = agent_info["system_prompt"]
            
            # Set waiting flag
            st.session_state.waiting_for_response = True
            
            # Get response from current agent
            try:
                response = agent_module.get_agent_response(
                    user_input, 
                    system_prompt, 
                    chat_history,
                    current_agent_name=st.session_state.current_agent
                )
            except:
                # Fallback to old method
                response = agent_module.get_agent_response(user_input, system_prompt, chat_history)
            
            # Add agent response with agent information
            assistant_message = {
                "role": "assistant", 
                "content": response,
                "agent": st.session_state.current_agent
            }
            chat_history.append(assistant_message)
            
            # Save unified chat history
            if st.session_state.authenticated and st.session_state.username:
                try:
                    # Try new unified save method
                    save_success = db_manager.save_unified_chat_history(
                        st.session_state.username,
                        conversation_id,
                        chat_history
                    )
                except:
                    # Fallback to old method
                    save_success = db_manager.save_chat_history(
                        st.session_state.username,
                        st.session_state.current_agent,
                        conversation_id,
                        chat_history
                    )
                
                if st.session_state.debug_mode and not save_success:
                    st.warning("Failed to save chat history to database")
            
            # Reset waiting flag
            st.session_state.waiting_for_response = False
            
            return None
            
    except Exception as e:
        # Add error message to chat history
        error_message = f"I'm sorry, I encountered an error: {str(e)}"
        error_msg = {
            "role": "assistant", 
            "content": error_message,
            "agent": st.session_state.current_agent
        }
        chat_history.append(error_msg)
        
        # Reset waiting flag
        st.session_state.waiting_for_response = False
        
        if st.session_state.debug_mode:
            return traceback.format_exc()
        
        return None

def generate_conversation_id():
    """Generate a unique conversation ID"""
    import uuid
    return str(uuid.uuid4())

# Main application
def main():
    render_sidebar()
    
    if not st.session_state.authenticated:
        # Show authentication page
        auth.show_auth_page()
    else:
        # Show page based on selection
        if st.session_state.page == "chat":
            render_enhanced_chat_page()
        elif st.session_state.page == "admin" and st.session_state.role == "admin":
            admin.show_admin_page()
        else:
            st.warning("Page not found or access denied.")

def render_enhanced_chat_page():
    # Header with current agent and conversation info
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        st.title(f"💬 Chat with {st.session_state.current_agent}")
    
    with col2:
        if st.session_state.unified_conversation_id:
            st.caption(f"📝 Conversation: {st.session_state.unified_conversation_id[:8]}...")
    
    with col3:
        # Quick agent switch buttons for top 3 recommended agents
        if st.session_state.last_query:
            with st.popover("🔄 Quick Switch"):
                st.write("**Recommended for your last query:**")
                try:
                    recommendations = rag_system.get_agent_recommendations(
                        st.session_state.last_query, 
                        top_n=3, 
                        exclude_current=st.session_state.current_agent
                    )
                    for agent in recommendations[:3]:
                        if st.button(f"➡️ {agent}", key=f"quick_{agent}"):
                            st.session_state.current_agent = agent
                            st.rerun()
                except:
                    st.write("No recommendations available")
    
    # API Key Configuration Panel
    if st.session_state.show_api_key_panel:
        with st.expander("🔑 OpenAI API Key Configuration", expanded=True):
            st.warning("⚠️ You need to configure an OpenAI API key to use this chatbot.")
            
            config = db_manager.get_config()
            current_api_key = config.get("openai_api_key", "")
            api_key_placeholder = "****************************" if current_api_key else "No API key set"
            
            st.text_input("Current API Key", value=api_key_placeholder, disabled=True)
            new_api_key = st.text_input("New API Key", type="password", 
                                       help="Get your key from https://platform.openai.com/api-keys")
            
            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button("💾 Save"):
                    if new_api_key:
                        try:
                            config["openai_api_key"] = new_api_key
                            db_manager.update_config(config)
                            st.success("API key updated!")
                            st.session_state.show_api_key_panel = False
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
            with col2:
                if st.button("❌ Close"):
                    st.session_state.show_api_key_panel = False
                    st.rerun()
    
    # Initialize conversation if needed
    if not st.session_state.unified_conversation_id:
        st.session_state.unified_conversation_id = generate_conversation_id()
    
    current_conv_id = st.session_state.unified_conversation_id
    
    # Initialize unified chat history
    if current_conv_id not in st.session_state.unified_chat_history:
        # Try to load from database
        try:
            load_conversation(current_conv_id)
        except Exception as e:
            if st.session_state.debug_mode:
                st.error(f"Error loading conversation: {e}")
            st.session_state.unified_chat_history[current_conv_id] = []
    
    # Get current conversation messages
    chat_history = st.session_state.unified_chat_history[current_conv_id]
    
    # Create chat container
    chat_container = st.container()
    
    # Display chat messages with agent indicators
    with chat_container:
        display_enhanced_chat_messages(chat_history)
        
        # Show thinking indicator with spinner - this appears in real-time
        if st.session_state.waiting_for_response:
            with st.chat_message("assistant", avatar="🤖"):
                # Show agent name and thinking indicator
                st.caption(f"🤖 **{st.session_state.current_agent}**")
                with st.spinner(""):
                    st.write("🤔 Thinking...")
                    # Force the UI to update immediately
                    time.sleep(0.1)
    
    # Agent switch notification
    if st.session_state.agent_switch_suggestion and not st.session_state.waiting_for_response:
        suggestion = st.session_state.agent_switch_suggestion
        st.info(f"💡 **{suggestion['recommended_agent']}** might handle your query better. "
               f"Check the sidebar to switch agents or continue with {st.session_state.current_agent}.")
    
    # Debug information
    if st.session_state.debug_mode and st.session_state.role == "admin":
        with st.expander("🐛 Debug Information", expanded=False):
            st.subheader("Session Info")
            st.json({
                "username": st.session_state.username,
                "current_agent": st.session_state.current_agent,
                "conversation_id": current_conv_id,
                "messages_count": len(chat_history),
                "agent_switch_suggestion": st.session_state.agent_switch_suggestion
            })
            
            st.subheader("Chat History")
            st.json(chat_history)
    
    # Process new message if exists
    if st.session_state.new_message is not None:
        debug_info = process_message_with_agent_switching(
            st.session_state.new_message, 
            chat_history, 
            current_conv_id
        )
        
        st.session_state.new_message = None
        
        if debug_info and st.session_state.debug_mode:
            st.error("Debug Error Info:")
            st.code(debug_info)
        
        st.rerun()
    
    # Chat input
    user_input = st.chat_input("Type your message here...")
    
    if user_input:
        # Immediately show the user message and set waiting state
        st.session_state.new_message = user_input
        st.session_state.waiting_for_response = True
        st.rerun()

def display_enhanced_chat_messages(messages):
    """Display chat messages with agent indicators"""
    if not messages:
        st.info("👋 Start a conversation! You can switch agents anytime during our chat.")
        return
    
    for message in messages:
        # Determine the role and agent
        role = message.get("role", "user")
        content = message.get("content", "")
        agent_name = message.get("agent", "Unknown Agent")
        
        if role == "system":
            # Show system messages (like agent switches) with special styling
            st.info(content)
        elif role == "assistant":
            # Show which agent responded
            with st.chat_message("assistant", avatar="🤖"):
                # Agent indicator
                st.caption(f"🤖 **{agent_name}**")
                chat.format_message_content(content)
        else:
            with st.chat_message("user", avatar="👤"):
                chat.format_message_content(content)

if __name__ == "__main__":
    main()