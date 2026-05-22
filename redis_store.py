from __future__ import annotations

import asyncio
import time
from fnmatch import fnmatch
from typing import Any

from .config import Settings


class MemoryRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.sets: dict[str, set[str]] = {}
        self.hashes: dict[str, dict[str, str]] = {}
        self.expires: dict[str, float] = {}
        self._lock = asyncio.Lock()

    def _expire(self, key: str) -> None:
        deadline = self.expires.get(key)
        if deadline is not None and deadline <= time.time():
            self.values.pop(key, None)
            self.sets.pop(key, None)
            self.hashes.pop(key, None)
            self.expires.pop(key, None)

    async def get(self, key: str) -> str | None:
        self._expire(key)
        return self.values.get(key)

    async def set(self, key: str, value: Any) -> bool:
        self.values[key] = str(value)
        return True

    async def setex(self, key: str, seconds: int, value: Any) -> bool:
        self.values[key] = str(value)
        self.expires[key] = time.time() + int(seconds)
        return True

    async def delete(self, *keys: str) -> int:
        count = 0
        for key in keys:
            self._expire(key)
            existed = key in self.values or key in self.sets or key in self.hashes
            self.values.pop(key, None)
            self.sets.pop(key, None)
            self.hashes.pop(key, None)
            self.expires.pop(key, None)
            count += int(existed)
        return count

    async def sadd(self, key: str, *values: Any) -> int:
        bucket = self.sets.setdefault(key, set())
        before = len(bucket)
        bucket.update(str(v) for v in values)
        return len(bucket) - before

    async def srem(self, key: str, *values: Any) -> int:
        bucket = self.sets.setdefault(key, set())
        count = 0
        for value in values:
            if str(value) in bucket:
                bucket.remove(str(value))
                count += 1
        return count

    async def sismember(self, key: str, value: Any) -> bool:
        self._expire(key)
        return str(value) in self.sets.get(key, set())

    async def smembers(self, key: str) -> set[str]:
        self._expire(key)
        return set(self.sets.get(key, set()))

    async def scard(self, key: str) -> int:
        self._expire(key)
        return len(self.sets.get(key, set()))

    async def incrby(self, key: str, amount: int) -> int:
        current = int(float(await self.get(key) or 0))
        current += int(amount)
        await self.set(key, current)
        return current

    async def decrby(self, key: str, amount: int) -> int:
        return await self.incrby(key, -int(amount))

    async def hset(self, key: str, field: str, value: Any) -> int:
        self.hashes.setdefault(key, {})[field] = str(value)
        return 1

    async def hget(self, key: str, field: str) -> str | None:
        self._expire(key)
        return self.hashes.get(key, {}).get(field)

    async def hgetall(self, key: str) -> dict[str, str]:
        self._expire(key)
        return dict(self.hashes.get(key, {}))

    async def hdel(self, key: str, *fields: str) -> int:
        self._expire(key)
        bucket = self.hashes.get(key, {})
        count = 0
        for field in fields:
            if field in bucket:
                bucket.pop(field, None)
                count += 1
        return count

    async def ttl(self, key: str) -> int:
        self._expire(key)
        if key not in self.expires:
            return -1
        return max(0, int(self.expires[key] - time.time()))

    async def keys(self, pattern: str) -> list[str]:
        for key in list(self.expires):
            self._expire(key)
        all_keys = set(self.values) | set(self.sets) | set(self.hashes)
        return [key for key in all_keys if fnmatch(key, pattern)]


class RedisStore:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.prefix = settings.redis_prefix
        self.client: Any | None = None

    def key(self, *parts: Any) -> str:
        return self.prefix + "".join(str(part) for part in parts)

    async def connect(self) -> None:
        if self.settings.in_memory_redis:
            self.client = MemoryRedis()
            return
        try:
            import redis.asyncio as redis
        except Exception:
            self.client = MemoryRedis()
            return
        self.client = redis.from_url(self.settings.redis_url, decode_responses=True)
        await self.client.ping()

    async def close(self) -> None:
        if self.client and hasattr(self.client, "aclose"):
            await self.client.aclose()

    def _c(self) -> Any:
        if self.client is None:
            raise RuntimeError("RedisStore.connect() was not called")
        return self.client

    async def get(self, key: str) -> str | None:
        return await self._c().get(key)

    async def set(self, key: str, value: Any) -> bool:
        return bool(await self._c().set(key, value))

    async def setex(self, key: str, seconds: int, value: Any) -> bool:
        return bool(await self._c().setex(key, seconds, value))

    async def delete(self, *keys: str) -> int:
        return int(await self._c().delete(*keys))

    async def sadd(self, key: str, *values: Any) -> int:
        return int(await self._c().sadd(key, *values))

    async def srem(self, key: str, *values: Any) -> int:
        return int(await self._c().srem(key, *values))

    async def sismember(self, key: str, value: Any) -> bool:
        return bool(await self._c().sismember(key, value))

    async def smembers(self, key: str) -> set[str]:
        values = await self._c().smembers(key)
        return {str(v) for v in values}

    async def scard(self, key: str) -> int:
        return int(await self._c().scard(key))

    async def incrby(self, key: str, amount: int) -> int:
        return int(await self._c().incrby(key, amount))

    async def decrby(self, key: str, amount: int) -> int:
        return int(await self._c().decrby(key, amount))

    async def hset(self, key: str, field: str, value: Any) -> int:
        return int(await self._c().hset(key, field, value))

    async def hget(self, key: str, field: str) -> str | None:
        return await self._c().hget(key, field)

    async def hgetall(self, key: str) -> dict[str, str]:
        data = await self._c().hgetall(key)
        return {str(k): str(v) for k, v in data.items()}

    async def hdel(self, key: str, *fields: str) -> int:
        return int(await self._c().hdel(key, *fields))

    async def ttl(self, key: str) -> int:
        return int(await self._c().ttl(key))

    async def keys(self, pattern: str) -> list[str]:
        values = await self._c().keys(pattern)
        return [str(v) for v in values]

    async def snapshot(self) -> dict[str, Any]:
        client = self._c()
        if isinstance(client, MemoryRedis):
            for key in list(client.expires):
                client._expire(key)
            return {
                "values": dict(client.values),
                "sets": {key: sorted(values) for key, values in client.sets.items()},
                "hashes": {key: dict(values) for key, values in client.hashes.items()},
                "ttls": {key: await client.ttl(key) for key in client.expires},
            }
        keys: set[str] = set()
        for pattern in (self.prefix + "*", "tags:*"):
            keys.update(str(key) for key in await client.keys(pattern))
        values: dict[str, str] = {}
        sets: dict[str, list[str]] = {}
        hashes: dict[str, dict[str, str]] = {}
        ttls: dict[str, int] = {}
        for key in keys:
            raw_type = await client.type(key)
            key_type = raw_type.decode() if isinstance(raw_type, bytes) else str(raw_type)
            ttl = int(await client.ttl(key))
            if ttl >= 0:
                ttls[key] = ttl
            if key_type == "string":
                value = await client.get(key)
                if value is not None:
                    values[key] = str(value)
            elif key_type == "set":
                sets[key] = sorted(str(value) for value in await client.smembers(key))
            elif key_type == "hash":
                data = await client.hgetall(key)
                hashes[key] = {str(k): str(v) for k, v in data.items()}
        return {"values": values, "sets": sets, "hashes": hashes, "ttls": ttls}

    async def apply_operations(self, operations: list[dict[str, Any]]) -> None:
        for operation in operations:
            op = operation.get("op")
            key = operation.get("key")
            if op == "set" and key is not None:
                await self.set(str(key), operation.get("value", ""))
            elif op == "setex" and key is not None:
                await self.setex(str(key), int(operation.get("seconds") or 0), operation.get("value", ""))
            elif op == "del":
                keys = [str(item) for item in operation.get("keys", []) if item is not None]
                if keys:
                    await self.delete(*keys)
            elif op == "sadd" and key is not None:
                values = operation.get("values", [])
                if values:
                    await self.sadd(str(key), *values)
            elif op == "srem" and key is not None:
                values = operation.get("values", [])
                if values:
                    await self.srem(str(key), *values)
            elif op == "hset" and key is not None:
                await self.hset(str(key), str(operation.get("field", "")), operation.get("value", ""))
            elif op == "hdel" and key is not None:
                fields = [str(item) for item in operation.get("fields", [])]
                if fields:
                    await self.hdel(str(key), *fields)
