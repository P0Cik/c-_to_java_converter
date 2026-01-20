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

        elif child.kind == clang.cindex.CursorKind.CXX_FINAL_ATTR:
            class_info['is_final'] = True

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
        'is_static': False,
        'is_virtual': False,
        'is_const': False,
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
        'needs_raii_emulation': True
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