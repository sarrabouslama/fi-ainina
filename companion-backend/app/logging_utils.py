import hashlib
import logging


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
)

logger = logging.getLogger('companion-backend')


def anon_user(user_id: str | None) -> str:
    if not user_id:
        return 'anon'
    return hashlib.sha256(user_id.encode('utf-8')).hexdigest()[:12]
