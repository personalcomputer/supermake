Supermake
=========

> [!CAUTION]
> I wrote this code in **2011** while learning Python as a teenager. I still use it for personal use, but it is otherwise abandoned, is not available in PyPI, and I have archived the repository. Proceed at your own risk.

----

Supermake is a C and C++ 'build tool' focused on ease of use for simple projects. You run a single command and get running software.

http://personalcomputer.github.io/supermake/

### Features
* Generate Unix makefiles from any sourcecode found in current directory.
* Automatically determine what libraries need to be linked.
* Easily specify custom gcc flags.
* Automatically compile your project.
* Automatically execute the resultant binary.
* Build static and dynamic libraries.

### Example Usage
* `supermake` (By itself. Supermake is designed to do everything for you automatically with aggressive defaults. Run this from a C/C++ repository and you'll go straight from having sourcecode to having running software. As hard as running `python` or `ruby`, but for C/C++)
* `supermake --binary=../bin/myprogram.run --debug --warn`
* `supermake --binary=myprogram.run -R --custom=-DTEST`

**For full proper usage information, see `supermake --help`.**

### Install

Supermake is a Python package, available for install via uv:

```
git clone git@github.com:personalcomputer/supermake.git
uv tool install ./supermake
```

### Notes/Troubleshooting

- Supermake is written for Linux, but should work acceptably within a Windows+cgywin/mingw32 environment as well. MacOSX is untested.
- If Supermake fails to recognize some libraries you are using (there unfortunately won't be an error message on this until the compilation stage), you can manually add them to the `libraries` datastructure (definition near top of supermake.py). Supermake can't support every single library out there, but I try to support the ones I use most myself, at least. Send me your Github pull request with the additional library support and I'll gladly accept it.
- A known bug with Supermake is that it cannot preprocess code, so potentially disabled blocks of code from `#ifdefs` or `#ifs` and c-style comments (`/*` and `*/`) will still be read. This may lead to unwanted library inclusions if you use different libraries in your project depending upon preprocessor `#ifdefs` or `#ifs` or have such includes commented out with C-style comments. The undocumented `--override-depend` + `--custom=-llibrary -llibrary`(remember to escape the spaces for bash!) workaround is available though if this bug is causing problems.
- Lastly, it is worth noting that Supermake automatically includes libraries from /usr/local/lib, and sets LD_LIBRARY_PATH to /usr/local/lib when running. I've yet to encounter a real situation on a beginner's system where this causes problems.
