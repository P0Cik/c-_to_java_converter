"""C++ code validation module"""

import re
from typing import Dict, Any, List


class CppCodeValidator:
    """Validates C++ code before translation to Java"""

    def __init__(self, mode: str = "strict"):
        self.mode = mode
        self.unsupported_patterns = [
            (r'\bgoto\b', 'goto statements'),
            (r'\basm\b\s*\(', 'inline assembly'),
            (r'\bvolatile\b', 'volatile keyword (may need manual review)'),
            (r'\breinterpret_cast\b', 'reinterpret_cast (unsafe casting)'),
            (r'\bunion\b\s+\w+\s*\{', 'union declarations'),
            (r'#\s*pragma\b', 'pragma directives'),
            (r'\bfriend\b\s+class', 'friend classes'),
            (r'\bvirtual\b\s+.*\s+operator\s*=', 'virtual assignment operators'),
            (r'\bexplicit\b\s+operator\b', 'explicit conversion operators (may need review)'),
            (r'\bbit_cast\b', 'bit_cast (C++20 feature)'),
            (r'\bconcept\b', 'concepts (C++20 feature)'),
            (r'\brequires\b', 'requires clause (C++20 feature)'),
            (r'\bco_await\b|\bco_yield\b|\bco_return\b', 'coroutines (C++20 feature)'),
        ]

    def validate(self, cpp_code: str) -> Dict[str, Any]:
        """Perform comprehensive validation of C++ code before translation"""
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'unsupported_features': [],
            'complexity_metrics': {},
            'syntax_issues': []
        }

        if not cpp_code or not cpp_code.strip():
            validation_result['is_valid'] = False
            validation_result['errors'].append("Empty or whitespace-only code provided")
            return validation_result

        self._check_basic_syntax(cpp_code, validation_result)
        self._check_unsupported_features(cpp_code, validation_result)
        self._calculate_complexity_metrics(cpp_code, validation_result)
        self._check_common_issues(cpp_code, validation_result)

        if validation_result['unsupported_features'] and self.mode == 'strict':
            validation_result['is_valid'] = False
            validation_result['errors'].append("Unsupported features detected in strict mode")

        if validation_result['syntax_issues']:
            validation_result['is_valid'] = False

        return validation_result

    def _check_basic_syntax(self, cpp_code: str, result: Dict[str, Any]) -> None:
        """Check basic syntax issues"""
        open_braces = cpp_code.count('{')
        close_braces = cpp_code.count('}')
        if open_braces != close_braces:
            result['syntax_issues'].append(f"Mismatched braces: {open_braces} opening, {close_braces} closing")
            result['errors'].append("Syntax error: Mismatched braces")

        open_parens = cpp_code.count('(')
        close_parens = cpp_code.count(')')
        if open_parens != close_parens:
            result['syntax_issues'].append(f"Mismatched parentheses: {open_parens} opening, {close_parens} closing")
            result['errors'].append("Syntax error: Mismatched parentheses")

        lines = cpp_code.split('\n')
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith('#include') and not (stripped.endswith('>') or stripped.endswith('"')):
                result['warnings'].append(f"Line {i}: Malformed #include directive")

    def _check_unsupported_features(self, cpp_code: str, result: Dict[str, Any]) -> None:
        """Check for unsupported C++ features"""
        for pattern, feature_name in self.unsupported_patterns:
            matches = re.finditer(pattern, cpp_code)
            for match in matches:
                line_num = cpp_code[:match.start()].count('\n') + 1
                snippet = cpp_code[max(0, match.start()-20):min(len(cpp_code), match.end()+20)]
                result['unsupported_features'].append({
                    'feature': feature_name,
                    'line': line_num,
                    'snippet': snippet.strip()
                })
                result['warnings'].append(f"Line {line_num}: Unsupported feature '{feature_name}' detected")

    def _calculate_complexity_metrics(self, cpp_code: str, result: Dict[str, Any]) -> None:
        """Calculate code complexity metrics"""
        class_count = len(re.findall(r'\bclass\s+\w+', cpp_code))
        struct_count = len(re.findall(r'\bstruct\s+\w+', cpp_code))
        template_count = len(re.findall(r'\btemplate\s*<', cpp_code))
        operator_count = len(re.findall(r'\boperator\s*[+\-*/=<>!\[\]()]+', cpp_code))
        pointer_count = len(re.findall(r'\w+\s*\*\s*\w+', cpp_code))
        reference_count = len(re.findall(r'\w+\s*&\s*\w+', cpp_code))
        virtual_count = len(re.findall(r'\bvirtual\b', cpp_code))
        inheritance_count = len(re.findall(r':\s*public\s+\w+', cpp_code))
        namespace_count = len(re.findall(r'\bnamespace\s+\w+', cpp_code))
        macro_count = len(re.findall(r'#\s*define\s+\w+', cpp_code))

        result['complexity_metrics'] = {
            'class_count': class_count,
            'struct_count': struct_count,
            'template_count': template_count,
            'operator_overload_count': operator_count,
            'pointer_usage_count': pointer_count,
            'reference_usage_count': reference_count,
            'virtual_method_count': virtual_count,
            'inheritance_count': inheritance_count,
            'namespace_count': namespace_count,
            'macro_count': macro_count,
            'total_lines': len(cpp_code.split('\n'))
        }

        if pointer_count > 50:
            result['warnings'].append(
                f"High pointer usage detected ({pointer_count} instances) - may require manual review"
            )

        if template_count > 20:
            result['warnings'].append(
                f"High template usage detected ({template_count} instances) - complex generics may be generated"
            )

        if operator_count > 15:
            result['warnings'].append(
                f"High operator overloading detected ({operator_count} instances) - verify generated method names"
            )

        if inheritance_count > 10:
            result['warnings'].append(
                f"Complex inheritance hierarchy detected ({inheritance_count} instances)"
            )

    def _check_common_issues(self, cpp_code: str, result: Dict[str, Any]) -> None:
        """Check for common translation issues"""
        if re.search(r'\bmultiple\s+inheritance\b', cpp_code, re.IGNORECASE):
            result['warnings'].append("Multiple inheritance detected - will be converted to interfaces")

        if re.search(r'\bstd::shared_ptr\b|\bstd::unique_ptr\b', cpp_code):
            result['warnings'].append("Smart pointers detected - Java uses garbage collection, manual conversion may be needed")

        if re.search(r'\bstd::thread\b|\bstd::mutex\b|\bstd::atomic\b', cpp_code):
            result['warnings'].append("Threading primitives detected - Java threading model differs from C++")

        if re.search(r'\bconstexpr\b', cpp_code):
            result['warnings'].append("constexpr detected - will be converted to static final, compile-time evaluation may differ")

        if re.search(r'\bauto\b\s+\w+\s*=', cpp_code):
            result['warnings'].append("auto keyword detected - type inference may need manual verification in Java")

        if re.search(r'\blambda\b|\[\s*\]\s*\(', cpp_code):
            result['warnings'].append("Lambda expressions detected - will be converted to Java lambdas/anonymous classes")


def validate_cpp_code(cpp_code: str, mode: str = "strict") -> Dict[str, Any]:
    """Convenience function to validate C++ code"""
    validator = CppCodeValidator(mode)
    return validator.validate(cpp_code)
