#include "parser.hpp"

#include "clang/AST/RecursiveASTVisitor.h"

#include <set>

// Extracts definitions of functions, methods, function templates, method
// templates, and their specializations, filtered to files under root_dir.
class DefVisitor : public clang::RecursiveASTVisitor<DefVisitor> {
    const clang::SourceManager &sm_;
    const fs::path &root_;
    std::set<std::string> &seen_;
    llvm::raw_ostream &out_;

    // Emit one CSV row.
    // decl_for_usr: FunctionTemplateDecl for primary templates, FunctionDecl otherwise.
    void emit(const clang::FunctionDecl *fd, const clang::Decl *decl_for_usr) {
        const std::string file = expansion_file(sm_, fd->getBeginLoc());
        if (!under_root(file, root_))
            return;
        const bool is_tmpl = llvm::isa<clang::FunctionTemplateDecl>(decl_for_usr);
        const std::string row =
            csv_field(get_usr(decl_for_usr))                             + ','
            + csv_field(fd->getQualifiedNameAsString())                  + ','
            + csv_field(decl_kind(fd, is_tmpl))                          + ','
            + csv_field(parent_class(fd))                                + ','
            + csv_field(access_str(fd->getAccess()))                     + ','
            + csv_field(fs::relative(file, root_).string())              + ','
            + std::to_string(expansion_line(sm_, fd->getBeginLoc()))     + ','
            + std::to_string(expansion_line(sm_, fd->getEndLoc()));
        if (seen_.insert(row).second)
            out_ << row << '\n';
    }

public:
    DefVisitor(const clang::SourceManager &sm, const fs::path &root,
               std::set<std::string> &seen, llvm::raw_ostream &out)
        : sm_(sm), root_(root), seen_(seen), out_(out) {}

    // Include implicit template instantiations.
    bool shouldVisitTemplateInstantiations() const { return true; }

    // Handles free functions, CXX methods, constructors, destructors,
    // conversion functions, and explicit/implicit template specializations.
    // The "templated decl" inside a FunctionTemplateDecl is skipped here and
    // handled by VisitFunctionTemplateDecl instead to use the template's USR.
    bool VisitFunctionDecl(clang::FunctionDecl *fd) {
        if (fd->getDescribedFunctionTemplate()) return true;
        if (!fd->doesThisDeclarationHaveABody()) return true;
        emit(fd, fd);
        return true;
    }

    // Handles primary function templates (both free and member).
    bool VisitFunctionTemplateDecl(clang::FunctionTemplateDecl *ftd) {
        const auto *fd = ftd->getTemplatedDecl();
        if (!fd->doesThisDeclarationHaveABody()) return true;
        emit(fd, ftd);
        return true;
    }
};

class DefConsumer : public clang::ASTConsumer {
    const fs::path &root_;
    std::set<std::string> &seen_;
    llvm::raw_ostream &out_;
public:
    DefConsumer(const fs::path &root, std::set<std::string> &seen,
                llvm::raw_ostream &out)
        : root_(root), seen_(seen), out_(out) {}

    void HandleTranslationUnit(clang::ASTContext &ctx) override {
        DefVisitor v(ctx.getSourceManager(), root_, seen_, out_);
        v.TraverseDecl(ctx.getTranslationUnitDecl());
    }
};

class DefAction : public clang::ASTFrontendAction {
    fs::path root_;
    std::set<std::string> &seen_;
    llvm::raw_ostream &out_;
public:
    DefAction(fs::path root, std::set<std::string> &seen, llvm::raw_ostream &out)
        : root_(std::move(root)), seen_(seen), out_(out) {}

    std::unique_ptr<clang::ASTConsumer>
    CreateASTConsumer(clang::CompilerInstance &, llvm::StringRef) override {
        return std::make_unique<DefConsumer>(root_, seen_, out_);
    }
};

int main(int argc, char *argv[]) {
    try {
        std::set<std::string> seen;
        return run_tool(argc, argv,
            "usr,fully_qualified_name,kind,class,visibility,filename,start_line,end_line",
            [&seen](const fs::path &root, llvm::raw_ostream &out) {
                return std::make_unique<DefAction>(root, seen, out);
            });
    } catch (const std::exception &e) {
        llvm::errs() << "error: " << e.what() << '\n';
        return 1;
    }
}
