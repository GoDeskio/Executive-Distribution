import logging
import re
import uuid
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("server")


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def slugify(text: str) -> str:
    s = re.sub(r'[^a-zA-Z0-9\s-]', '', text or '').strip().lower()
    s = re.sub(r'[\s_-]+', '-', s)
    return s or str(uuid.uuid4())[:8]


def clean(doc):
    if not doc:
        return doc
    doc = dict(doc)
    doc['id'] = str(doc.pop('_id')) if '_id' in doc else doc.get('id')
    doc.pop('password_hash', None)
    return doc
