"""
Models for the C++ to Java converter
"""

class Expression:
    """Base class for expressions"""
    def __init__(self):
        self.type = None
        self.value = None

class SimpleDeclaration:
    """Model for a simple declaration"""
    def __init__(self, name=None, type_decl=None, init_expr=None, is_static=False, is_public=True):
        self.name = name
        self.type = type_decl
        self.init_expr = init_expr
        self.is_static = is_static
        self.is_public = is_public

class ClassDeclaration:
    """Model for a class declaration"""
    def __init__(self, name=None, declarations=None, super_class=None, has_ctor=False, has_dtor=False, has_copy=False, has_assign=False):
        self.name = name
        self.declarations = declarations or []
        self.super_class = super_class
        self.has_ctor = has_ctor
        self.has_dtor = has_dtor
        self.has_copy = has_copy
        self.has_assign = has_assign