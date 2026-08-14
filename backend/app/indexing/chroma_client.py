import threading

import chromadb
from chromadb.api.models.Collection import Collection

_lock = threading.Lock()
_clients: dict[str, chromadb.ClientAPI] = {}


def get_chroma_client(chroma_dir: str) -> chromadb.ClientAPI:
    """Ein PersistentClient pro chroma_dir-Pfad und Prozess (Tests nutzen einen
    eigenen temporaeren Pfad, siehe conftest.py, und bekommen damit automatisch
    eine isolierte Instanz).
    """
    with _lock:
        if chroma_dir not in _clients:
            _clients[chroma_dir] = chromadb.PersistentClient(path=chroma_dir)
        return _clients[chroma_dir]


def get_or_create_collection(client: chromadb.ClientAPI, name: str) -> Collection:
    # cosine statt Chroma-Default (l2), da die Embeddings normalisiert sind
    # (siehe Embedder) und E5-Modelle auf Cosine-Similarity ausgelegt sind.
    return client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})
