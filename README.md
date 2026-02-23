# crux-cpp

* crux-cpp is a set of CLI tools which extracts relevant information from a C++ code base and constructs a graph.

## def
`def` is a CLI program which extracts the definitions of all functions, methods, function templates, method templates, and their specializations.
Its options are:
```
$ def SOURCE1.cpp [SOURCE2.cpp]... --build BUILD_DIR --root ROOT_DIR
```
Both `--build` and `--root` options are required.
It will fetch compile_commands.json from the BUILD_DIR, and then extract all the function/method definitions.
It will only output the definition from a file within the `ROOT_DIR` and its descendents, to avoid large amount of data from the system headers.

It will produce a table with seven columns:
- usr: USR of the object
- fully_qualified_name: fully qualified name
- class: parent class if it is a method
- visibility: visibility of the method
- filename: filename of the physical location of the definition. If defined using macro, mark location of where the macro was used.
- start_line: starting line
- end_line: end line

## call

`call` is a CLI program which extracts the caller-callee relationship of all the functions.
It takes the same CLI arguments as `def`
It will produce a table with two columns
- caller_usr: USR of the caller function/method
- callee_usr: USR of the callee function/method

