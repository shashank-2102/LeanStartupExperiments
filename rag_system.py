"""
Retrieval Augmented Generation (RAG) System for Multi-Agent Chatbot
This module handles automatic agent assignment based on user query
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

class RAGSystem:
    def __init__(self):
        """Initialize the RAG system"""
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
                    print(f"RAG system updated with {len(agents)} agents")
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
    
    def get_best_agent_for_query(self, query):
        """
        Find the most appropriate agent for a given query
        
        Args:
            query (str): The user's query
            
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
            
            # Get the index of the highest similarity score
            best_agent_idx = np.argmax(similarity_scores)
            
            # Return the name of the best matching agent
            return self.agents[best_agent_idx]["name"]
        except Exception as e:
            print(f"Error finding best agent: {e}")
            # Return default agent in case of error
            if self.agents and len(self.agents) > 0:
                return self.agents[0]["name"]
            return "General Assistant"
    
    def get_agent_recommendations(self, query, top_n=3):
        """
        Get the top N recommended agents for a query
        
        Args:
            query (str): The user's query
            top_n (int): Number of recommendations to return
            
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
            top_indices = similarity_scores.argsort()[-top_n:][::-1]
            
            # Return names of the top matching agents
            return [self.agents[idx]["name"] for idx in top_indices]
        except Exception as e:
            print(f"Error finding agent recommendations: {e}")
            # Return default recommendations in case of error
            if self.agents and len(self.agents) > 0:
                return [self.agents[0]["name"]]
            return ["General Assistant"]

# Create a singleton instance
rag_system = RAGSystem()

def get_best_agent(query):
    """Get the best agent for a given query"""
    return rag_system.get_best_agent_for_query(query)

def get_agent_recommendations(query, top_n=3):
    """Get top N recommended agents for a query"""
    return rag_system.get_agent_recommendations(query, top_n)

def update_agent_knowledge():
    """Update the RAG system with the latest agent data"""
    rag_system.update_agent_knowledge()