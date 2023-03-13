from libc.stdint cimport *

cdef extern from "vec.hpp":
    cdef cppclass _ui64_vec:
        void append(uint64_t _val)
        uint64_t pop(size_t _ind) except +IndexError
        uint64_t get(size_t _ind) except +IndexError
        void set(size_t _ind, uint64_t _val) except +IndexError
        size_t lenght()

cdef class ui64_vec:
    cdef _ui64_vec _data
    def __init__(self, list _val = []):
        for _item in _val:
            self._data.append(_item)
    def __getitem__(self, int _item):
        if len(self) <= _item:
            raise IndexError("array index out of range")
        return self._data.get(_item)
    def __setitem__(self, int _item, uint64_t _val):
        if len(self) <= _item:
            raise IndexError("array assignment index out of range")
        self._data.set(_item, _val)
    def append(self, uint64_t _val):
        self._data.append(_val)
    def pop(self, int _item):
        return self._data.pop(_item)
    def __len__(self):
        return self._data.lenght()