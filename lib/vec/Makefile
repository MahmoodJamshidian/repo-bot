PYTHON=python3.11
INCLUDE_DIR=/usr/include/python3.11
LIBRARY_DIR=/usr/lib/python3.11
LIBRARY_NAME=python311
CPYC=cython
CPPC=g++

build: vec.pyx
	mkdir -p build
	$(PYTHON) -m $(CPYC) -3 -v --cplus -o build/vec.cpp vec.pyx
	$(CPPC) -c -fPIC -Ofast -I$(INCLUDE_DIR) -o build/vec.o build/vec.cpp -I.
ifeq ($(OS),Windows_NT)
	$(CPPC) -shared -L$(LIBRARY_DIR) -o vec.pyd build/vec.o -l$(LIBRARY_NAME)
else
	$(CPPC) -shared -L$(LIBRARY_DIR) -o vec.so build/vec.o
endif

clean:
ifeq ($(OS),Windows_NT)
	rmdir build
else
	rm -rf build
endif
