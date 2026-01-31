import numpy as np
from resemblyzer import VoiceEncoder, preprocess_wav
from pathlib import Path

class VoiceAuthenticator:
    def __init__(self):
        print("Loading Voice Encoder Model...")
        self.encoder = VoiceEncoder()
        print("Voice Encoder Model Loaded.")

    def extract_embedding_from_file(self, audio_path):
        """
        Extracts a 256-d vector embedding from an audio file.
        """
        try:
            wav = preprocess_wav(Path(audio_path))
            embedding = self.encoder.embed_utterance(wav)
            return embedding
        except Exception as e:
            # Silence error implicitly or log debug only
            return None

    def compare_embeddings(self, emb1, emb2):
        """
        Compares two embeddings using cosine similarity.
        Returns a score between 0.0 (no match) and 1.0 (perfect match).
        """
        if emb1 is None or emb2 is None:
            return 0.0
            
        # Ensure numpy arrays
        emb1 = np.array(emb1)
        emb2 = np.array(emb2)
        
        # Calculate cosine similarity
        # Resemblyzer embeddings are already normalized usually, but let's be safe
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        dot_product = np.dot(emb1, emb2)
        similarity = dot_product / (norm1 * norm2)
        
        # Clip to [0, 1] for safety (though cosine implies [-1, 1], voices are generally positive correlation)
        return max(0.0, min(1.0, similarity))

    def is_match(self, score, threshold=0.75):
        """
        Determines if the score meets the verification threshold.
        Common threshold for Resemblyzer is around 0.75-0.80 for same speaker.
        """
        return score >= threshold
