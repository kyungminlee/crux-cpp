#pragma once

// ── Abstract base class with method overloads ─────────────────────────────────

class Shape {
public:
    Shape() = default;
    virtual ~Shape() = default;

    virtual double area()      const = 0;
    virtual double perimeter() const = 0;

    // Overloaded: uniform vs. axis-specific scale
    virtual void scale(double factor)       = 0;
    virtual void scale(double sx, double sy) = 0;

    double ratio_to(const Shape& other) const;  // area(this) / area(other)
};

// ── Concrete classes ──────────────────────────────────────────────────────────

class Circle : public Shape {
    double r_;
public:
    explicit Circle(double r);
    double area()      const override;
    double perimeter() const override;
    void   scale(double factor)        override;
    void   scale(double sx, double sy) override;
    double radius() const;
};

class Rectangle : public Shape {
    double w_, h_;
public:
    Rectangle(double w, double h);
    double area()      const override;
    double perimeter() const override;
    void   scale(double factor)        override;
    void   scale(double sx, double sy) override;
    double width()  const;
    double height() const;
};

// Triangle delegates its two-arg scale to single-arg scale.
class Triangle : public Shape {
    double a_, b_, c_;
public:
    Triangle(double a, double b, double c);
    double area()      const override;
    double perimeter() const override;
    void   scale(double factor)        override;
    void   scale(double sx, double sy) override;  // calls scale(double)
};
