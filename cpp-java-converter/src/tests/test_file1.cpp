#include <string>  // ← добавь это

namespace Geometry {
    namespace Shapes {

        class Shape {
        protected:
            std::string name;  // ← std::

        public:
            Shape(const std::string& n) : name(n) {}
            virtual ~Shape() = default;
            
            virtual double getArea() const = 0;
            
            bool operator==(const Shape& other) const {
                return this->name == other.name;
            }
        };
    }
}