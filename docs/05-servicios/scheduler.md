# Servicios — Scheduler (Jobs automáticos)

El scheduler usa **APScheduler** con el backend `AsyncIOScheduler`, integrado en el lifespan de FastAPI. Se inicia junto con la aplicación y corre en el mismo proceso.

---

## Jobs configurados

### 1. Fetch de noticias — `fetch_news`

| Parámetro | Valor |
|---|---|
| Trigger | `IntervalTrigger` |
| Frecuencia | Cada `FETCH_INTERVAL_MINUTES` minutos (por defecto: **10 min**) |
| Timeout | 5 minutos máximo por ciclo |
| Grace time | 60 segundos |

**Qué hace:**
1. Fetch RSS + NewsAPI + Scrapers en paralelo
2. Deduplica artículos
3. Verifica keywords activas
4. Auto-resume con IA (hasta 30 artículos nuevos)
5. Emite evento `fetch_complete` por WebSocket al panel
6. Crea notificación in-app con el resultado

---

### 2. Digest diario — `daily_digest`

| Parámetro | Valor |
|---|---|
| Trigger | `CronTrigger` |
| Hora | Configurable por DB (por defecto: `DIGEST_HOUR=8`, o sea las 08:00) |
| Grace time | 5 minutos |

**Qué hace:**
1. Obtiene artículos aprobados/pendientes respetando la configuración del digest (count, min_score, categorías)
2. Envía el digest al canal del administrador en Telegram
3. Hace broadcast simplificado a todos los suscriptores públicos
4. Registra notificación in-app

La hora del digest se puede cambiar desde el panel web (sección Noticias diarias) o via `PATCH /api/v1/digest/config`. El cambio se aplica inmediatamente sin reiniciar.

---

### 3. Clustering temático — `topic_cluster`

| Parámetro | Valor |
|---|---|
| Trigger | `IntervalTrigger` |
| Frecuencia | Cada **2 horas** |

**Qué hace:** agrupa artículos que hablan del mismo tema y les asigna un `cluster_id`. Útil para identificar noticias recurrentes y evitar saturar el digest con variaciones del mismo evento.

---

### 4. Backup de base de datos — `db_backup`

| Parámetro | Valor |
|---|---|
| Trigger | `CronTrigger` |
| Hora | Todos los días a las **02:00 UTC** |
| Activación | Automática si `BACKUP_DIR` está configurado o si el directorio `/app/data` existe |

**Qué hace:**
1. Copia el archivo `.db` al directorio de backup (conserva los últimos 7)
2. Envía el archivo `.db` como documento al chat de Telegram del admin

---

### 5. Informe semanal — `weekly_report`

| Parámetro | Valor |
|---|---|
| Trigger | `CronTrigger` |
| Día | Todos los **lunes** a las 08:00 |

**Qué hace:**
1. Genera estadísticas de la semana: artículos recolectados, enviados, score promedio
2. Envía el informe por Telegram al canal del admin
3. Si `SMTP_ENABLED=true`, también envía el informe por email

---

### 6. Limpieza de artículos — `cleanup`

| Parámetro | Valor |
|---|---|
| Trigger | `CronTrigger` |
| Día | Todos los **domingos** a las 03:00 |

**Qué hace:**
- Elimina artículos con `status = "rejected"` de más de **30 días**
- Elimina artículos con `status = "sent"` de más de **60 días**

Mantiene la base de datos ligera sin eliminar historial reciente.

---

## Diagrama de horario semanal

```
Lun   08:00 → Informe semanal
      08:xx → Fetch (cada 10 min, todo el día)
      ...
      08:00 → Digest diario (configurable)

Jue   Continúa el ciclo normal

Dom   03:00 → Limpieza de artículos

Diario
      02:00 → Backup de DB
      Cada 2h → Clustering temático
      Cada 10min → Fetch + IA + WebSocket
```

---

## Reprogramar el digest manualmente

```python
# Desde código (ej: en un endpoint de la API)
from app.scheduler.jobs import reschedule_digest
reschedule_digest(hour=9)  # Cambia a las 09:00
```

O desde el panel web en **Noticias diarias → Hora de envío**.
