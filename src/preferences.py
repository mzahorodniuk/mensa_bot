"""Per-user preferences (default mensa + diet filter).

Backed by Azure Table Storage when ``AzureWebJobsStorage`` is configured (always
the case on a deployed Function App), and by an in-memory dict otherwise so that
local development and polling keep working without a storage account.

All public functions are synchronous; call them from async handlers via
``asyncio.to_thread`` so the event loop is never blocked on network I/O.
"""
import os
import logging

logger = logging.getLogger(__name__)

_TABLE_NAME = 'mensaprefs'
_PARTITION = 'prefs'

DEFAULTS = {'location': 'oben', 'diet': 'all'}

# In-memory fallback store (also used as a write-through cache).
_mem = {}

_table_client = None
_table_ready = False


def _get_table():
    """Return a ready Table Storage client, or None to use the in-memory store."""
    global _table_client, _table_ready
    if _table_ready:
        return _table_client
    _table_ready = True  # only attempt setup once per process

    conn = os.getenv('AzureWebJobsStorage')
    if not conn:
        logger.info('AzureWebJobsStorage not set; using in-memory preferences.')
        return None
    try:
        from azure.data.tables import TableServiceClient
        from azure.core.exceptions import ResourceExistsError
        service = TableServiceClient.from_connection_string(conn)
        try:
            service.create_table(_TABLE_NAME)
        except ResourceExistsError:
            pass
        _table_client = service.get_table_client(_TABLE_NAME)
        logger.info('Preferences backed by Azure Table Storage.')
    except Exception:
        logger.exception('Table Storage unavailable; using in-memory preferences.')
        _table_client = None
    return _table_client


def get_prefs(user_id):
    """Return {'location', 'diet'} for a user, falling back to DEFAULTS."""
    table = _get_table()
    if table is None:
        return {**DEFAULTS, **_mem.get(str(user_id), {})}
    try:
        entity = table.get_entity(_PARTITION, str(user_id))
        return {
            'location': entity.get('location', DEFAULTS['location']),
            'diet': entity.get('diet', DEFAULTS['diet']),
        }
    except Exception:
        # Most commonly ResourceNotFound for first-time users.
        return dict(DEFAULTS)


def set_prefs(user_id, location=None, diet=None):
    """Persist a user's default location and/or diet (merge update)."""
    current = get_prefs(user_id)
    if location is not None:
        current['location'] = location
    if diet is not None:
        current['diet'] = diet

    _mem[str(user_id)] = current  # keep the cache/fallback in sync

    table = _get_table()
    if table is None:
        return current
    try:
        table.upsert_entity({
            'PartitionKey': _PARTITION,
            'RowKey': str(user_id),
            'location': current['location'],
            'diet': current['diet'],
        })
    except Exception:
        logger.exception('Failed to persist preferences for %s', user_id)
    return current
