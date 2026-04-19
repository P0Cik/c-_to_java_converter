"""Code generation functions for the converter"""

import re
from typing import Any, Dict, List


def _generate_java_code(self, java_ast: List[Any]) -> str:
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
        elif elem_type in ('function', 'function_template'):
            if element.get('name') == 'main':
                classes.append(self._generate_main_class(element))
            else:
                global_functions.append(element)
        elif elem_type == 'macro_constant':
            java_type = self._cpp_to_java_type(element.get('underlying_type', 'int'))
            java_name = self._cpp_name_to_java_name(element['name']).upper()
            constants.append(f"public static final {java_type} {java_name} = {element['value']};")
        elif elem_type == 'variable':
            constants.append(element)
        elif elem_type in ('class_template', 'function_template'):

            other_lines.append(f"// Template '{element['name']}' not fully supported in Java")
        elif elem_type == 'typedef':
            other_lines.append(f"// typedef {element['name']} = {element['underlying_type']};")
        elif elem_type == 'conversion_operator':
            other_lines.append(f"// Conversion operator to {element['target_type']}")

    if global_functions:
        other_lines.append(self._generate_util_class(global_functions))


    lines = []
    if package_line:
        lines.append(package_line)
        lines.append("")

    if self.java_imports:
        for imp in sorted(self.java_imports):
            lines.append(f"import {imp};")
        lines.append("")

    if constants:
        const_class = self._generate_globals_class(constants)
        classes.insert(0, const_class)

    lines.extend(classes)
    lines.extend(enums)
    lines.extend(other_lines)

    return '\n'.join(lines)


def _generate_java_class(self, class_info: Dict[str, Any]) -> str:
    java_lines = []
    modifiers = []
    if class_info.get('is_abstract', False):
        modifiers.append("abstract")
    if class_info.get('is_final', False):
        modifiers.append("final")

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


    has_destructor = bool(class_info.get('destructors'))
    if has_destructor:
        self.java_imports.add("java.lang.AutoCloseable")
        implements_parts.append("AutoCloseable")

    implements_clause = ""
    if implements_parts:
        implements_clause = f" implements {', '.join(implements_parts)}"


    class_name = self._cpp_name_to_java_name(class_info['name'])
    java_lines.append(f"{' '.join(modifiers)} class {class_name}{extends_clause}{implements_clause} {{")
    java_lines.append("")


    for field in class_info.get('members', []):
        access = field.get('access', 'private')
        java_type = self._cpp_to_java_type(field['type'])
        java_name = self._cpp_name_to_java_name(field['name'])
        static_keyword = "static " if field.get('is_static', False) else ""
        final_keyword = "final " if field.get('is_const', False) else ""
        init_value = field.get('init_value')
        if init_value is not None:
            java_init_value = self._cpp_literal_to_java(init_value)
            java_lines.append(f"    {access} {static_keyword}{final_keyword}{java_type} {java_name} = {java_init_value};")
        else:
            java_lines.append(f"    {access} {static_keyword}{final_keyword}{java_type} {java_name};")

    java_lines.append("")


    for constructor in class_info.get('constructors', []):
        params = ", ".join([
            f"{self._cpp_to_java_type(p['type'])} {self._cpp_name_to_java_name(p['name'])}"
            for p in constructor.get('parameters', [])
        ])
        if constructor.get('body'):
            body_code = self._generate_block(constructor['body'], 1)
            java_lines.append(f"    public {class_name}({params}) {body_code}")
        else:
            java_lines.append(f"    public {class_name}({params}) {{")
            java_lines.append("    }")
        java_lines.append("")


    if has_destructor:
        java_lines.append("    @Override")
        if class_info['destructors'][0].get('body'):
            body_code = self._generate_block(class_info['destructors'][0]['body'], 1)
            java_lines.append(f"    public void close() {body_code}")
        else:
            java_lines.append("    public void close() {")
            java_lines.append("    }")
        java_lines.append("")


    has_equals = False
    for method in class_info.get('methods', []):
        method_lines = self._generate_java_method(method, class_name)

        if any("public boolean equals(" in line for line in method_lines):
            has_equals = True
        java_lines.extend(method_lines)
        java_lines.append("")


    if has_equals:
        java_lines.append("    @Override")
        java_lines.append("    public int hashCode() {")
        java_lines.append("        // TODO: Generate proper hash code based on fields")
        java_lines.append("        return super.hashCode();")
        java_lines.append("    }")
        java_lines.append("")

    java_lines.append("}")
    return '\n'.join(java_lines)

def _generate_main_class(self, main_func: Dict[str, Any]) -> str:
    """Generate Java Main class from C++ main function"""
    lines = ["public class Main {"]
    
    if main_func.get('body'):
        body_str = self._generate_block(main_func['body'], 1)
        # Replace 'return 0;' with 'return;' since Java main is void
        body_str = body_str.replace("return 0;", "return;")
        lines.append(f"    public static void main(String[] args) {body_str}")
    else:
        lines.append("    public static void main(String[] args) {}")
        
    lines.append("}")
    return '\n'.join(lines)


def _generate_java_method(self, method_info: Dict[str, Any], class_name: str) -> List[str]:
    """Generate Java method from C++ method info"""

    access = method_info.get('access', 'public')
    modifiers = [access]


    if method_info.get('is_override', False):
        modifiers.insert(0, '@Override')


    if method_info.get('is_static', False):
        modifiers.append('static')
    if method_info.get('is_final', False):
        modifiers.append('final')
    if method_info.get('is_pure_virtual', False):
        modifiers.append('abstract')


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

   
    if is_equals:
        return_type = 'boolean'
        param_str = 'Object obj'
        if '@Override' not in modifiers:
            modifiers.insert(0, '@Override')
    else:
        return_type = self._cpp_to_java_type(method_info['return_type'])

        params = []
        for param in method_info.get('parameters', []):
            param_type = self._cpp_to_java_type(param['type'])
            param_name = self._cpp_name_to_java_name(param['name'])
            params.append(f"{param_type} {param_name}")
        param_str = ", ".join(params)

 
    java_lines = []
    
    if is_equals and method_info.get('body') is None:
        java_lines.append(f"    {' '.join(modifiers)} {return_type} {method_name}({param_str}) {{")
        java_lines.append("        if (this == obj) return true;")
        java_lines.append("        if (obj == null || getClass() != obj.getClass()) return false;")
        java_lines.append("        // TODO: Compare relevant fields")
        java_lines.append("        return true;")
        java_lines.append("    }")
    elif method_info.get('is_pure_virtual', False):
        java_lines.append(f"    {' '.join(modifiers)} {return_type} {method_name}({param_str});")
    else:
        if method_info.get('body'):
            body_code = self._generate_block(method_info['body'], 1)
            java_lines.append(f"    {' '.join(modifiers)} {return_type} {method_name}({param_str}) {body_code}")
        else:
            java_lines.append(f"    {' '.join(modifiers)} {return_type} {method_name}({param_str}) {{")
            if return_type != 'void' and return_type:
                java_lines.append(f"        return {self._get_default_value(return_type)}; // TODO: Implement")
            java_lines.append("    }")

    return java_lines


def _generate_util_class(self, functions: List[Dict[str, Any]]) -> str:
    """Generate a single utility class containing all global and template functions"""
    if not functions:
        return ""

    lines = ["class Util {"]

    for func in functions:
        is_template = func.get('kind') == 'function_template'

        if is_template:

            template_params = func['template_parameters']
            type_param_names = [p['name'] for p in template_params if not p.get('is_non_type', False)]
            generics_clause = f"<{', '.join(type_param_names)}> " if type_param_names else ""


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

        lines.append("")

    lines.append("}")
    return '\n'.join(lines)


def _generate_globals_class(self, variables: List[Any]) -> str:
    """Generate a class containing all global variables as static fields"""
    if not variables:
        return ""

    lines = ["class Globals {"]

    for var in variables:
        if isinstance(var, str):
            lines.append(f"    {var}")
            continue
            
        access = 'public'
        static_keyword = "static " if var.get('is_static', True) else ""
        final_keyword = "final " if var.get('is_const', False) else ""
        java_type = self._cpp_to_java_type(var['type'])
        java_name = self._cpp_name_to_java_name(var['name'])


        init_value = var.get('init_value')
        if init_value is not None:
            java_init_value = self._cpp_literal_to_java(init_value)
            lines.append(f"    {access} {static_keyword}{final_keyword}{java_type} {java_name} = {java_init_value};")
        else:
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

    
    has_custom_values = any(val.get('value', i) != i for i, val in enumerate(values))

    lines = [f"public enum {enum_name} {{"]


    value_lines = []
    for i, val in enumerate(values):
        name = val['name'].upper()
        if has_custom_values:

            value = val.get('value', i)
            value_lines.append(f"    {name}({value})")
        else:
            value_lines.append(f"    {name}")

    if has_custom_values:

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
    access = "public"
    static_keyword = "static " if variable_info.get('is_static', True) else ""
    final_keyword = "final " if variable_info.get('is_const', False) else ""
    java_type = self._cpp_to_java_type(variable_info['type'])
    java_name = self._cpp_name_to_java_name(variable_info['name'])

    array_size = variable_info.get('array_size')
    if array_size is not None:

        element_type = variable_info.get('element_type', variable_info['type'])
        if 'char' in element_type.lower():
            element_java_type = 'byte'
            java_type = 'byte[]'
        else:
            element_java_type = self._cpp_to_java_type(element_type)
            if not element_java_type.endswith('[]'):
                java_type = f'{element_java_type}[]'
            else:
                java_type = element_java_type
        
        return f"    {access} {static_keyword}{final_keyword}{java_type} {java_name} = new {element_java_type}[{array_size}];"
    
    init_value = variable_info.get('init_value')
    if init_value is not None:
        java_init_value = self._cpp_literal_to_java(init_value)
        return f"    {access} {static_keyword}{final_keyword}{java_type} {java_name} = {java_init_value};"
    
    # No initializer - use Java default value
    default_value = self._get_default_value(java_type)
    return f"    {access} {static_keyword}{final_keyword}{java_type} {java_name} = {default_value};"

def _generate_statement(self, stmt: Dict[str, Any], indent_level: int = 2) -> str:
    """Генерация кода для одного оператора с правильным отступом"""
    indent = "    " * indent_level
    
    if stmt['kind'] == 'if_stmt':
        condition = self._generate_expression(stmt['condition'])
        then_body = self._generate_block(stmt['then_body'], indent_level)
        
        code = f"{indent}if ({condition}) {then_body}"
        
        if stmt.get('else_body'):
            else_body = self._generate_block(stmt['else_body'], indent_level)
            # Проверка на вложенный if-else для правильного форматирования
            if stmt['else_body'].get('kind') == 'if_stmt':
                code += f" else {else_body}"
            else:
                code += f"\n{indent}else {else_body}"
        return code
    
    elif stmt['kind'] == 'for_stmt':
        init = self._generate_expression(stmt['init']) if stmt.get('init') else ""
        condition = self._generate_expression(stmt['condition']) if stmt.get('condition') else "true"
        increment = self._generate_expression(stmt['increment']) if stmt.get('increment') else ""
        
        # Форматирование: for (init; condition; increment) { body }
        header = f"for ({init}; {condition}; {increment})"
        body = self._generate_block(stmt['body'], indent_level)
        return f"{indent}{header} {body}"
    
    elif stmt['kind'] == 'while_stmt':
        condition = self._generate_expression(stmt['condition'])
        body = self._generate_block(stmt['body'], indent_level)
        return f"{indent}while ({condition}) {body}"
    
    elif stmt['kind'] == 'do_stmt':
        body = self._generate_block(stmt['body'], indent_level)
        condition = self._generate_expression(stmt['condition'])
        # do-while в Java требует точки с запятой после условия
        return f"{indent}do {body}\n{indent}while ({condition});"
    
    elif stmt['kind'] == 'return_stmt':
        value = self._generate_expression(stmt['value']) if stmt.get('value') else ""
        return f"{indent}return {value};"
    
    elif stmt['kind'] == 'compound_stmt':
        return self._generate_block(stmt, indent_level)
    
    elif stmt['kind'] == 'decl_stmt':
        # Объявление локальной переменной
        var_type = self._cpp_to_java_type(stmt['type'])
        var_name = self._cpp_name_to_java_name(stmt['name'])
        
        array_size = stmt.get('array_size')
        if array_size is not None:
            elem_type = stmt.get('element_type') or "int"
            java_elem_type = self._cpp_to_java_type(elem_type)
            if not java_elem_type.endswith('[]'):
                var_type = f"{java_elem_type}[]"
            else:
                var_type = java_elem_type
            
            init = f" = new {java_elem_type}[{array_size}]"
            return f"{indent}{var_type} {var_name}{init};"

        init_val = stmt.get('init_value')
        if init_val is not None:
            if isinstance(init_val, dict):
                java_init = self._generate_expression(init_val)
            else:
                java_init = self._cpp_literal_to_java(str(init_val))
            init = f" = {java_init}"
        else:
            init = ""

        return f"{indent}{var_type} {var_name}{init};"
    
    elif stmt['kind'] == 'expr_stmt':
        expr = self._generate_expression(stmt['expression'])
        return f"{indent}{expr};"
    
    else:
        return f"{indent}// TODO: Unsupported statement type: {stmt['kind']}"

def _generate_block(self, block: Dict[str, Any], indent_level: int = 2) -> str:
    """Генерация блока кода { ... } с правильной индентацией"""
    if not block or block.get('kind') != 'compound_stmt':
        # Если нет блока — оборачиваем в {}
        inner = self._generate_statement(block, indent_level + 1) if block else f"{'    ' * (indent_level + 1)}// empty"
        return f"{{\n{inner}\n{'    ' * indent_level}}}"
    
    statements = block.get('statements', [])
    if not statements:
        return "{\n" + "    " * indent_level + "}"
    
    inner_lines = []
    for stmt in statements:
        inner_lines.append(self._generate_statement(stmt, indent_level + 1))
    
    inner = "\n".join(inner_lines)
    return f"{{\n{inner}\n{'    ' * indent_level}}}"

def _generate_expression(self, expr: Dict[str, Any]) -> str:
    """Генерация выражения с рекурсивной обработкой подвыражений"""
    if not expr:
        return ""
        
    if isinstance(expr, str):
        return self._cpp_literal_to_java(expr)
    
    kind = expr.get('kind', '')
    
    if kind == 'literal':
        return expr['value']
    
    elif kind == 'identifier':
        return self._cpp_name_to_java_name(expr['name'])
    
    elif kind == 'binary_op':
        left = self._generate_expression(expr['left'])
        right = self._generate_expression(expr['right'])
        return f"{left} {expr['op']} {right}"
    
    elif kind == 'unary_op':
        operand = self._generate_expression(expr['operand'])
        # Особый случай: ! для булевых значений
        if expr['op'] == '!':
            return f"!{operand}"
        # Инкремент/декремент
        elif expr['op'] in ('++', '--'):
            return f"{expr['op']}{operand}"  # prefix
        else:
            return f"{expr['op']}{operand}"
    
    elif kind == 'constructor_call':
        class_type = self._cpp_to_java_type(expr.get('type', ''))
        args = ", ".join(self._generate_expression(arg) for arg in expr.get('arguments', []))
        if class_type == "String" and len(expr.get('arguments', [])) == 1:
            return self._generate_expression(expr.get('arguments', [])[0])
        return f"new {class_type}({args})"

    elif kind == 'call':
        callee_orig = expr.get('callee_orig', '')
        args_ast = expr.get('arguments', [])
        
        # Специальная трансляция для std::cout << ...
        if "operator<<" in callee_orig or callee_orig == "<<":
            if len(args_ast) == 2:
                left_ast, right_ast = args_ast[0], args_ast[1]
            elif len(args_ast) == 1:
                right_ast = args_ast[0]
                left_ast = expr.get('callee', {}).get('base') if expr.get('callee', {}).get('kind') == 'member_access' else None
            else:
                left_ast = right_ast = None
                
            if left_ast and right_ast:
                left = self._generate_expression(left_ast)
                right = self._generate_expression(right_ast)
                if right == "endl" or "std::endl" in right:
                    right = '"\\n"'
                
                if left == "cout" or left == "std::cout":
                    return f"System.out.print({right})"
                elif left.startswith("System.out.print("):
                    inner = left[17:-1]
                    return f"System.out.print({inner} + {right})" if inner else f"System.out.print({right})"
                else:
                    return f"{left} << {right}"

        callee_str = self._generate_expression(expr.get('callee', {}))
        args = ", ".join(self._generate_expression(arg) for arg in args_ast)
        return f"{callee_str}({args})"
    
    elif kind == 'member_access':
        base = self._generate_expression(expr['base'])
        member = self._cpp_name_to_java_name(expr['member'])
        # В Java всегда используется точка, даже для указателей
        return f"{base}.{member}"
    
    elif kind == 'unknown_expr':
        return expr.get('repr', '/* unknown */')
    
    else:
        return f"/* {kind} */"

def _cpp_literal_to_java(self, cpp_literal: str) -> str:
    """Convert C++ literal to Java equivalent"""
    
    if cpp_literal.startswith('"') and cpp_literal.endswith('"'):
        inner_content = cpp_literal[1:-1]
        return f'"{inner_content}"'  
    elif cpp_literal.startswith("'") and cpp_literal.endswith("'"):
        return cpp_literal
    elif cpp_literal.lower() in ('true', 'false'):
        return cpp_literal.lower()  
    else:
        
        return cpp_literal