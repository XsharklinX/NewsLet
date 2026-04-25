# Guía — Extensibilidad

Esta guía explica cómo agregar nuevas funcionalidades al sistema sin romper lo existente.

---

## Agregar un nuevo tipo de fuente

Para soportar un nuevo tipo de fuente (ej: una API específica de noticias):

**1. Crear el fetcher** en `app/services/`:
```python
# app/services/mi_fetcher.py
from app.database import Session
from app.services.deduplicator import is_duplicate, save_url_hash
from app.models import Article, Source

async def fetch_mi_fuente(db: Session) -> int:
    """Retorna el número de artículos nuevos guardados."""
    sources = db.query(Source).filter(
        Source.source_type == "mi_tipo",
        Source.is_active == True
    ).all()
    
    total_new = 0
    for source in sources:
        # ... lógica de fetch ...
        for item in results:
            if is_duplicate(db, item["url"]):
                continue
            article = Article(
                source_id=source.id,
                title=item["title"],
                url=item["url"],
                url_hash=save_url_hash(item["url"]),
                original_text=item.get("text", ""),
                status="pending",
            )
            db.add(article)
            total_new += 1
        db.commit()
    
    return total_new
```

**2. Registrar en el job de fetch** (`app/scheduler/jobs.py`):
```python
from app.services.mi_fetcher import fetch_mi_fuente

# En _fetch_all_impl():
rss, newsapi, scraped, mi_fuente = await asyncio.gather(
    fetch_all_rss(db),
    fetch_all_newsapi(db),
    fetch_all_scrapers(db),
    fetch_mi_fuente(db),
    return_exceptions=True,
)
```

**3. Agregar el tipo al modelo** — el campo `source_type` acepta cualquier string, no hay restricción de enum en la DB.

**4. (Opcional) Agregar opción en el frontend** (`js/sources.js`):
```javascript
// En el select de tipo de fuente
<option value="mi_tipo">Mi Fuente</option>
```

---

## Agregar un nuevo proveedor de IA

Para usar un modelo diferente además de Groq y OpenAI:

**1. Extender `services/summarizer.py`:**
```python
elif settings.ai_provider == "anthropic":
    import anthropic
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    response = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = response.content[0].text
```

**2. Agregar variables a `app/config.py`:**
```python
anthropic_api_key: str = ""
anthropic_model: str = "claude-3-haiku-20240307"
```

**3. Agregar a `_MASKED_FIELDS` en `js/config.js`** para que el panel web la trate como campo sensible.

---

## Agregar un nuevo canal de distribución

Para enviar artículos a otro canal (ej: Discord, Slack, WhatsApp Business):

**1. Crear el notificador** en `app/services/`:
```python
# app/services/discord_notifier.py
import httpx

async def send_to_discord(article, webhook_url: str):
    embed = {
        "title": article.title,
        "description": article.summary.summary_text if article.summary else "",
        "url": article.url,
        "color": 3447003,
    }
    async with httpx.AsyncClient() as client:
        await client.post(webhook_url, json={"embeds": [embed]})
```

**2. Llamarlo desde el endpoint de envío** (`app/api/routers/articles.py`) o desde el job de digest.

---

## Agregar un nuevo endpoint de API

**1. Crear o editar el router** en `app/api/routers/`:
```python
@router.get("/mis-datos")
def get_mis_datos(db: Session = Depends(get_db)):
    return {"datos": []}
```

**2. Registrar en `app/api/routes.py`** si es un router nuevo.

Todos los routers en `protected_routers` requieren JWT automáticamente. Los routers en `public_routers` son accesibles sin autenticación.

---

## Agregar una nueva vista al panel web

**1. Agregar el HTML** de la vista en `index.html`:
```html
<div id="v-mi-vista" class="view">
  <div class="view-header">
    <h2>Mi Vista</h2>
  </div>
  <!-- contenido -->
</div>
```

**2. Agregar el item al sidebar:**
```html
<a class="nav-item" onclick="showView('v-mi-vista')">
  <span class="nav-icon">🔧</span>
  <span class="nav-label">Mi Vista</span>
</a>
```

**3. Crear el JS** en `app/static/js/mi-vista.js`.

**4. Agregar el script** en `index.html` y en `sw.js` (para que se cachee).

---

## Agregar un nuevo job al scheduler

```python
# En app/scheduler/jobs.py

async def mi_job():
    """Descripción del job."""
    db = SessionLocal()
    try:
        # lógica aquí
        pass
    finally:
        db.close()

# En start_scheduler():
scheduler.add_job(
    mi_job,
    CronTrigger(hour=12, minute=0),  # o IntervalTrigger(hours=1)
    id="mi_job",
    replace_existing=True,
)
```

---

## Agregar variables de configuración

**1. En `app/config.py`:**
```python
mi_nueva_variable: str = "valor_por_defecto"
```

**2. En `Docs/02-instalacion/configuracion.md`** — documenta la variable.

**3. Opcional — en el panel de configuración** (`index.html`):
```html
<div class="cfg-row">
  <label>Mi Variable</label>
  <input id="sf-MI_NUEVA_VARIABLE" type="text" placeholder="Valor">
</div>
```

El endpoint `POST /api/v1/admin/settings` detecta automáticamente los campos con `id="sf-NOMBRE_VARIABLE"` y los guarda en el `.env`.

---

## Convenciones del proyecto

- **Servicios:** siempre async, reciben `db: Session` como parámetro, hacen `db.close()` en `finally`
- **Endpoints API:** usan `Depends(get_db)` para la sesión, retornan dict o Pydantic model
- **Frontend:** funciones globales en snake_case, elementos DOM con id en kebab-case
- **Sin dependencias adicionales** a menos que sea estrictamente necesario — el proyecto prefiere stdlib + las deps ya instaladas
