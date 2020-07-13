"""Simple syntactic wrapper for nested dictionaries to allow dot traversal."""
from collections.abc import MutableMapping
from flax import serialization
from flax.core.frozen_dict import FrozenDict
from jax import tree_util


def is_leaf(x):
  return tree_util.treedef_is_leaf(tree_util.tree_flatten(x)[1])


# We subclass MutableMapping for automatic dict-like utility fns.
# We subclass dict so that freeze, unfreeze work transparently:
# i.e freeze(DotGetter(d)) == freeze(d)
#     unfreeze(DotGetter(d)) == unfreeze(d)
class DotGetter(MutableMapping, dict):
  """Dot-notation helper for interactive access of variable trees."""
  __slots__ = ('_data',)

  def __init__(self, data):
    object.__setattr__(self, '_data', data)

  def __getattr__(self, key):
    if is_leaf(self._data[key]):  # Returns leaves unwrapped.
      return self._data[key]
    else:
      return DotGetter(self._data[key])

  def __setattr__(self, key, val):
    if isinstance(self._data, FrozenDict):
      raise ValueError("Can't set value on FrozenDict.")
    self._data[key] = val

  def __getitem__(self, key):
    return self.__getattr__(key)

  def __setitem__(self, key, val):
    self.__setattr__(key, val)

  def __delitem__(self, key):
    if isinstance(self._data, FrozenDict):
      raise ValueError("Can't delete value on FrozenDict.")
    del self._data[key]

  def __iter__(self):
    return iter(self._data)

  def __len__(self):
    return len(self._data)

  def __keytransform__(self, key):
    return key

  def __dir__(self):
    if isinstance(self._data, dict):
      return list(self._data.keys())
    elif isinstance(self._data, FrozenDict):
      return list(self._data._dict.keys())
    else:
      return []

  def __repr__(self):
    return f'{self._data}'

  def __hash__(self):
    # Note: will only work when wrapping FrozenDict.
    return hash(self._data)


tree_util.register_pytree_node(
    DotGetter,
    lambda x: ((x._data,), ()),  # pylint: disable=protected-access
    lambda _, data: DotGetter(data[0]))

# Note: restores as raw dict, intentionally.
serialization.register_serialization_state(
  DotGetter,
  serialization._dict_state_dict,  # pylint: disable=protected-access
  serialization._restore_dict)  # pylint: disable=protected-access