"""
Main C++ to Java converter implementation
"""
import re
from typing import Dict, List, Optional
from models import SimpleDeclaration, ClassDeclaration, Expression
from helpers import TypeConverter, NameConverter, ExpressionHelpers


class CppToJavaConverter:
    """
    Converts C++ source code to Java source code
    """
    
    def __init__(self):
        self.type_converter = TypeConverter()
        self.name_converter = NameConverter()
        self.expr_helper = ExpressionHelpers()
        self.classes = {}
        self.variables = {}
        self.functions = {}
        self.current_scope = []
        self.java_imports = set()
        
    def convert(self, cpp_code: str) -> str:
        """
        Convert C++ code to Java code
        
        Args:
            cpp_code (str): Input C++ source code
            
        Returns:
            str: Converted Java source code
        """
        # Reset state for new conversion
        self.classes = {}
        self.variables = {}
        self.functions = {}
        self.current_scope = []
        self.java_imports = set()
        
        # Split code into logical blocks (declarations, statements, etc.)
        lines = cpp_code.strip().split('\n')
        
        # Process the code line by line
        java_code = self._process_cpp_lines(lines)
        
        # Generate imports section
        imports_section = self._generate_imports()
        
        # Combine imports and main code
        full_java_code = imports_section + java_code
        
        return full_java_code
    
    def _generate_imports(self) -> str:
        """Generate Java import statements based on needed utilities"""
        if not self.java_imports:
            return ""
        
        imports = []
        for imp in sorted(self.java_imports):
            imports.append(f"import {imp};")
        
        return '\n'.join(imports) + '\n\n' if imports else ""
    
    def _process_cpp_lines(self, lines: List[str]) -> str:
        """Process C++ code lines and convert to Java"""
        java_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            if not line or line.startswith('//'):
                # Skip empty lines and comments
                i += 1
                continue
            
            # Check for class definitions
            class_match = re.match(r'^(\w+)\s+(\w+)\s*{', line)
            if class_match:
                class_info = self._parse_class(lines, i)
                java_class = self._convert_class_to_java(class_info)
                java_lines.append(java_class)
                i = class_info['end_index']
                continue
            
            # Check for variable declarations - updated to handle arrays
            var_match = re.match(r'^(\w+(?:\s*\*|\s*&)?(?:\s*\w+)?(?:\s*\**)?)\s+([a-zA-Z_][a-zA-Z0-9_\[\]\s,]+)\s*(?:=\s*(.+))?;', line)
            if var_match:
                java_vars = self._convert_variable_declaration(var_match)
                java_lines.extend(java_vars)
                i += 1
                continue
            
            # Check for standalone variable declarations (could be multiple in one line)
            if ';' in line:
                java_vars = self._process_variable_line(line)
                java_lines.extend(java_vars)
                i += 1
                continue
            
            # For now, just add other lines as comments indicating they weren't processed
            java_lines.append(f"// TODO: Unprocessed line: {line}")
            i += 1
        
        return '\n'.join(java_lines)
    
    def _process_variable_line(self, line: str) -> List[str]:
        """Process a line that contains variable declarations"""
        java_lines = []
        
        # Handle the pattern: type var1, var2, var3;
        # Find the semicolon to ensure we're processing a complete statement
        if not line.endswith(';'):
            return [f"// TODO: Incomplete statement: {line}"]
        
        line = line.rstrip(';')
        
        # Find the type by identifying the last word before the variable names
        # This is a simplified approach - a full parser would be more robust
        parts = line.split()
        if len(parts) < 2:
            return [f"// TODO: Cannot parse: {line}"]
        
        # Identify the type by looking for the type keyword and any modifiers
        type_parts = []
        var_part_idx = 0
        
        # Look for common type patterns
        for i, part in enumerate(parts):
            if part in ['int', 'long', 'short', 'char', 'wchar_t', 'bool', 'float', 'double', 'void', 
                       'unsigned', 'signed']:
                # Gather all type-related parts (including modifiers like unsigned, long long, etc.)
                j = i
                while j < len(parts) and parts[j] in ['int', 'long', 'short', 'char', 'wchar_t', 'bool', 
                                                     'float', 'double', 'void', 'unsigned', 'signed']:
                    type_parts.append(parts[j])
                    j += 1
                var_part_idx = j
                break
            elif '*' in part or '&' in part:
                # Handle pointer/reference types
                if i > 0:
                    type_parts.append(parts[i-1])
                type_parts.append(part)
                var_part_idx = i + 1
                break
            elif i == len(parts) - 1:
                # Last resort: assume first part is type
                type_parts = [parts[0]]
                var_part_idx = 1
        
        cpp_type = ' '.join(type_parts).strip()
        java_type = self.type_converter.cpp_to_java_type(cpp_type)
        
        # Extract variable names (everything after the type)
        var_defs = ' '.join(parts[var_part_idx:]).split(',')
        
        for var_def in var_defs:
            var_def = var_def.strip()
            
            # Check if there's an initialization
            if '=' in var_def:
                var_and_init = var_def.split('=', 1)
                var_name = var_and_init[0].strip()
                init_value = var_and_init[1].strip()
                
                # Handle array declarations properly
                if '[' in var_name:
                    # Extract base name and preserve dimensions
                    # Handle multi-dimensional arrays like arr[10][20]
                    array_parts = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)((?:\[[^\]]*\])+)', var_name)
                    if array_parts:
                        base_name = array_parts.group(1)
                        dimensions = array_parts.group(2)  # This captures all bracket parts like [10][20]
                        java_name = self.name_converter.cpp_name_to_java_name(base_name)
                        
                        # Convert array initialization
                        java_init = self._convert_expression(init_value)
                        java_lines.append(f"public static {java_type} {java_name}{dimensions} = {java_init};")
                    else:
                        # Fallback for simpler cases
                        base_name = re.sub(r'\[.*\]', '', var_name).strip()
                        java_name = self.name_converter.cpp_name_to_java_name(base_name)
                        java_init = self._convert_expression(init_value)
                        java_lines.append(f"public static {java_type}[] {java_name} = {java_init};")
                else:
                    java_name = self.name_converter.cpp_name_to_java_name(var_name)
                    java_init = self._convert_expression(init_value)
                    java_lines.append(f"public static {java_type} {java_name} = {java_init};")
            else:
                # Just declaration
                if '[' in var_def:
                    # Array declaration - handle multi-dimensional arrays
                    array_parts = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)((?:\[[^\]]*\])+)', var_def)
                    if array_parts:
                        base_name = array_parts.group(1)
                        dimensions = array_parts.group(2)  # This captures all bracket parts like [10][20]
                        java_name = self.name_converter.cpp_name_to_java_name(base_name)
                        java_lines.append(f"public static {java_type} {java_name}{dimensions};")
                    else:
                        # Fallback for simpler cases
                        base_name = re.sub(r'\[.*\]', '', var_def).strip()
                        java_name = self.name_converter.cpp_name_to_java_name(base_name)
                        java_lines.append(f"public static {java_type}[] {java_name};")
                else:
                    java_name = self.name_converter.cpp_name_to_java_name(var_def)
                    java_lines.append(f"public static {java_type} {java_name};")
        
        return java_lines
    
    def _parse_class(self, lines: List[str], start_idx: int) -> Dict:
        """Parse a C++ class definition"""
        class_info = {
            'name': '',
            'members': [],
            'parent': None,
            'start_index': start_idx,
            'end_index': start_idx
        }
        
        # Get class name from the line
        class_line = lines[start_idx]
        class_match = re.match(r'^(\w+)\s+(\w+)\s*{', class_line)
        if class_match:
            class_info['name'] = class_match.group(2)
        
        # Look for inheritance
        inherit_match = re.search(r':\s*(\w+)\s+(\w+)', class_line)
        if inherit_match:
            if inherit_match.group(1) in ['public', 'private', 'protected']:
                class_info['parent'] = inherit_match.group(2)
        
        # Parse class members until closing brace
        brace_count = 1
        i = start_idx
        while i < len(lines) and brace_count > 0:
            line = lines[i]
            brace_count += line.count('{') - line.count('}')
            
            if brace_count == 0:
                # Found the closing brace
                class_info['end_index'] = i
                break
                
            # Look for member variables and methods
            if ':' in line and any(mod in line for mod in ['public', 'private', 'protected']):
                # Access specifier - skip
                pass
            elif re.search(r'\w+\s+\w+\s*[=,;\[\]]', line) and not any(kw in line for kw in ['if', 'for', 'while', 'return']):
                # Likely a member variable
                class_info['members'].append(line.strip())
            
            i += 1
        
        return class_info
    
    def _convert_class_to_java(self, class_info: Dict) -> str:
        """Convert parsed C++ class to Java class"""
        java_lines = []
        
        # Start class definition
        extends_clause = f" extends {class_info['parent']}" if class_info['parent'] else ""
        java_class_name = self.name_converter.cpp_name_to_java_name(class_info['name'], "PascalCase")
        java_lines.append(f"public class {java_class_name}{extends_clause} {{")
        
        # Add class members
        for member in class_info['members']:
            if member.strip():
                # Try to convert member as variable
                converted_member = self._process_variable_line(member + ";")
                for conv_line in converted_member:
                    if not conv_line.startswith("// TODO"):
                        # Indent the member
                        java_lines.append(f"    {conv_line}")
                    else:
                        java_lines.append(f"    // {member}")
        
        java_lines.append("}")
        return '\n'.join(java_lines) + "\n"
    
    def _convert_variable_declaration(self, match) -> List[str]:
        """Convert a matched variable declaration to Java"""
        cpp_type = match.group(1)
        java_type = self.type_converter.cpp_to_java_type(cpp_type)
        var_names = [v.strip() for v in match.group(2).split(',')]
        
        java_lines = []
        for var_name in var_names:
            # Check if it's an array
            if '[' in var_name and ']' in var_name:
                base_name = re.sub(r'\[.*\]', '', var_name).strip()
                java_var_name = self.name_converter.cpp_name_to_java_name(base_name)
                java_lines.append(f"public static {java_type} {java_var_name};")
            else:
                java_var_name = self.name_converter.cpp_name_to_java_name(var_name)
                java_lines.append(f"public static {java_type} {java_var_name};")
        
        # Handle initialization if present
        if match.group(3):
            init_val = match.group(3).strip()
            # Update the last declaration with initialization
            if java_lines:
                last_line = java_lines[-1]
                converted_init = self._convert_expression(init_val)
                java_lines[-1] = last_line.replace(';', f' = {converted_init};')
        
        return java_lines
    
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