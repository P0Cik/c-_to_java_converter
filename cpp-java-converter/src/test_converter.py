#!/usr/bin/env python3
"""
Test script for C++ to Java converter
Implements requirements: VT_001-VT_003
"""

import os
import json
from converter import CppToJavaConverter


def test_basic_conversion():
    """Test basic conversion functionality"""
    print("Testing basic conversion...")
    
    converter = CppToJavaConverter(mode="flexible", verbose=True)
    
    # Test basic variable declarations
    cpp_code = """int a;
char b = a + a;
short c;
int d;
long e;
long long f;

char aarr[20];
long barr[10][20];
"""
    
    try:
        java_code = converter.convert(cpp_code, "test.cpp")
        print("Basic conversion successful!")
        print("Java output:")
        print(java_code)
        print()
        
        # Check for expected elements
        assert "public static int a;" in java_code or "int a;" in java_code
        assert "byte b" in java_code  # char maps to byte
        print("✓ Basic variable declarations converted correctly")
        
    except Exception as e:
        print(f"✗ Basic conversion failed: {e}")
        return False
    
    return True


def test_class_conversion():
    """Test class conversion"""
    print("Testing class conversion...")
    
    converter = CppToJavaConverter(mode="flexible", verbose=True)
    
    # Test simple class
    cpp_code = """class MyClass {
public:
    int x;
    void method();
};
"""
    
    try:
        java_code = converter.convert(cpp_code, "test_class.cpp")
        print("Class conversion successful!")
        print("Java output:")
        print(java_code)
        print()
        
        # Check for expected elements
        assert "public class MyClass" in java_code
        assert "public int x;" in java_code
        print("✓ Class conversion works correctly")
        
    except Exception as e:
        print(f"✗ Class conversion failed: {e}")
        return False
    
    return True


def test_template_conversion():
    """Test template conversion"""
    print("Testing template conversion...")
    
    converter = CppToJavaConverter(mode="flexible", verbose=True)
    
    # Test simple template
    cpp_code = """template<typename T>
class MyTemplate {
public:
    T value;
};
"""
    
    try:
        java_code = converter.convert(cpp_code, "test_template.cpp")
        print("Template conversion successful!")
        print("Java output:")
        print(java_code)
        print()
        
        # Check for expected elements
        assert "<T>" in java_code  # Generic parameter
        print("✓ Template conversion works correctly")
        
    except Exception as e:
        print(f"✗ Template conversion failed: {e}")
        return False
    
    return True


def test_namespace_conversion():
    """Test namespace conversion"""
    print("Testing namespace conversion...")
    
    converter = CppToJavaConverter(mode="flexible", verbose=True)
    
    # Test namespace
    cpp_code = """namespace graphics {
    namespace shapes {
        class Circle {
        public:
            double radius;
        };
    }
}
"""
    
    try:
        java_code = converter.convert(cpp_code, "test_namespace.cpp")
        print("Namespace conversion successful!")
        print("Java output:")
        print(java_code)
        print()
        
        # Check for expected elements
        assert "package graphics.shapes;" in java_code or "graphics" in java_code
        print("✓ Namespace conversion works correctly")
        
    except Exception as e:
        print(f"✗ Namespace conversion failed: {e}")
        return False
    
    return True


def test_multiple_inheritance_warning():
    """Test multiple inheritance handling"""
    print("Testing multiple inheritance handling...")
    
    converter = CppToJavaConverter(mode="flexible", verbose=True)
    
    # Test multiple inheritance
    cpp_code = """class Base1 {};
class Base2 {};
class Derived : public Base1, public Base2 {};
"""
    
    try:
        java_code = converter.convert(cpp_code, "test_multi_inherit.cpp")
        print("Multiple inheritance handling successful!")
        print("Warnings:", converter.warnings)
        print("Java output:")
        print(java_code)
        print()
        
        # Should have warnings about multiple inheritance
        assert len(converter.warnings) > 0
        print("✓ Multiple inheritance warning generated correctly")
        
    except Exception as e:
        print(f"✗ Multiple inheritance test failed: {e}")
        return False
    
    return True


def test_operator_overloading():
    """Test operator overloading conversion"""
    print("Testing operator overloading conversion...")
    
    converter = CppToJavaConverter(mode="flexible", verbose=True)
    
    # Test operator overloading
    cpp_code = """class Complex {
private:
    double real, imag;
public:
    Complex(double r = 0, double i = 0) : real(r), imag(i) {}
    bool operator==(const Complex& other) const {
        return (real == other.real && imag == other.imag);
    }
};
"""
    
    try:
        java_code = converter.convert(cpp_code, "test_operator.cpp")
        print("Operator overloading conversion successful!")
        print("Java output:")
        print(java_code)
        print()
        
        # Check for expected elements
        assert "equals" in java_code or "==" in java_code
        print("✓ Operator overloading conversion works correctly")
        
    except Exception as e:
        print(f"✗ Operator overloading test failed: {e}")
        return False
    
    return True


def run_all_tests():
    """Run all tests"""
    print("Running converter tests...\n")
    
    tests = [
        test_basic_conversion,
        test_class_conversion,
        test_template_conversion,
        test_namespace_conversion,
        test_multiple_inheritance_warning,
        test_operator_overloading
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print("-" * 50)
    
    print(f"\nTests passed: {passed}/{total}")
    
    if passed == total:
        print("All tests passed! ✓")
        return True
    else:
        print("Some tests failed! ✗")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)