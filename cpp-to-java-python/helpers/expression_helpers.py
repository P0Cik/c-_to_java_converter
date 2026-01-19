"""
Expression helper utilities for C++ to Java conversion
"""

class ExpressionHelpers:
    """Helper functions for handling C++ to Java expression conversions"""
    
    @staticmethod
    def handle_assignment_expression(lhs, rhs, op=''):
        """
        Handle assignment expressions, including compound assignments
        
        Args:
            lhs (str): Left-hand side of assignment
            rhs (str): Right-hand side of assignment  
            op (str): Assignment operator ('', '*', '/', '%', '+', '-', '<<', '>>', '&', '^', '|')
            
        Returns:
            str: Converted Java assignment expression
        """
        if op == '':
            return f"{lhs} = {rhs}"
        elif op == '*':
            return f"{lhs} = {lhs} * {rhs}"
        elif op == '/':
            return f"{lhs} = {lhs} / {rhs}"
        elif op == '%':
            return f"{lhs} = {lhs} % {rhs}"
        elif op == '+':
            return f"{lhs} = {lhs} + {rhs}"
        elif op == '-':
            return f"{lhs} = {lhs} - {rhs}"
        elif op == '<<':
            return f"{lhs} = {lhs} << {rhs}"
        elif op == '>>':
            return f"{lhs} = {lhs} >> {rhs}"
        elif op == '&':
            return f"{lhs} = {lhs} & {rhs}"
        elif op == '^':
            return f"{lhs} = {lhs} ^ {rhs}"
        elif op == '|':
            return f"{lhs} = {lhs} | {rhs}"
        else:
            return f"{lhs} = {rhs}"  # Default fallback
    
    @staticmethod
    def handle_unary_operators(expr, op):
        """
        Handle unary operators
        
        Args:
            expr (str): The expression to apply operator to
            op (str): The unary operator ('*', '&', '!', '~', '++', '--', '+', '-')
            
        Returns:
            str: Converted Java unary expression
        """
        if op == '*':  # Dereference
            return f"{expr}.get()"
        elif op == '&':  # Address-of
            return f"{expr}.addressOf()"
        elif op == '!':  # Logical NOT
            return f"!({expr})"
        elif op == '~':  # Bitwise NOT
            return f"~({expr})"
        elif op == '++':  # Pre-increment
            return f"{expr}.increment()"
        elif op == '--':  # Pre-decrement
            return f"{expr}.decrement()"
        elif op == '+':  # Unary plus
            return f"+({expr})"
        elif op == '-':  # Unary minus
            return f"-({expr})"
        else:
            return expr
    
    @staticmethod
    def handle_binary_operators(left, right, op):
        """
        Handle binary operators
        
        Args:
            left (str): Left operand
            right (str): Right operand
            op (str): Binary operator
            
        Returns:
            str: Converted Java binary expression
        """
        op_map = {
            '+': '+',
            '-': '-',
            '*': '*',
            '/': '/',
            '%': '%',
            '==': '==',
            '!=': '!=',
            '<': '<',
            '>': '>',
            '<=': '<=',
            '>=': '>=',
            '&&': '&&',
            '||': '||',
            '&': '&',
            '|': '|',
            '^': '^',
            '<<': '<<',
            '>>': '>>'
        }
        
        java_op = op_map.get(op, op)
        return f"({left}) {java_op} ({right})"
    
    @staticmethod
    def handle_array_access(array_expr, index_expr):
        """
        Handle array access expressions
        
        Args:
            array_expr (str): Array expression
            index_expr (str): Index expression
            
        Returns:
            str: Converted Java array access
        """
        return f"{array_expr}[{index_expr}]"
    
    @staticmethod
    def handle_function_call(func_name, args_list):
        """
        Handle function calls
        
        Args:
            func_name (str): Function name
            args_list (list): List of argument expressions
            
        Returns:
            str: Converted Java function call
        """
        args_str = ', '.join(args_list) if args_list else ''
        return f"{func_name}({args_str})"
    
    @staticmethod
    def handle_member_access(obj_expr, member_name, is_pointer=False):
        """
        Handle member access (dot or arrow operator)
        
        Args:
            obj_expr (str): Object expression
            member_name (str): Member name
            is_pointer (bool): Whether to use arrow (->) or dot (.) operator
            
        Returns:
            str: Converted Java member access
        """
        if is_pointer:
            # For pointer access, we might need special handling in Java
            return f"{obj_expr}.get().{member_name}"
        else:
            return f"{obj_expr}.{member_name}"