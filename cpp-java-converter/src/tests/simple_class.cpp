class Point {
private:
    double x = 5.0; 
    double y = 6.1;

public:
    double getX() const { return x; }
    double getY() const { return y; }
    void setX(double val) { x = val; }
    void setY(double val) { y = val; }
};