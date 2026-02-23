#pragma once

// ── Free function overloads ───────────────────────────────────────────────────

int    add(int a, int b);
double add(double a, double b);
int    add(int a, int b, int c);      // 3-arg overload: delegates to 2-arg

int    square(int x);
double square(double x);
float  square(float x);

// ── Function templates ────────────────────────────────────────────────────────

// Primary template.
template<typename T>
T clamp(T val, T lo, T hi) {
    return val < lo ? lo : (val > hi ? hi : val);
}

// Explicit full specialization for float (NaN-safe); defined in math.cpp.
template<>
float clamp<float>(float val, float lo, float hi);

// Linear interpolation.
template<typename T>
T lerp(T a, T b, double t) {
    return static_cast<T>(a * (1.0 - t) + b * t);
}

template<typename T>
T min_of(T a, T b) { return a < b ? a : b; }

template<typename T>
T max_of(T a, T b) { return a > b ? a : b; }

// Two-type-parameter template.
template<typename T, typename U>
double weighted_sum(T a, T b, U wa, U wb) {
    return static_cast<double>(a) * static_cast<double>(wa)
         + static_cast<double>(b) * static_cast<double>(wb);
}
