"""Cache descartável de vetores; falhas do Redis não impedem a busca."""
import hashlib
import json
import os
from functools import lru_cache
import redis

@lru_cache(maxsize=1)
def cliente():
    url = os.getenv("REDIS_URL")
    return redis.Redis.from_url(url, socket_timeout=1, socket_connect_timeout=1) if url else None

def chave(textos, modelo):
    return "embedding:v1:" + hashlib.sha256(json.dumps([modelo, textos], ensure_ascii=False).encode()).hexdigest()

def recuperar(textos, modelo):
    try:
        c = cliente()
        valor = c.get(chave(textos, modelo)) if c else None
        return json.loads(valor) if valor else None
    except (redis.RedisError, ValueError):
        return None

def salvar(textos, modelo, vetor):
    try:
        c = cliente()
        if c:
            c.setex(chave(textos, modelo), int(os.getenv("CACHE_TTL_SECONDS", "3600")), json.dumps(vetor))
    except redis.RedisError:
        pass
