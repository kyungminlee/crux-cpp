#include "parser.hpp"

#include "clang/AST/RecursiveASTVisitor.h"
#include "llvm/Support/ManagedStatic.h"

#include <set>

// Extracts class information for CXX record declarations whose source file is
// under root_dir.
class ClassVisitor : public clang::RecursiveASTVisitor<ClassVisitor> {
    const clang::SourceManager &sm_;
    const fs::path &root_;
    std::set<std::string> &seen_;
    llvm::raw_ostream &out_;

public:
    ClassVisitor(const clang::SourceManager &sm, const fs::path &root,
                 std::set<std::string> &seen, llvm::raw_ostream &out)
        : sm_(sm), root_(root), seen_(seen), out_(out) {}

    // Include implicit template instantiations so that e.g. Derived<int> rows
    // are emitted alongside the primary template row.
    bool shouldVisitTemplateInstantiations() const { return true; }

    bool VisitCXXRecordDecl(clang::CXXRecordDecl *decl) {
        // Only process the canonical definition.
        if (!decl->isThisDeclarationADefinition()) return true;

        // Filter to declarations whose definition lives under root.
        const auto loc = sm_.getExpansionLoc(decl->getBeginLoc());
        if (!loc.isValid()) return true;

        const auto filename = sm_.getFilename(loc).str();
        if (!under_root(filename, root_)) return true;

        const std::string usr = get_usr(decl);
        if (usr.empty()) return true;
        const std::string canonical_usr = get_usr(get_canonical(decl));

        const std::string name = decl->getQualifiedNameAsString();
        const auto start_line = sm_.getExpansionLineNumber(decl->getBeginLoc());
        const auto end_line = sm_.getExpansionLineNumber(decl->getEndLoc());

        const std::string row = csv_field(usr) + ','
                              + csv_field(canonical_usr) + ','
                              + csv_field(name) + ','
                              + csv_field(filename) + ','
                              + std::to_string(start_line) + ','
                              + std::to_string(end_line);

        if (seen_.insert(row).second)
            out_ << row << '\n';

        return true;
    }
};

class ClassConsumer : public clang::ASTConsumer {
    const fs::path &root_;
    std::set<std::string> &seen_;
    llvm::raw_ostream &out_;
public:
    ClassConsumer(const fs::path &root, std::set<std::string> &seen,
                  llvm::raw_ostream &out)
        : root_(root), seen_(seen), out_(out) {}

    void HandleTranslationUnit(clang::ASTContext &ctx) override {
        ClassVisitor v(ctx.getSourceManager(), root_, seen_, out_);
        v.TraverseDecl(ctx.getTranslationUnitDecl());
    }
};

class ClassAction : public clang::ASTFrontendAction {
    fs::path root_;
    std::set<std::string> &seen_;
    llvm::raw_ostream &out_;
public:
    ClassAction(fs::path root, std::set<std::string> &seen, llvm::raw_ostream &out)
        : root_(std::move(root)), seen_(seen), out_(out) {}

    std::unique_ptr<clang::ASTConsumer>
    CreateASTConsumer(clang::CompilerInstance &, llvm::StringRef) override {
        return std::make_unique<ClassConsumer>(root_, seen_, out_);
    }
};

int main(int argc, char *argv[]) {
    llvm::llvm_shutdown_obj shutdown_guard;
    try {
        std::set<std::string> seen;
        return run_tool(argc, argv, "usr,canonical_usr,fully_qualified_name,filename,start,end",
            [&seen](const fs::path &root, llvm::raw_ostream &out) {
                return std::make_unique<ClassAction>(root, seen, out);
            });
    } catch (const std::exception &e) {
        llvm::errs() << "error: " << e.what() << '\n';
        return 1;
    }
}
