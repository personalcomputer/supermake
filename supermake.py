#!/usr/bin/env python
#
#   Supermake is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#
#
#
# The objective of Supermake is to be a simple user-friendly makefile generator that attempts its best to figure out what the user wants with well thought out defaults that work for most basic compilation needs. Additionally supermake provides the option to automatically perform the rest of the build proccess, even launching the resultant binary for you! I currently(11/2011) feel that supermake is fairly mature and accomplishes its objective.
#
# Supermake is created by John M
#
# This is python 3 code, but it should also be mostly back-compatible with python 2.
# TESTED ON LINUX ONLY

import re
import os
import sys

cliName = os.path.basename(sys.argv[0])

####### Constants
usage = '''Usage: '''+cliName+''' [OPTION]...
Automatically generate a basic makefile for C or C++ source files in the current
directory and optionally compile and execute it, streamlining and simplifying
the build proccess.

  --print           Print to the console instead of writing to a makefile.
  --make            'make' the generated makefile. ie: compile the project.
  --run             Execute the compiled binary. Only to be used in combination
                    with --make.
  --debug           Add the -g and -DDEBUG debug flags to the gcc compilation
                    flags.
  --warn            Add the -Wall warning flag to the gcc compilation flags.
  --binary=NAME     Name the binary that the makefile generates. Supermake
                    defaultly just takes a guess.
  --autoclean       Automatically run 'make clean' if the generated makefile
                    differs from the previous one.
  --usrlocal        Enable the use of librarys in /usr/local/lib.
  --deplevel=LEVEL  Limit how many LEVELs deep to add file dependencies. 0 means
                    no dependencies, 1 includes only direct dependencies, 2
                    includes dependencies from direct dependencies etc. The
                    default is a virtually infinite max deplevel.
  --custom=FLAGS    Compiles everything with additional custom gcc FLAGS. This
                    can be used, for example, for specifying extra -D defines.
  --lib=NAME        Build the project as a library instead. NAME specifys the
                    name (ex: ../lib/mylibrary). This automatically adds both
                    shared(.so) and static(.a) library types, so do not specify
                    an extension in NAME.
  --quiet           Supress all general messages and warnings that origin from
                    Supermake.
  --descrete        Do not add the "this makefile generated by Supermake..."
                    message at the top of the makefile.

Ex: '''+cliName+'''
Ex: '''+cliName+''' --binary=../bin/myprogram.run --debug --warn --make
Ex: '''+cliName+''' --binary=myprogram.run --make --run.'''

makefileMessage = '#This makefile was generated by Supermake. Modify as you wish, but remember that your changes will not be preserved when you run Supermake again. Try to use the available basic options(see --help) to tune it how you desire, if possible. Lastly, remember that Supermake is not suitable for most involved projects\' build requirements.\n\n'

###All of the currently supported librarys. Expanding this list is encouraged!
librarys = {}
librarys['SDL/SDL.h'] = ['-lSDL']
librarys['SDL/SDL_image.h'] = ['-lSDL_image', '-lSDL']
librarys['SDL/SDL_mixer.h'] = ['-lSDL_mixer', '-lSDL']
librarys['SDL/SDL_opengl.h'] = ['-lGL', '-lSDL']
librarys['SDL/SDL_ttf.h'] = ['-lSDL_ttf', '-lSDL']
librarys['SDL/SDL_net.h'] = ['-lSDL_net', '-lSDL']
librarys['SDL/SDL_thread.h'] = ['-lSDL'] #`sdl-config --libs` says I need -lpthread, but this is not crossplatform and there doesnt seem to be any issues from leaving it out (can sdl auto add it through _Pragmas or something?).  
librarys['GL/glfw.h'] = ['-lglfw', '-lGL']
librarys['Box2D/Box2D.h'] = ['-lBox2D']
librarys['openssl/sha.h'] = ['-lcrypto']
librarys['gcrypt.h'] = ['-lgcrypt', '-lgpg-error']
librarys['zmq.hpp'] = ['-lzmq']
librarys['zmq.h'] = ['-lzmq']
librarys['OIS/OISInputManager.h'] = ['-lOIS']
librarys['OIS/OISEvents.h'] = ['-lOIS']
librarys['OIS/OISInputManager.h'] = ['-lOIS']
librarys['ncurses.h'] = ['-lncurses']
librarys['GL/gl.h'] = ['-lGL']
librarys['GL/glu.h'] = ['-lGLU', '-lGL']
librarys['GL/glew.h'] = ['-lGLEW', '-lGLU', '-lGL']
librarys['GL/glut.h'] = ['-lGLUT', '-lGLU', '-lGL']
librarys['Horde3D/Horde3D.h'] = ['-lHorde3D']
librarys['Horde3D/Horde3DUtils.h'] = ['-lHorde3D', '-lHorde3DUtils']
librarys['OGRE/OgreCamera.h'] = ['-lOgreMain'] #There are more base ogre includes than the ones defined here. The thing is though, if it includes any of these(and it will if it uses ogre, for these are required for most uses) then it is already taken care of.
librarys['OGRE/OgreEntity.h'] = ['-lOgreMain']
librarys['OGRE/OgrePrerequisites.h'] = ['-lOgreMain']
librarys['OGRE/OgreRoot.h'] = ['-lOgreMain']
librarys['OGRE/OgreViewport.h'] = ['-lOgreMain']
librarys['OGRE/OgreSceneManager.h'] = ['-lOgreMain']
###

####### Globals
depend = [] #Library dependencies (Such as -lSDL)
fileDeps = [] #All found source files and the files that they individualy have been determined to depend upon

quiet = False

isCCode = True #until proven otherwise.

####### Util Functions
def message(text):
  if not quiet or text[:6] == 'Error:':
    print('Supermake: ' + text)
    
fileCache = {}

def GetFileFromCache(filename): #This loads and caches all files for speed. (supermake requests the same sorucecode files multiple times each run). This uses the lazy-load idiom.
  if filename not in fileCache:
    f = open(filename, 'r')
    fileCache[filename] = f.read()
    f.close()
  return fileCache[filename]
  
####### Helper Functions
def filterCommandlineOptionDescrepency(argv):
  libSpecified = False
  for argument in argv:
    m = re.search('--lib=.+', argument)
    if m:
      libSpecified = True
  binarySpecified = False
  binary = ''
  for argument in argv:
    m = re.search('--binary=.+', argument)
    if m:
      binarySpecified = True
      binary = m

  validArgumentRegexPatterns = ['--binary=.+', '--lib=.+', '--deplevel=\d+', '--custom=.+', '--autoclean', '--usrlocal', '--warn', '--debug', '--descrete', '--quiet', '--print', '--make', '--run']

  for argument in argv[1:]:
    argumentIsValid = False;
    for validArgumentPattern in validArgumentRegexPatterns:
      m = re.search('^'+validArgumentPattern+'$', argument, re.MULTILINE)
      if m:
        argumentIsValid = True
        break;
    if not argumentIsValid:
      message('Error: Invalid or malformed argument: "'+argument+'". See --help.')
      exit(1)

  if '--print' in argv and '--make' in argv:
    message('Error: --print and --make specified but --print supresses writing to makefile.')
    exit(1)

  if libSpecified and '--run' in argv:
    message('Error: --run specified, but you are building a library (--lib specified).')
    exit(1)

  if '--run' in argv and '--make' not in argv:
    message('Error: --run specified, but --run requires --make, which is unspecified.')
    exit(1)

  if binarySpecified and libSpecified:
    message('Error: Both --lib and --binary specified.')
    exit(1)

def getFileDeps(filename, maxrecurse): #takes a sourcefile and finds all #includes(recusively) in order to determine what files the sourcefile depends upon
  global isCCode #you so silly python
  global depend
  maxrecurse -= 1
  if(maxrecurse < 0):
    emptylist = []
    return emptylist

  m = re.findall(r'^#include <(.+(?:\.h)?(?:pp)?)>', GetFileFromCache(filename), re.MULTILINE) #Warning, if #includes are commented out using C comments(/* */), they will still be included.  I don't know how to avoid this using regex, probally not possible with just regex. TODO
  for case in m:
    if case in librarys:
      depend.extend(librarys[case])
  m = re.findall(r'^#include "(.+\.h(?:pp)?)"', GetFileFromCache(filename), re.MULTILINE)
  deps = []
  for case in m:
    if case[-4:] == ('.hpp') > -1: #language is determined entirely by file extensions :x
      isCCode = False
    if case in librarys:
      depend.extend(librarys[case])
    else:
      if case not in deps:
        if os.path.exists(case): #otherwise it is like #include "stdlib.h"
          deps.append(os.path.join(os.path.split(filename)[0], os.path.normpath(case))) #Add the found file dependency, with proper directory
          deps.extend(getFileDeps(case, maxrecurse))
          deps = list(set(deps))
  return deps


def BinaryGuessingStrategy1():
  #Guessing Strategy 1: Name the binary after the containing folder (if sourcecode is under 'src' path then it is likely it is part of a larger folder named as the projectname)
  #Eg: if the soruce directory[where supermake was ran from] is at say ~/projects/DeathStar/src/ then this will create the binary at ~/projects/DeathStar/DeathStar.run
  if os.path.basename(os.getcwd()) != 'src':
    return False
  binary = os.path.basename(os.path.realpath('..')) + '.run'
  if os.path.isdir('../bin'):
    binary = '..bin/'+binary
  elif os.path.isdir('./bin'):
    binary = './bin/'+binary
  else:
    binary = '../'+binary
  return binary

def BinaryGuessingStrategy2():
  #Guessing Strategy 2: Look for the common GPL disclaimer and name it after the specified project name.
  filenames = sorted(os.listdir('.'))
  for filename in filenames:
    if (not os.path.isdir(filename)) and (filename[-4:] == '.cpp' or filename[-4:] == '.cxx' or filename[-4:] == '.c++' or filename[-3:] == '.cc' or filename[-2:] == '.c'):
      m = re.search('\s*(.+) is free software(?:;)|(?::) you can redistribute it and/or modify', GetFileFromCache(filename))
      if m:
        if m.group(1) != 'This program' and m.group(1) != 'This software':
          return m.group(1)
        break; #breaks nomatter what, because if this file uses the generic one ('This program') then they all will
  return False

def BinaryGuessingStrategy3():
  #Guessing Strategy 3: Look for pre-existing binarys (.run, .exe) and name it after those.
  #filenames = os.listdir('.')
  #for filename in filenames:
  #  if filename[-4:] == '.run' or filename[-4:] == '.bin' or filename[-4:] == '.exe':
  #    if filename[-5] != '1':
  #      return filename[:-4]+'1'+filename[-4:]
  #    return filename
  return False

def BinaryGuessingStrategy4():
  #Guessing Strategy 4: Look for the main() function and see if it is in the top-level application class file, which is semi common afaik, at least in java ;).
  binary = ''
  if os.path.isdir('./bin'):
    binary = './bin/'+binary
  else:
    binary = './'+binary
  return False

def BinaryGuessingStrategy5():
  #Guessing Strategy 5: If the only file is main.cpp, call it main.run
  filenames = os.listdir('.')
  for filename in filenames:
    if (not os.path.isdir(filename)) and (filename[-4:] == '.cpp' or filename[-4:] == '.cxx' or filename[-4:] == '.c++' or filename[-3:] == '.cc' or filename[-2:] == '.c'):
      if filename[:4] != 'main':
        return False
  return 'main.run'

def BinaryGuessingStrategy6():
  #Guessing Strategy 6: Screw it. Call it something totally generic.
  return 'program.run'

####### Main - mostly everything
def main():
  global quiet
  global isCCode
  global depend

  argv = sys.argv

  if '--quiet' in argv:
    quiet = True

  if sys.hexversion < 0x03000000: #hexversion is used as it is the most compatible with older versions according to http://stackoverflow.com/questions/446052/python-best-way-to-check-for-python-version-in-program-that-uses-new-language-fe/3132402#3132402
    message('Warning: Your python interpreter is too old, Supermake may therefore perform erratically or crash. Supermake is intended for python 3.0 or newer.')

  if '--help' in argv or '-help' in argv or '-h' in argv or '-?' in argv or 'help' in argv or '/h' in argv or '/?' in argv:
    print(usage)
    sys.exit()

  filterCommandlineOptionDescrepency(argv) #this doesn't really filter, just terminates on errors.

  #Determine maxrecurse(--deplevel).
  maxrecurse = 15 #default #I personally make code I write work with 1(excluding a lot of things like inheritance -- nevermind), but there are different ideas on where you should place #includes. In most projects 15 is enough to cover them all and making sure their project compiles is far more important to supermake's objectives than defaulting to enforcing a subjective methodology decision on users.
  for argument in argv:
    m = re.search('--deplevel=(\d+)', argument)
    if m:
      maxrecurse = int(m.group(1))

  #Find sourcefiles and acquire their dependencies(Supermake considers a file to depend upon another if it is #included)
  hasSourceFiles = False
  filenames = sorted(os.listdir('.'))
  for filename in filenames:
    if (not os.path.isdir(filename)) and (filename[-4:] == '.cpp' or filename[-4:] == '.cxx' or filename[-4:] == '.c++' or filename[-3:] == '.cc' or filename[-2:] == '.c'):
      hasSourceFiles = True
      if filename[-4:] == '.cpp' or filename[-4:] == '.cxx' or filename[-4:] == '.c++':
        isCCode = False
      deps = sorted(getFileDeps(filename, maxrecurse))
      for depIndex in range(len(deps)):
        if deps[depIndex][:-2] == filename[:-4]: #This puts the corrosponding header file right after the source file. [ie  :monster.cpp monster.h otherstuff.h otherstuff2.h]
          dep = deps[depIndex]
          deps.remove(deps[depIndex])
          deps.insert(0,dep)
          break;
      fileDeps.append((filename, deps))

  if not hasSourceFiles:
    message('Error: No sourcecode found in directory. For help see --help.')
    sys.exit()

  depend = list(set(depend)) #remove duplicates
  depend = sorted(depend) #These alphabetic sorts are just to make the output look nice and consistent.

  #Name the library
  library = ''
  for argument in argv:
    m = re.search('--lib=(\S+)', argument)
    if m:
      library = m.group(1)
      basename = os.path.basename(library)
      if basename[:3] != 'lib':
        library = os.path.join(os.path.dirname(library), 'lib'+ basename)
        message('Warning: Prepending "lib" to the library name: "'+library+'.so", "'+library+'.a".')

  #Name the binary
  binary = ''
  if library == '':
    for argument in argv:
      m = re.search('--binary=(\S+)', argument)
      if m:
        binary = m.group(1)
    if binary == '': #'Guess' an acceptable binary name
      crazyGuesswork = False

      binary = BinaryGuessingStrategy1()
      if not binary:
        binary = BinaryGuessingStrategy2()
        if not binary:
          binary = BinaryGuessingStrategy3()
          if not binary:
            binary = BinaryGuessingStrategy4()
            if not binary:
              binary = BinaryGuessingStrategy5()
              if not binary:
                binary = BinaryGuessingStrategy6()
          else:
            crazyGuesswork = True #Because this will be REALLY FREAKING WEIRD when they have like random other shit in the directory and this names it after it

      guessMessage = 'Warning: Guessed a binary name: ' + binary + ' (use --binary=NAME to specify this yourself)'
      if crazyGuesswork:
        guessMessage += '(this uses crazy guesswork and could be totally off)'
      message(guessMessage)

  customFlags = ''
  for argument in argv:
    m = re.search('--custom=(.+)', argument)
    if m:
      customFlags = m.group(1)

  #Write out the makefile.
  makefile = ''
  if not '--print' in argv and not '--descrete' in argv:
    makefile += makefileMessage

  makefile += 'OBJS ='
  for fileDep in fileDeps:
    if isCCode:
      makefile += ' ' + fileDep[0][:-2] + '.o'
    else:
      makefile += ' ' + fileDep[0][:-4] + '.o'
  makefile += '\n'

  if customFlags != '':
    makefile += 'CUSTOMFLAGS = ' + customFlags + '\n'

  makefile += 'FLAGS ='

  if '--usrlocal' in argv:
    makefile += ' -L/usr/local/include '

  makefile += ' ' + ' '.join(depend)

  if '--debug' in argv:
    makefile += ' -g -DDEBUG'# -pg'

  if '--warn' in argv:
    makefile += ' -Wall'

  if customFlags != '':
    makefile += ' $(CUSTOMFLAGS)'

  makefile += '\n\n'

  compiler = 'g++'
  if isCCode:
    compiler = 'gcc'
    #message('Warning: Detected that this is a C project. C support in Supermake is not well tested, there is a chance you might encounter problems.')

  if library == '':
    makefile += binary + ': $(OBJS)\n'
    makefile += '\t'+compiler+' $(FLAGS) $(OBJS) -o '+binary+'\n\n'

  else:
    makefile += 'all: '+library+'.a '+library+'.so\n\n'
    #static library
    makefile += library+'.a: $(OBJS)\n'
    makefile += '\tar rcs '+library+'.a $(OBJS)\n\n'

    #shared library
    makefile += library + '.so: $(OBJS)\n'
    makefile += '\t'+compiler+' -shared -Wl,-soname,'+os.path.basename(library)+'.so $(OBJS) -o '+library+'.so\n\n'


  for fileDep in fileDeps:
    objectFileName = ""
    if isCCode:
      objectFileName = fileDep[0][:-2] + '.o'
    else:
      objectFileName = fileDep[0][:-4] + '.o'
    makefile += objectFileName+': '+fileDep[0]+' '+' '.join(fileDep[1])+'\n'
    makefile += '\t'+compiler+' $(FLAGS) -c '+fileDep[0]+' -o '+objectFileName+'\n\n'

  if library == '':
    makefile += 'clean:\n\trm -f '+binary+' *.o'
  else:
    makefile += 'clean:\n\trm -f '+library+'.a '+library+'.so *.o'

  if '--print' in argv:
    print(makefile)
  else:
    autoClean = False
    if os.path.exists('makefile') or os.path.exists('Makefile'):
      oldFilename = ''
      if os.path.exists('makefile'):
        oldFilename = 'makefile'
      elif os.path.exists('Makefile'):
        oldFilename = 'Makefile'

      oldMakefile = open(oldFilename, 'r').read();
      if oldMakefile != makefile:
        autoClean = True;

      os.rename(oldFilename, '/tmp/'+oldFilename+'.old')
      message('Warning: Overwriting previous makefile (previous makefile copied to /tmp/'+oldFilename+'.old in case you weren\'t ready for this!)')

    f = open('makefile', 'w')
    f.write(makefile)
    f.close()

    if autoClean and '--autoclean' in sys.argv:
      message('Makefiles differ, executing command: make clean')
      os.system('make clean')

    #Compile
    if '--make' in argv:
      cmd = 'make'
      #Run
      if '--run' in argv:
        splitBinPath = os.path.split(binary)
        if splitBinPath[0] != '':
          cmd += ' && cd "'+splitBinPath[0]+'"' #move to the working directory likely expected by the binary
        cmd += ' &&'
        if '--usrlocal' in argv:
          cmd += ' LD_LIBRARY_PATH=/usr/local/lib/'
        cmd += ' "./' + splitBinPath[1]+'"' #If --debug is enabled I would also have it automatically run in gdb but I expect this will put off users who aren't familiar with gdb, don't expect it, and don't know what to do when the alien gdb console pops up.
      message('Executing command: ' + cmd)
      os.system(cmd)

if __name__ == '__main__':
  main()
