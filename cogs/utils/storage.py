import json
import os
import uuid
import asyncio
import datetime

class StorageHook(json.JSONEncoder):
    def default(self, o):
        if hasattr(o, 'to_json'):
            return o.to_json()
        if isinstance(o, datetime.datetime):
            return {'__date__': o.isoformat()}
        return super().default(o)

    @classmethod
    def object_hook(cls, data):
        if '__date__' in data:
            return datetime.datetime.fromisoformat(data['__date__'])
        if cls.from_json is not StorageHook.from_json:
            return cls.from_json(data)
        return data

    @classmethod
    def from_json(cls, data):
        return data

class Storage:
    """The "database" object. Internally based on ``json``.

    You can pass a hook keyword argument to denote a class that is
    used to hook into the (de)serialization.

    Has built-in support for datetime types.

    It must subclass StorageHook and can provide a from_json
    classmethod.
    """

    def __init__(self, name, *, hook=StorageHook, init=None):
        self.name = name
        if not issubclass(hook, StorageHook):
            raise TypeError('hook has to subclass StorageHook')

        self.object_hook = hook.object_hook
        self.encoder = hook
        self.loop = asyncio.get_event_loop()
        self.lock = asyncio.Lock()
        self.init = init
        self.load_from_file()

    def load_from_file(self):
        try:
            with open(self.name, 'r') as f:
                self._db = json.load(f, object_hook=self.object_hook)
        except FileNotFoundError:
            if self.init is not None:
                self._db = self.init()
            else:
                self._db = {}

    async def load(self):
        async with self.lock:
            await self.loop.run_in_executor(None, self.load_from_file)

    def _dump(self):
        temp = '%s-%s.tmp' % (uuid.uuid4(), self.name)
        with open(temp, 'w', encoding='utf-8') as tmp:
            json.dump(self._db.copy(), tmp, ensure_ascii=True, cls=self.encoder, separators=(',', ':'))

        # atomically move the file
        os.replace(temp, self.name)

    async def save(self):
        async with self.lock:
            await self.loop.run_in_executor(None, self._dump)

    def get(self, key, *args):
        """Retrieves a config entry."""
        return self._db.get(str(key), *args)

    async def put(self, key, value, *args):
        """Edits a config entry."""
        self._db[str(key)] = value
        await self.save()

    async def remove(self, key):
        """Removes a config entry."""
        del self._db[str(key)]
        await self.save()

    def __contains__(self, item):
        return str(item) in self._db

    def __getitem__(self, item):
        return self._db[str(item)]

    def __len__(self):
        return len(self._db)

    def all(self):
        return self._db
