"""
Name conversion utilities for C++ to Java
"""

class NameConverter:
    """Converts C++ names to Java names following Java conventions"""
    
    @staticmethod
    def cpp_name_to_java_name(cpp_name, naming_convention="camelCase"):
        """
        Convert C++ name to Java name following Java conventions
        
        Args:
            cpp_name (str): The C++ name to convert
            naming_convention (str): The naming convention to use ("camelCase", "PascalCase")
            
        Returns:
            str: The converted Java name
        """
        if not cpp_name:
            return cpp_name
            
        # Handle reserved keywords in Java by adding underscore prefix
        java_reserved = {
            'abstract', 'assert', 'boolean', 'break', 'byte', 'case', 'catch', 
            'char', 'class', 'const', 'continue', 'default', 'do', 'double', 
            'else', 'enum', 'extends', 'final', 'finally', 'float', 'for', 
            'goto', 'if', 'implements', 'import', 'instanceof', 'int', 
            'interface', 'long', 'native', 'new', 'package', 'private', 
            'protected', 'public', 'return', 'short', 'static', 'strictfp', 
            'super', 'switch', 'synchronized', 'this', 'throw', 'throws', 
            'transient', 'try', 'void', 'volatile', 'while', 'true', 'false', 'null'
        }
        
        if cpp_name.lower() in [word.lower() for word in java_reserved]:
            return f"_{cpp_name}"
        
        # Split the name by underscores and other separators
        parts = cpp_name.replace('-', '_').split('_')
        
        if naming_convention == "PascalCase":
            # Capitalize first letter of each part
            java_name = ''.join(part.capitalize() for part in parts if part)
        else:  # camelCase (default)
            # First part lowercase, rest capitalized
            if len(parts) == 1:
                java_name = parts[0].lower()
            else:
                java_name = parts[0].lower() + ''.join(part.capitalize() for part in parts[1:] if part)
        
        # Ensure first character is alphabetic or underscore
        if java_name and not (java_name[0].isalpha() or java_name[0] == '_'):
            java_name = '_' + java_name
            
        return java_name
    
    @staticmethod
    def convert_operator_names(op_name):
        """
        Convert C++ operator names to Java-friendly names
        Since Java doesn't support operator overloading, we convert to method names
        
        Args:
            op_name (str): The C++ operator name (e.g., "operator+", "operator==")
            
        Returns:
            str: The Java-friendly method name
        """
        op_mapping = {
            'operator+': 'add',
            'operator-': 'subtract', 
            'operator*': 'multiply',
            'operator/': 'divide',
            'operator%': 'modulo',
            'operator==': 'equals',
            'operator!=': 'notEquals',
            'operator<': 'lessThan',
            'operator>': 'greaterThan',
            'operator<=': 'lessThanOrEqual',
            'operator>=': 'greaterThanOrEqual',
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
            'operator[]': 'at',
            'operator->': 'arrow'
        }
        
        return op_mapping.get(op_name, op_name.replace('operator', 'op'))