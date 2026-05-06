import hashlib

def get_file_hash(content: bytes):
    """Generates a unique SHA-256 hash for the file content."""
    return hashlib.sha256(content).hexdigest()