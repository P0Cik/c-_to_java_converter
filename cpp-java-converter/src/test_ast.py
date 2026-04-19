import clang.cindex
from converter_modules.core import CppToJavaConverter
import json

cpp_code = """
namespace std {
class string {
public:
    string();
    string(const char*);
    string(const string&);
    ~string();
    string& operator=(const string&);
    string& operator=(const char*);
    bool operator==(const string&) const;
    bool operator!=(const string&) const;
    string operator+(const string&) const;
};

class ostream {
public:
    template<typename T>
    ostream& operator<<(const T&);
    ostream& operator<<(ostream& (*)(ostream&));
};
class istream {
public:
    template<typename T>
    istream& operator>>(T&);
};
extern ostream cout;
extern istream cin;
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
