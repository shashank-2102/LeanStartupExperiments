"""
Enhanced Retrieval Augmented Generation (RAG) System for Multi-Agent Chatbot
This module handles automatic agent assignment and switching within conversations
"""
import nltk
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import db_manager
import re
import os

# Download NLTK resources if not already available
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

# Initialize stop words
stop_words = set(nltk.corpus.stopwords.words('english'))

class EnhancedRAGSystem:
    def __init__(self):
        """Initialize the enhanced RAG system"""
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.agent_vectors = None
        self.agents = []
        self.update_agent_knowledge()
    
    def update_agent_knowledge(self):
        """Update the agent knowledge base from the database"""
        try:
            # Get all agents from the database
            agents = db_manager.get_agents()
            
            if not agents:
                # Default agents if database query fails
                agents = [{
                    "name": "General Assistant",
                    "description": "A helpful assistant that can discuss a wide range of topics.",
                    "system_prompt": "You are a helpful assistant. Answer questions clearly and honestly."
                }]
            
            self.agents = agents
            
            # Create a corpus of agent descriptions and prompts for vectorization
            corpus = []
            for agent in agents:
                # Combine name, description and system prompt for better matching
                agent_text = f"{agent['name']} {agent['description']} {agent['system_prompt']}"
                # Clean text
                agent_text = re.sub(r'[^\w\s]', ' ', agent_text.lower())
                corpus.append(agent_text)
            
            # Vectorize the corpus
            if corpus:
                try:
                    # Reset the vectorizer and fit it with the new corpus
                    self.vectorizer = TfidfVectorizer(stop_words='english')
                    self.agent_vectors = self.vectorizer.fit_transform(corpus)
                    print(f"Enhanced RAG system updated with {len(agents)} agents")
                except Exception as e:
                    print(f"Error vectorizing agent corpus: {e}")
                    self.agent_vectors = None
            else:
                print("No corpus available for vectorization")
                self.agent_vectors = None
        except Exception as e:
            print(f"Error updating agent knowledge: {e}")
            # Set fallback values
            self.agents = [{
                "name": "General Assistant",
                "description": "A helpful assistant that can discuss a wide range of topics.",
                "system_prompt": "You are a helpful assistant. Answer questions clearly and honestly."
            }]
            self.agent_vectors = None
    
    def get_best_agent_for_query(self, query, exclude_current=None):
        """
        Find the most appropriate agent for a given query
        
        Args:
            query (str): The user's query
            exclude_current (str): Current agent name to exclude from recommendations
            
        Returns:
            str: The name of the most appropriate agent
        """
        if not self.agents or self.agent_vectors is None:
            # Return default agent if no agents or vectors
            return "General Assistant"
        
        try:
            # Clean and vectorize the query
            clean_query = re.sub(r'[^\w\s]', ' ', query.lower())
            query_vec = self.vectorizer.transform([clean_query])
            
            # Calculate similarity scores
            similarity_scores = cosine_similarity(query_vec, self.agent_vectors)[0]
            
            # Get sorted indices by similarity score (highest first)
            sorted_indices = similarity_scores.argsort()[::-1]
            
            # Find the best agent that's not the current one
            for idx in sorted_indices:
                agent_name = self.agents[idx]["name"]
                if exclude_current is None or agent_name != exclude_current:
                    return agent_name
            
            # If all agents are excluded, return the highest scoring one
            best_agent_idx = np.argmax(similarity_scores)
            return self.agents[best_agent_idx]["name"]
        except Exception as e:
            print(f"Error finding best agent: {e}")
            # Return default agent in case of error
            if self.agents and len(self.agents) > 0:
                return self.agents[0]["name"]
            return "General Assistant"
    
    def get_agent_recommendations(self, query, top_n=3, exclude_current=None):
        """
        Get the top N recommended agents for a query
        
        Args:
            query (str): The user's query
            top_n (int): Number of recommendations to return
            exclude_current (str): Current agent name to exclude from recommendations
            
        Returns:
            list: List of agent names ordered by relevance
        """
        if not self.agents or self.agent_vectors is None:
            # Return default recommendation if no agents or vectors
            return ["General Assistant"]
        
        try:
            # Clean and vectorize the query
            clean_query = re.sub(r'[^\w\s]', ' ', query.lower())
            query_vec = self.vectorizer.transform([clean_query])
            
            # Calculate similarity scores
            similarity_scores = cosine_similarity(query_vec, self.agent_vectors)[0]
            
            # Get indices of the top N highest similarity scores
            top_indices = similarity_scores.argsort()[::-1]
            
            # Filter out current agent and return names of the top matching agents
            recommendations = []
            for idx in top_indices:
                agent_name = self.agents[idx]["name"]
                if exclude_current is None or agent_name != exclude_current:
                    recommendations.append(agent_name)
                    if len(recommendations) >= top_n:
                        break
            
            return recommendations
        except Exception as e:
            print(f"Error finding agent recommendations: {e}")
            # Return default recommendations in case of error
            if self.agents and len(self.agents) > 0:
                available_agents = [a["name"] for a in self.agents if a["name"] != exclude_current]
                return available_agents[:top_n] if available_agents else [self.agents[0]["name"]]
            return ["General Assistant"]
    
    def should_switch_agent(self, query, current_agent, threshold=0.15):
        """
        Determine if the system should recommend switching agents based on query relevance
        
        Args:
            query (str): The user's query
            current_agent (str): Name of the current agent
            threshold (float): Minimum difference in similarity scores to recommend switch
            
        Returns:
            tuple: (should_switch: bool, recommended_agent: str, confidence: float)
        """
        if not self.agents or self.agent_vectors is None:
            return False, current_agent, 0.0
        
        try:
            # Clean and vectorize the query
            clean_query = re.sub(r'[^\w\s]', ' ', query.lower())
            query_vec = self.vectorizer.transform([clean_query])
            
            # Calculate similarity scores
            similarity_scores = cosine_similarity(query_vec, self.agent_vectors)[0]
            
            # Find current agent index and score
            current_agent_idx = None
            current_agent_score = 0.0
            for i, agent in enumerate(self.agents):
                if agent["name"] == current_agent:
                    current_agent_idx = i
                    current_agent_score = similarity_scores[i]
                    break
            
            # Find best agent and score
            best_agent_idx = np.argmax(similarity_scores)
            best_agent_score = similarity_scores[best_agent_idx]
            best_agent_name = self.agents[best_agent_idx]["name"]
            
            # Calculate confidence (difference in scores)
            confidence = best_agent_score - current_agent_score
            
            # Recommend switch if:
            # 1. Best agent is different from current agent
            # 2. Confidence difference exceeds threshold
            should_switch = (best_agent_name != current_agent and confidence > threshold)
            
            return should_switch, best_agent_name, confidence
            
        except Exception as e:
            print(f"Error determining agent switch: {e}")
            return False, current_agent, 0.0
    
    def get_agent_expertise_summary(self, agent_name):
        """
        Get a summary of what an agent specializes in
        
        Args:
            agent_name (str): Name of the agent
            
        Returns:
            str: Summary of agent's expertise
        """
        try:
            agent = next((a for a in self.agents if a["name"] == agent_name), None)
            if agent:
                return agent.get("description", "General assistant capabilities")
            return "Unknown agent"
        except Exception as e:
            print(f"Error getting agent expertise: {e}")
            return "General assistant capabilities"

# Create a singleton instance
enhanced_rag_system = EnhancedRAGSystem()

def get_best_agent(query, exclude_current=None):
    """Get the best agent for a given query"""
    return enhanced_rag_system.get_best_agent_for_query(query, exclude_current)

def get_agent_recommendations(query, top_n=3, exclude_current=None):
    """Get top N recommended agents for a query"""
    return enhanced_rag_system.get_agent_recommendations(query, top_n, exclude_current)

def should_switch_agent(query, current_agent, threshold=0.15):
    """Determine if the system should recommend switching agents"""
    return enhanced_rag_system.should_switch_agent(query, current_agent, threshold)

def get_agent_expertise_summary(agent_name):
    """Get a summary of what an agent specializes in"""
    return enhanced_rag_system.get_agent_expertise_summary(agent_name)

def update_agent_knowledge():
    """Update the RAG system with the latest agent data"""
    enhanced_rag_system.update_agent_knowledge()