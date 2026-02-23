#!/usr/bin/env python3
"""
Mock summarizer for testing summarize.py without a real LLM.

Usage:
    mock_summarize.py <database> [--force]

Produces summaries of the form:
    "{fully_qualified_name} is a great function and has size of {size}"
where size is the number of characters in the source text.
"""

import re
import sys
import summarize


def _mock(prompt: str) -> str:
    # First line: "Summarize the following C++ function or method `{fqn}`."
    first_line = prompt.split("\n")[0]
    m = re.search(r"`([^`]+)`", first_line)
    fqn = m.group(1) if m else "unknown"

    # Source text is between the ```cpp and ``` fences.
    m = re.search(r"```cpp\n(.*?)\n```", prompt, re.DOTALL)
    size = len(m.group(1)) if m else 0

    return f"{fqn} is a great function and has size of {size}"


summarize.summarize = _mock

if __name__ == "__main__":
    sys.exit(summarize.main())
