"""
Type conversion utilities for C++ to Java
"""
import re

class TypeConverter:
    """Converts C++ types to Java types"""
    
    # Mapping of C++ basic types to Java equivalents
    CPP_TO_JAVA_TYPES = {
        'int': 'int',
        'long': 'long',
        'short': 'short',
        'char': 'byte',  # char in C++ is typically 1 byte, so map to Java byte
        'wchar_t': 'char',  # wide char to Java char
        'bool': 'boolean',
        'float': 'float',
        'double': 'double',
        'void': 'void',
        'unsigned int': 'int',
        'unsigned long': 'long',
        'unsigned short': 'short',
        'unsigned char': 'byte',
        'signed char': 'byte',
        'long long': 'long',
        'unsigned long long': 'long'
    }
    
    @classmethod
    def cpp_to_java_type(cls, cpp_type):
        """
        Convert a C++ type to its Java equivalent
        
        Args:
            cpp_type (str): The C++ type to convert
            
        Returns:
            str: The corresponding Java type
        """
        # Handle pointer types - convert to Object reference or array
        if '*' in cpp_type:
            # Remove multiple pointer stars and replace with array notation
            base_type = cpp_type.replace('*', '').strip()
            java_base = cls.CPP_TO_JAVA_TYPES.get(base_type, base_type)
            # For pointers, we'll use a special wrapper class in Java
            return f"{java_base}Pointer"
        
        # Handle array types
        if '[' in cpp_type and ']' in cpp_type:
            # Extract the base type
            base_type_match = re.match(r'^([^\[\]]+)\s*\[.*\]', cpp_type)
            if base_type_match:
                base_type = base_type_match.group(1).strip()
                java_base = cls.CPP_TO_JAVA_TYPES.get(base_type, base_type)
                return f"{java_base}[]"
        
        # Handle reference types
        if '&' in cpp_type:
            base_type = cpp_type.replace('&', '').strip()
            java_base = cls.CPP_TO_JAVA_TYPES.get(base_type, base_type)
            return java_base  # References become regular objects in Java
        
        # Direct mapping
        return cls.CPP_TO_JAVA_TYPES.get(cpp_type, cpp_type)
    
    @classmethod
    def is_basic_type(cls, cpp_type):
        """Check if the given type is a basic C++ type"""
        clean_type = cpp_type.replace('*', '').replace('&', '').strip()
        return clean_type in cls.CPP_TO_JAVA_TYPES
    
    @classmethod
    def handle_pointer_access(cls, expression, operation='get'):
        """
        Handle pointer operations in Java
        
        Args:
            expression (str): The expression to wrap
            operation (str): The operation ('get', 'set', 'address_of', etc.)
            
        Returns:
            str: The converted Java expression
        """
        if operation == 'get':
            return f"{expression}.get()"
        elif operation == 'set':
            return f"{expression}.set(value)"
        elif operation == 'address_of':
            return f"{expression}.addressOf()"
        elif operation == 'offset':
            return f"{expression}.ptrOffset(offset)"
        else:
            return expression