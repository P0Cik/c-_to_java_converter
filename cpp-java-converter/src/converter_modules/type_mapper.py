"""Type mapping functions for the converter"""

import re


def _cpp_to_java_type(self, cpp_type: str) -> str:
    """Convert C++ type to Java type"""
    # Очищаем от const, volatile и т.п.
    clean_type = re.sub(r'\b(const|volatile|mutable|struct|class)\s+', '', cpp_type).strip()

    if clean_type.startswith('std::'):
        if clean_type.startswith('std::string'):
            return 'String'
        elif clean_type.startswith('std::vector'):
            self.java_imports.add("java.util.ArrayList")
            return 'ArrayList'
        elif clean_type.startswith('std::list'):
            self.java_imports.add("java.util.LinkedList")
            return 'LinkedList'
        elif clean_type.startswith('std::map'):
            self.java_imports.add("java.util.HashMap")
            return 'HashMap'
        elif clean_type.startswith('std::unordered_map'):
            self.java_imports.add("java.util.HashMap")
            return 'HashMap'
        elif clean_type.startswith('std::set'):
            self.java_imports.add("java.util.HashSet")
            return 'HashSet'
        elif clean_type.startswith('std::unordered_set'):
            self.java_imports.add("java.util.HashSet")
            return 'HashSet'
        elif clean_type.startswith('std::shared_ptr'):
            self.java_imports.add("java.lang.ref.WeakReference")
            return 'WeakReference'
        elif clean_type.startswith('std::unique_ptr'):
            return ''

    if clean_type == 'string':
        return 'String'
    
    cpp_to_java_types = {
        'int': 'int', 'long': 'long', 'short': 'short', 'char': 'byte',
        'wchar_t': 'char', 'bool': 'boolean', 'float': 'float', 'double': 'double',
        'void': 'void', 'unsigned int': 'int', 'unsigned long': 'long',
        'unsigned short': 'short', 'unsigned char': 'byte', 'signed char': 'byte',
        'long long': 'long', 'unsigned long long': 'long',
        'size_t': 'long'
    }

    # Указатели → массивы
    if '*' in clean_type:
        base_part = clean_type.split('*')[0].strip()
        java_base = cpp_to_java_types.get(base_part, base_part)
        return java_base + '[]'

    # Массивы
    if '[' in clean_type and ']' in clean_type:
        # Берём часть до первой [
        base_part = clean_type.split('[')[0].strip()
        java_base = cpp_to_java_types.get(base_part, base_part)
        dim_count = clean_type.count('[')
        return java_base + '[]' * dim_count

    # Ссылки → обычный тип
    if clean_type.endswith('&'):
        clean_type = clean_type[:-1].strip()

    return cpp_to_java_types.get(clean_type, clean_type)