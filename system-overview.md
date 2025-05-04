# Multi-Agent Chatbot System Documentation

## System Overview

This document provides a comprehensive breakdown of the multi-agent chatbot system built with Streamlit, explaining the purpose of each component and how they interact.

## Key Features

- Multiple AI assistants (agents) with different personalities and expertise
- User authentication system with role-based access control
- Persistent chat history stored in PostgreSQL database
- Agent recommendation system based on query content
- Administrative dashboard for system management
- Support for multiple conversations with each agent

## Core Components

### 1. Database Layer

The system uses PostgreSQL (Neon.tech) with SQLAlchemy ORM for data persistence:

- **User Model**: Stores user accounts with username, password, and role
- **Agent Model**: Stores AI assistant profiles with name, description, and system prompt
- **ChatHistory Model**: Stores conversations between users and agents
- **Config Model**: Stores system-wide configuration like API keys

### 2. Authentication System

Manages user sessions and access control:

- Login/registration interface
- Role-based access (admin vs. regular users)
- Session management with Streamlit session state

### 3. Chat Interface

The primary user-facing component:

- Agent selection via sidebar
- Conversation display with formatted messages
- Multiple conversation support for each agent
- Immediate message display with async processing

### 4. Agent Communication

Handles interaction with OpenAI's API:

- Retrieves API keys from configuration
- Formats and sends messages to OpenAI
- Processes and displays responses
- Provides fallbacks for API errors

### 5. RAG System (Retrieval Augmented Generation)

Intelligent agent recommendation based on query content:

- Uses TF-IDF vectorization to match queries to agents
- Analyzes agent descriptions and system prompts
- Recommends the most suitable agent for each query

### 6. Administration Dashboard

Provides system management capabilities for admin users:

- User management (add, update, import/export)
- Agent management (create, edit, update)
- Chat history viewing and export
- System configuration

## Technical Architecture

### Data Flow

1. **Authentication Flow**:
   - User provides credentials
   - System verifies against database
   - Session state is updated with user info
   - Chat history is loaded for the user

2. **Chat Flow**:
   - User selects an agent and enters a message
   - Message immediately appears in the chat
   - Message is processed by the OpenAI API
   - Response is added to chat history
   - Chat history is saved to database

3. **Admin Flow**:
   - Admin user navigates to admin dashboard
   - System loads relevant data from database
   - Admin makes changes via the interface
   - Changes are saved to database
   - Relevant systems are updated (e.g., RAG system)

### File Structure and Purpose

1. **app.py**: Main application file that initializes the Streamlit interface and coordinates the other components

2. **models.py**: Defines database models and connection handling

3. **db_manager.py**: Provides functions for database operations with error handling

4. **auth.py**: Manages user authentication and session state

5. **agent.py**: Handles communication with the OpenAI API

6. **chat.py**: Manages chat display and formatting

7. **rag_system.py**: Implements agent recommendation logic

8. **admin.py**: Provides administration interface and functions

9. **csv_helper.py**: Handles CSV import/export for users and chat history

## Deployment Requirements

1. **Environment Variables**:
   - PostgreSQL connection details (NEON_DB_*)
   - OpenAI API key

2. **Dependencies**:
   - Streamlit for web interface
   - SQLAlchemy and psycopg2 for database
   - OpenAI for AI capabilities
   - Other Python libraries (see requirements.txt)

3. **Initialization**:
   - Database setup with default admin user
   - Initial agent configurations

## Usage Guide

### Regular Users

1. Register or log in to access the system
2. Select an agent from the sidebar
3. Start a new conversation or continue a previous one
4. Enter messages and receive responses
5. Configure OpenAI API key if prompted

### Administrators

1. Log in with admin credentials
2. Navigate to the Admin dashboard
3. Manage users, agents, and system configuration
4. View and export chat history
5. Enable debug mode for troubleshooting

## Recommendations for Enhancement

1. Implement more robust error handling for API rate limits
2. Add message encryption for better security
3. Implement user preference storage
4. Add support for file uploads in conversations
5. Create a more sophisticated agent recommendation system
6. Implement conversation search functionality