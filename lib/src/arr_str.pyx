from libc.stdint cimport *
cdef extern from "arr_str.hpp":
    cdef struct result:
        char *data
        size_t len
    cdef cppclass str_arr:
        str_arr()
        void append(char *)
        result get(size_t) const
        result operator[](size_t) const
        void set(size_t _i, const char *)


cdef class Array:
    cdef str_arr arr
    def __init__(self):
        pass
    def __setitem__(self, _i, _val):
        self.arr.set(_i, _val)
    def __getitem__(self, _i):
        cdef result res = self.arr.get(_i)
        return res.data[:res.len]
    def append(self, _val):
        self.arr.append(_val)