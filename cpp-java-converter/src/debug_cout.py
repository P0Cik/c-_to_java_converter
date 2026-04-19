import clang.cindex
from converter_modules.core import CppToJavaConverter
from converter_modules.handlers import *
import json

cpp_code = """
namespace std {
class ostream {
public:
    template<typename T> ostream& operator<<(const T&);
};
extern ostream cout;
extern ostream endl(ostream&);
}

int main() {
    int sum = 5;
    std::cout << "Sum: " << sum << std::endl;
    return 0;
}
"""

converter = CppToJavaConverter()
ast = converter._parse_with_libclang(cpp_code)
java_ast = converter._transform_ast(ast)
print(json.dumps(java_ast, indent=2))
