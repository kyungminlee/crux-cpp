#include "parser.hpp"

#include "clang/AST/Expr.h"
#include "clang/AST/ExprCXX.h"
#include "clang/AST/RecursiveASTVisitor.h"

#include <iostream>
#include <set>
#include <vector>

// Extracts caller-callee USR pairs for all call expressions inside function
// definitions whose source file is under root_dir.
//
// Caller tracking uses Traverse* overrides (rather than Visit*) so the caller
// context is pushed before descending into a function body and popped on exit.
// RecursiveASTVisitor dispatches on the concrete type, so each function-like
// subclass needs its own override.
class CallVisitor : public clang::RecursiveASTVisitor<CallVisitor> {
    using Base = clang::RecursiveASTVisitor<CallVisitor>;

    const clang::SourceManager &sm_;
    const fs::path &root_;
    std::vector<std::string> caller_stack_;
    std::set<std::string> &seen_;

    void emit(const clang::Decl *callee_decl) {
        if (caller_stack_.empty()) return;
        const std::string &caller = caller_stack_.back();
        if (caller.empty()) return;
        std::string callee = get_usr(callee_decl);
        if (callee.empty()) return;
        const std::string row = csv_field(caller) + ',' + csv_field(callee);
        if (seen_.insert(row).second)
            std::cout << row << '\n';
    }

    // Push usr, call traverse(decl), pop.
    template<typename D, typename TraverseFn>
    bool withCaller(D *decl, const std::string &usr, TraverseFn traverse) {
        caller_stack_.push_back(usr);
        const bool r = traverse(decl);
        caller_stack_.pop_back();
        return r;
    }

    // For FunctionDecl-derived nodes: push their USR if in-root with a body.
    // Skips the "templated decl" inside a FunctionTemplateDecl (handled
    // by TraverseFunctionTemplateDecl which uses the template's own USR).
    template<typename D, typename TraverseFn>
    bool traverseFunction(D *decl, const clang::FunctionDecl *fd,
                          TraverseFn traverse) {
        if (fd->doesThisDeclarationHaveABody() &&
            !fd->getDescribedFunctionTemplate() &&
            fd_in_root(fd, sm_, root_)) {
            return withCaller(decl, get_usr(fd), traverse);
        }
        return traverse(decl);
    }

public:
    CallVisitor(const clang::SourceManager &sm, const fs::path &root,
                std::set<std::string> &seen)
        : sm_(sm), root_(root), seen_(seen) {}

    bool shouldVisitTemplateInstantiations() const { return true; }

    // ── Traverse overrides (caller context) ──────────────────────────────────

    bool TraverseFunctionDecl(clang::FunctionDecl *D) {
        return traverseFunction(D, D, [this](clang::FunctionDecl *d) {
            return Base::TraverseFunctionDecl(d);
        });
    }
    bool TraverseCXXMethodDecl(clang::CXXMethodDecl *D) {
        return traverseFunction(D, D, [this](clang::CXXMethodDecl *d) {
            return Base::TraverseCXXMethodDecl(d);
        });
    }
    bool TraverseCXXConstructorDecl(clang::CXXConstructorDecl *D) {
        return traverseFunction(D, D, [this](clang::CXXConstructorDecl *d) {
            return Base::TraverseCXXConstructorDecl(d);
        });
    }
    bool TraverseCXXDestructorDecl(clang::CXXDestructorDecl *D) {
        return traverseFunction(D, D, [this](clang::CXXDestructorDecl *d) {
            return Base::TraverseCXXDestructorDecl(d);
        });
    }
    bool TraverseCXXConversionDecl(clang::CXXConversionDecl *D) {
        return traverseFunction(D, D, [this](clang::CXXConversionDecl *d) {
            return Base::TraverseCXXConversionDecl(d);
        });
    }
    // Function templates (free and member): use the template's own USR.
    bool TraverseFunctionTemplateDecl(clang::FunctionTemplateDecl *D) {
        const auto *fd = D->getTemplatedDecl();
        if (fd->doesThisDeclarationHaveABody() && fd_in_root(fd, sm_, root_)) {
            return withCaller(D, get_usr(D), [this](clang::FunctionTemplateDecl *d) {
                return Base::TraverseFunctionTemplateDecl(d);
            });
        }
        return Base::TraverseFunctionTemplateDecl(D);
    }

    // ── Visit call expressions ────────────────────────────────────────────────

    // Direct calls: f(), obj.method(), ptr->method(), ns::f(), etc.
    bool VisitCallExpr(clang::CallExpr *expr) {
        if (const auto *callee = expr->getDirectCallee())
            emit(callee);
        return true;
    }

    // Constructor calls do not go through CallExpr.
    bool VisitCXXConstructExpr(clang::CXXConstructExpr *expr) {
        if (const auto *ctor = expr->getConstructor())
            emit(ctor);
        return true;
    }
};

class CallConsumer : public clang::ASTConsumer {
    const fs::path &root_;
    std::set<std::string> &seen_;
public:
    CallConsumer(const fs::path &root, std::set<std::string> &seen)
        : root_(root), seen_(seen) {}

    void HandleTranslationUnit(clang::ASTContext &ctx) override {
        CallVisitor v(ctx.getSourceManager(), root_, seen_);
        v.TraverseDecl(ctx.getTranslationUnitDecl());
    }
};

class CallAction : public clang::ASTFrontendAction {
    fs::path root_;
    std::set<std::string> &seen_;
public:
    CallAction(fs::path root, std::set<std::string> &seen)
        : root_(std::move(root)), seen_(seen) {}

    std::unique_ptr<clang::ASTConsumer>
    CreateASTConsumer(clang::CompilerInstance &, llvm::StringRef) override {
        return std::make_unique<CallConsumer>(root_, seen_);
    }
};

int main(int argc, char *argv[]) {
    try {
        std::set<std::string> seen;
        std::cout << "caller_usr,callee_usr\n";
        return run_tool(argc, argv, [&seen](const fs::path &root) {
            return std::make_unique<CallAction>(root, seen);
        });
    } catch (const std::exception &e) {
        std::cerr << "error: " << e.what() << '\n';
        return 1;
    }
}
