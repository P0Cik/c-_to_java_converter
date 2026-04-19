import sys
import os
sys.path.append(os.path.dirname(__file__))
from converter import CppToJavaConverter

if __name__ == '__main__':
    converter = CppToJavaConverter(mode='flexible', verbose=True)
    with open('tests/simple_class.cpp', 'r') as f:
        cpp_code = f.read()
    java_code = converter.convert(cpp_code, 'tests/simple_class.cpp')
    print("=== JAVA ===\n")
    print(java_code)
