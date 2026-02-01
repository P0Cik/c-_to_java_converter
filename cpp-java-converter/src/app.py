
import streamlit as st
from converter import CppToJavaConverter


def main():
    st.set_page_config(
        page_title="Конвертер C++ в Java",
        page_icon="file_icon",
        layout="wide"
    )
    
    
    st.markdown("""
    <style>
    .main {
        background-color: white;
        color: black;
    }
    .stButton>button {
        background-color: #007bff;
        color: white;
        border: none;
    }
    .stButton>button:hover {
        background-color: #0056b3;
    }
    .css-1d391kg, .css-1off84d, .css-1avcm0n {
        background-color: white !important;
        color: black !important;
    }
    .st-emotion-cache-1v0mbdj {
        border: 1px solid #007bff;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.title(" Конвертер исходного кода C++ в Java")
    st.markdown("""
    Этот инструмент преобразует исходный код C++ в код Java с использованием парсинга на основе AST с помощью libclang.
    Он обрабатывает различные конструкции C++, включая классы, шаблоны, паттерны RAII и перегрузку операторов.
    """)

    # Initialize session state
    if 'converted_code' not in st.session_state:
        st.session_state.converted_code = ""
    if 'conversion_report' not in st.session_state:
        st.session_state.conversion_report = {}
    if 'error_message' not in st.session_state:
        st.session_state.error_message = ""
    if 'cpp_input' not in st.session_state:
        st.session_state.cpp_input = ""
    
    # Sidebar for settings
    st.sidebar.header(" Настройки")
    conversion_mode = st.sidebar.radio(
        "Режим конвертации:",
        ("strict", "flexible"),
        help="Строгий режим останавливается при неподдерживаемых конструкциях, гибкий режим генерирует заглушки с комментариями TODO"
    )
    
    verbose_output = st.sidebar.checkbox("Подробный вывод", value=False)
    
    # Create tabs for input and examples
    tab1, tab2, tab3 = st.tabs([" Ввод кода", " Примеры", " Отчет о конвертации"])
    
    with tab1:
        # File uploader for C++ files
        uploaded_file = st.file_uploader(
            "Загрузите C++ файл (.cpp, .h, .cxx, .cc)",
            type=['cpp', 'cxx', 'cc', 'c', 'h', 'hpp'],
            key="file_uploader"
        )
        
        if uploaded_file is not None:
            # Read the uploaded file
            content = uploaded_file.read().decode("utf-8")
            st.session_state.cpp_input = content
            st.success(f"Файл '{uploaded_file.name}' успешно загружен!")
        
        # Text area for C++ code input
        cpp_input = st.text_area(
            "Введите ваш C++ код:",
            value=st.session_state.cpp_input,
            height=400,
            placeholder="// Вставьте ваш C++ код сюда...\n// Поддерживает классы, функции, шаблоны, пространства имен и т.д.",
            key="cpp_input_textarea"
        )
        
        # Update session state when text area changes
        if cpp_input != st.session_state.cpp_input:
            st.session_state.cpp_input = cpp_input
        
        # Conversion button
        col1, col2 = st.columns([1, 3])
        with col1:
            convert_clicked = st.button("🔄 Конвертировать в Java", type="primary")
        
        with col2:
            st.caption("Примечание: Этот конвертер использует libclang для точного синтаксического анализа AST и семантического анализа.")
    
    with tab2:
        st.subheader("Примеры кода C++")
        
        example_tabs = st.tabs(["Класс", "Шаблон", "Пространство имен", "Оператор"])
        
        with example_tabs[0]:
            class_example = """// Базовый класс с конструктором и методами
class Rectangle {
private:
    double width, height;

public:
    Rectangle(double w, double h) : width(w), height(h) {}
    
    double getArea() const {
        return width * height;
    }
    
    double getPerimeter() const {
        return 2 * (width + height);
    }
    
    ~Rectangle() {
        // Код очистки
    }
};"""
            st.code(class_example, language="cpp")
            if st.button("Загрузить пример класса"):
                st.session_state.cpp_input = class_example
                st.rerun()
        
        with example_tabs[1]:
            template_example = """// Шаблон класса
template<typename T>
class Container {
private:
    T* data;
    size_t size;

public:
    Container(size_t s) : size(s) {
        data = new T[size];
    }
    
    T& operator[](size_t index) {
        return data[index];
    }
    
    ~Container() {
        delete[] data;
    }
};"""
            st.code(template_example, language="cpp")
            if st.button("Загрузить пример шаблона"):
                st.session_state.cpp_input = template_example
                st.rerun()
        
        with example_tabs[2]:
            namespace_example = """// Использование пространства имен
namespace graphics {
    namespace shapes {
        class Circle {
        public:
            double radius;
            
            Circle(double r) : radius(r) {}
            double area() const {
                return 3.14159 * radius * radius;
            }
        };
    }
}"""
            st.code(namespace_example, language="cpp")
            if st.button("Загрузить пример пространства имен"):
                st.session_state.cpp_input = namespace_example
                st.rerun()
        
        with example_tabs[3]:
            operator_example = """// Перегрузка оператора
class Complex {
private:
    double real, imag;

public:
    Complex(double r = 0, double i = 0) : real(r), imag(i) {}
    
    Complex operator+(const Complex& other) const {
        return Complex(real + other.real, imag + other.imag);
    }
    
    Complex operator-(const Complex& other) const {
        return Complex(real - other.real, imag - other.imag);
    }
    
    bool operator==(const Complex& other) const {
        return (real == other.real && imag == other.imag);
    }
};"""
            st.code(operator_example, language="cpp")
            if st.button("Загрузить пример оператора"):
                st.session_state.cpp_input = operator_example
                st.rerun()
    
    # Perform conversion when button is clicked
    if convert_clicked and cpp_input.strip():
        try:
            with st.spinner("Конвертируем C++ код в Java... Это может занять некоторое время."):
                converter = CppToJavaConverter(mode=conversion_mode, verbose=verbose_output)
                java_output = converter.convert(cpp_input)
                
                st.session_state.converted_code = java_output
                st.session_state.conversion_report = converter.generate_report()
                st.session_state.error_message = ""
                
                st.success(" Конвертация успешно завершена!")
                
        except Exception as e:
            st.session_state.error_message = f" Ошибка во время конвертации: {str(e)}"
            st.session_state.converted_code = ""
            st.session_state.conversion_report = {}
            st.error(st.session_state.error_message)
    
    # Display results if available
    if st.session_state.converted_code:
        st.subheader(" Сконвертированный Java код")
        
        # Show the converted code
        st.code(st.session_state.converted_code, language="java")
        
        # Provide download button
        st.download_button(
            label=" Скачать Java код",
            data=st.session_state.converted_code,
            file_name="converted_code.java",
            mime="text/plain"
        )
    
    with tab3:
        st.subheader(" Отчет о конвертации")
        
        if st.session_state.conversion_report:
            report = st.session_state.conversion_report
            
            # Display report metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("AST Nodes", report['stats'].get('ast_nodes', 0))
            with col2:
                st.metric("Warnings", len(report.get('warnings', [])))
            with col3:
                st.metric("Errors", len(report.get('errors', [])))
            with col4:
                st.metric("Mode", conversion_mode.upper())
            
            # Show warnings if any
            if report.get('warnings'):
                st.warning(f" Warnings ({len(report['warnings'])}):")
                for warning in report['warnings']:
                    st.text("- " + warning)
            
            # Show errors if any
            if report.get('errors'):
                st.error(f" Errors ({len(report['errors'])}):")
                for error in report['errors']:
                    st.text("- " + error)
            
            # Show detailed stats
            with st.expander("Technical Details"):
                st.json(report)
        else:
            st.info("No conversion report available. Run a conversion to see the report.")
    
    # Add information about the tool
    with st.expander("ℹ️ About this tool"):
        st.markdown("""
        ### Features:
        - **AST-based parsing**: Uses libclang for accurate C++ parsing and semantic analysis
        - **Comprehensive conversion**: Handles classes, inheritance, templates, RAII, operator overloading
        - **Multiple inheritance**: Converts to Java interfaces + composition
        - **Template support**: Transforms C++ templates to Java generics
        - **RAII emulation**: Converts C++ RAII patterns to Java AutoCloseable/Try-with-resources
        - **Operator overloading**: Maps C++ operators to appropriate Java methods
        - **Detailed reporting**: Provides conversion statistics and diagnostics
        
        ### Supported Conversions:
        - Classes and single inheritance → Java classes
        - Multiple inheritance → Interfaces + composition
        - Templates → Generics
        - RAII patterns → AutoCloseable + try-with-resources
        - Operator overloading → Named methods (e.g., operator+ → plus())
        - Namespaces → Packages
        - Const/constexpr → final/static final
        - Virtual/final/override → Java equivalents
        
        ### Modes:
        - **Strict mode**: Stops conversion when encountering unsupported C++ features
        - **Flexible mode**: Generates stubs with `// TODO: manual fix required` comments
        
        This tool implements all requirements for C++ to Java conversion with focus on semantic correctness.
        """)


if __name__ == "__main__":
    main()