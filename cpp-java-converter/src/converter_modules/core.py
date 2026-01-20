import clang.cindex
import re
import json
from typing import Any, Dict, List, Optional
import tempfile
import logging
from datetime import datetime
import time


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
        from .handlers import _handle_class_declaration
        return _handle_class_declaration(self, node)

    def _handle_function_declaration(self, node) -> Dict[str, Any]:
        """Handle C++ global function declaration"""
        from .handlers import _handle_function_declaration
        return _handle_function_declaration(self, node)

    def _handle_variable_declaration(self, node) -> Dict[str, Any]:
        """Handle C++ variable declaration"""
        from .handlers import _handle_variable_declaration
        return _handle_variable_declaration(self, node)

    def _handle_namespace(self, node) -> Dict[str, Any]:
        from .handlers import _handle_namespace
        return _handle_namespace(self, node)

    def _handle_template_parameter(self, node) -> Dict[str, Any]:
        """Handle template parameter"""
        from .handlers import _handle_template_parameter
        return _handle_template_parameter(self, node)

    def _handle_constructor(self, node) -> Dict[str, Any]:
        """Handle C++ constructor"""
        from .handlers import _handle_constructor
        return _handle_constructor(self, node)

    def _handle_destructor(self, node) -> Dict[str, Any]:
        """Handle C++ destructor - important for RAII to Java conversion"""
        from .handlers import _handle_destructor
        return _handle_destructor(self, node)

    def _handle_method(self, node) -> Dict[str, Any]:
        """Handle C++ method"""
        from .handlers import _handle_method
        return _handle_method(self, node)

    def _handle_typedef(self, node) -> Dict[str, Any]:
        """Handle typedef declaration"""
        from .handlers import _handle_typedef
        return _handle_typedef(self, node)

    def _handle_macro_definition(self, node) -> Dict[str, Any]:
        """Handle macro definition - only process constant macros"""
        from .handlers import _handle_macro_definition
        return _handle_macro_definition(self, node)

    def _handle_enum_declaration(self, node) -> Dict[str, Any]:
        """Handle enum declaration"""
        from .handlers import _handle_enum_declaration
        return _handle_enum_declaration(self, node)

    def _handle_class_template(self, node) -> Dict[str, Any]:
        """Handle class template"""
        from .handlers import _handle_class_template
        return _handle_class_template(self, node)

    def _handle_function_template(self, node) -> Dict[str, Any]:
        """Handle function template"""
        from .handlers import _handle_function_template
        return _handle_function_template(self, node)

    def _handle_conversion_function(self, node) -> Dict[str, Any]:
        """Handle conversion operator (like operator bool())"""
        from .handlers import _handle_conversion_function
        return _handle_conversion_function(self, node)

    def _handle_cast_operator(self, node) -> Dict[str, Any]:
        """Handle cast operator"""
        from .handlers import _handle_cast_operator
        return _handle_cast_operator(self, node)

    def _handle_field(self, node) -> Dict[str, Any]:
        """Handle class field/attribute"""
        from .handlers import _handle_field
        return _handle_field(self, node)

    def _handle_param(self, param_node) -> Dict[str, Any]:
        """Handle function/method parameter"""
        from .handlers import _handle_param
        return _handle_param(self, param_node)

    def _handle_namespace_child(self, child_node):
        """Handle children of namespace"""
        from .handlers import _handle_namespace_child
        return _handle_namespace_child(self, child_node)

    def _get_access_level(self, node) -> str:
        """Get access level (public, private, protected) for a node"""
        from .helpers import _get_access_level
        return _get_access_level(self, node)

    def _handle_unsupported_feature(self, feature_name: str, node) -> None:
        """Handle unsupported C++ features"""
        from .helpers import _handle_unsupported_feature
        return _handle_unsupported_feature(self, feature_name, node)

    def _generate_java_code(self, java_ast: List[Any]) -> str:
        from .code_generator import _generate_java_code
        return _generate_java_code(self, java_ast)

    def _generate_java_class(self, class_info: Dict[str, Any]) -> str:
        from .code_generator import _generate_java_class
        return _generate_java_class(self, class_info)

    def _generate_java_method(self, method_info: Dict[str, Any], class_name: str) -> List[str]:
        """Generate Java method from C++ method info"""
        from .code_generator import _generate_java_method
        return _generate_java_method(self, method_info, class_name)

    def _get_default_value(self, java_type: str) -> str:
        """Get default return value for a Java type"""
        from .helpers import _get_default_value
        return _get_default_value(self, java_type)


    def _map_template_type(self, cpp_type: str, template_params: List[Dict[str, Any]]) -> str:
        """Map C++ template types to Java generic types"""
        from .helpers import _map_template_type
        return _map_template_type(self, cpp_type, template_params)

    def _generate_util_class(self, functions: List[Dict[str, Any]]) -> str:
        """Generate a single utility class containing all global and template functions"""
        from .code_generator import _generate_util_class
        return _generate_util_class(self, functions)


    def _generate_globals_class(self, variables: List[Dict[str, Any]]) -> str:
        """Generate a class containing all global variables as static fields"""
        from .code_generator import _generate_globals_class
        return _generate_globals_class(self, variables)

    def _convert_namespace_to_package(self, namespace: str) -> str:
        from .helpers import _convert_namespace_to_package
        return _convert_namespace_to_package(self, namespace)


    def _generate_java_enum(self, enum_info: Dict[str, Any]) -> str:
        """Generate Java enum from C++ enum"""
        from .code_generator import _generate_java_enum
        return _generate_java_enum(self, enum_info)


    def _generate_imports(self) -> str:
        """Generate Java import statements based on needed utilities"""
        from .code_generator import _generate_imports
        return _generate_imports(self)

    def _cpp_to_java_type(self, cpp_type: str) -> str:
        """Convert C++ type to Java type"""
        from .type_mapper import _cpp_to_java_type
        return _cpp_to_java_type(self, cpp_type)


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
        from .helpers import _cpp_name_to_java_name
        return _cpp_name_to_java_name(self, cpp_name, naming_convention)

    def _convert_operator_name(self, op_name: str) -> str:
        from .helpers import _convert_operator_name
        return _convert_operator_name(self, op_name)

    def generate_report(self) -> Dict[str, Any]:
        """Generate a detailed conversion report"""
        from .helpers import generate_report
        return generate_report(self)


# Test function to demonstrate the converter
def test_converter():
    """Test the converter with sample C++ code"""
    from .helpers import test_converter as helper_test_converter
    return helper_test_converter()