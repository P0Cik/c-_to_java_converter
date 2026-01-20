import clang.cindex
import re
from typing import Any, Dict, List
import time


def _get_access_level(self, node) -> str:
    """Get access level (public, private, protected) for a node"""
    access_map = {
        clang.cindex.AccessSpecifier.PUBLIC: 'public',
        clang.cindex.AccessSpecifier.PROTECTED: 'protected',
        clang.cindex.AccessSpecifier.PRIVATE: 'private',
        clang.cindex.AccessSpecifier.INVALID: 'public'
    }
    return access_map.get(node.access_specifier, 'public')


def _handle_unsupported_feature(self, feature_name: str, node) -> None:
    """Handle unsupported C++ features"""
    msg = f"Unsupported C++ feature '{feature_name}' found at {node.location.file}:{node.location.line}"

    if self.mode == "strict":
        raise ValueError(msg)
    else:
        self.warnings.append(msg)


def _get_default_value(self, java_type: str) -> str:
    """Get default return value for a Java type"""
    defaults = {
        'boolean': 'false',
        'int': '0',
        'long': '0L',
        'float': '0.0f',
        'double': '0.0',
        'char': "'\\0'",
        'byte': '(byte)0',
        'short': '(short)0'
    }
    return defaults.get(java_type, 'null')


def _map_template_type(self, cpp_type: str, template_params: List[Dict[str, Any]]) -> str:

    java_type = self._cpp_to_java_type(cpp_type)

    for param in template_params:
        if param.get('is_non_type', False):
            continue
        param_name = param['name']

        java_type = re.sub(r'\b' + re.escape(param_name) + r'\b', param_name, java_type)

    return java_type


def _convert_namespace_to_package(self, namespace: str) -> str:
    pkg = namespace.replace('::', '.')

    java_keywords = {
        'abstract', 'assert', 'boolean', 'break', 'byte', 'case', 'catch',
        'char', 'class', 'const', 'continue', 'default', 'do', 'double',
        'else', 'enum', 'extends', 'final', 'finally', 'float', 'for',
        'goto', 'if', 'implements', 'import', 'instanceof', 'int',
        'interface', 'long', 'native', 'new', 'package', 'private',
        'protected', 'public', 'return', 'short', 'static', 'strictfp',
        'super', 'switch', 'synchronized', 'this', 'throw', 'throws',
        'transient', 'try', 'void', 'volatile', 'while'
    }

    parts = []
    for part in pkg.split('.'):
        clean_part = part.lower()
        if clean_part in java_keywords:
            clean_part = f"_{clean_part}"
        if clean_part and clean_part[0].isdigit():
            clean_part = f"_{clean_part}"
        parts.append(clean_part)

    return '.'.join(parts)


def _cpp_name_to_java_name(self, cpp_name: str, naming_convention: str = "camelCase") -> str:
    if not cpp_name:
        return cpp_name

    if cpp_name.lower() in self.JAVA_RESERVED_LOWER:
        return f"_{cpp_name}"

    parts = [part for part in cpp_name.replace('-', '_').split('_') if part]

    if not parts:
        return "_unnamed"

    if naming_convention == "PascalCase":
        java_name = ''.join(part.capitalize() for part in parts)
    else:  
        java_name = parts[0].lower() + ''.join(part.capitalize() for part in parts[1:])

    if not (java_name[0].isalpha() or java_name[0] == '_'):
        java_name = '_' + java_name

    return java_name


def _convert_operator_name(self, op_name: str) -> str:
    op_mapping = {
        'operator+': 'plus',
        'operator-': 'minus',
        'operator*': 'times',
        'operator/': 'dividedBy',
        'operator%': 'modulo',
        'operator==': 'isEqualTo',          
        'operator!=': 'isNotEqualTo',
        'operator<': 'isLessThan',
        'operator>': 'isGreaterThan',
        'operator<=': 'isLessThanOrEqual',
        'operator>=': 'isGreaterThanOrEqual',
        'operator&&': 'logicalAnd',
        'operator||': 'logicalOr',
        'operator!': 'logicalNot',
        'operator&': 'bitwiseAnd',
        'operator|': 'bitwiseOr',
        'operator^': 'bitwiseXor',
        'operator<<': 'leftShift',
        'operator>>': 'rightShift',
        'operator++': 'increment',
        'operator--': 'decrement',
        'operator=': 'assign',
        'operator[]': 'get',
        'operator->': 'arrow'
    }

    result = op_mapping.get(op_name)
    if result is not None:
        return result

    if op_name.startswith('operator'):
        return 'op' + op_name[8:].replace(' ', '_')

    return op_name


def generate_report(self) -> Dict[str, Any]:
    """Generate a detailed conversion report"""
    return {
        'metadata': {
            'mode': self.mode,
            'timestamp': time.time(),
            'processed_nodes': self.ast_node_count
        },
        'stats': dict(self.last_conversion_stats) if self.last_conversion_stats else {},
        'warnings': list(self.warnings),
        'errors': list(self.errors)
    }
