namespace Geometry {
    namespace Shapes {

        // Базовый класс
        class Shape {
        protected:
            string name;
        
        public:
            Shape(const string& n) : name(n) {}
            virtual ~Shape() = default;
            
            // Виртуальный метод
            virtual double getArea() const = 0;
            
            // Оператор сравнения
            bool operator==(const Shape& other) const {
                return this->name == other.name;
            }
        };
    }
}