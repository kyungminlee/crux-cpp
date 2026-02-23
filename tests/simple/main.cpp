#include "shapes.hpp"
#include "math.hpp"
#include "storage.hpp"

// ── Helpers used by demo_storage (function pointers for method templates) ─────

static double int_to_double(const int& x)                    { return static_cast<double>(x); }
static int    sum_ints(const int& a, const int& b)           { return a + b; }
static double double_to_double(const double& x)              { return x * 2.0; }
static double sum_doubles(const double& a, const double& b)  { return a + b; }

// ── Demos ─────────────────────────────────────────────────────────────────────

static void demo_shapes() {
    Circle    c(5.0);
    Rectangle r(3.0, 4.0);
    Triangle  t(3.0, 4.0, 5.0);

    c.area();
    c.perimeter();
    c.scale(2.0);           // single-arg overload
    c.scale(1.0, 1.5);      // two-arg overload

    r.area();
    r.perimeter();
    r.scale(2.0);
    r.scale(1.5, 0.5);

    t.area();
    t.perimeter();
    t.scale(3.0);
    t.scale(1.0, 1.0);      // two-arg overload → calls single-arg internally

    c.ratio_to(r);          // calls area() on both
}

static void demo_math() {
    add(1, 2);              // int overload
    add(1.5, 2.5);          // double overload
    add(1, 2, 3);           // 3-arg overload → calls 2-arg add internally

    square(3);
    square(3.0);
    square(3.0f);

    clamp(5,    0,    10);      // clamp<int>   — primary template
    clamp(5.0f, 0.0f, 10.0f);  // clamp<float> — explicit specialization

    lerp(0, 100, 0.25);         // lerp<int>
    lerp(0.0, 1.0, 0.5);        // lerp<double>

    min_of(3, 5);
    min_of(3.0, 5.0);
    max_of(3, 5);
    max_of(3.0f, 5.0f);

    weighted_sum(1, 2, 0.3, 0.7);   // weighted_sum<int, double>
    weighted_sum(1.0f, 2.0f, 2, 3); // weighted_sum<float, int>
}

static void demo_storage() {
    // ── Primary template ──────────────────────────────────────────────────────
    Pair<int> pi(1, 2);
    pi.first();
    pi.second();
    pi.equal();
    pi.equal(1);
    pi.swap();

    // Const overloads.
    const Pair<int>& cpi = pi;
    cpi.first();
    cpi.second();

    // Method templates on primary template.
    pi.map<double>(int_to_double);
    pi.reduce<int>(sum_ints);

    Pair<double> pd(1.0, 2.0);
    pd.map<double>(double_to_double);
    pd.reduce<double>(sum_doubles);

    // ── Full specialization ───────────────────────────────────────────────────
    Pair<bool> pb(true, false);
    pb.first();
    pb.second();
    pb.flip_first();
    pb.flip_all();          // calls flip_first + flip_second
    pb.any();
    pb.all();
    pb.as<int>();           // method template specialization
    pb.as<double>();        // method template specialization

    // ── Partial specialization (pointer) ──────────────────────────────────────
    int x = 10, y = 20;
    Pair<int*> pp(&x, &y);
    pp.first();
    pp.second();
    pp.either_null();
    pp.both_null();
    pp.swap();
}

// ── Entry point ───────────────────────────────────────────────────────────────

int main() {
    demo_shapes();
    demo_math();
    demo_storage();
    return 0;
}
