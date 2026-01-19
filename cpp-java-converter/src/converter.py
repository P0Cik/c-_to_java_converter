import clang.cindex
import re
import json
from typing import Any, Dict, List, Optional
import tempfile
import logging
from datetime import datetime
import time
# clang.cindex.Config.set_library_path("C:/Dev/c-_to_java_converter/venv/Lib/site-packages/clang/native")

class CppToJavaConverter:
    """
    Converts C++ source code to Java source code
    Implements AST-based parsing with libclang and comprehensive transformation rules
    """

    def __init__(self, mode: str = "strict", verbose: bool = False):
        """
        Initialize converter with specified mode

        Args:
            mode (str): "strict" or "flexible" conversion mode
            verbose (bool): Enable verbose logging
        """
        

        self.mode = mode
        self.verbose = verbose
        self.logger = logging.getLogger(__name__) if verbose else logging.getLogger()

        # Initialize tracking variables
        self.classes = {}
        self.variables = {}
        self.functions = {}
        self.current_scope = []
        self.java_imports = set()
        self.warnings = []
        self.errors = []
        self.ast_node_count = 0
        self.last_conversion_stats = {}

        

    def convert(self, cpp_code: str, source_file_path: Optional[str] = None) -> str:
        """
        Convert C++ code to Java code using AST parsing

        Args:
            cpp_code (str): Input C++ source code
            source_file_path (str, optional): Path to source file for context

        Returns:
            str: Converted Java source code
        """
        # Reset state for new conversion
        self.classes = {}
        self.variables = {}
        self.functions = {}
        self.current_scope = []
        self.java_imports = set()
        self.warnings = []
        self.errors = []
        self.ast_node_count = 0

        try:
            # Parse C++ code using libclang
            ast = self._parse_with_libclang(cpp_code, source_file_path)

            # Transform AST to Java representation
            java_ast = self._transform_ast(ast)

            # Generate Java code from transformed AST
            java_code = self._generate_java_code(java_ast)

            # Generate imports section
            imports_section = self._generate_imports()

            # Combine imports and main code
            full_java_code = imports_section + java_code

            # Record statistics
            self.last_conversion_stats = {
                'ast_nodes': self.ast_node_count,
                'warnings_count': len(self.warnings),
                'errors_count': len(self.errors),
                'conversion_time': datetime.now().isoformat()
            }

            return full_java_code

        except Exception as e:
            error_msg = f"Conversion failed: {str(e)}"
            self.errors.append(error_msg)
            if self.mode == "strict":
                raise
            else:
                # In flexible mode, return a stub with error comment
                return f"// TODO: Manual fix required - conversion failed due to: {str(e)}\n// Original code was not converted."

    def _parse_with_libclang(self, cpp_code: str, source_file_path: Optional[str] = None) -> Any:
        """Parse C++ code using libclang and return AST"""
        # Write temporary file for libclang to parse

        if source_file_path is None:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp', delete=False) as temp_file:
                temp_file.write(cpp_code)
                temp_filename = temp_file.name
        else:
            temp_filename = source_file_path  # Use provided path if available

        try:
            # Create index and translation unit
            index = clang.cindex.Index.create()

            # Parse with standard C++17
            args = ['-std=c++17', '-I/usr/include/c++/v1', '-I/usr/include']  # Common include paths

            tu = index.parse(temp_filename, args=args)

            if not tu.cursor:
                raise ValueError("Failed to parse C++ code - invalid syntax")

            # Validate AST
            self._validate_ast(tu)

            return tu

        finally:
            # Clean up temp file if we created one
            if source_file_path is None:
                import os
                os.unlink(temp_filename)

    def _validate_ast(self, tu) -> bool:
        """Validate AST for semantic correctness"""
        diagnostics = []
        for diag in tu.diagnostics:
            if diag.severity >= clang.cindex.Diagnostic.Error:
                diagnostics.append(f"Error: {diag.spelling} at {diag.location.file}:{diag.location.line}")
            elif diag.severity >= clang.cindex.Diagnostic.Warning:
                self.warnings.append(f"Warning: {diag.spelling} at {diag.location.file}:{diag.location.line}")

        if diagnostics:
            raise ValueError("C++ code has compilation errors:\n" + "\n".join(diagnostics))

        return True

    def _transform_ast(self, tu) -> List[Any]:
        """Transform C++ AST to internal representation suitable for Java generation"""
        java_ast = []

        def traverse(node, depth=0):
            self.ast_node_count += 1

            # Handle different kinds of declarations
            if node.kind == clang.cindex.CursorKind.CLASS_DECL:
                java_ast.append(self._handle_class_declaration(node))
            elif node.kind == clang.cindex.CursorKind.FUNCTION_DECL:
                java_ast.append(self._handle_function_declaration(node))
            elif node.kind == clang.cindex.CursorKind.VAR_DECL:
                java_ast.append(self._handle_variable_declaration(node))
            elif node.kind == clang.cindex.CursorKind.NAMESPACE:
                java_ast.append(self._handle_namespace(node))
            elif node.kind == clang.cindex.CursorKind.TEMPLATE_TYPE_PARAMETER:
                java_ast.append(self._handle_template_parameter(node))
            elif node.kind == clang.cindex.CursorKind.CONSTRUCTOR:
                java_ast.append(self._handle_constructor(node))
            elif node.kind == clang.cindex.CursorKind.DESTRUCTOR:
                java_ast.append(self._handle_destructor(node))
            elif node.kind == clang.cindex.CursorKind.TYPEDEF_DECL:
                java_ast.append(self._handle_typedef(node))
            elif node.kind == clang.cindex.CursorKind.MACRO_DEFINITION:
                java_ast.append(self._handle_macro_definition(node))
            elif node.kind == clang.cindex.CursorKind.UNION_DECL:
                self._handle_unsupported_feature("union declaration", node)
            elif node.kind == clang.cindex.CursorKind.ENUM_DECL:
                java_ast.append(self._handle_enum_declaration(node))
            elif node.kind == clang.cindex.CursorKind.CLASS_TEMPLATE:
                java_ast.append(self._handle_class_template(node))
            elif node.kind == clang.cindex.CursorKind.FUNCTION_TEMPLATE:
                java_ast.append(self._handle_function_template(node))
            elif node.kind == clang.cindex.CursorKind.CONVERSION_FUNCTION:
                java_ast.append(self._handle_conversion_function(node))
            else:
                # Log unhandled node types for debugging
                if self.verbose:
                    self.logger.debug(f"Unhandled node kind: {node.kind}, spelling: {node.spelling}")

            # Continue traversal for children
            for child in node.get_children():
                traverse(child, depth + 1)

        traverse(tu.cursor)
        return java_ast

    def _handle_class_declaration(self, node) -> Dict[str, Any]:
        """Handle C++ class declaration and convert to Java class"""
        class_info = {
            'kind': 'class',
            'name': node.spelling or 'AnonymousClass',
            'members': [],
            'methods': [],
            'constructors': [],
            'destructors': [],
            'base_classes': [],
            'access_specifier': 'public',  # Default in Java
            'is_abstract': False,
            'is_final': False,
            'templates': [],
            'location': f"{node.location.file}:{node.location.line}"
        }

        # Process children to gather class information
        for child in node.get_children():
            if child.kind == clang.cindex.CursorKind.CXX_BASE_SPECIFIER:  # ✅ ИСПРАВЛЕНО
                # Handle inheritance
                base_class_name = child.type.spelling
                if base_class_name:
                    access_modifier = "public" if child.access_specifier == clang.cindex.AccessSpecifier.PUBLIC else "private"
                    class_info['base_classes'].append({
                        'name': base_class_name,
                        'access': access_modifier
                    })

            elif child.kind == clang.cindex.CursorKind.CXX_METHOD:
                method_info = self._handle_method(child)
                class_info['methods'].append(method_info)

            elif child.kind == clang.cindex.CursorKind.CONSTRUCTOR:
                constructor_info = self._handle_constructor(child)
                class_info['constructors'].append(constructor_info)

            elif child.kind == clang.cindex.CursorKind.DESTRUCTOR:
                destructor_info = self._handle_destructor(child)
                class_info['destructors'].append(destructor_info)

            elif child.kind == clang.cindex.CursorKind.FIELD_DECL:
                field_info = self._handle_field(child)
                class_info['members'].append(field_info)

            elif child.kind == clang.cindex.CursorKind.CXX_ACCESS_SPEC_DECL:
                # Update access specifier for following members
                if child.access_specifier == clang.cindex.AccessSpecifier.PRIVATE:
                    class_info['access_specifier'] = 'private'
                elif child.access_specifier == clang.cindex.AccessSpecifier.PROTECTED:
                    class_info['access_specifier'] = 'protected'
                elif child.access_specifier == clang.cindex.AccessSpecifier.PUBLIC:
                    class_info['access_specifier'] = 'public'

            elif child.kind == clang.cindex.CursorKind.CXX_FINAL_ATTR:
                class_info['is_final'] = True

        # ✅ Проверка множественного наследования — после цикла
        if len(class_info['base_classes']) > 1:
            msg = f"Multiple inheritance detected in class {class_info['name']} - this is not supported in Java. Using interfaces/composition instead."
            if self.mode == "strict":
                raise ValueError(msg)
            else:
                self.warnings.append(msg)

        return class_info

    def _handle_function_declaration(self, node) -> Dict[str, Any]:
        """Handle C++ global function declaration"""
        return {
            'kind': 'function',
            'name': node.spelling,
            'return_type': node.result_type.spelling,
            'parameters': [self._handle_param(param) for param in node.get_arguments()],
            'is_static': False,  # Global functions are not "static" in class sense
            'is_virtual': False,  # Not applicable to free functions
            'is_const': False,    # Not applicable to free functions
            'location': f"{node.location.file}:{node.location.line}"
        }
    

    def _handle_variable_declaration(self, node) -> Dict[str, Any]:
        """Handle C++ variable declaration"""
        return {
            'kind': 'variable',
            'name': node.spelling,
            'type': node.type.spelling,
            'is_static': node.storage_class == clang.cindex.StorageClass.STATIC,
            'is_const': node.type.is_const_qualified(),
            'location': f"{node.location.file}:{node.location.line}"
        }

    def _handle_namespace(self, node) -> Dict[str, Any]:
        return {
            'kind': 'namespace',
            'name': node.spelling,
            'children': [self._handle_namespace_child(child) for child in node.get_children()],
            'location': f"{node.location.file}:{node.location.line}"
        }

    def _handle_template_parameter(self, node) -> Dict[str, Any]:
        """Handle template parameter"""
        return {
            'kind': 'template_param',
            'name': node.spelling or 'T',
            'type': 'typename',
            'location': f"{node.location.file}:{node.location.line}"
        }

    def _handle_constructor(self, node) -> Dict[str, Any]:
        """Handle C++ constructor"""
        return {
            'kind': 'constructor',
            'name': node.spelling,
            'parameters': [self._handle_param(param) for param in node.get_arguments()],
            'location': f"{node.location.file}:{node.location.line}"
        }

    def _handle_destructor(self, node) -> Dict[str, Any]:
        """Handle C++ destructor - important for RAII to Java conversion"""
        return {
            'kind': 'destructor',
            'name': node.spelling,
            'location': f"{node.location.file}:{node.location.line}",
            'needs_raii_emulation': True  # Destructors indicate RAII pattern
        }

    def _handle_method(self, node) -> Dict[str, Any]:
        """Handle C++ method"""
        method_info = {
            'kind': 'method',
            'name': node.spelling,
            'return_type': node.result_type.spelling,
            'parameters': [self._handle_param(param) for param in node.get_arguments()],
            'is_static': node.is_static_method(),
            'is_virtual': node.is_virtual_method(),
            'is_const': hasattr(node, 'is_const_method') and node.is_const_method(),
            'is_override': any(child.kind == clang.cindex.CursorKind.CXX_OVERRIDE_ATTR for child in node.get_children()),
            'is_final': any(child.kind == clang.cindex.CursorKind.CXX_FINAL_ATTR for child in node.get_children()),
            'access': self._get_access_level(node),
            'location': f"{node.location.file}:{node.location.line}"
        }

        # Check if this is an operator overload
        if node.spelling and node.spelling.startswith('operator'):
            method_info['is_operator'] = True
            method_info['operator_name'] = node.spelling

        return method_info

    def _handle_typedef(self, node) -> Dict[str, Any]:
        """Handle typedef declaration"""
        underlying = getattr(node, 'underlying_typedef_type', None)
        underlying_type = underlying.spelling if underlying else 'void'
        return {
            'kind': 'typedef',
            'name': node.spelling,
            'underlying_type': underlying_type,
            'location': f"{node.location.file}:{node.location.line}"
        }

    def _handle_macro_definition(self, node) -> Dict[str, Any]:
        """Handle macro definition - only process constant macros"""
        # Extract macro text
        tokens = list(node.get_tokens())
        if len(tokens) >= 3:  # At least name, value
            macro_text = ' '.join([token.spelling for token in tokens[1:]])  # Skip macro name

            # Check if it's a constant macro (simple value assignment)
            if self._is_constant_macro(macro_text):
                return {
                    'kind': 'macro_constant',
                    'name': node.spelling,
                    'value': macro_text.strip(),
                    'location': f"{node.location.file}:{node.location.line}"
                }
            else:
                # Non-constant macro - warn about it
                msg = f"Non-constant macro '{node.spelling}' detected - this cannot be directly translated to Java. Consider refactoring to const/constexpr."
                self.warnings.append(msg)

        return {
            'kind': 'macro',
            'name': node.spelling,
            'raw_text': ' '.join([token.spelling for token in node.get_tokens()]),
            'location': f"{node.location.file}:{node.location.line}"
        }

    def _is_constant_macro(self, macro_text: str) -> bool:
        """Check if macro represents a constant value"""
        text = macro_text.strip()
        if text.lower() in ('true', 'false'):
            return True
        if text.startswith('"') and text.endswith('"'):
            return True
        # Remove operators and whitespace; allow digits, ., _
        cleaned = re.sub(r'[-+*/%<>!=&|^~(),\s]+', '', text)
        return cleaned.replace('.', '').replace('_', '').isdigit()

    def _handle_enum_declaration(self, node) -> Dict[str, Any]:
        """Handle enum declaration"""
        enum_values = []
        for child in node.get_children():
            if child.kind == clang.cindex.CursorKind.ENUM_CONSTANT_DECL:
                enum_values.append({
                    'name': child.spelling,
                    'value': child.enum_value
                })

        return {
            'kind': 'enum',
            'name': node.spelling,
            'values': enum_values,
            'location': f"{node.location.file}:{node.location.line}"
        }

    def _handle_class_template(self, node) -> Dict[str, Any]:
        """Handle class template"""
        template_params = []
        class_decl_node = None

        for child in node.get_children():
            if child.kind == clang.cindex.CursorKind.TEMPLATE_TYPE_PARAMETER:
                template_params.append({
                    'name': child.spelling,
                    'type': 'typename'
                })
            elif child.kind == clang.cindex.CursorType.TEMPLATE_NON_TYPE_PARAMETER:
                template_params.append({
                    'name': child.spelling,
                    'type': child.type.spelling,
                    'is_non_type': True
                })
            elif child.kind == clang.cindex.CursorKind.CLASS_DECL:
                class_decl_node = child

        if class_decl_node is None:
            # Попробуем найти STRUCT_DECL (иногда используется)
            for child in node.get_children():
                if child.kind == clang.cindex.CursorKind.STRUCT_DECL:
                    class_decl_node = child
                    break

        class_body = {}
        if class_decl_node:
            class_body = self._handle_class_declaration(class_decl_node)
        else:
            # Fallback: минимальная информация
            class_body = {
                'kind': 'class',
                'name': node.spelling,
                'members': [],
                'methods': [],
                'constructors': [],
                'destructors': [],
                'base_classes': [],
                'is_final': False,
                'location': f"{node.location.file}:{node.location.line}"
            }

        return {
            'kind': 'class_template',
            'name': node.spelling,
            'template_parameters': template_params,
            'class_info': class_body,
            'location': f"{node.location.file}:{node.location.line}"
        }

    def _handle_function_template(self, node) -> Dict[str, Any]:
        """Handle function template"""
        template_params = []
        for child in node.get_children():
            if child.kind == clang.cindex.CursorKind.TEMPLATE_TYPE_PARAMETER:
                template_params.append({
                    'name': child.spelling,
                    'type': 'typename'
                })

        # Process the function body
        func_info = self._handle_function_declaration(node)

        return {
            'kind': 'function_template',
            'name': node.spelling,
            'template_parameters': template_params,
            'function_info': func_info,
            'location': f"{node.location.file}:{node.location.line}"
        }

    def _handle_conversion_function(self, node) -> Dict[str, Any]:
        """Handle conversion operator (like operator bool())"""
        return {
            'kind': 'conversion_operator',
            'target_type': node.result_type.spelling,
            'method_name': self._convert_operator_name(node.spelling),
            'location': f"{node.location.file}:{node.location.line}"
        }

    def _handle_cast_operator(self, node) -> Dict[str, Any]:
        """Handle cast operator"""
        return {
            'kind': 'cast_operator',
            'target_type': node.result_type.spelling,
            'location': f"{node.location.file}:{node.location.line}"
        }

    def _handle_field(self, node) -> Dict[str, Any]:
        """Handle class field/attribute"""
        return {
            'kind': 'field',
            'name': node.spelling,
            'type': node.type.spelling,
            'is_static': node.storage_class == clang.cindex.StorageClass.STATIC,
            'is_const': node.type.is_const_qualified(),
            'access': self._get_access_level(node),
            'location': f"{node.location.file}:{node.location.line}"
        }

    def _handle_param(self, param_node) -> Dict[str, Any]:
        """Handle function/method parameter"""
        type_kind = param_node.type.kind
        is_ref = (type_kind == clang.cindex.TypeKind.LVALUEREFERENCE or
                type_kind == clang.cindex.TypeKind.RVALUEREFERENCE)
        return {
            'name': param_node.spelling,
            'type': param_node.type.spelling,
            'is_const': param_node.type.is_const_qualified(),
            'is_reference': is_ref
        }

    def _handle_namespace_child(self, child_node):
        """Handle children of namespace"""
        # Defer to appropriate handler based on node kind
        if child_node.kind == clang.cindex.CursorKind.CLASS_DECL:
            return self._handle_class_declaration(child_node)
        elif child_node.kind == clang.cindex.CursorKind.FUNCTION_DECL:
            return self._handle_function_declaration(child_node)
        elif child_node.kind == clang.cindex.CursorKind.VAR_DECL:
            return self._handle_variable_declaration(child_node)
        else:
            # Return basic info for other types
            return {
                'kind': str(child_node.kind),
                'spelling': child_node.spelling,
                'location': f"{child_node.location.file}:{child_node.location.line}"
            }

    def _get_access_level(self, node) -> str:
        """Get access level (public, private, protected) for a node"""
        access_map = {
            clang.cindex.AccessSpecifier.PUBLIC: 'public',
            clang.cindex.AccessSpecifier.PROTECTED: 'protected',
            clang.cindex.AccessSpecifier.PRIVATE: 'private',
            clang.cindex.AccessSpecifier.INVALID: 'public'  # Default
        }
        return access_map.get(node.access_specifier, 'public')

    def _handle_unsupported_feature(self, feature_name: str, node) -> None:
        """Handle unsupported C++ features"""
        msg = f"Unsupported C++ feature '{feature_name}' found at {node.location.file}:{node.location.line}"

        if self.mode == "strict":
            raise ValueError(msg)
        else:
            self.warnings.append(msg)

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
        # Убираем автоматическое добавление 'abstract' — слишком рискованно
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
        """Map C++ template types to Java generic types"""
        # Сначала преобразуем базовый тип
        java_type = self._cpp_to_java_type(cpp_type)
    
        # Заменяем параметры шаблона на их имена
        for param in template_params:
            if param.get('is_non_type', False):
                continue
            param_name = param['name']
            # Заменяем целые слова (чтобы не затронуть подстроки)
        
            java_type = re.sub(r'\b' + re.escape(param_name) + r'\b', param_name, java_type)
    
        return java_type
    
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

    def _convert_namespace_to_package(self, namespace: str) -> str:
        # Convert :: to .
        pkg = namespace.replace('::', '.')
    
        # Split and sanitize each part
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
            # Also ensure it starts with a letter
            if clean_part and clean_part[0].isdigit():
                clean_part = f"_{clean_part}"
            parts.append(clean_part)
    
        return '.'.join(parts)
    

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


    JAVA_RESERVED_WORDS = {
        'abstract', 'assert', 'boolean', 'break', 'byte', 'case', 'catch',
        'char', 'class', 'const', 'continue', 'default', 'do', 'double',
        'else', 'enum', 'extends', 'final', 'finally', 'float', 'for',
        'goto', 'if', 'implements', 'import', 'instanceof', 'int',
        'interface', 'long', 'native', 'new', 'package', 'private',
        'protected', 'public', 'return', 'short', 'static', 'strictfp',
        'super', 'switch', 'synchronized', 'this', 'throw', 'throws',
        'transient', 'try', 'void', 'volatile', 'while', 'true', 'false', 'null'
    }
    JAVA_RESERVED_LOWER = {word.lower() for word in JAVA_RESERVED_WORDS}

    def _cpp_name_to_java_name(self, cpp_name: str, naming_convention: str = "camelCase") -> str:
        """Convert C++ name to Java name following Java conventions"""
        if not cpp_name:
            return cpp_name

        # Handle reserved keywords
        if cpp_name.lower() in self.JAVA_RESERVED_LOWER:
            return f"_{cpp_name}"

        # Split by underscores and hyphens
        parts = [part for part in cpp_name.replace('-', '_').split('_') if part]
    
        if not parts:
            return "_unnamed"

        if naming_convention == "PascalCase":
            java_name = ''.join(part.capitalize() for part in parts)
        else:  # camelCase
            java_name = parts[0].lower() + ''.join(part.capitalize() for part in parts[1:])

        # Ensure valid Java identifier start
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
            'operator==': 'isEqualTo',          # ⚠️ Изменено с 'equals'
            'operator!=': 'isNotEqualTo',       # ⚠️ Более читаемо
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
    
        # Fallback: remove 'operator' prefix
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


# Test function to demonstrate the converter
def test_converter():
    """Test the converter with sample C++ code"""
    converter = CppToJavaConverter(mode="flexible")

    # Sample C++ code
    cpp_sample = """int a;
char b = a + a;
short c;
int d;
long e;
long long f;

char aarr[20];
long barr[10][20];
"""

    java_result = converter.convert(cpp_sample)
    print("Converted Java code:")
    print(java_result)

    print("\nConversion Report:")
    report = converter.generate_report()
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    test_converter()