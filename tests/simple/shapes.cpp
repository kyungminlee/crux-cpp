#include "shapes.hpp"
#include <cmath>
#include <stdexcept>

static constexpr double PI = 3.14159265358979323846;

// ── Shape ─────────────────────────────────────────────────────────────────────

double Shape::ratio_to(const Shape& other) const {
    return area() / other.area();
}

// ── Circle ────────────────────────────────────────────────────────────────────

Circle::Circle(double r) : r_(r) {
    if (r <= 0) throw std::invalid_argument("radius must be positive");
}
double Circle::area()      const { return PI * r_ * r_; }
double Circle::perimeter() const { return 2.0 * PI * r_; }
void   Circle::scale(double f)          { r_ *= f; }
void   Circle::scale(double sx, double) { r_ *= sx; }   // uniform: ignore sy
double Circle::radius() const { return r_; }

// ── Rectangle ─────────────────────────────────────────────────────────────────

Rectangle::Rectangle(double w, double h) : w_(w), h_(h) {}
double Rectangle::area()      const { return w_ * h_; }
double Rectangle::perimeter() const { return 2.0 * (w_ + h_); }
void   Rectangle::scale(double f)            { w_ *= f;  h_ *= f;  }
void   Rectangle::scale(double sx, double sy) { w_ *= sx; h_ *= sy; }
double Rectangle::width()  const { return w_; }
double Rectangle::height() const { return h_; }

// ── Triangle ──────────────────────────────────────────────────────────────────

Triangle::Triangle(double a, double b, double c) : a_(a), b_(b), c_(c) {
    if (a + b <= c || b + c <= a || a + c <= b)
        throw std::invalid_argument("invalid triangle sides");
}
double Triangle::area() const {
    double s = (a_ + b_ + c_) / 2.0;
    return std::sqrt(s * (s - a_) * (s - b_) * (s - c_));
}
double Triangle::perimeter() const { return a_ + b_ + c_; }
void   Triangle::scale(double f)            { a_ *= f; b_ *= f; c_ *= f; }
void   Triangle::scale(double sx, double)   { scale(sx); }   // delegates
