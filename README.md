Supermake Readme
================

Supermake is a C and C++ 'build tool' focused on radical ease of use. You run a single command and get running software.

http://personalcomputer.github.com/supermake/

### Features
* Start using it like you expect in an instant. Supermake just works, if you will.
* Generate Unix makefiles from any sourcecode found in current directory.
* Automatically determine what libraries need to be linked.
* Easily specify custom gcc flags.
* Automatically compile your project.
* Automatically execute the resultant binary.
* Build static and dynamic libraries.

### Example Usage
* `supermake` (Really. Supermake is designed to do everything for you automatically with aggressive defaults. Run this and you'll go straight from all the sourcecode in your current directory to running software. As hard as running `python` or `ruby`, but C/C++)
* `supermake --binary=../bin/myprogram.run --debug --warn`
* `supermake --binary=myprogram.run -R --custom=-DTEST`

**For full proper usage information, see `supermake --help`.**

### Notes/Troubleshooting
Supermake is written for python 3, but should (and seems to, from tests) work in python 2 as well.

Supermake is written for linux, but should work acceptably within a windows/mingw32 environment as well. MacOSX is wholy untested.

If Supermake fails to recognize some libraries you are using (there unfortunately won't be an error message on this until the compilation stage), you can manually add them to the `libraries` datastructure (definition near top of supermake.py). Supermake can't support every single library out there, but I try to support the ones I use most myself, at least. Send me your Github pull request with the additional library support and I'll gladly accept it.

A known bug with Supermake is that it cannot preprocess code, so potentially disabled blocks of code from `#ifdefs` or `#ifs` and c-style comments (`/*` and `*/`) will still be read. This may lead to unwanted library inclusions if you use different libraries in your project depending upon preprocessor `#ifdefs` or `#ifs` or have such includes commented out with C-style comments. The undocumented `--override-depend` + `--custom=-llibrary -llibrary`(remember to escape the spaces for bash!) workaround is available though if this bug is causing problems.

Lastly, it is worth noting that Supermake automatically includes libraries from /usr/local/lib, and sets LD_LIBRARY_PATH to /usr/local/lib when running. I've yet to encounter a real situation on a beginner's system where this causes problems.

### Install
To use Supermake effectively, you will need to need to create a symbolic link somewhere in your $PATH that points to supermake.py. This allows you to execute the command `supermake` from any working directory.

Ex: (install to /usr/local/bin, using sudo) `sudo mkdir -p /usr/local/bin && sudo ln -s $PWD/supermake.py /usr/local/bin/supermake`

Ex: (install to ~/bin and add ~/bin to $PATH through .bashrc) `mkdir -p ~/bin && ln -s $PWD/supermake.py ~/bin/supermake && echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc`

### Legal
Supermake is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
