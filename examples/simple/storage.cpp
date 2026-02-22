#include "storage.hpp"

// ── Pair<bool> — non-template members ────────────────────────────────────────

Pair<bool>::Pair(bool a, bool b) : first_(a), second_(b) {}

bool Pair<bool>::first()  const { return first_;  }
bool Pair<bool>::second() const { return second_; }

void Pair<bool>::flip_first()  { first_  = !first_;  }
void Pair<bool>::flip_second() { second_ = !second_; }
void Pair<bool>::flip_all()    { flip_first(); flip_second(); }

bool Pair<bool>::any() const { return first_ || second_; }
bool Pair<bool>::all() const { return first_ && second_; }

// ── Pair<bool> — method template specializations ──────────────────────────────
//
// Only one template<> needed: Pair<bool> is already a full class specialization.

template<>
int Pair<bool>::as<int>() const {
    return (first_ ? 2 : 0) + (second_ ? 1 : 0);
}

template<>
double Pair<bool>::as<double>() const {
    return (first_ ? 1.0 : 0.0) + (second_ ? 0.5 : 0.0);
}
