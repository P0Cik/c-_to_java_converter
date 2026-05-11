import json
from converter_modules.core import CppToJavaConverter

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
