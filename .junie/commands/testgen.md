---
description: "Find untested code paths and automatically generate missing tests."
---


- find any parts of the code that are not fully tested and add tests for them as needed. 
- Use a class-based approach to test. 
- Ignore anything under if __name__ == "__main__".
- Try not to duplicate tests found in other files and append to existing test files where logical.
- Coverage greater than or equal to 95% is considered good enough.
- Remove any files created for testing like .coverage
