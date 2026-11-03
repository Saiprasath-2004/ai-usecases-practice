from ats_agent.embeddings import get_embedding_model
from ats_agent.scoring.matcher import _cosine_similarity

embedder = get_embedding_model()

pairs = [
    (
        "Build front-end web applications",
        "Develop responsive frontend applications"
    ),
    (
        "Participate in code reviews",
        "Review code submitted by other developers"
    ),
    (
        "Develop REST APIs",
        "Build backend API services"
    ),
    (
        "React",
        "React.js"
    ),
    (
        "React",
        "React Native"
    ),
    (
        "Python",
        "PostgreSQL"
    ),
]

for text_a, text_b in pairs:
    a = embedder.embed_query(text_a)
    b = embedder.embed_query(text_b)

    similarity = _cosine_similarity(a, b)

    print(f"{similarity:.4f} | {text_a} <-> {text_b}")