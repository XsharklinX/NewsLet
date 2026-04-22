# 🛠️ PLAN DE MEJORA DETALLADO — NewsLet Pro

**Guía paso-a-paso para pasar de MVP a production-grade.**

---

## FASE 1: ESTABILIZACIÓN (Semanas 1-2)

### Objetivo
Hacer el código confiable y testeable.

### 1.1 Setup Testing Framework

```bash
# 1. Instalar dependencias
pip install pytest pytest-asyncio pytest-cov pytest-mock factory-boy faker

# 2. Crear estructura
tests/
├── __init__.py
├── conftest.py                    # Fixtures globales
├── factories.py                   # Object factories
├── unit/
│   ├── services/
│   │   ├── test_deduplicator.py
│   │   ├── test_enricher.py
│   │   ├── test_summarizer.py
│   │   └── test_telegram_bot.py
│   └── models/
│       └── test_article.py
├── integration/
│   ├── test_fetch_workflow.py
│   ├── test_api_articles.py
│   └── test_telegram_integration.py
└── e2e/
    └── test_user_workflow.py
```

### 1.2 Crear Fixtures Base

```python
# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base

@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine

@pytest.fixture
def db_session(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()
    yield session
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db_session):
    # Monkeypatch SessionLocal to use test DB
    app.dependency_overrides[get_db] = lambda: db_session
    from fastapi.testclient import TestClient
    return TestClient(app)

@pytest.fixture
def sample_article(db_session):
    article = Article(
        title="Test Article",
        url="https://example.com",
        status="pending",
        source_id=1
    )
    db_session.add(article)
    db_session.commit()
    return article
```

### 1.3 Tests Críticos (Primer Pass)

```python
# tests/unit/services/test_deduplicator.py
import pytest
from app.services.deduplicator import deduplicate_articles

def test_deduplicate_same_urls():
    """Same URL = duplicate detection"""
    articles = [
        {"title": "News 1", "url": "https://example.com/news"},
        {"title": "News 1", "url": "https://example.com/news?utm_source=fb"},
    ]
    result = deduplicate_articles(articles)
    assert len(result) == 1

def test_deduplicate_preserves_first():
    """Keep first, remove duplicates"""
    articles = [
        {"url": "https://example.com", "fetched_at": "2026-04-01"},
        {"url": "https://example.com", "fetched_at": "2026-04-02"},
    ]
    result = deduplicate_articles(articles)
    assert result[0]["fetched_at"] == "2026-04-01"

# tests/unit/services/test_summarizer.py
@pytest.mark.asyncio
async def test_summarize_article_openai():
    """Summarizer uses OpenAI"""
    article = Article(title="Test", full_text="Long text...")
    summary = await summarize_article(article)
    assert len(summary) < len(article.full_text)
    assert len(summary) > 10

# tests/integration/test_fetch_workflow.py
@pytest.mark.asyncio
async def test_full_fetch_workflow(db_session):
    """End-to-end: fetch → dedupe → enrich → save"""
    count = await fetch_and_save_articles(db_session)
    articles = db_session.query(Article).all()
    assert len(articles) > 0
    for a in articles:
        assert a.title is not None
        assert a.summary is not None or a.status == "pending"
```

### 1.4 Coverage Report

```bash
pytest tests/ --cov=app --cov-report=html
# Genera: htmlcov/index.html (visibilidad de cobertura)

# Goal: 70% inicial
# Mínimo: sources/ y models/ al 90%
```

**Deliverable:** `tests/` funcional con ~200 test cases, 60-70% coverage

---

## FASE 2: PERFORMANCE (Semanas 2-3)

### Objetivo
3-5x más rápido, soporta 100+ usuarios simultáneos.

### 2.1 Implementar Redis Caché

```python
# app/cache.py
from redis import Redis
from typing import Any
import json
import logging

logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis = Redis.from_url(redis_url, decode_responses=True)
    
    def get(self, key: str) -> Any:
        try:
            value = self.redis.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            logger.warning(f"Cache get failed: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 300):
        try:
            self.redis.setex(key, ttl, json.dumps(value))
        except Exception as e:
            logger.warning(f"Cache set failed: {e}")
    
    def delete(self, key: str):
        try:
            self.redis.delete(key)
        except Exception as e:
            logger.warning(f"Cache delete failed: {e}")

# app/config.py
from app.cache import CacheService

cache = CacheService(redis_url=settings.redis_url)

# app/api/routers/articles.py
@router.get("/articles")
async def list_articles(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    cache_key = f"articles:pending:{skip}:{limit}"
    
    # Try cache first
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    # DB query if not cached
    articles = db.query(Article).filter(
        Article.status == "pending"
    ).offset(skip).limit(limit).all()
    
    # Store in cache (5 min TTL)
    cache.set(cache_key, [a.dict() for a in articles], ttl=300)
    
    return articles
```

### 2.2 Eager Loading en Queries

```python
# ANTES (N+1 problem)
articles = db.query(Article).all()
for a in articles:
    print(a.source.name)  # Extra query cada uno

# DESPUÉS (Eager loading)
from sqlalchemy.orm import joinedload

articles = db.query(Article).options(
    joinedload(Article.source),
    joinedload(Article.summary)
).all()

# Todo en 1 query con JOINs
for a in articles:
    print(a.source.name)  # Sin queries extras
```

### 2.3 Índices en BD

```python
# app/models/article.py
class Article(Base):
    __tablename__ = "articles"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String, index=True)
    url: Mapped[str] = mapped_column(String, unique=True, index=True)
    status: Mapped[str] = mapped_column(
        String, 
        default="pending",
        index=True  # ← Índice para filtrado
    )
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime,
        index=True  # ← Índice para ordenamiento
    )
    relevance_score: Mapped[int] = mapped_column(index=True)

# Crear índices compuestos
__table_args__ = (
    Index('idx_status_score', 'status', 'relevance_score'),
    Index('idx_fetched_status', 'fetched_at', 'status'),
)
```

### 2.4 Paralizar Summarizer

```python
# app/services/summarizer.py
async def summarize_batch(articles: list[Article], batch_size: int = 12):
    """Process multiple articles in parallel"""
    
    # Dividir en batches
    batches = [
        articles[i:i+batch_size] 
        for i in range(0, len(articles), batch_size)
    ]
    
    for batch in batches:
        # Ejecutar 12 resúmenes en paralelo
        tasks = [summarize_article(a) for a in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Guardar resultados
        for article, summary in zip(batch, results):
            if summary and not isinstance(summary, Exception):
                article.summary_text = summary
                
        db.commit()

# ANTES: 100 artículos = 200-300s (1 por 1)
# DESPUÉS: 100 artículos = 20-30s (12 en paralelo)
# Ganancia: 10x más rápido
```

### 2.5 Paginación (API)

```python
# app/api/routers/articles.py
from pydantic import BaseModel, Field

class PaginationParams(BaseModel):
    skip: int = Field(0, ge=0)
    limit: int = Field(10, ge=1, le=100)

@router.get("/articles")
async def list_articles(
    params: PaginationParams = Depends(),
    db: Session = Depends(get_db)
):
    articles = db.query(Article)\
        .offset(params.skip)\
        .limit(params.limit)\
        .all()
    
    total = db.query(Article).count()
    
    return {
        "data": articles,
        "pagination": {
            "skip": params.skip,
            "limit": params.limit,
            "total": total,
            "has_next": params.skip + params.limit < total
        }
    }
```

**Deliverable:** Redis, eager loading, índices, paginación. **Benchmark: 3x faster**

---

## FASE 3: SEGURIDAD (Semana 4)

### Objetivo
Production-grade security hardening.

### 3.1 CORS Configurado

```python
# app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://newslet-pro.fly.dev",  # Production
        "http://localhost:3000",         # Local dev
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=600,  # Preflight cache 10min
)
```

### 3.2 Sanitización HTML

```python
# pip install bleach

# app/services/html_sanitizer.py
import bleach

ALLOWED_TAGS = {'b', 'i', 'u', 'p', 'br', 'a', 'strong', 'em'}
ALLOWED_ATTRS = {'a': ['href', 'title']}

def sanitize_html(html: str) -> str:
    return bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        strip=True
    )

# Usar en Model validators
class Article(Base):
    @validator('title')
    def sanitize_title(cls, v):
        return sanitize_html(v)
```

### 3.3 Password Hashing

```python
# pip install passlib[bcrypt]

# app/services/auth.py
from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12
)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

# En startup
@app.on_event("startup")
async def check_admin_password():
    if settings.admin_password == "change-me-in-production-please":
        raise RuntimeError("❌ CAMBIAR ADMIN_PASSWORD AHORA")
```

### 3.4 Redact Secrets en Logs

```python
# app/logging_config.py
import re
import logging

class RedactingSensitiveFilter(logging.Filter):
    PATTERNS = {
        'tokens': r'(sk_live|gsk_)[a-zA-Z0-9]+',
        'passwords': r'(password|passwd)=[\w]+',
        'keys': r'(key|secret)=[\w]+',
    }
    
    def filter(self, record):
        for pattern in self.PATTERNS.values():
            record.msg = re.sub(pattern, '[REDACTED]', str(record.msg))
        return True

# Aplicar
logger = logging.getLogger(__name__)
logger.addFilter(RedactingSensitiveFilter())
```

### 3.5 Security Headers

```python
# app/main.py
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    
    return response
```

**Deliverable:** CORS, sanitization, hashing, no secrets in logs, security headers.

---

## FASE 4: OPERACIONES (Semanas 4-5)

### Objetivo
Production monitoring y automation.

### 4.1 Prometheus Metrics

```python
# pip install prometheus-client

# app/metrics.py
from prometheus_client import Counter, Histogram, Gauge
import time

# Contadores
articles_fetched = Counter(
    'articles_fetched_total',
    'Total articles fetched',
    ['source']
)

articles_sent = Counter(
    'articles_sent_total',
    'Total articles sent to users'
)

# Histogramas (timing)
fetch_duration = Histogram(
    'fetch_duration_seconds',
    'Time to fetch articles'
)

summarize_duration = Histogram(
    'summarize_duration_seconds',
    'Time to summarize article'
)

# Gauges (valores instantáneos)
pending_articles = Gauge(
    'pending_articles',
    'Number of pending articles'
)

active_users = Gauge(
    'active_users',
    'Number of active subscribers'
)

# app/scheduler/jobs.py
async def job_fetch_all():
    with fetch_duration.time():
        count = await fetch_all_articles()
        articles_fetched.labels(source='rss').inc(count)
        pending_articles.set(db.query(Article).filter(...).count())

# app/main.py
from prometheus_client import make_wsgi_app
from starlette.responses import Response

@app.get("/metrics")
async def metrics():
    from prometheus_client import generate_latest
    return Response(generate_latest(), media_type="text/plain")
```

### 4.2 Automated Backups

```python
# app/services/backup_service.py
import os
from datetime import datetime
import shutil

class BackupService:
    def __init__(self, backup_dir: str):
        self.backup_dir = backup_dir
        os.makedirs(backup_dir, exist_ok=True)
    
    async def backup_database(self):
        """Daily backup of SQLite or export from PostgreSQL"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if settings.database_url.startswith("sqlite"):
            # SQLite: copy file
            shutil.copy(
                f"./newslet.db",
                f"{self.backup_dir}/newslet_{timestamp}.db"
            )
        else:
            # PostgreSQL: dump
            os.system(f"pg_dump {settings.database_url} > {self.backup_dir}/dump_{timestamp}.sql")
        
        # Cleanup old backups (keep 30 days)
        self._cleanup_old_backups(days=30)
    
    def _cleanup_old_backups(self, days: int = 30):
        import time
        cutoff = time.time() - (days * 86400)
        for f in os.listdir(self.backup_dir):
            path = os.path.join(self.backup_dir, f)
            if os.stat(path).st_mtime < cutoff:
                os.remove(path)

# En scheduler
backup_service = BackupService(settings.backup_dir)

@scheduler.scheduled_job('cron', hour=2, minute=0)
async def job_backup():
    await backup_service.backup_database()
```

### 4.3 Health Checks

```python
# app/services/health.py
from sqlalchemy import text

class HealthChecker:
    async def check_all(self) -> dict:
        return {
            "status": "healthy" if all(
                [
                    await self.check_database(),
                    await self.check_telegram(),
                    await self.check_openai(),
                ]
            ) else "degraded",
            "database": await self.check_database(),
            "telegram": await self.check_telegram(),
            "openai": await self.check_openai(),
            "timestamp": datetime.now().isoformat()
        }
    
    async def check_database(self) -> bool:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False
    
    async def check_telegram(self) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    f"https://api.telegram.org/bot{settings.telegram_bot_token}/getMe",
                    timeout=5
                )
            return r.status_code == 200
        except Exception:
            return False
    
    async def check_openai(self) -> bool:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.openai_api_key)
            client.models.list()  # Simple check
            return True
        except Exception:
            return False

# app/main.py
health_checker = HealthChecker()

@app.get("/health")
async def health():
    return await health_checker.check_all()
```

**Deliverable:** Prometheus metrics, automated backups, health checks.

---

## FASE 5: MEJORAS UX/UI (Semanas 5-6)

### Objetivo
Polish professional-grade frontend.

### 5.1 Loading States

```javascript
// app/static/app.js
async function fetchArticles() {
    const btn = document.getElementById('fetch-btn');
    const spinner = document.getElementById('spinner');
    
    btn.disabled = true;
    spinner.style.display = 'block';
    
    try {
        const response = await api('POST', '/fetch/now');
        showNotification(`✅ ${response.count} artículos nuevos`);
    } catch (e) {
        showNotification('❌ Error al buscar artículos', 'error');
    } finally {
        btn.disabled = false;
        spinner.style.display = 'none';
    }
}
```

### 5.2 Confirmación en Acciones

```html
<!-- Modal de confirmación -->
<div id="confirm-modal" style="display: none;">
    <div class="modal-content">
        <h3>¿Estás seguro?</h3>
        <p id="confirm-message"></p>
        <button id="confirm-yes" class="btn-danger">Eliminar</button>
        <button id="confirm-no" class="btn">Cancelar</button>
    </div>
</div>

<!-- JS -->
<script>
function confirmAction(message, callback) {
    document.getElementById('confirm-message').textContent = message;
    document.getElementById('confirm-modal').style.display = 'block';
    
    document.getElementById('confirm-yes').onclick = () => {
        callback();
        document.getElementById('confirm-modal').style.display = 'none';
    };
    
    document.getElementById('confirm-no').onclick = () => {
        document.getElementById('confirm-modal').style.display = 'none';
    };
}
</script>
```

### 5.3 Design System (Tailwind)

```css
/* app/static/tailwind-config.js */
const colors = {
    approved: '#10b981',    // Esmeralda
    rejected: '#ef4444',    // Rojo
    pending: '#f59e0b',     // Ámbar
    neutral: '#6b7280',     // Gris
};

/* Uso consistente en todo */
.badge-approved { @apply bg-green-100 text-green-800; }
.badge-rejected { @apply bg-red-100 text-red-800; }
.badge-pending { @apply bg-yellow-100 text-yellow-800; }
```

**Deliverable:** Loading states, confirmations, design system.

---

## RESUMEN IMPLEMENTACIÓN

| Fase | Duración | Mejoras | Impact |
|------|----------|---------|--------|
| 1: Testing | 2 sem | Tests, fixtures, coverage | +500% confianza |
| 2: Performance | 1.5 sem | Caché, eager load, índices | 3-5x faster |
| 3: Security | 1 sem | CORS, hashing, hardening | -99% vulns |
| 4: DevOps | 1.5 sem | Metrics, backups, health | Production-grade |
| 5: UX/UI | 1.5 sem | Polish, design, UX | +40% usabilidad |

**Total: 7-8 semanas | Salto de v3.0 → v4.0**

---

## TRACKING PROGRESS

```bash
# Week 1-2
- [ ] Tests setup + first 50 test cases
- [ ] Coverage report (60%+)

# Week 2-3
- [ ] Redis implementado
- [ ] Eager loading en queries
- [ ] Índices en BD
- [ ] Paginación (todo APIs)

# Week 4
- [ ] CORS configurado
- [ ] Sanitización HTML
- [ ] Password hashing
- [ ] Security headers

# Week 4-5
- [ ] Prometheus metrics
- [ ] Automated backups
- [ ] Health checks
- [ ] Monitoring dashboard

# Week 5-6
- [ ] Loading states
- [ ] Confirmation modals
- [ ] Design system
- [ ] Mobile testing

# Week 7-8
- [ ] Load testing (100+ users)
- [ ] Security audit (3rd party)
- [ ] Documentation
- [ ] Release v4.0
```

---

**Siguiendo este plan, tienes un sistema production-grade listo para vender/escalar.**

