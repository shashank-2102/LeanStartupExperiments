# Multi-Agent Chatbot System Documentation

## Overview

The Multi-Agent Chatbot System is a Streamlit-based web application that enables users to interact with different AI assistants (agents), each with unique characteristics defined by customizable system prompts. The application features user authentication, persistent chat history, and an administration panel for managing users and agents. It connects to OpenAI's API for generating responses and stores all data in a PostgreSQL database.

## Core Features

- **Multiple AI Personalities**: Chat with different specialized agents
- **User Authentication**: Secure login and registration system
- **Persistent Chat History**: Conversations are saved and can be resumed later
- **Admin Dashboard**: Manage users, agents, and system settings
- **Agent Recommendations**: Suggests the most appropriate agent for specific queries
- **Responsive UI**: Messages appear instantly with visual feedback during processing

## System Architecture

The application follows a modular architecture with clear separation of concerns:

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│   Web UI    │────▶│  Application  │────▶│  Database     │
│  (Streamlit)│◀────│   Logic       │◀────│  (PostgreSQL) │
└─────────────┘     └──────────────┘     └───────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  OpenAI API  │
                    │  (GPT-4o)    │
                    └──────────────┘
```

## Key Components

### 1. Database Models (`models.py`)

This module defines the database schema and handles the connection to the Neon PostgreSQL database:

- **User**: Stores user accounts (username, password, role)
- **Agent**: Stores AI assistant profiles (name, description, system prompt)
- **ChatHistory**: Stores conversations between users and agents
- **Config**: Stores application settings like API keys

The module also handles database initialization and connection management with robust error handling for cloud-based databases.

### 2. Database Manager (`db_manager.py`)

Provides an interface for all database operations with built-in retry mechanisms for handling potential connection issues:

- **User Management**: Functions to get, add, and update users
- **Agent Management**: Functions to get, add, and update agents
- **Chat History**: Functions to save and load conversations
- **Configuration**: Functions to store and retrieve application settings

### 3. Authentication System (`auth.py`)

Manages user authentication with these key functions:

- **Login**: Validates user credentials against the database
- **Registration**: Creates new user accounts with validation
- **Logout**: Clears session state
- **Role-Based Access**: Differentiates between regular users and administrators

### 4. Agent Handler (`agent.py`)

Handles communication with the OpenAI API:

- **API Integration**: Creates the client using the configured API key
- **Message Formatting**: Prepares messages with proper system prompts
- **Response Generation**: Gets completions from the GPT-4o model
- **Error Handling**: Gracefully handles API errors

### 5. Chat Display (`chat.py`)

Manages the display and formatting of chat messages:

- **Message Rendering**: Shows conversations with proper styling
- **Content Formatting**: Handles code blocks and other special content
- **History Management**: Provides functions to clear chat history

### 6. Admin Dashboard (`admin.py`)

Provides administrative functions for system management:

- **Agent Management**: Interface to create, edit, and delete agents
- **User Management**: Interface to edit user roles and reset passwords
- **System Configuration**: Interface to configure the OpenAI API key

### 7. Agent Recommendations (`rag_system.py`)

Implements a Retrieval Augmented Generation (RAG) system to recommend appropriate agents:

- **Text Analysis**: Uses NLP techniques to analyze user queries
- **Agent Matching**: Finds the most suitable agent based on content
- **Knowledge Base**: Maintains a vector representation of agent capabilities

### 8. Main Application (`app.py`)

The central module that ties everything together:

- **UI Rendering**: Creates the Streamlit interface
- **Session Management**: Maintains user state and chat history
- **Message Processing**: Handles the flow of conversations
- **Navigation**: Manages different pages and views

## Data Flow

1. **User Authentication**
   - User enters credentials → `auth.py` verifies with `db_manager.py`
   - On success, chat history is loaded from the database

2. **Agent Selection**
   - User selects an agent from the sidebar
   - Application loads appropriate system prompt and chat history

3. **Conversation Flow**
   - User sends message → Added to UI immediately
   - Background processing with `agent.py` to get AI response
   - Response added to UI and saved to database

4. **Agent Recommendations**
   - When enabled, user messages are analyzed by `rag_system.py`
   - System suggests other appropriate agents for the current query

5. **Administrative Tasks**
   - Admin users access dashboard through `admin.py`
   - Changes to agents, users, or settings update the database
   - Agent changes trigger an update to the recommendation system

## Setup and Deployment

### Environment Variables

The application requires these environment variables:

```
NEON_DB_USER=your_username
NEON_DB_PASSWORD=your_password
NEON_DB_HOST=your_hostname
NEON_DB_NAME=your_database_name
OPENAI_API_KEY=your_openai_api_key
```

### Running with Streamlit

To run the application directly:

```bash
streamlit run app.py
```

### Docker Deployment

For containerized deployment, use the included docker-compose.yml:

```bash
docker-compose up -d
```

## Technical Implementation Details

### Two-Phase Message Processing

The application uses a two-phase approach for processing messages:

1. **Immediate Display**: User messages are added to the UI instantly
2. **Background Processing**: AI response generation happens asynchronously
3. **UI Update**: Interface refreshes when the response is ready

This provides a responsive user experience without waiting for the API.

### Database Resilience

The system implements several techniques to maintain database reliability:

- **Connection Pooling**: Efficiently manages database connections
- **Retry Logic**: Automatically retries failed operations
- **Error Handling**: Gracefully handles temporary connection issues

### Security Features

- **Password-based Authentication**: Secure user login system
- **Role-based Access Control**: Different capabilities for users and admins
- **API Key Security**: Secure storage of OpenAI API keys
- **Environment Variable Management**: Sensitive data kept in environment variables

## Extending the System

The modular architecture makes it easy to extend with new features:

- **New Agent Types**: Add specialized agents by updating the database
- **Additional Authentication Methods**: Enhance `auth.py` with new methods
- **Enhanced Recommendation Engine**: Improve `rag_system.py` with better algorithms
- **More Administrative Features**: Add functionality to `admin.py`

## Troubleshooting

### Database Connection Issues
- Check your environment variables for correct credentials
- Verify network connectivity to the Neon PostgreSQL database
- Enable debug mode as an admin to see detailed error information

### OpenAI API Problems
- Verify your API key is correctly configured
- Check for rate limiting or quota issues
- Look for error messages in the agent response

### UI Response Issues
- If messages don't appear immediately, check browser console for errors
- Verify session state is properly maintaining conversation history
- Check for any Python errors in the terminal running Streamlit
