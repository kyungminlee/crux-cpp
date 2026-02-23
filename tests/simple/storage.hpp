#pragma once

// ── Primary class template ────────────────────────────────────────────────────

template<typename T>
class Pair {
    T first_;
    T second_;
public:
    Pair(T a, T b) : first_(a), second_(b) {}

    // Const/non-const accessor overloads.
    T&       first()        { return first_; }
    const T& first()  const { return first_; }
    T&       second()       { return second_; }
    const T& second() const { return second_; }

    void swap() { T tmp = first_; first_ = second_; second_ = tmp; }

    // Equality overloads.
    bool equal() const             { return first_ == second_; }
    bool equal(const T& val) const { return first_ == val && second_ == val; }

    // Method template: transform both elements via a function pointer.
    template<typename U>
    Pair<U> map(U (*fn)(const T&)) const {
        return Pair<U>(fn(first_), fn(second_));
    }

    // Method template: reduce both elements to a single value.
    template<typename U>
    U reduce(U (*fn)(const T&, const T&)) const {
        return fn(first_, second_);
    }
};

// ── Full class template specialization: Pair<bool> ───────────────────────────

template<>
class Pair<bool> {
    bool first_;
    bool second_;
public:
    Pair(bool a, bool b);

    bool first()  const;
    bool second() const;

    void flip_first();
    void flip_second();
    void flip_all();     // calls flip_first + flip_second

    bool any() const;
    bool all() const;

    // Method template inside the class specialization.
    template<typename U>
    U as() const;
};

// Method template specializations for Pair<bool> (defined in storage.cpp).
// Only one template<> needed: the class is already fully specialized.
template<>
int Pair<bool>::as<int>() const;

template<>
double Pair<bool>::as<double>() const;

// ── Partial class template specialization: Pair<T*> ──────────────────────────

template<typename T>
class Pair<T*> {
    T* first_;
    T* second_;
public:
    Pair(T* a, T* b) : first_(a), second_(b) {}

    T* first()  const { return first_; }
    T* second() const { return second_; }

    bool either_null() const { return !first_ || !second_; }
    bool both_null()   const { return !first_ && !second_; }

    void swap() { T* tmp = first_; first_ = second_; second_ = tmp; }
};
