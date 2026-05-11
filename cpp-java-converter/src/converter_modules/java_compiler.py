"""Java compiler integration module"""

import subprocess
import tempfile
import os
from typing import Dict, Any, List, Optional


class JavaCompiler:
    """Compiles and validates generated Java code"""

    def __init__(self, javac_path: str = "javac"):
        """
        Initialize Java compiler

        Args:
            javac_path (str): Path to javac executable
        """
        self.javac_path = javac_path
        self._check_javac_available()

    def _check_javac_available(self) -> bool:
        """Check if javac is available in the system"""
        try:
            result = subprocess.run(
                [self.javac_path, "-version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def compile(self, java_code: str, class_name: str = "GeneratedCode") -> Dict[str, Any]:
        """
        Compile Java code and return compilation result

        Args:
            java_code (str): Java source code to compile
            class_name (str): Name of the main class

        Returns:
            Dict containing compilation status, errors, and warnings
        """
        result = {
            'success': False,
            'errors': [],
            'warnings': [],
            'output': '',
            'class_files': []
        }

        if not self._check_javac_available():
            result['errors'].append(f"Java compiler (javac) not found at '{self.javac_path}'")
            return result

        with tempfile.TemporaryDirectory() as temp_dir:
            java_file_path = os.path.join(temp_dir, f"{class_name}.java")

            try:
                with open(java_file_path, 'w', encoding='utf-8') as f:
                    f.write(java_code)

                compile_result = subprocess.run(
                    [self.javac_path, "-d", temp_dir, "-Xlint:all", java_file_path],
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                result['output'] = compile_result.stdout + compile_result.stderr

                if compile_result.returncode == 0:
                    result['success'] = True

                    for root, dirs, files in os.walk(temp_dir):
                        for file in files:
                            if file.endswith('.class'):
                                result['class_files'].append(file)

                self._parse_javac_output(compile_result.stderr, result)

            except subprocess.TimeoutExpired:
                result['errors'].append("Compilation timeout (30 seconds exceeded)")
            except Exception as e:
                result['errors'].append(f"Compilation error: {str(e)}")

        return result

    def _parse_javac_output(self, output: str, result: Dict[str, Any]) -> None:
        """Parse javac output to extract errors and warnings"""
        if not output:
            return

        lines = output.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue

            if 'error:' in line.lower():
                result['errors'].append(line)
            elif 'warning:' in line.lower():
                result['warnings'].append(line)

    def validate_syntax(self, java_code: str) -> Dict[str, Any]:
        """
        Quick syntax validation without full compilation

        Args:
            java_code (str): Java source code

        Returns:
            Dict with validation results
        """
        validation_result = {
            'is_valid': True,
            'issues': []
        }

        open_braces = java_code.count('{')
        close_braces = java_code.count('}')
        if open_braces != close_braces:
            validation_result['is_valid'] = False
            validation_result['issues'].append(
                f"Mismatched braces: {open_braces} opening, {close_braces} closing"
            )

        open_parens = java_code.count('(')
        close_parens = java_code.count(')')
        if open_parens != close_parens:
            validation_result['is_valid'] = False
            validation_result['issues'].append(
                f"Mismatched parentheses: {open_parens} opening, {close_parens} closing"
            )

        if 'class ' not in java_code and 'interface ' not in java_code and 'enum ' not in java_code:
            validation_result['is_valid'] = False
            validation_result['issues'].append("No class, interface, or enum declaration found")

        return validation_result


def compile_java_code(java_code: str, class_name: str = "GeneratedCode", javac_path: str = "javac") -> Dict[str, Any]:
    """
    Convenience function to compile Java code

    Args:
        java_code (str): Java source code
        class_name (str): Name of the main class
        javac_path (str): Path to javac executable

    Returns:
        Dict with compilation results
    """
    compiler = JavaCompiler(javac_path)
    return compiler.compile(java_code, class_name)
