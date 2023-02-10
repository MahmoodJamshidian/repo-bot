from libcpp.vector cimport vector
from libc.stdint cimport *

cdef class ui64_vec:
    cdef vector[uint64_t] _data
    def __init__(self, list _val = []):
        for _item in _val:
            self._data.push_back(_item)
    def __getitem__(self, int _item):
        return self._data[_item]
    def __setitem__(self, int _item, uint64_t _val):
        self._data[_item] = _val
    def append(self, uint64_t _val):
        self._data.push_back(_val)
    def pop(self, int _item):
        cdef uint64_t res = self._data[_item]
        cdef vector[uint64_t].iterator ptr
        for _ in range(_item):
            ptr+=1
        self._data.erase(ptr)
        return res
    def __len__(self):
        return self._data.size()