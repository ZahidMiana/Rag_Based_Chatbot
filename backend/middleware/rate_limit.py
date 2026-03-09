from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# Usage in routers (applied as decorator):
#   @limiter.limit("20/minute")   — for /chat/query
#   @limiter.limit("10/minute")   — for /documents/upload
