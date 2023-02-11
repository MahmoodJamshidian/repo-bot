#include <stdlib.h>
#include <string.h>
#include <iostream>
#include <stdexcept>

struct result
{
    char *data;
    size_t len;
};

class str_arr
{
    char *_data = (char *)malloc(0);
    size_t _ptr = 0;
    public:
    str_arr(){}
    void append(char *_val)
    {
        _data = (char *)realloc(_data, strlen(_data)+strlen(_val)+1);
        for(size_t _i = 0; _i < strlen(_val); _i++, _ptr++)
        {
            _data[_ptr] = _val[_i];
        }
        _data[_ptr++] = 0;
    }

    result get(size_t _i) const
    {
        static char *_res;
        _res = (char *)malloc(1);
        size_t _data_ind = 0, _res_ind = 0, _ind = 0;
        size_t len = 0;
        for(; _ind < _ptr; _ind++)
        {
            if(_data[_ind] == 0){
                _data_ind++;
                continue;
            }
            if(_data_ind == _i)
            {
                while(_data[_ind] != 0)
                {
                    len++;
                    _res[_res_ind++] = _data[_ind++];
                    _res = (char *)realloc(_res, _res_ind+1);
                }
                break;
            }
        }
        if(_ind >= _ptr)
        {
            throw std::runtime_error("index out of range");
        }
        return {_res, len};
    }
    result operator[](size_t _i) const { return get(_i); }

    void set(size_t _i, const char *_val)
    {
        size_t _data_ind = 0, _res_ind = 0, _ind = 0;
        for(; _ind < _ptr; _ind++)
        {
            if(_data[_ind] == 0){
                _data_ind++;
                continue;
            }
            if(_data_ind == _i)
            {
                size_t _wi = 0, _riw = _ind;
                for(; _wi < strlen(_val); _wi++, _ind++)
                {
                    if(_data[_ind] == 0)
                    {
                        _data = (char *)realloc(_data, ++_ptr);
                        for(size_t _mi = _ptr; _mi >_ind; _mi--)
                        {
                            _data[_mi] = _data[_mi-1]; 
                        }
                    }
                    _data[_ind] = _val[_wi];
                }
                size_t _ri = _ptr-1;
                _wi += _riw;
                while(_data[_wi] != 0)
                {
                    for(size_t _ri = _wi; _ri < _ptr; _ri++)
                    {
                        _data[_ri] = _data[_ri+1];
                    }
                    _data = (char *)realloc(_data, --_ptr);
                }
                return;
            }
        }
        throw std::runtime_error("index out of range");
    }
};