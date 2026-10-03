import django.template.context as c
from copy import copy

class PatchedBaseContext(c.BaseContext):
    def __copy__(self):
        duplicate = object.__new__(self.__class__)
        duplicate.__dict__.update(self.__dict__)
        duplicate.dicts = self.dicts[:]
        return duplicate

class PatchedContext(c.Context):
    def __copy__(self):
        duplicate = object.__new__(self.__class__)
        duplicate.__dict__.update(self.__dict__)
        duplicate.dicts = self.dicts[:]
        duplicate.render_context = copy(self.render_context)
        return duplicate

c.BaseContext.__copy__ = PatchedBaseContext.__copy__
c.Context.__copy__ = PatchedContext.__copy__
