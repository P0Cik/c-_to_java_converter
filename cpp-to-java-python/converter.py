"""
Main C++ to Java converter implementation
Implements requirements: FE_001-FE_004, TR_001-TR_004, BE_001-BE_003, VT_001-VT_003
"""
import re
import clang.cindex
from typing import Dict, List, Optional, Any, Union
from models import SimpleDeclaration, ClassDeclaration, Expression
from helpers import TypeConverter, NameConverter, ExpressionHelpers
import logging


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
        
        self.type_converter = TypeConverter()
        self.name_converter = NameConverter()
        self.expr_helper = ExpressionHelpers()
        self.classes = {}
        self.variables = {}
        self.functions = {}
        self.current_scope = []
        self.java_imports = set()
        self.warnings = []
        self.errors = []
        self.ast_node_count = 0
        self.last_conversion_stats = {}
        
        # Set up libclang
        try:
            # Try to find libclang library automatically
            clang.cindex.Config.set_library_path('/usr/lib')  # Common Linux location
        except:
            try:
                # Try specific LLVM versions
                clang.cindex.Config.set_library_file('/usr/lib/llvm-12/lib/libclang.so')  # Ubuntu/Debian
            except:
                try:
                    clang.cindex.Config.set_library_file('/usr/lib/x86_64-linux-gnu/libclang-12.so')  # Alternative location
                except:
                    try:
                        clang.cindex.Config.set_library_file('/usr/lib/llvm-12/lib/libclang.dylib')  # macOS
                    except:
                        try:
                            clang.cindex.Config.set_search_path('/usr/lib/clang/12.0.0/lib/')  # Alternative
                        except:
                            # If all else fails, let libclang find it automatically
                            pass
        
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
                'errors_count': len(self.errors)
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
        import tempfile
        
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
        # Walk through AST and collect relevant nodes
        java_ast = []
        
        def traverse(node, depth=0):
            self.ast_node_count += 1  # Count nodes for reporting
            
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
            elif node.kind == clang.cindex.CursorKind.CXX_METHOD:
                java_ast.append(self._handle_method(node))
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
            elif node.kind == clang.cindex.CursorKind.CXX_ACCESS_SPEC_DECL:
                # Access specifiers are handled within class context
                pass
            elif node.kind == clang.cindex.CursorKind.INHERITANCE:
                # Inheritance info is collected in class processing
                pass
            elif node.kind == clang.cindex.CursorKind.CXX_OVERRIDE_ATTR:
                # Override attribute - note for Java translation
                pass
            elif node.kind == clang.cindex.CursorKind.CXX_FINAL_ATTR:
                # Final attribute - translate to Java final
                pass
            elif node.kind == clang.cindex.CursorKind.CXX_NOEXCEPT_ATTR:
                # Noexcept - Java doesn't have exact equivalent
                pass
            elif node.kind == clang.cindex.CursorKind.CONVERSION_FUNCTION:
                # Handle conversion operators (like operator bool())
                java_ast.append(self._handle_conversion_function(node))
            elif node.kind == clang.cindex.CursorKind.CXX_CAST_OPERATOR:
                # Cast operators
                java_ast.append(self._handle_cast_operator(node))
            elif node.kind == clang.cindex.CursorKind.CXX_ACCESS_SPEC_DECL:
                # Access specifiers - these are handled in class context
                pass
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
            if child.kind == clang.cindex.CursorKind.CXX_BASESpecifier:
                # Handle inheritance
                base_class_name = child.type.spelling
                if base_class_name:
                    access_modifier = "public" if child.access_specifier == clang.cindex.AccessSpecifier.PUBLIC else "private"
                    class_info['base_classes'].append({
                        'name': base_class_name,
                        'access': access_modifier
                    })
                    
                    # Check if multiple inheritance (not allowed in Java)
                    if len(class_info['base_classes']) > 1:
                        msg = f"Multiple inheritance detected in class {class_info['name']} - this is not supported in Java. Using interfaces/composition instead."
                        if self.mode == "strict":
                            raise ValueError(msg)
                        else:
                            self.warnings.append(msg)
                            
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
                
        return class_info

    def _handle_function_declaration(self, node) -> Dict[str, Any]:
        """Handle C++ function declaration"""
        return {
            'kind': 'function',
            'name': node.spelling,
            'return_type': node.result_type.spelling,
            'parameters': [self._handle_param(param) for param in node.get_arguments()],
            'is_static': node.is_static_method(),
            'is_virtual': node.is_virtual_method(),
            'is_const': hasattr(node, 'is_const_method') and node.is_const_method(),
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
        """Handle C++ namespace declaration"""
        # In Java, namespaces become packages
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
            'name': node.spelling,
            'type': node.type.spelling if node.type else 'typename',
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
        return {
            'kind': 'typedef',
            'name': node.spelling,
            'underlying_type': node.underlying_typedef_type.spelling,
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
        # Simple heuristic: contains only literals, numbers, and operators
        import re
        # Remove whitespace and common operators to see if it's just a literal
        cleaned = re.sub(r'[+\-*/%<>!=&|^~(),\s]+', '', macro_text.strip())
        return cleaned.replace('.', '').replace('_', '').isdigit() or \
               (cleaned.startswith('"') and cleaned.endswith('"')) or \
               (cleaned.lower() in ['true', 'false'])

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
        for child in node.get_children():
            if child.kind == clang.cindex.CursorKind.TEMPLATE_TYPE_PARAMETER:
                template_params.append({
                    'name': child.spelling,
                    'type': 'typename'  # Default for template params
                })
            elif child.kind == clang.cindex.CursorKind.TEMPLATE_NON_TYPE_PARAMETER:
                template_params.append({
                    'name': child.spelling,
                    'type': child.type.spelling,
                    'is_non_type': True
                })
        
        # Process the template class body
        class_body = self._handle_class_declaration(node)  # Reuse class handling logic
        
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
            'method_name': self.name_converter.convert_operator_names(node.spelling),
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
        return {
            'name': param_node.spelling,
            'type': param_node.type.spelling,
            'is_const': param_node.type.is_const_qualified(),
            'is_reference': param_node.type.get_reference().kind != clang.cindex.TypeKind.INVALID
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
        """Generate Java code from internal AST representation"""
        java_lines = []
        
        # Process each element in the AST
        for element in java_ast:
            elem_type = element.get('kind', '')
            
            if elem_type == 'class':
                java_lines.append(self._generate_java_class(element))
            elif elem_type == 'function':
                java_lines.append(self._generate_java_function(element))
            elif elem_type == 'variable':
                java_lines.append(self._generate_java_variable(element))
            elif elem_type == 'namespace':
                # Namespaces become packages - this affects the overall file structure
                pkg_name = self._convert_namespace_to_package(element['name'])
                java_lines.insert(0, f"package {pkg_name};\n")
            elif elem_type == 'typedef':
                # Typedefs become type aliases in Java (usually handled by direct substitution)
                java_lines.append(f"// typedef {element['name']} = {element['underlying_type']}; // Handled via direct substitution")
            elif elem_type == 'macro_constant':
                # Macros become constants in Java
                java_type = self.type_converter.cpp_to_java_type(element['underlying_type'] if 'underlying_type' in element else 'int')
                java_name = self.name_converter.cpp_name_to_java_name(element['name'], "UPPER_SNAKE_CASE").upper()
                java_lines.append(f"public static final {java_type} {java_name} = {element['value']};")
            elif elem_type == 'enum':
                java_lines.append(self._generate_java_enum(element))
            elif elem_type == 'class_template':
                java_lines.append(self._generate_java_template_class(element))
            elif elem_type == 'function_template':
                java_lines.append(self._generate_java_template_function(element))
            elif elem_type == 'conversion_operator':
                # Conversion operators become explicit conversion methods
                java_lines.append(f"// Conversion operator to {element['target_type']} -> {element['method_name']}()")
            else:
                # Other elements might be handled differently or skipped
                java_lines.append(f"// Unhandled element: {element}")
        
        return '\n'.join(java_lines)

    def _generate_java_class(self, class_info: Dict[str, Any]) -> str:
        """Generate Java class from C++ class info"""
        java_lines = []
        
        # Determine modifiers
        modifiers = ["public"]
        if class_info.get('is_final', False):
            modifiers.append("final")
        elif any(m.get('is_virtual', False) for m in class_info.get('methods', [])):
            modifiers.append("abstract")
        
        # Handle inheritance
        extends_clause = ""
        implements_clause = ""
        
        base_classes = class_info.get('base_classes', [])
        if base_classes:
            # In Java, single inheritance only. Multiple inheritance becomes interfaces/composition
            java_bases = []
            interfaces = []
            
            for base in base_classes:
                base_name = base['name']
                java_base_name = self.name_converter.cpp_name_to_java_name(base_name, "PascalCase")
                
                # For now, assume first base is the parent class, others become interfaces
                # In practice, this would need more sophisticated analysis
                if len(java_bases) == 0:
                    java_bases.append(java_base_name)
                else:
                    interfaces.append(java_base_name)
            
            if java_bases:
                extends_clause = f" extends {''.join(java_bases[:1])}"  # Only first base
            if interfaces:
                implements_clause = f" implements {', '.join(interfaces)}"
        
        # Start class declaration
        class_name = self.name_converter.cpp_name_to_java_name(class_info['name'], "PascalCase")
        java_lines.append(f"{' '.join(modifiers)} class {class_name}{extends_clause}{implements_clause} {{")
        
        # Add fields
        for field in class_info.get('members', []):
            access = field.get('access', 'private')  # Default to private in Java
            java_type = self.type_converter.cpp_to_java_type(field['type'])
            java_name = self.name_converter.cpp_name_to_java_name(field['name'])
            
            static_keyword = "static " if field.get('is_static', False) else ""
            final_keyword = "final " if field.get('is_const', False) else ""
            
            java_lines.append(f"    {access} {static_keyword}{final_keyword}{java_type} {java_name};")
        
        # Add constructors
        for constructor in class_info.get('constructors', []):
            params = ", ".join([
                f"{self.type_converter.cpp_to_java_type(p['type'])} {self.name_converter.cpp_name_to_java_name(p['name'])}"
                for p in constructor.get('parameters', [])
            ])
            
            java_lines.append(f"    public {class_name}({params}) {{")
            java_lines.append("        // Constructor implementation")
            java_lines.append("    }")
        
        # Add destructor handling as close() method for AutoCloseable
        destructors = class_info.get('destructors', [])
        if destructors:
            # Add AutoCloseable import
            self.java_imports.add("java.lang.AutoCloseable")
            java_lines.append("")
            java_lines.append("    // Destructor emulation via AutoCloseable")
            java_lines.append("    public void close() {")
            java_lines.append("        // Emulated destructor code here")
            for dtor in destructors:
                java_lines.append(f"        // Original destructor from {dtor['location']}")
            java_lines.append("    }")
        
        # Add methods
        for method in class_info.get('methods', []):
            java_lines.extend(self._generate_java_method(method, class_info['name']))
        
        # Close class
        java_lines.append("}")
        java_lines.append("")  # Empty line after class
        
        return '\n'.join(java_lines)

    def _generate_java_method(self, method_info: Dict[str, Any], class_name: str) -> List[str]:
        """Generate Java method from C++ method info"""
        java_lines = []
        
        # Determine access level
        access = method_info.get('access', 'public')
        
        # Determine modifiers
        modifiers = [access]
        if method_info.get('is_static', False):
            modifiers.append('static')
        if method_info.get('is_final', False):
            modifiers.append('final')
        if method_info.get('is_virtual', False) and not method_info.get('is_override', False):
            # Virtual methods in C++ might become abstract in Java
            # Or just remain as regular methods with possibility of override
            pass  # Regular method allows overriding by default in Java
        
        # Handle operator overloads
        method_name = method_info['name']
        if method_name.startswith('operator'):
            # Convert operator to Java method name
            method_name = self.name_converter.convert_operator_names(method_name)
            # Special handling for certain operators
            if method_name in ['equals', 'hashCode']:
                modifiers.append('@Override')
        
        # Handle return type
        return_type = self.type_converter.cpp_to_java_type(method_info['return_type'])
        
        # Handle parameters
        params = []
        for param in method_info.get('parameters', []):
            param_type = self.type_converter.cpp_to_java_type(param['type'])
            param_name = self.name_converter.cpp_name_to_java_name(param['name'])
            params.append(f"{param_type} {param_name}")
        
        param_str = ", ".join(params)
        
        # Special handling for comparison operators
        if method_name == 'equals':
            return_type = 'boolean'
            if len(params) == 1 and params[0].startswith('Object'):
                # Already properly formatted for equals
                pass
            else:
                # Ensure proper equals signature
                param_str = 'Object obj'
        
        java_lines.append(f"    {' '.join(modifiers)} {return_type} {method_name}({param_str}) {{")
        java_lines.append("        // Method implementation")
        if return_type != 'void':
            java_lines.append(f"        return {self._get_default_value(return_type)}; // TODO: Implement method")
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

    def _generate_java_function(self, func_info: Dict[str, Any]) -> str:
        """Generate Java function (as static method in a utility class)"""
        # Functions in C++ become static methods in Java utility classes
        java_lines = []
        
        # Determine access level
        access = func_info.get('access', 'public')
        
        # Determine modifiers
        modifiers = [access, 'static']
        
        # Handle return type
        return_type = self.type_converter.cpp_to_java_type(func_info['return_type'])
        
        # Handle function name
        func_name = self.name_converter.cpp_name_to_java_name(func_info['name'])
        
        # Handle parameters
        params = []
        for param in func_info.get('parameters', []):
            param_type = self.type_converter.cpp_to_java_type(param['type'])
            param_name = self.name_converter.cpp_name_to_java_name(param['name'])
            params.append(f"{param_type} {param_name}")
        
        param_str = ", ".join(params)
        
        java_lines.append(f"{access} class Util {{  // Utility class for global functions")
        java_lines.append(f"    {' '.join(modifiers)} {return_type} {func_name}({param_str}) {{")
        java_lines.append("        // Function implementation")
        if return_type != 'void':
            java_lines.append(f"        return {self._get_default_value(return_type)}; // TODO: Implement function")
        java_lines.append("    }")
        java_lines.append("}")
        
        return '\n'.join(java_lines)

    def _generate_java_variable(self, var_info: Dict[str, Any]) -> str:
        """Generate Java variable declaration"""
        access = 'public'  # Global vars become public static in Java
        static_keyword = "static " if var_info.get('is_static', True) else ""  # Default to static for globals
        final_keyword = "final " if var_info.get('is_const', False) else ""
        
        java_type = self.type_converter.cpp_to_java_type(var_info['type'])
        java_name = self.name_converter.cpp_name_to_java_name(var_info['name'])
        
        return f"{access} {static_keyword}{final_keyword}{java_type} {java_name};"

    def _convert_namespace_to_package(self, namespace: str) -> str:
        """Convert C++ namespace to Java package"""
        # Convert namespace to lowercase with dots
        return namespace.lower().replace('::', '.')

    def _generate_java_enum(self, enum_info: Dict[str, Any]) -> str:
        """Generate Java enum from C++ enum"""
        java_lines = []
        
        enum_name = self.name_converter.cpp_name_to_java_name(enum_info['name'], "PascalCase")
        java_lines.append(f"public enum {enum_name} {{")
        
        values = enum_info.get('values', [])
        for i, val in enumerate(values):
            separator = "," if i < len(values) - 1 else ";"
            java_lines.append(f"    {val['name'].upper()}{separator}")
        
        java_lines.append("")
        java_lines.append("    // Enum values with potential integer mappings")
        java_lines.append("}")
        
        return '\n'.join(java_lines)

    def _generate_java_template_class(self, template_info: Dict[str, Any]) -> str:
        """Generate Java generic class from C++ template class"""
        java_lines = []
        
        # Extract template parameters
        template_params = template_info['template_parameters']
        param_names = [p['name'] for p in template_params]
        
        # Generate generics clause
        generics_clause = ""
        if param_names:
            generics_clause = f"<{', '.join(param_names)}>"

        # Process the class info inside the template
        class_info = template_info['class_info']
        
        # Determine modifiers
        modifiers = ["public"]
        if class_info.get('is_final', False):
            modifiers.append("final")
        
        # Handle inheritance (same as regular class)
        extends_clause = ""
        implements_clause = ""
        
        base_classes = class_info.get('base_classes', [])
        if base_classes:
            # Apply same inheritance logic as regular classes
            java_bases = []
            interfaces = []
            
            for base in base_classes:
                base_name = base['name']
                java_base_name = self.name_converter.cpp_name_to_java_name(base_name, "PascalCase")
                
                if len(java_bases) == 0:
                    java_bases.append(java_base_name)
                else:
                    interfaces.append(java_base_name)
            
            if java_bases:
                extends_clause = f" extends {''.join(java_bases[:1])}"
            if interfaces:
                implements_clause = f" implements {', '.join(interfaces)}"
        
        # Generate class declaration with generics
        class_name = self.name_converter.cpp_name_to_java_name(class_info['name'], "PascalCase")
        java_lines.append(f"{' '.join(modifiers)} class {class_name}{generics_clause}{extends_clause}{implements_clause} {{")
        
        # Add class body (fields, methods, etc.)
        # For now, just add a comment about template parameters
        param_descriptions = [f"{p['name']} ({p['type']})" for p in template_params]
        java_lines.append(f"    // Template parameters: {', '.join(param_descriptions)}")
        
        # Add fields
        for field in class_info.get('members', []):
            access = field.get('access', 'private')
            java_type = self.type_converter.cpp_to_java_type(field['type'])
            java_name = self.name_converter.cpp_name_to_java_name(field['name'])
            
            static_keyword = "static " if field.get('is_static', False) else ""
            final_keyword = "final " if field.get('is_const', False) else ""
            
            java_lines.append(f"    {access} {static_keyword}{final_keyword}{java_type} {java_name};")
        
        # Add methods (similar to regular class)
        for method in class_info.get('methods', []):
            java_lines.extend(self._generate_java_method(method, class_name))
        
        # Close class
        java_lines.append("}")
        java_lines.append("")
        
        return '\n'.join(java_lines)

    def _generate_java_template_function(self, template_info: Dict[str, Any]) -> str:
        """Generate Java generic method from C++ template function"""
        # Template functions become generic static methods
        func_info = template_info['function_info']
        
        java_lines = []
        java_lines.append("// Template function converted to generic method")
        
        # Determine access level
        access = func_info.get('access', 'public')
        
        # Determine modifiers
        modifiers = [access, 'static']
        
        # Extract template parameters
        template_params = template_info['template_parameters']
        generics_clause = ""
        if template_params:
            param_names = [p['name'] for p in template_params]
            generics_clause = f"<{', '.join(param_names)}> "
        
        # Handle return type
        return_type = self.type_converter.cpp_to_java_type(func_info['return_type'])
        
        # Handle function name
        func_name = self.name_converter.cpp_name_to_java_name(func_info['name'])
        
        # Handle parameters
        params = []
        for param in func_info.get('parameters', []):
            param_type = self.type_converter.cpp_to_java_type(param['type'])
            param_name = self.name_converter.cpp_name_to_java_name(param['name'])
            params.append(f"{param_type} {param_name}")
        
        param_str = ", ".join(params)
        
        java_lines.append(f"{access} class Util {{  // Utility class for template functions")
        java_lines.append(f"    public {generics_clause}{return_type} {func_name}({param_str}) {{")
        java_lines.append("        // Generic function implementation")
        if return_type != 'void':
            java_lines.append(f"        return {self._get_default_value(return_type)}; // TODO: Implement function")
        java_lines.append("    }")
        java_lines.append("}")
        
        return '\n'.join(java_lines)

    def _generate_imports(self) -> str:
        """Generate Java import statements based on needed utilities"""
        if not self.java_imports:
            return ""
        
        imports = []
        for imp in sorted(self.java_imports):
            imports.append(f"import {imp};")
        
        return '\n'.join(imports) + '\n\n' if imports else ""

    def _convert_expression(self, expr: str) -> str:
        """Convert C++ expressions to Java expressions"""
        # Handle basic replacements
        java_expr = expr
        
        # Handle pointer dereference (*)
        java_expr = re.sub(r'\*\s*(\w+)', r'\1.get()', java_expr)
        
        # Handle address-of (&)
        java_expr = re.sub(r'&\s*(\w+)', r'\1.addressOf()', java_expr)
        
        # Handle array indexing - keep as is for now since Java arrays work similarly
        # But we might need special handling if dealing with pointer arithmetic
        
        return java_expr


# Test function to demonstrate the converter
def test_converter():
    """Test the converter with sample C++ code"""
    converter = CppToJavaConverter()
    
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


if __name__ == "__main__":
    test_converter()