"""Code generation functions for the converter"""

import re
from typing import Any, Dict, List


def _generate_java_code(self, java_ast: List[Any]) -> str:
    # 1. Извлекаем package
    package_line = None
    classes = []
    enums = []
    global_functions = []
    constants = []
    other_lines = []

    for element in java_ast:
        elem_type = element.get('kind', '')
        if elem_type == 'namespace':
            pkg_name = self._convert_namespace_to_package(element['name'])
            package_line = f"package {pkg_name};"
        elif elem_type == 'class':
            classes.append(self._generate_java_class(element))
        elif elem_type == 'enum':
            enums.append(self._generate_java_enum(element))
        elif elem_type == 'function':
            global_functions.append(element)
        elif elem_type == 'macro_constant':
            java_type = self._cpp_to_java_type(element.get('underlying_type', 'int'))
            java_name = self._cpp_name_to_java_name(element['name']).upper()
            constants.append(f"public static final {java_type} {java_name} = {element['value']};")
        elif elem_type == 'variable':
            constants.append(self._generate_java_variable(element))
        elif elem_type in ('class_template', 'function_template'):
            # Генерируем заглушки или предупреждения
            other_lines.append(f"// Template '{element['name']}' not fully supported in Java")
        elif elem_type == 'typedef':
            other_lines.append(f"// typedef {element['name']} = {element['underlying_type']};")
        elif elem_type == 'conversion_operator':
            other_lines.append(f"// Conversion operator to {element['target_type']}")

    # 2. Генерируем единый Util-класс для всех функций
    for element in java_ast:
        if element.get('kind') in ('function', 'function_template'):
            global_functions.append(element)

    if global_functions:
        other_lines.append(self._generate_util_class(global_functions))

    # 3. Собираем всё вместе
    lines = []
    if package_line:
        lines.append(package_line)
        lines.append("")

    # Импорты (если есть)
    if self.java_imports:
        for imp in sorted(self.java_imports):
            lines.append(f"import {imp};")
        lines.append("")

    # Константы на уровне файла (в Java они должны быть внутри класса!)
    if constants:
        # Создаём отдельный класс для констант, например Constants
        const_class = self._generate_constants_class(constants)
        classes.insert(0, const_class)

    lines.extend(classes)
    lines.extend(enums)
    lines.extend(other_lines)

    return '\n'.join(lines)


def _generate_java_class(self, class_info: Dict[str, Any]) -> str:
    java_lines = []

    # Determine modifiers
    modifiers = ["public"]
    if class_info.get('is_final', False):
        modifiers.append("final")
    # Убираем автоматическое добавление 'abstract' – слишком рискованно
    # elif any(...): ...

    # Handle inheritance and AutoCloseable
    extends_clause = ""
    implements_parts = []

    base_classes = class_info.get('base_classes', [])
    if base_classes:
        java_bases = []
        for base in base_classes:
            base_name = base['name']
            java_base_name = self._cpp_name_to_java_name(base_name)
            if len(java_bases) == 0:
                java_bases.append(java_base_name)
            else:
                implements_parts.append(java_base_name)

        if java_bases:
            extends_clause = f" extends {java_bases[0]}"

    # Add AutoCloseable if destructor exists
    has_destructor = bool(class_info.get('destructors'))
    if has_destructor:
        self.java_imports.add("java.lang.AutoCloseable")
        implements_parts.append("AutoCloseable")

    implements_clause = ""
    if implements_parts:
        implements_clause = f" implements {', '.join(implements_parts)}"

    # Start class declaration
    class_name = self._cpp_name_to_java_name(class_info['name'])
    java_lines.append(f"{' '.join(modifiers)} class {class_name}{extends_clause}{implements_clause} {{")
    java_lines.append("")

    # Add fields
    for field in class_info.get('members', []):
        access = field.get('access', 'private')
        java_type = self._cpp_to_java_type(field['type'])
        java_name = self._cpp_name_to_java_name(field['name'])
        static_keyword = "static " if field.get('is_static', False) else ""
        final_keyword = "final " if field.get('is_const', False) else ""
        java_lines.append(f"    {access} {static_keyword}{final_keyword}{java_type} {java_name};")

    java_lines.append("")

    # Add constructors
    for constructor in class_info.get('constructors', []):
        params = ", ".join([
            f"{self._cpp_to_java_type(p['type'])} {self._cpp_name_to_java_name(p['name'])}"
            for p in constructor.get('parameters', [])
        ])
        java_lines.append(f"    public {class_name}({params}) {{")
        java_lines.append("        // Constructor implementation")
        java_lines.append("    }")
        java_lines.append("")

    # Add destructor as close()
    if has_destructor:
        java_lines.append("    @Override")
        java_lines.append("    public void close() {")
        java_lines.append("        // Emulated destructor")
        java_lines.append("    }")
        java_lines.append("")

    # Add methods
    has_equals = False
    for method in class_info.get('methods', []):
        method_lines = self._generate_java_method(method, class_name)
        # Check if this is equals
        if any("public boolean equals(" in line for line in method_lines):
            has_equals = True
        java_lines.extend(method_lines)
        java_lines.append("")

    # Add hashCode if equals is present
    if has_equals:
        java_lines.append("    @Override")
        java_lines.append("    public int hashCode() {")
        java_lines.append("        // TODO: Generate proper hash code based on fields")
        java_lines.append("        return super.hashCode();")
        java_lines.append("    }")
        java_lines.append("")

    java_lines.append("}")
    return '\n'.join(java_lines)


def _generate_java_method(self, method_info: Dict[str, Any], class_name: str) -> List[str]:
    """Generate Java method from C++ method info"""
    # Determine access level
    access = method_info.get('access', 'public')
    modifiers = [access]

    # Add @Override if needed
    if method_info.get('is_override', False):
        modifiers.insert(0, '@Override')

    # Handle static/final
    if method_info.get('is_static', False):
        modifiers.append('static')
    if method_info.get('is_final', False):
        modifiers.append('final')

    # Handle operator overloads
    original_name = method_info['name']
    method_name = original_name
    is_equals = False
    is_hash_code = False

    if original_name.startswith('operator'):
        method_name = self._convert_operator_name(original_name)
        if method_name == 'equals':
            is_equals = True
            method_name = 'equals'
        elif method_name == 'hashCode':
            is_hash_code = True
            method_name = 'hashCode'

    # Special handling for equals: enforce correct signature
    if is_equals:
        return_type = 'boolean'
        param_str = 'Object obj'
        if '@Override' not in modifiers:
            modifiers.insert(0, '@Override')
    else:
        return_type = self._cpp_to_java_type(method_info['return_type'])
        # Handle parameters normally
        params = []
        for param in method_info.get('parameters', []):
            param_type = self._cpp_to_java_type(param['type'])
            param_name = self._cpp_name_to_java_name(param['name'])
            params.append(f"{param_type} {param_name}")
        param_str = ", ".join(params)

    # Generate method
    java_lines = []
    java_lines.append(f"    {' '.join(modifiers)} {return_type} {method_name}({param_str}) {{")
    java_lines.append("        // Method implementation")

    if is_equals:
        java_lines.append("        if (this == obj) return true;")
        java_lines.append("        if (obj == null || getClass() != obj.getClass()) return false;")
        java_lines.append("        // TODO: Compare relevant fields")
        java_lines.append("        return true;")
    elif return_type != 'void':
        java_lines.append(f"        return {self._get_default_value(return_type)}; // TODO: Implement")

    java_lines.append("    }")
    return java_lines


def _generate_util_class(self, functions: List[Dict[str, Any]]) -> str:
    """Generate a single utility class containing all global and template functions"""
    if not functions:
        return ""

    lines = ["public class Util {"]

    for func in functions:
        is_template = func.get('kind') == 'function_template'

        if is_template:
            # Обработка шаблонной функции
            template_params = func['template_parameters']
            type_param_names = [p['name'] for p in template_params if not p.get('is_non_type', False)]
            generics_clause = f"<{', '.join(type_param_names)}> " if type_param_names else ""

            # Используем исходную функцию внутри
            inner_func = func['function_info']
            access = inner_func.get('access', 'public')
            return_type = self._map_template_type(inner_func['return_type'], template_params)
            func_name = self._cpp_name_to_java_name(inner_func['name'])

            params = []
            for param in inner_func.get('parameters', []):
                param_type = self._map_template_type(param['type'], template_params)
                param_name = self._cpp_name_to_java_name(param['name'])
                params.append(f"{param_type} {param_name}")
            param_str = ", ".join(params)

            lines.append(f"    {access} static {generics_clause}{return_type} {func_name}({param_str}) {{")
            lines.append("        // Template function implementation")
            if return_type != 'void':
                lines.append(f"        return {self._get_default_value(return_type)}; // TODO: Implement")
            lines.append("    }")

        else:
            # Обработка обычной функции
            access = func.get('access', 'public')
            return_type = self._cpp_to_java_type(func['return_type'])
            func_name = self._cpp_name_to_java_name(func['name'])
            params = []
            for param in func.get('parameters', []):
                param_type = self._cpp_to_java_type(param['type'])
                param_name = self._cpp_name_to_java_name(param['name'])
                params.append(f"{param_type} {param_name}")
            param_str = ", ".join(params)

            lines.append(f"    {access} static {return_type} {func_name}({param_str}) {{")
            lines.append("        // Function implementation")
            if return_type != 'void':
                lines.append(f"        return {self._get_default_value(return_type)}; // TODO: Implement")
            lines.append("    }")

        lines.append("")  # Empty line between methods

    lines.append("}")
    return '\n'.join(lines)


def _generate_globals_class(self, variables: List[Dict[str, Any]]) -> str:
    """Generate a class containing all global variables as static fields"""
    if not variables:
        return ""

    lines = ["public class Globals {"]

    for var in variables:
        access = 'public'
        static_keyword = "static " if var.get('is_static', True) else ""
        final_keyword = "final " if var.get('is_const', False) else ""
        java_type = self._cpp_to_java_type(var['type'])
        java_name = self._cpp_name_to_java_name(var['name'])

        # Добавляем инициализацию по умолчанию
        default_value = self._get_default_value(java_type)
        lines.append(f"    {access} {static_keyword}{final_keyword}{java_type} {java_name} = {default_value};")

    lines.append("}")
    return '\n'.join(lines)


def _generate_java_enum(self, enum_info: Dict[str, Any]) -> str:
    """Generate Java enum from C++ enum"""
    enum_name = self._cpp_name_to_java_name(enum_info['name'])
    values = enum_info.get('values', [])

    if not values:
        return f"public enum {enum_name} {{\n    // Empty enum\n}}"

    # Проверяем, есть ли нестандартные значения (требуется тело enum)
    has_custom_values = any(val.get('value', i) != i for i, val in enumerate(values))

    lines = [f"public enum {enum_name} {{"]

    # Генерируем значения
    value_lines = []
    for i, val in enumerate(values):
        name = val['name'].upper()
        if has_custom_values:
            # Сохраняем оригинальное значение
            value = val.get('value', i)
            value_lines.append(f"    {name}({value})")
        else:
            value_lines.append(f"    {name}")

    if has_custom_values:
        # Добавляем конструктор и поле
        lines.extend(value_lines)
        lines.append("    ;")
        lines.append("")
        lines.append("    private final int value;")
        lines.append("")
        lines.append("    private " + enum_name + "(int value) {")
        lines.append("        this.value = value;")
        lines.append("    }")
        lines.append("")
        lines.append("    public int getValue() {")
        lines.append("        return value;")
        lines.append("    }")
    else:
        # Простой enum без тела
        lines.append(", ".join(v.strip() for v in value_lines) + "")

    lines.append("}")
    return '\n'.join(lines)


def _generate_imports(self) -> str:
    """Generate Java import statements based on needed utilities"""
    if not self.java_imports:
        return ""

    imports = []
    for imp in sorted(self.java_imports):
        imports.append(f"import {imp};")

    return '\n'.join(imports) + '\n\n' if imports else ""


def _generate_constants_class(self, constants: List[str]) -> str:
    """Generate a class containing all constants"""
    lines = ["public class Constants {"]
    for const in constants:
        lines.append(f"    {const}")
    lines.append("}")
    return '\n'.join(lines)


def _generate_java_variable(self, variable_info: Dict[str, Any]) -> str:
    """Generate Java variable from C++ variable info"""
    access = "public"
    static_keyword = "static " if variable_info.get('is_static', True) else ""
    final_keyword = "final " if variable_info.get('is_const', False) else ""
    java_type = self._cpp_to_java_type(variable_info['type'])
    java_name = self._cpp_name_to_java_name(variable_info['name'])

    return f"    {access} {static_keyword}{final_keyword}{java_type} {java_name};"