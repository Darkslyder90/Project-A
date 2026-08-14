import threading

from sentence_transformers import SentenceTransformer

from app.config import get_settings

_lock = threading.Lock()
_cache: dict[str, "Embedder"] = {}


class Embedder:
    """Wrapper um ein lokales Sentence-Transformers-Modell.

    Default-Modell ist intfloat/multilingual-e5-base (siehe README "Technische
    Entscheidungen" fuer die Begruendung, warum nicht das im Briefing nur
    beispielhaft genannte paraphrase-multilingual-mpnet-base-v2). E5-Modelle
    erwarten laut Modellkarte "query: "/"passage: "-Praefixe fuer beste
    Retrieval-Qualitaet - das ist daher hier fest verdrahtet, nicht generisch
    fuer beliebige Sentence-Transformers-Modelle (waere bei einem spaeteren
    Modellwechsel auf eine andere Modellfamilie anzupassen).
    """

    def __init__(self, model_name: str) -> None:
        settings = get_settings()
        self._model = SentenceTransformer(model_name, cache_folder=str(settings.embedding_model_cache_dir))
        self.model_name = model_name
        self.max_seq_length: int = self._model.max_seq_length

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        prefixed = [f"passage: {t}" for t in texts]
        return self._model.encode(prefixed, normalize_embeddings=True, show_progress_bar=False).tolist()

    def embed_query(self, text: str) -> list[float]:
        vec = self._model.encode([f"query: {text}"], normalize_embeddings=True, show_progress_bar=False)
        return vec[0].tolist()

    def count_tokens(self, text: str) -> int:
        return len(self._model.tokenizer.encode(text, add_special_tokens=False))

    def encode_ids(self, text: str) -> list[int]:
        return self._model.tokenizer.encode(text, add_special_tokens=False)

    def decode_ids(self, ids: list[int]) -> str:
        return self._model.tokenizer.decode(ids, skip_special_tokens=True).strip()


def get_embedder(model_name: str) -> Embedder:
    """Pro Modellname genau eine geladene Instanz pro Prozess (Laden dauert
    spuerbar, u. a. Download beim allerersten Aufruf) - siehe Persistenzpfade
    fuer den Modell-Cache.
    """
    with _lock:
        if model_name not in _cache:
            _cache[model_name] = Embedder(model_name)
        return _cache[model_name]
