from redis import Redis

from app.config import settings


CLAIM_PREFIX = "gni:ingestion:endpoint:"


def create_lock_client() -> Redis:
    """Create the synchronous Redis client used by Celery."""

    return Redis.from_url(
        settings.celery_lock_url,
        decode_responses=True,
    )


def endpoint_claim_key(endpoint_id: int) -> str:
    return f"{CLAIM_PREFIX}{endpoint_id}"


def get_endpoint_claim_owner(
    client: Redis,
    endpoint_id: int,
) -> str | None:
    """Return the current claim owner."""

    return client.get(
        endpoint_claim_key(endpoint_id)
    )


def acquire_endpoint_claim(
    client: Redis,
    endpoint_id: int,
    owner: str,
) -> bool:
    """
    Atomically claim an endpoint.

    Redis SET NX prevents two dispatchers from claiming it.
    """

    acquired = client.set(
        endpoint_claim_key(endpoint_id),
        owner,
        nx=True,
        ex=settings.celery_endpoint_claim_ttl_seconds,
    )

    return bool(acquired)


def release_endpoint_claim(
    client: Redis,
    endpoint_id: int,
    owner: str,
) -> bool:
    """
    Delete a claim only when it still belongs to this owner.

    The comparison and deletion are atomic.
    """

    script = """
    if redis.call("get", KEYS[1]) == ARGV[1] then
        return redis.call("del", KEYS[1])
    end
    return 0
    """

    result = client.eval(
        script,
        1,
        endpoint_claim_key(endpoint_id),
        owner,
    )

    return bool(result)