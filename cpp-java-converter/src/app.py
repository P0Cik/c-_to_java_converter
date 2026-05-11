import streamlit as st
from converter_modules.core import CppToJavaConverter


def main():
    st.set_page_config(
        page_title="Конвертер C++ в Java",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Material Design inspired CSS
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');

    * {
        font-family: 'Roboto', sans-serif;
    }

    .main {
        background-color: #fafafa;
    }

    .stButton>button {
        background-color: #1976D2;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 0.5rem 1.5rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        transition: all 0.3s ease;
    }

    .stButton>button:hover {
        background-color: #1565C0;
        box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        transform: translateY(-1px);
    }

    .stTextArea textarea {
        border: 1px solid #37474F;
        border-radius: 4px;
        font-family: 'Courier New', monospace;
        background-color: #263238;
        color: #E0E0E0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.3);
    }

    .stTextArea textarea:focus {
        border-color: #64B5F6;
        box-shadow: 0 0 0 2px rgba(100,181,246,0.3);
    }

    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 0.5rem 0;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #263238;
        padding: 0.5rem;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 4px;
        padding: 0.5rem 1rem;
        font-weight: 500;
        color: #B0BEC5;
    }

    .stTabs [aria-selected="true"] {
        background-color: #37474F;
        color: #64B5F6;
    }

    .success-box {
        background-color: #E8F5E9;
        border-left: 4px solid #4CAF50;
        padding: 1rem;
        border-radius: 4px;
        margin: 1rem 0;
    }

    .error-box {
        background-color: #FFEBEE;
        border-left: 4px solid #F44336;
        padding: 1rem;
        border-radius: 4px;
        margin: 1rem 0;
    }

    .warning-box {
        background-color: #FFF3E0;
        border-left: 4px solid #FF9800;
        padding: 1rem;
        border-radius: 4px;
        margin: 1rem 0;
    }

    h1, h2, h3 {
        color: #212121;
        font-weight: 500;
    }

    .stDownloadButton>button {
        background-color: #43A047;
        color: white;
        border-radius: 4px;
        font-weight: 500;
    }

    .stDownloadButton>button:hover {
        background-color: #388E3C;
    }
    </style>
    """, unsafe_allow_html=True)

    # Header
    st.title("Конвертер C++ в Java")
    st.markdown("**Преобразование C++ кода в Java с семантическим анализом на основе AST**")
    st.divider()

    # Initialize session state
    if 'converted_code' not in st.session_state:
        st.session_state.converted_code = ""
    if 'conversion_report' not in st.session_state:
        st.session_state.conversion_report = {}
    if 'error_message' not in st.session_state:
        st.session_state.error_message = ""
    if 'cpp_input' not in st.session_state:
        st.session_state.cpp_input = ""
    if 'compilation_result' not in st.session_state:
        st.session_state.compilation_result = None

    # Sidebar settings
    with st.sidebar:
        st.header("Настройки")

        conversion_mode = st.radio(
            "Режим конвертации",
            ("strict", "flexible"),
            help="Строгий режим останавливается на неподдерживаемых функциях, гибкий режим генерирует TODO заглушки"
        )

        verbose_output = st.checkbox("Подробный вывод", value=False)

        compile_java = st.checkbox(
            "Компилировать Java код",
            value=True,
            help="Автоматически компилировать сгенерированный Java код для проверки корректности"
        )

        st.divider()

        st.subheader("Быстрая статистика")
        if st.session_state.conversion_report:
            report = st.session_state.conversion_report
            stats = report.get('stats', {})
            st.metric("Узлов AST", stats.get('ast_nodes', 0))
            st.metric("Предупреждений", stats.get('warnings_count', 0))
            st.metric("Ошибок", stats.get('errors_count', 0))

    # Main tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "Ввод кода",
        "Примеры",
        "Вывод Java и компилятор",
        "Отчет о конвертации"
    ])

    with tab1:
        st.subheader("Ввод C++ кода")

        col1, col2 = st.columns([3, 1])

        with col1:
            uploaded_file = st.file_uploader(
                "Загрузить C++ файл",
                type=['cpp', 'cxx', 'cc', 'c', 'h', 'hpp'],
                key="file_uploader"
            )

        with col2:
            if uploaded_file is not None:
                content = uploaded_file.read().decode("utf-8")
                st.session_state.cpp_input = content
                st.success(f"✓ Загружен {uploaded_file.name}")

        cpp_input = st.text_area(
            "Исходный код C++",
            value=st.session_state.cpp_input,
            height=450,
            placeholder="// Вставьте ваш C++ код сюда...\n// Поддерживаются классы, шаблоны, пространства имен, операторы и многое другое",
            key="cpp_input_textarea"
        )

        if cpp_input != st.session_state.cpp_input:
            st.session_state.cpp_input = cpp_input

        col1, col2, col3 = st.columns([1, 1, 2])

        with col1:
            convert_clicked = st.button("Конвертировать в Java", type="primary", use_container_width=True)

        with col2:
            if st.button("Очистить", use_container_width=True):
                st.session_state.cpp_input = ""
                st.session_state.converted_code = ""
                st.session_state.conversion_report = {}
                st.session_state.compilation_result = None
                st.rerun()

    with tab2:
        st.subheader("Примеры кода")

        example_tabs = st.tabs(["Класс", "Шаблон", "Пространство имен", "Операторы", "RAII"])

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
            if st.button("Загрузить пример класса", key="load_class"):
                st.session_state.cpp_input = class_example
                st.rerun()

        with example_tabs[1]:
            template_example = """// Шаблонный класс
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
            if st.button("Загрузить пример шаблона", key="load_template"):
                st.session_state.cpp_input = template_example
                st.rerun()

        with example_tabs[2]:
            namespace_example = """// Использование пространств имен
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
            if st.button("Загрузить пример пространства имен", key="load_namespace"):
                st.session_state.cpp_input = namespace_example
                st.rerun()

        with example_tabs[3]:
            operator_example = """// Перегрузка операторов
class Complex {
private:
    double real, imag;

public:
    Complex(double r = 0, double i = 0) : real(r), imag(i) {}

    Complex operator+(const Complex& other) const {
        return Complex(real + other.real, imag + other.imag);
    }

    bool operator==(const Complex& other) const {
        return (real == other.real && imag == other.imag);
    }
};"""
            st.code(operator_example, language="cpp")
            if st.button("Загрузить пример операторов", key="load_operator"):
                st.session_state.cpp_input = operator_example
                st.rerun()

        with example_tabs[4]:
            raii_example = """// Паттерн RAII
class FileHandler {
private:
    FILE* file;

public:
    FileHandler(const char* filename) {
        file = fopen(filename, "r");
    }

    ~FileHandler() {
        if (file) {
            fclose(file);
        }
    }

    bool isOpen() const {
        return file != nullptr;
    }
};"""
            st.code(raii_example, language="cpp")
            if st.button("Загрузить пример RAII", key="load_raii"):
                st.session_state.cpp_input = raii_example
                st.rerun()

    # Perform conversion
    if convert_clicked and cpp_input.strip():
        try:
            with st.spinner("🔄 Конвертация C++ в Java..."):
                converter = CppToJavaConverter(
                    mode=conversion_mode,
                    verbose=verbose_output,
                    compile_output=compile_java
                )
                java_output = converter.convert(cpp_input)

                st.session_state.converted_code = java_output
                st.session_state.conversion_report = converter.generate_report()
                st.session_state.error_message = ""

                # Extract compilation result if available
                if compile_java and converter.last_conversion_stats.get('compilation_result'):
                    st.session_state.compilation_result = converter.last_conversion_stats['compilation_result']

                st.success("Конвертация завершена успешно!")

        except Exception as e:
            st.session_state.error_message = f"Ошибка конвертации: {str(e)}"
            st.session_state.converted_code = ""
            st.session_state.conversion_report = {}
            st.session_state.compilation_result = None
            st.error(st.session_state.error_message)

    with tab3:
        st.subheader("Сгенерированный Java код")

        if st.session_state.converted_code:
            st.code(st.session_state.converted_code, language="java", line_numbers=True)

            col1, col2 = st.columns([1, 3])
            with col1:
                st.download_button(
                    label="Скачать Java код",
                    data=st.session_state.converted_code,
                    file_name="ConvertedCode.java",
                    mime="text/x-java-source",
                    use_container_width=True
                )

            st.divider()

            # Java Compiler section in the same tab
            st.subheader("Вывод компилятора Java")

            if st.session_state.compilation_result:
                result = st.session_state.compilation_result

                if result['success']:
                    st.success("Компиляция Java успешна!")

                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Статус", "УСПЕХ", delta="Скомпилировано")
                    with col2:
                        st.metric("Файлов классов", len(result.get('class_files', [])))

                    if result.get('class_files'):
                        with st.expander("Сгенерированные файлы классов"):
                            for class_file in result['class_files']:
                                st.text(f"✓ {class_file}")
                else:
                    st.error("Компиляция Java не удалась")
                    st.metric("Статус", "ОШИБКА", delta="Найдены ошибки")

                if result.get('warnings'):
                    with st.expander(f"Предупреждения компилятора ({len(result['warnings'])})"):
                        for warning in result['warnings']:
                            st.warning(warning)

                if result.get('errors'):
                    with st.expander(f"Ошибки компилятора ({len(result['errors'])})"):
                        for error in result['errors']:
                            st.error(error)

                if result.get('output'):
                    with st.expander("Полный вывод компилятора"):
                        st.code(result['output'], language="text")
            else:
                st.info("Включите 'Компилировать Java код' в настройках и запустите конвертацию для просмотра вывода компилятора.")
        else:
            st.info("Java код еще не сгенерирован. Конвертируйте C++ код во вкладке 'Ввод кода'.")

    with tab4:
        st.subheader("Отчет о конвертации")

        if st.session_state.conversion_report:
            report = st.session_state.conversion_report

            # Metrics
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Узлов AST", report['stats'].get('ast_nodes', 0))
            with col2:
                st.metric("Предупреждений", len(report.get('warnings', [])))
            with col3:
                st.metric("Ошибок", len(report.get('errors', [])))
            with col4:
                st.metric("Режим", conversion_mode.upper())

            # Validation metrics
            if 'validation_metrics' in report['stats']:
                st.subheader("Метрики сложности кода")
                metrics = report['stats']['validation_metrics']

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Классов", metrics.get('class_count', 0))
                with col2:
                    st.metric("Шаблонов", metrics.get('template_count', 0))
                with col3:
                    st.metric("Операторов", metrics.get('operator_overload_count', 0))
                with col4:
                    st.metric("Указателей", metrics.get('pointer_usage_count', 0))

            # Warnings
            if report.get('warnings'):
                with st.expander(f"Предупреждения ({len(report['warnings'])})"):
                    for warning in report['warnings']:
                        st.warning(warning)

            # Errors
            if report.get('errors'):
                with st.expander(f"Ошибки ({len(report['errors'])})"):
                    for error in report['errors']:
                        st.error(error)

            # Technical details
            with st.expander("Технические детали"):
                st.json(report)
        else:
            st.info("Отчет о конвертации недоступен. Запустите конвертацию для просмотра отчета.")

    # Footer
    st.divider()
    with st.expander("О программе"):
        st.markdown("""
        ### Возможности
        - **Парсинг на основе AST** с использованием libclang для точного семантического анализа
        - **Поддержка шаблонов** - шаблоны C++ → дженерики Java
        - **Перегрузка операторов** - преобразование в именованные методы (operator+ → plus())
        - **Эмуляция RAII** - преобразование в AutoCloseable/try-with-resources
        - **Множественное наследование** - преобразование в интерфейсы + композицию
        - **Компиляция Java** - автоматическая проверка сгенерированного кода
        - **Предварительная валидация** - проверка C++ кода перед конвертацией

        ### Поддерживаемые преобразования
        - Классы и наследование → классы/интерфейсы Java
        - Шаблоны → Дженерики
        - Пространства имен → Пакеты
        - Операторы → Именованные методы
        - Макросы → static final константы
        - Паттерны RAII → AutoCloseable

        ### Режимы
        - **Строгий**: Останавливается на неподдерживаемых функциях
        - **Гибкий**: Генерирует TODO заглушки для неподдерживаемого кода

        ---
        **Версия 2.0** | Создано с помощью Streamlit и Material Design
        """)


if __name__ == "__main__":
    main()
