"""Dependencies for the ATS API."""

from ats_agent.graph.builder import build_graph
from ats_agent.persistence.database import Database

# Singleton instance of the compiled graph to be used across all API requests.
# The SqliteSaver checkpointer handles persistence and thread isolation.
graph = build_graph()
db = Database()

def get_graph():
    """Dependency to provide the compiled graph instance."""
    return graph

def get_session():
    """Dependency to provide a database session."""
    with db.get_session() as session:
        yield session
