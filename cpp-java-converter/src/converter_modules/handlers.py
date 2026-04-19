import clang.cindex
import re
from typing import Any, Dict, List


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
        'access_specifier': 'public',
        'is_abstract': False,
        'is_final': False,
        'templates': [],
        'location': f"{node.location.file}:{node.location.line}"
    }

    for child in node.get_children():
        if child.kind == clang.cindex.CursorKind.CXX_BASE_SPECIFIER:

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
            if child.access_specifier == clang.cindex.AccessSpecifier.PRIVATE:
                class_info['access_specifier'] = 'private'
            elif child.access_specifier == clang.cindex.AccessSpecifier.PROTECTED:
                class_info['access_specifier'] = 'protected'
            elif child.access_specifier == clang.cindex.AccessSpecifier.PUBLIC:
                class_info['access_specifier'] = 'public'

        elif getattr(child.kind, 'name', '') == 'CXX_FINAL_ATTR' or str(child.kind).endswith('CXX_FINAL_ATTR'):
            class_info['is_final'] = True

    # determine if abstract based on methods
    if any(m.get('is_pure_virtual', False) for m in class_info['methods']):
        class_info['is_abstract'] = True

    if len(class_info['base_classes']) > 1:
        msg = f"Multiple inheritance detected in class {class_info['name']} - this is not supported natively in Java. Using interfaces for secondary bases."
        self.warnings.append(msg)

    return class_info


def _handle_function_declaration(self, node) -> Dict[str, Any]:
    """Handle C++ global function declaration"""
    body = None
    for child in node.get_children():
        if child.kind == clang.cindex.CursorKind.COMPOUND_STMT:
            body = self._handle_compound_statement(child)
            break

    return {
        'kind': 'function',
        'name': node.spelling,
        'return_type': node.result_type.spelling,
        'parameters': [self._handle_param(param) for param in node.get_arguments()],
        'is_static': False,
        'is_virtual': False,
        'is_const': False,
        'body': body,
        'location': f"{node.location.file}:{node.location.line}"
    }


def _handle_variable_declaration(self, node) -> Dict[str, Any]:
    """Handle C++ variable declaration"""
    array_size = None
    element_type = None
    if node.type.kind == clang.cindex.TypeKind.CONSTANTARRAY:
        array_size = node.type.get_array_size()
        element_type = node.type.get_array_element_type().spelling
    elif node.type.kind == clang.cindex.TypeKind.INCOMPLETEARRAY:
        array_size = None  # Dynamic array (e.g., char[])
    
    init_value = None
    is_class_type = node.type.get_canonical().kind == clang.cindex.TypeKind.RECORD

    if is_class_type and "string" not in node.type.spelling.lower():
        args = []
        has_constructor = False
        for child in node.get_children():
            kind_name = getattr(child.kind, 'name', '') or str(child.kind)
            if child.kind in (clang.cindex.CursorKind.CALL_EXPR, clang.cindex.CursorKind.UNEXPOSED_EXPR) or 'CXX_CONSTRUCT_EXPR' in kind_name:
                has_constructor = True
                for arg_child in child.get_children():
                    args.append(self._handle_expression(arg_child))
                break
        
        if has_constructor:
            init_value = {'kind': 'constructor_call', 'type': node.type.spelling, 'arguments': args}
        else:
            init_value = {'kind': 'constructor_call', 'type': node.type.spelling, 'arguments': []}
    else:
        def extract_value_from_node(n):
            """Recursively extract value from a node and its children"""
            if n.kind == clang.cindex.CursorKind.INTEGER_LITERAL:
                if n.spelling:
                    return n.spelling
                else:
                    tokens = [t.spelling for t in n.get_tokens()]
                    return ' '.join(tokens) if tokens else None
            elif n.kind == clang.cindex.CursorKind.FLOATING_LITERAL:
                if n.spelling:
                    return n.spelling
                else:
                    tokens = [t.spelling for t in n.get_tokens()]
                    return ' '.join(tokens) if tokens else None
            elif n.kind == clang.cindex.CursorKind.STRING_LITERAL:
                if n.spelling:
                    return n.spelling
                else:
                    tokens = [t.spelling for t in n.get_tokens()]
                    return ' '.join(tokens) if tokens else None
            elif n.kind == clang.cindex.CursorKind.CHARACTER_LITERAL:
                if n.spelling:
                    return n.spelling
                else:
                    tokens = [t.spelling for t in n.get_tokens()]
                    return ' '.join(tokens) if tokens else None
            elif n.kind == clang.cindex.CursorKind.CXX_BOOL_LITERAL_EXPR:
                if n.spelling:
                    return n.spelling
                else:
                    tokens = [t.spelling for t in n.get_tokens()]
                    return ' '.join(tokens) if tokens else None
            elif n.kind == clang.cindex.CursorKind.UNEXPOSED_EXPR:
                tokens = [t.spelling for t in n.get_tokens()]
                if tokens:
                    return ' '.join(tokens)
            elif n.kind == clang.cindex.CursorKind.BINARY_OPERATOR:
                tokens = [t.spelling for t in n.get_tokens()]
                if tokens:
                    return ' '.join(tokens)
            elif n.kind == clang.cindex.CursorKind.UNARY_OPERATOR:
                tokens = [t.spelling for t in n.get_tokens()]
                if tokens:
                    return ' '.join(tokens)
            elif n.kind == clang.cindex.CursorKind.CALL_EXPR:
                tokens = [t.spelling for t in n.get_tokens()]
                if tokens:
                    return ' '.join(tokens)
            elif n.kind == clang.cindex.CursorKind.DECL_REF_EXPR:
                tokens = [t.spelling for t in n.get_tokens()]
                if tokens:
                    return ' '.join(tokens)
            elif n.kind == clang.cindex.CursorKind.MEMBER_REF_EXPR:
                tokens = [t.spelling for t in n.get_tokens()]
                if tokens:
                    return ' '.join(tokens)
            elif n.kind == clang.cindex.CursorKind.ARRAY_SUBSCRIPT_EXPR:
                tokens = [t.spelling for t in n.get_tokens()]
                if tokens:
                    return ' '.join(tokens)
            elif n.kind == clang.cindex.CursorKind.CSTYLE_CAST_EXPR or getattr(n.kind, 'name', '') == 'CXX_STATIC_CAST_EXPR' or str(n.kind).endswith('CXX_STATIC_CAST_EXPR'):
                tokens = [t.spelling for t in n.get_tokens()]
                if tokens:
                    return ' '.join(tokens)
            elif getattr(n.kind, 'name', '') == 'COMPOUND_ASSIGNMENT_OPERATOR' or str(n.kind).endswith('ASSIGNMENT_OPERATOR'):
                for child in n.get_children():
                    value = extract_value_from_node(child)
                    if value is not None:
                        return value
            else:
                for child in n.get_children():
                    value = extract_value_from_node(child)
                    if value is not None:
                        return value
            return None

        # Look for initialization value in the children of the variable declaration
        for child in node.get_children():
            if getattr(child.kind, 'is_expression', lambda: False)() or child.kind in (clang.cindex.CursorKind.CALL_EXPR, clang.cindex.CursorKind.UNEXPOSED_EXPR):
                try:
                    expr_val = self._handle_expression(child)
                    if expr_val and isinstance(expr_val, dict):
                        init_value = expr_val
                        break
                except Exception:
                    pass

            value = extract_value_from_node(child)
            if value is not None:
                if isinstance(value, str) and value.startswith('std :: string'):
                    # Skip garbage string tokens and just look for the string literal
                    for inner_child in child.get_children():
                        inner_val = extract_value_from_node(inner_child)
                        if inner_val:
                            value = inner_val
                            break
                init_value = value
                break
    
    return {
        'kind': 'variable',
        'name': node.spelling,
        'type': node.type.spelling,
        'is_static': node.storage_class == clang.cindex.StorageClass.STATIC,
        'is_const': node.type.is_const_qualified(),
        'init_value': init_value,
        'array_size': array_size,
        'element_type': element_type,
        'location': f"{node.location.file}:{node.location.line}"
    }

def _handle_if_statement(self, node) -> Dict[str, Any]:
    """Обработка условного оператора if/else"""
    # Условие — первый дочерний узел
    condition = None
    then_body = None
    else_body = None
    
    children = list(node.get_children())
    if len(children) >= 1:
        condition = self._handle_expression(children[0])
    if len(children) >= 2:
        then_body = self._handle_compound_statement(children[1])
    if len(children) >= 3:
        else_body = self._handle_compound_statement(children[2])
    
    return {
        'kind': 'if_stmt',
        'condition': condition,
        'then_body': then_body,
        'else_body': else_body
    }

def _handle_for_statement(self, node) -> Dict[str, Any]:
    """Обработка цикла for"""
    children = list(node.get_children())
    init = None
    condition = None
    increment = None
    body = None
    
    # В AST Clang узлы for расположены в порядке: инициализация, условие, инкремент, тело
    if len(children) >= 1:
        init = self._handle_expression(children[0]) if children[0].kind != clang.cindex.CursorKind.INVALID_CODE else None
    if len(children) >= 2:
        condition = self._handle_expression(children[1]) if children[1].kind != clang.cindex.CursorKind.INVALID_CODE else None
    if len(children) >= 3:
        increment = self._handle_expression(children[2]) if children[2].kind != clang.cindex.CursorKind.INVALID_CODE else None
    if len(children) >= 4:
        body = self._handle_compound_statement(children[3])
    
    return {
        'kind': 'for_stmt',
        'init': init,
        'condition': condition,
        'increment': increment,
        'body': body
    }

def _handle_while_statement(self, node) -> Dict[str, Any]:
    """Обработка цикла while"""
    children = list(node.get_children())
    condition = self._handle_expression(children[0]) if children else None
    body = self._handle_compound_statement(children[1]) if len(children) > 1 else None
    
    return {
        'kind': 'while_stmt',
        'condition': condition,
        'body': body
    }

def _handle_do_statement(self, node) -> Dict[str, Any]:
    """Обработка цикла do-while"""
    children = list(node.get_children())
    body = self._handle_compound_statement(children[0]) if children else None
    condition = self._handle_expression(children[1]) if len(children) > 1 else None
    
    return {
        'kind': 'do_stmt',
        'body': body,
        'condition': condition
    }

def _handle_return_statement(self, node) -> Dict[str, Any]:
    """Обработка оператора return с выражением"""
    children = list(node.get_children())
    value = self._handle_expression(children[0]) if children else None
    
    return {
        'kind': 'return_stmt',
        'value': value
    }

def _handle_decl_statement(self, node) -> Dict[str, Any]:
    child = next(node.get_children(), None)
    if child and child.kind == clang.cindex.CursorKind.VAR_DECL:
        var_info = self._handle_variable_declaration(child)
        return {
            'kind': 'decl_stmt',
            'type': var_info['type'],
            'name': var_info['name'],
            'init_value': var_info.get('init_value'),
            'array_size': var_info.get('array_size'),
            'element_type': var_info.get('element_type')
        }
    return {'kind': 'unknown_stmt'}

def _handle_expression_statement(self, node) -> Dict[str, Any]:
    return {
        'kind': 'expr_stmt',
        'expression': self._handle_expression(node)
    }

def _handle_compound_statement(self, node) -> Dict[str, Any]:
    """Обработка составного оператора { ... }"""
    statements = []
    for child in node.get_children():
        stmt = self._handle_statement(child)
        if stmt:
            statements.append(stmt)
    
    return {
        'kind': 'compound_stmt',
        'statements': statements
    }

def _handle_statement(self, node) -> Dict[str, Any]:
    """Диспетчеризация обработки различных типов операторов"""
    handlers = {
        clang.cindex.CursorKind.IF_STMT: self._handle_if_statement,
        clang.cindex.CursorKind.FOR_STMT: self._handle_for_statement,
        clang.cindex.CursorKind.WHILE_STMT: self._handle_while_statement,
        clang.cindex.CursorKind.DO_STMT: self._handle_do_statement,
        clang.cindex.CursorKind.RETURN_STMT: self._handle_return_statement,
        clang.cindex.CursorKind.COMPOUND_STMT: self._handle_compound_statement,
        clang.cindex.CursorKind.DECL_STMT: self._handle_decl_statement,  # объявления переменных внутри функции
        clang.cindex.CursorKind.BINARY_OPERATOR: self._handle_expression_statement,
        clang.cindex.CursorKind.CALL_EXPR: self._handle_expression_statement,
    }
    
    handler = handlers.get(node.kind)
    if handler:
        return handler(node)
    return None

def _handle_expression(self, node) -> Dict[str, Any]:
    """Рекурсивная обработка выражений с трансляцией синтаксиса"""
    # Базовый случай: литералы
    if node.kind == clang.cindex.CursorKind.INTEGER_LITERAL:
        tokens = list(node.get_tokens())
        value = tokens[0].spelling if tokens else "0"
        return {'kind': 'literal', 'value': value}
    
    elif node.kind == clang.cindex.CursorKind.FLOATING_LITERAL:
        tokens = list(node.get_tokens())
        value = tokens[0].spelling if tokens else "0.0"
        return {'kind': 'literal', 'value': value}
    
    elif node.kind == clang.cindex.CursorKind.STRING_LITERAL:
        tokens = list(node.get_tokens())
        value = tokens[0].spelling if tokens else '""'
        # Убираем лишние кавычки, добавленные лексером Clang
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        return {'kind': 'literal', 'value': f'"{value}"'}
    
    elif node.kind == clang.cindex.CursorKind.CXX_BOOL_LITERAL_EXPR:
        tokens = list(node.get_tokens())
        value = tokens[0].spelling.lower() if tokens else "false"
        return {'kind': 'literal', 'value': value}
    
    # Идентификаторы (переменные)
    elif node.kind == clang.cindex.CursorKind.DECL_REF_EXPR:
        return {'kind': 'identifier', 'name': node.spelling}
    
    # Вызовы функций/методов
    elif node.kind == clang.cindex.CursorKind.CALL_EXPR:
        callee_orig = node.spelling or ""
        children = list(node.get_children())
        
        args = []
        callee_expr = None
        
        # Determine if it's an overloaded binary operator call `[arg1, callee, arg2]` layout
        if len(children) == 3 and 'operator' in callee_orig:
            # Check if middle child looks like a callee (DECL_REF_EXPR or UNEXPOSED_EXPR)
            if children[1].kind in (clang.cindex.CursorKind.DECL_REF_EXPR, clang.cindex.CursorKind.UNEXPOSED_EXPR):
                callee_expr = self._handle_expression(children[1])
                args = [self._handle_expression(children[0]), self._handle_expression(children[2])]
        
        if callee_expr is None:
            if children:
                callee_expr = self._handle_expression(children[0])
                args = [self._handle_expression(arg) for arg in children[1:]]
            else:
                callee_expr = {'kind': 'identifier', 'name': callee_orig}
        
        return {'kind': 'call', 'callee': callee_expr, 'arguments': args, 'callee_orig': callee_orig}
    
    # Бинарные операторы (+, -, *, /, ==, !=, <, >, &&, ||)
    elif node.kind == clang.cindex.CursorKind.BINARY_OPERATOR:
        children = list(node.get_children())
        if len(children) >= 2:
            left = self._handle_expression(children[0])
            right = self._handle_expression(children[1])
            
            left_tokens = list(children[0].get_tokens())
            tokens = list(node.get_tokens())
            
            if len(left_tokens) < len(tokens):
                op = tokens[len(left_tokens)].spelling
            else:
                op = "?"
            
            # Маппинг операторов C++ → Java (большинство идентичны)
            op_map = {
                '&&': '&&', '||': '||', 
                '==': '==', '!=': '!=', 
                '<': '<', '<=': '<=', 
                '>': '>', '>=': '>=',
                '+': '+', '-': '-', 
                '*': '*', '/': '/', '%': '%',
                '=': '='
            }
            op = op_map.get(op, op)
            
            return {'kind': 'binary_op', 'op': op, 'left': left, 'right': right}
    
    # Унарные операторы (!, -, ++)
    elif node.kind == clang.cindex.CursorKind.UNARY_OPERATOR:
        children = list(node.get_children())
        if children:
            operand = self._handle_expression(children[0])
            tokens = list(node.get_tokens())
            op = tokens[0].spelling if tokens else "?"
            return {'kind': 'unary_op', 'op': op, 'operand': operand}
    
    # Доступ к членам через точку или стрелку (-> → .)
    elif node.kind == clang.cindex.CursorKind.MEMBER_REF_EXPR:
        children = list(node.get_children())
        if children:
            base = self._handle_expression(children[0])
            member = node.spelling
            return {'kind': 'member_access', 'base': base, 'member': member}
    
    # Указатели: *expr → expr (в Java нет разыменования)
    elif node.kind == clang.cindex.CursorKind.UNARY_OPERATOR:
        tokens = list(node.get_tokens())
        if tokens and tokens[0].spelling == '*':
            children = list(node.get_children())
            if children:
                return self._handle_expression(children[0])  # Просто возвращаем операнд
    
    # Выделение/освобождение памяти
    elif getattr(node.kind, 'name', '') == 'CXX_DELETE_EXPR' or str(node.kind).endswith('CXX_DELETE_EXPR'):
        return {'kind': 'unknown_expr', 'repr': '/* delete handled by GC */'}
    
    # По умолчанию — возвращаем исходный код по токенам
    tokens = list(node.get_tokens())
    if tokens:
        return {'kind': 'unknown_expr', 'repr': " ".join(t.spelling for t in tokens)}
    return {'kind': 'unknown_expr', 'repr': node.spelling or str(node.kind)}

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
    body = None
    initializers = []
    for child in node.get_children():
        if child.kind == clang.cindex.CursorKind.COMPOUND_STMT:
            body = self._handle_compound_statement(child)
        elif getattr(child.kind, 'name', '') == 'CXX_CTOR_INITIALIZER' or str(child.kind).endswith('CXX_CTOR_INITIALIZER'):
            exprs = list(child.get_children())
            if exprs and child.spelling:
                expr_ast = self._handle_expression(exprs[0])
                initializers.append({'field': child.spelling, 'value': expr_ast})

    if body is None:
        body = {'kind': 'compound_stmt', 'statements': []}
        
    init_stmts = []
    for init in initializers:
        init_stmts.append({
            'kind': 'expr_stmt',
            'expression': {
                'kind': 'binary_op',
                'op': '=',
                'left': {'kind': 'member_access', 'base': {'kind': 'identifier', 'name': 'this'}, 'member': init['field']},
                'right': init['value']
            }
        })
    body['statements'] = init_stmts + body.get('statements', [])

    return {
        'kind': 'constructor',
        'name': node.spelling,
        'parameters': [self._handle_param(param) for param in node.get_arguments()],
        'body': body,
        'location': f"{node.location.file}:{node.location.line}"
    }


def _handle_destructor(self, node) -> Dict[str, Any]:
    """Handle C++ destructor - important for RAII to Java conversion"""
    body = None
    for child in node.get_children():
        if child.kind == clang.cindex.CursorKind.COMPOUND_STMT:
            body = self._handle_compound_statement(child)
            break

    return {
        'kind': 'destructor',
        'name': node.spelling,
        'body': body,
        'location': f"{node.location.file}:{node.location.line}",
        'needs_raii_emulation': True
    }


def _handle_method(self, node) -> Dict[str, Any]:
    """Handle C++ method"""
    body = None
    for child in node.get_children():
        if child.kind == clang.cindex.CursorKind.COMPOUND_STMT:
            body = self._handle_compound_statement(child)
            break

    method_info = {
        'kind': 'method',
        'name': node.spelling,
        'return_type': node.result_type.spelling,
        'parameters': [self._handle_param(param) for param in node.get_arguments()],
        'is_static': node.is_static_method(),
        'is_virtual': node.is_virtual_method(),
        'is_const': hasattr(node, 'is_const_method') and node.is_const_method(),
        'is_override': any(getattr(child.kind, 'name', '') == 'CXX_OVERRIDE_ATTR' or str(child.kind).endswith('CXX_OVERRIDE_ATTR') for child in node.get_children()),
        'is_final': any(getattr(child.kind, 'name', '') == 'CXX_FINAL_ATTR' or str(child.kind).endswith('CXX_FINAL_ATTR') for child in node.get_children()),
        'is_pure_virtual': node.is_pure_virtual_method(),
        'access': self._get_access_level(node),
        'body': body,
        'location': f"{node.location.file}:{node.location.line}"
    }


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

    tokens = list(node.get_tokens())
    if len(tokens) >= 3:
        macro_text = ' '.join([token.spelling for token in tokens[1:]])


        if self._is_constant_macro(macro_text):
            return {
                'kind': 'macro_constant',
                'name': node.spelling,
                'value': macro_text.strip(),
                'location': f"{node.location.file}:{node.location.line}"
            }
        else:

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

        clean_text = text.replace('.', '').replace('_', '').replace('-', '')
        return clean_text.isdigit()


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
        elif child.kind == clang.cindex.CursorKind.TEMPLATE_NON_TYPE_PARAMETER:
            template_params.append({
                'name': child.spelling,
                'type': child.type.spelling,
                'is_non_type': True
            })
        elif child.kind == clang.cindex.CursorKind.CLASS_DECL:
            class_decl_node = child

    if class_decl_node is None:

        for child in node.get_children():
            if child.kind == clang.cindex.CursorKind.STRUCT_DECL:
                class_decl_node = child
                break

    class_body = {}
    if class_decl_node:
        class_body = self._handle_class_declaration(class_decl_node)
    else:

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
    init_value = None
    def extract_value_from_node(n):
        """Recursively extract value from a node and its children"""
        if n.kind == clang.cindex.CursorKind.INTEGER_LITERAL:
            # Use tokens if spelling is empty
            if n.spelling:
                return n.spelling
            else:
                tokens = [t.spelling for t in n.get_tokens()]
                return ' '.join(tokens) if tokens else None
        elif n.kind == clang.cindex.CursorKind.FLOATING_LITERAL:
            # Use tokens if spelling is empty
            if n.spelling:
                return n.spelling
            else:
                tokens = [t.spelling for t in n.get_tokens()]
                return ' '.join(tokens) if tokens else None
        elif n.kind == clang.cindex.CursorKind.STRING_LITERAL:
            # Use tokens if spelling is empty
            if n.spelling:
                return n.spelling
            else:
                tokens = [t.spelling for t in n.get_tokens()]
                return ' '.join(tokens) if tokens else None
        elif n.kind == clang.cindex.CursorKind.CHARACTER_LITERAL:
            # Use tokens if spelling is empty
            if n.spelling:
                return n.spelling
            else:
                tokens = [t.spelling for t in n.get_tokens()]
                return ' '.join(tokens) if tokens else None
        elif n.kind == clang.cindex.CursorKind.CXX_BOOL_LITERAL_EXPR:
            # Use tokens if spelling is empty
            if n.spelling:
                return n.spelling
            else:
                tokens = [t.spelling for t in n.get_tokens()]
                return ' '.join(tokens) if tokens else None
        elif n.kind == clang.cindex.CursorKind.UNEXPOSED_EXPR:
            # Get the raw tokens for the expression
            tokens = [t.spelling for t in n.get_tokens()]
            if tokens:
                return ' '.join(tokens)
        elif n.kind == clang.cindex.CursorKind.BINARY_OPERATOR:
            # Handle binary operations like assignment expressions
            tokens = [t.spelling for t in n.get_tokens()]
            if tokens:
                return ' '.join(tokens)
        elif n.kind == clang.cindex.CursorKind.UNARY_OPERATOR:
            # Handle unary operations
            tokens = [t.spelling for t in n.get_tokens()]
            if tokens:
                return ' '.join(tokens)
        elif n.kind == clang.cindex.CursorKind.CALL_EXPR:
            # Handle function calls in initialization
            tokens = [t.spelling for t in n.get_tokens()]
            if tokens:
                return ' '.join(tokens)
        elif n.kind == clang.cindex.CursorKind.DECL_REF_EXPR:
            # Handle references to other variables/constants
            tokens = [t.spelling for t in n.get_tokens()]
            if tokens:
                return ' '.join(tokens)
        elif n.kind == clang.cindex.CursorKind.MEMBER_REF_EXPR:
            # Handle member references
            tokens = [t.spelling for t in n.get_tokens()]
            if tokens:
                return ' '.join(tokens)
        elif n.kind == clang.cindex.CursorKind.ARRAY_SUBSCRIPT_EXPR:
            # Handle array subscript expressions
            tokens = [t.spelling for t in n.get_tokens()]
            if tokens:
                return ' '.join(tokens)
        elif n.kind == clang.cindex.CursorKind.CSTYLE_CAST_EXPR or n.kind == clang.cindex.CursorKind.CXX_STATIC_CAST_EXPR:
            # Handle casts in initialization
            tokens = [t.spelling for t in n.get_tokens()]
            if tokens:
                return ' '.join(tokens)
        elif n.kind == clang.cindex.CursorKind.COMPOUND_ASSIGNMENT_OPERATOR or (hasattr(clang.cindex.CursorKind, 'ASSIGNMENT_OPERATOR') and n.kind == clang.cindex.CursorKind.ASSIGNMENT_OPERATOR):
            for child in n.get_children():
                # Skip the left operand (the variable name) and focus on the right operand (the value)
                value = extract_value_from_node(child)
                if value is not None:
                    return value
        else:
            # Recursively check children for initialization values
            for child in n.get_children():
                value = extract_value_from_node(child)
                if value is not None:
                    return value
        return None

    # Look for initialization value in the children of the field declaration
    for child in node.get_children():
        value = extract_value_from_node(child)
        if value is not None:
            init_value = value
            break

    return {
        'kind': 'field',
        'name': node.spelling,
        'type': node.type.spelling,
        'is_static': node.storage_class == clang.cindex.StorageClass.STATIC,
        'is_const': node.type.is_const_qualified(),
        'init_value': init_value,
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
    if child_node.kind == clang.cindex.CursorKind.CLASS_DECL:
        return self._handle_class_declaration(child_node)
    elif child_node.kind == clang.cindex.CursorKind.FUNCTION_DECL:
        return self._handle_function_declaration(child_node)
    elif child_node.kind == clang.cindex.CursorKind.VAR_DECL:
        return self._handle_variable_declaration(child_node)
    else:
        return {
            'kind': str(child_node.kind),
            'spelling': child_node.spelling,
            'location': f"{child_node.location.file}:{child_node.location.line}"
        }