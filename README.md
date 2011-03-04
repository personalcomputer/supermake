Supermake
=========

Supermake is a simple makefile generator for C or C++ that goes above and beyond to _streamline_ and _simplify_ the entire tedious build proccess.

Give it a try, and run `supermake --make --run --autoclean` (alternatively just do `supermake --print` to see what it would of generated, without overwriting anything)) in your project's directory to observe its power, automatically generating a makefile, compiling it, and then running the resultant binary. You may wish to first backup your pre-existing makefile, although Supermake will do this automatically.

**See `supermake --help` for further information and usage.**

### Features
* Start using it like you expect in an instant. Supermake just works, if you will.
* Generate unix makefiles from any sourcecode found in current directory.
* Automatically determine what librarys need to be linked.
* Easily specify custom gcc flags.
* Automatically compile your project.
* Automatically execute the resultant binary.
* Build static and dynamic librarys, too.

### Notes/Troubleshooting
If Supermake fails to recognize some librarys you are using (there unfortunately is no error message on this until the compilation stage), you can manually add them to the 'librarys' datastructure as defined on lines 73-101 of supermake.py. Supermake can't support every single lbirary out there, but I try to support the ones I use most myself, at least. Send me a message with the additional library support added and I'll commit it to master.

Supermake is written for python version 3.x, allthough it it spits out a warning it should be able to work with python 2 as well.

A known bug with supermake is that it cannot preproccess potentially disabledblocks of code from `#ifdefs` or `#ifs`. This may lead to unwanted library inclusions if you use different librarys in your project depending uponpreproccessor `#ifdefs` or `#ifs`.

Another known issue is that supermake will not ackowledge source files (.cpp and .c) not in the current directory. Changing this would require an overhaul of the fundamental design (requiring manually specifying files, etc).

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

_See LEGAL for full license information._
