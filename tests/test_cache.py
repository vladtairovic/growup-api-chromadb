from rag import cache
def test_cache_roundtrip_and_expiration(monkeypatch):
    class Fake:
        def setex(self,k,ttl,v):
            assert ttl == 3600
            self.k,self.v=k,v
        def get(self,k):
            return self.v if k==self.k else None
    c=Fake()
    monkeypatch.setattr(cache,"cliente",lambda:c)
    cache.salvar(["pergunta"],"modelo",[[1,2]])
    assert cache.recuperar(["pergunta"],"modelo")==[[1,2]]
    assert cache.recuperar(["pergunta"],"outro") is None

def test_cache_failure_is_optional(monkeypatch):
    def fail(): raise cache.redis.ConnectionError()
    monkeypatch.setattr(cache,"cliente",fail)
    assert cache.recuperar(["x"],"m") is None
    cache.salvar(["x"],"m",[[1]])
