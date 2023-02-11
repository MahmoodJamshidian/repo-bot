from setuptools import setup, Extension
from Cython.Distutils import build_ext
import sys

ext_modules = [
    Extension(
        name="vector",
        sources=["vector.pyx"],
        language="c++"
    ),
    Extension(
        name="arr_str",
        sources=["arr_str.pyx"],
        language="c++"
    )
]

setup(
    name = 'vector',
    cmdclass = {'build_ext': build_ext},
    ext_modules = ext_modules,
    compiler_directives={'language_level': 3}
)
