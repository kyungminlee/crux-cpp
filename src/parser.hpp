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

std::string get_usr(const clang::Decl *decl);

// ── Source location ───────────────────────────────────────────────────────────

// Expansion location follows macros to their invocation site, per README.
std::string expansion_file(const clang::SourceManager &sm,
                                   clang::SourceLocation loc);

unsigned expansion_line(const clang::SourceManager &sm,
                                clang::SourceLocation loc);

// ── Root filter ───────────────────────────────────────────────────────────────

bool under_root(const std::string &path, const fs::path &root);

bool fd_in_root(const clang::FunctionDecl *fd,
                        const clang::SourceManager &sm,
                        const fs::path &root);

// ── Metadata helpers ──────────────────────────────────────────────────────────

std::string access_str(clang::AccessSpecifier as);

// Returns the name of the parent class/struct if fd is a method, else empty.
std::string parent_class(const clang::FunctionDecl *fd);

// ── Decl kind ────────────────────────────────────────────────────────────────

// Returns a string describing the concrete kind of a function-like decl.
// is_template is true when the decl is the templated function of a
// FunctionTemplateDecl (i.e. the primary template, not a specialization).
std::string decl_kind(const clang::FunctionDecl *fd, bool is_template);

// ── CSV output ────────────────────────────────────────────────────────────────

// Quotes a field if it contains a comma, double-quote, or newline.
// Embedded double-quotes are escaped by doubling them (RFC 4180).
inline std::string csv_field(const std::string &s) {
    if (s.find_first_of(",\"\n") == std::string::npos)
        return s;
    std::string out;
    out.reserve(s.size() + 2);
    out += '"';
    for (char c : s) {
        if (c == '"') out += '"';  // double the quote
        out += c;
    }
    out += '"';
    return out;
}

// ── Argument parsing ──────────────────────────────────────────────────────────

struct Args {
    std::vector<std::string> sources;
    fs::path build_dir;
    fs::path root_dir;
};

Args parse_args(int argc, char *argv[]);

// ── Tool runner ───────────────────────────────────────────────────────────────

// Parses CLI args, loads compile_commands.json, and runs a ClangTool.
// makeAction is called once per TU with the root_dir.
int run_tool(
    int argc, char *argv[],
    std::function<std::unique_ptr<clang::FrontendAction>(const fs::path &)> makeAction);