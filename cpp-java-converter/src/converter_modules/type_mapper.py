"""Type mapping functions for the converter"""

import re


def _cpp_to_java_type(self, cpp_type: str) -> str:
    """Convert C++ type to Java type"""
    # Очищаем от const, volatile и т.п.
    clean_type = re.sub(r'\b(const|volatile|mutable|struct|class)\s+', '', cpp_type).strip()

    cpp_to_java_types = {
        'int': 'int', 'long': 'long', 'short': 'short', 'char': 'byte',
        'wchar_t': 'char', 'bool': 'boolean', 'float': 'float', 'double': 'double',
        'void': 'void', 'unsigned int': 'int', 'unsigned long': 'long',
        'unsigned short': 'short', 'unsigned char': 'byte', 'signed char': 'byte',
        'long long': 'long', 'unsigned long long': 'long',
        'size_t': 'long', 'std::string': 'String', 'string': 'String'
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