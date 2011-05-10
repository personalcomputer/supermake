Supermake Readme
================

Supermake is a simple makefile generator for C and C++ that goes above and beyond to _streamline_ and _simplify_ the entire tedious build proccess.

Try it out with `supermake --print`, which will automatically generate a makefile for the sourcecode in your current directory and print out the generated makefile to the console, without overwriting anything.

**For full proper usage information, see `supermake --help`.**

### Features
* Start using it like you expect in an instant. Supermake just works, if you will.
* Generate unix makefiles from any sourcecode found in current directory.
* Automatically determine what libraries need to be linked.
* Easily specify custom gcc flags.
* Automatically compile your project.
* Automatically execute the resultant binary.
* Build static and dynamic libraries.

### Notes/Troubleshooting
Supermake is written for python 3, but should (and seems to, from tests) work in python 2 as well.

If Supermake fails to recognize some libraries you are using (there unfortunately won't be an error message on this until the compilation stage), you can manually add them to the 'libraries' datastructure (definition near top of supermake.py). Supermake can't support every single library out there, but I try to support the ones I use most myself, at least. Send me your github pull request with the additional library support and I'll gladly accept it.

A known bug with Supermake is that it cannot preproccess potentially disabled blocks of code from `#ifdefs` or `#ifs` and cannot understand c-style comments ('/\*' and '\*/'). This may lead to unwanted library inclusions if you use different libraries in your project depending upon preproccessor `#ifdefs` or `#ifs` or has such includes commented out with C-style comments.

Another known issue is that Supermake will not acknowledge source files (.cpp and .c) not in the current directory. Changing this would require an overhaul of the fundamental design (requiring manually specifying files, etc).

Lastly, it is worth noting that Supermake automatically includes librarys from /usr/local/lib, and then if `--run` is specified it sets LD_LIBRARY_PATH accordingly as well.

### Install
To use Supermake effectively, you will need to need to create a symbolic link somewhere in your $PATH that points to supermake.py. This allows you to execute the command 'supermake' from any working directory.

Ex (install to /usr/local/bin, using sudo): `sudo mkdir -p /usr/local/bin && sudo ln -s supermake.py /usr/local/bin/supermake`
Ex (install to ~/bin and add ~/bin to $PATH through .bashrc): `mkdir -p ~/bin && ln -s supermake.py ~/bin/supermake && echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc`

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
