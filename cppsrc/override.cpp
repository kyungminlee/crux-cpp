#include "parser.hpp"

#include "clang/AST/RecursiveASTVisitor.h"

#include <set>

// Extracts virtual method override relationships: for each CXXMethodDecl that
// overrides one or more base-class methods, emit (usr, parent_usr) for each
// directly overridden method.  Filtered to methods whose parent class is
// defined under root_dir.
//
// No canonicalization is applied — raw USRs are emitted so that rows join
// directly with def.csv's usr column.  Downstream users can join through
// def.canonical_usr to canonicalize if needed.
class OverrideVisitor : public clang::RecursiveASTVisitor<OverrideVisitor> {
    const clang::SourceManager &sm_;
    const fs::path &root_;
    std::set<std::string> &seen_;
    llvm::raw_ostream &out_;

public:
    OverrideVisitor(const clang::SourceManager &sm, const fs::path &root,
                    std::set<std::string> &seen, llvm::raw_ostream &out)
        : sm_(sm), root_(root), seen_(seen), out_(out) {}

    // Include implicit template instantiations so that e.g. overrides inside
    // Derived<int> are emitted alongside any primary-template overrides.
    bool shouldVisitTemplateInstantiations() const { return true; }

    bool VisitCXXRecordDecl(clang::CXXRecordDecl *cls) {
        // Only process the canonical definition.
        if (!cls->isThisDeclarationADefinition()) return true;

        // Filter to classes defined under --root.
        const auto loc = sm_.getExpansionLoc(cls->getBeginLoc());
        if (!loc.isValid()) return true;
        if (!under_root(sm_.getFilename(loc).str(), root_)) return true;

        for (auto *member : cls->methods()) {
            // Skip compiler-generated implicit methods (e.g. implicit destructors).
            // def.cpp doesn't emit implicit methods, so their USRs have no match there.
            if (member->isImplicit()) continue;
            if (member->size_overridden_methods() == 0) continue;
            const std::string usr = get_usr(member);
            if (usr.empty()) continue;
            for (const auto *overridden : member->overridden_methods()) {
                const std::string parent_usr = get_usr(overridden);
                if (parent_usr.empty()) continue;
                const std::string row = csv_field(usr) + ',' + csv_field(parent_usr);
                if (seen_.insert(row).second)
                    out_ << row << '\n';
            }
        }
        return true;
    }
};

class OverrideConsumer : public clang::ASTConsumer {
    const fs::path &root_;
    std::set<std::string> &seen_;
    llvm::raw_ostream &out_;
public:
    OverrideConsumer(const fs::path &root, std::set<std::string> &seen,
                     llvm::raw_ostream &out)
        : root_(root), seen_(seen), out_(out) {}

    void HandleTranslationUnit(clang::ASTContext &ctx) override {
        OverrideVisitor v(ctx.getSourceManager(), root_, seen_, out_);
        v.TraverseDecl(ctx.getTranslationUnitDecl());
    }
};

class OverrideAction : public clang::ASTFrontendAction {
    fs::path root_;
    std::set<std::string> &seen_;
    llvm::raw_ostream &out_;
public:
    OverrideAction(fs::path root, std::set<std::string> &seen, llvm::raw_ostream &out)
        : root_(std::move(root)), seen_(seen), out_(out) {}

    std::unique_ptr<clang::ASTConsumer>
    CreateASTConsumer(clang::CompilerInstance &, llvm::StringRef) override {
        return std::make_unique<OverrideConsumer>(root_, seen_, out_);
    }
};

int main(int argc, char *argv[]) {
    try {
        std::set<std::string> seen;
        return run_tool(argc, argv, "usr,parent_usr",
            [&seen](const fs::path &root, llvm::raw_ostream &out) {
                return std::make_unique<OverrideAction>(root, seen, out);
            });
    } catch (const std::exception &e) {
        llvm::errs() << "error: " << e.what() << '\n';
        return 1;
    }
}
