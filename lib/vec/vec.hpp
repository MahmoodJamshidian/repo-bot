#include <vector>
#include <stdint.h>
#include <iostream>

class _ui64_vec
{
    std::vector<uint64_t> _data;
    public:
    void append(uint64_t _val)
    {
        _data.push_back(_val);
    }
    uint64_t pop(size_t _ind)
    {
        uint64_t res = _data[_ind];
        std::vector<uint64_t>::iterator iter = _data.begin();
        iter += _ind;
        _data.erase(iter);
        return res;
    }
    uint64_t get(size_t _ind)
    {
        return _data[_ind];
    }
    void set(size_t _ind, uint64_t _val)
    {
        _data[_ind] = _val;
    }
    size_t lenght()
    {
        return _data.size();
    }
};