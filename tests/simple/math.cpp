#include "math.hpp"

// ── Free function overloads ───────────────────────────────────────────────────

int    add(int a, int b)        { return a + b; }
double add(double a, double b)  { return a + b; }
int    add(int a, int b, int c) { return add(a, b) + c; }  // calls 2-arg add

int    square(int x)    { return x * x; }
double square(double x) { return x * x; }
float  square(float x)  { return x * x; }

// ── Function template explicit specialization ─────────────────────────────────

// clamp<float>: NaN-safe, saturates at boundaries.
template<>
float clamp<float>(float val, float lo, float hi) {
    if (val != val) return lo;   // NaN → lo
    return val < lo ? lo : (val > hi ? hi : val);
}
