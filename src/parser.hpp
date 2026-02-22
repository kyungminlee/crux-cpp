#pragma once

#include "clang/AST/ASTConsumer.h"
#include "clang/AST/ASTContext.h"
#include "clang/AST/Decl.h"
#include "clang/AST/DeclCXX.h"
#include "clang/AST/DeclTemplate.h"
#include "clang/Basic/SourceManager.h"
#include "clang/Frontend/CompilerInstance.h"
#include "clang/Frontend/FrontendAction.h"
#include "clang/Index/USRGeneration.h"
#include "clang/Tooling/CompilationDatabase.h"
#include "clang/Tooling/JSONCompilationDatabase.h"
#include "clang/Tooling/Tooling.h"
#include "llvm/ADT/SmallString.h"
#include "llvm/Support/Casting.h"

#include <filesystem>
#include <functional>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;

// ── USR ───────────────────────────────────────────────────────────────────────

inline std::string get_usr(const clang::Decl *decl) {
    llvm::SmallString<128> buf;
    if (clang::index::generateUSRForDecl(decl, buf))
        return {};
    return std::string(buf);
}

// ── Source location ───────────────────────────────────────────────────────────

// Expansion location follows macros to their invocation site, per README.
inline std::string expansion_file(const clang::SourceManager &sm,
                                   clang::SourceLocation loc) {
    return sm.getFilename(sm.getExpansionLoc(loc)).str();
}

inline unsigned expansion_line(const clang::SourceManager &sm,
                                clang::SourceLocation loc) {
    return sm.getExpansionLineNumber(loc);
}

// ── Root filter ───────────────────────────────────────────────────────────────

inline bool under_root(const std::string &path, const fs::path &root) {
    std::error_code ec;
    auto rel = fs::relative(path, root, ec);
    return !ec && !rel.empty() && *rel.begin() != "..";
}

inline bool fd_in_root(const clang::FunctionDecl *fd,
                        const clang::SourceManager &sm,
                        const fs::path &root) {
    auto loc = sm.getExpansionLoc(fd->getBeginLoc());
    return loc.isValid() && under_root(sm.getFilename(loc).str(), root);
}

// ── Metadata helpers ──────────────────────────────────────────────────────────

inline std::string access_str(clang::AccessSpecifier as) {
    switch (as) {
    case clang::AS_public:    return "public";
    case clang::AS_protected: return "protected";
    case clang::AS_private:   return "private";
    default:                  return {};
    }
}

// Returns the name of the parent class/struct if fd is a method, else empty.
inline std::string parent_class(const clang::FunctionDecl *fd) {
    if (const auto *m = llvm::dyn_cast<clang::CXXMethodDecl>(fd))
        if (const auto *cls = m->getParent())
            return cls->getNameAsString();
    return {};
}

// ── Decl kind ────────────────────────────────────────────────────────────────

// Returns a string describing the concrete kind of a function-like decl.
// is_template is true when the decl is the templated function of a
// FunctionTemplateDecl (i.e. the primary template, not a specialization).
inline std::string decl_kind(const clang::FunctionDecl *fd, bool is_template) {
    if (llvm::isa<clang::CXXConstructorDecl>(fd))
        return is_template ? "ConstructorTemplate" : "Constructor";
    if (llvm::isa<clang::CXXDestructorDecl>(fd))
        return is_template ? "DestructorTemplate"  : "Destructor";
    if (llvm::isa<clang::CXXConversionDecl>(fd))
        return is_template ? "ConversionTemplate"  : "ConversionFunction";
    if (llvm::isa<clang::CXXMethodDecl>(fd))
        return is_template ? "CXXMethodTemplate"   : "CXXMethod";
    return     is_template ? "FunctionTemplate"    : "Function";
}

// ── Argument parsing ──────────────────────────────────────────────────────────

struct Args {
    std::vector<std::string> sources;
    fs::path build_dir;
    fs::path root_dir;
};

inline Args parse_args(int argc, char *argv[]) {
    Args a;
    for (int i = 1; i < argc; ++i) {
        std::string s = argv[i];
        if (s == "--build") {
            if (++i >= argc) throw std::runtime_error("--build requires a value");
            a.build_dir = argv[i];
        } else if (s == "--root") {
            if (++i >= argc) throw std::runtime_error("--root requires a value");
            a.root_dir = argv[i];
        } else {
            a.sources.push_back(s);
        }
    }
    if (a.build_dir.empty()) throw std::runtime_error("--build is required");
    if (a.root_dir.empty())  throw std::runtime_error("--root is required");
    if (a.sources.empty())   throw std::runtime_error("at least one source file is required");
    a.build_dir = fs::absolute(a.build_dir);
    a.root_dir  = fs::absolute(a.root_dir);
    return a;
}

// ── Tool runner ───────────────────────────────────────────────────────────────

// Parses CLI args, loads compile_commands.json, and runs a ClangTool.
// makeAction is called once per TU with the root_dir.
inline int run_tool(
    int argc, char *argv[],
    std::function<std::unique_ptr<clang::FrontendAction>(const fs::path &)> makeAction)
{
    struct Factory : clang::tooling::FrontendActionFactory {
        fs::path root;
        std::function<std::unique_ptr<clang::FrontendAction>(const fs::path &)> fn;
        Factory(fs::path r, decltype(fn) f) : root(std::move(r)), fn(std::move(f)) {}
        std::unique_ptr<clang::FrontendAction> create() override { return fn(root); }
    };

    const Args args = parse_args(argc, argv);

    std::string err;
    auto db = clang::tooling::JSONCompilationDatabase::loadFromDirectory(
        args.build_dir.string(), err);
    if (!db)
        throw std::runtime_error("Cannot load compile_commands.json from "
                                 + args.build_dir.string() + ": " + err);

    clang::tooling::ClangTool tool(*db, args.sources);
    Factory factory(args.root_dir, makeAction);
    return tool.run(&factory);
}
