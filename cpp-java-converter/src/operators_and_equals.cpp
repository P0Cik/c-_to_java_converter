class Vector2D {
private:
    double x, y;

public:
    Vector2D(double x, double y) : x(x), y(y) {}

    bool operator==(const Vector2D& other) const {
        return x == other.x && y == other.y;
    }

    Vector2D operator+(const Vector2D& other) const {
        return Vector2D(x + other.x, y + other.y);
    }
};