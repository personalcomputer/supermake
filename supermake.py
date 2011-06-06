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
# The objective of Supermake is to be a simple user-friendly makefile generator that attempts its best to figure out what the user wants with well thought out aggressive defaults that work for most basic compilation needs. Additionally supermake provides the option to automatically perform the rest of the build process, even launching the resultant binary for you! I feel that supermake is now fairly mature and accomplishes this objective.
#
# Supermake is created by personalcomputer <https://github.com/personalcomputer>
#
# This is python 3 code written to be fully back-compatible with python 2.7 as well.
# Lots, of this is unix-like only (possibly even linux only), but it should be fairly simple to get the resulting makefiles to work with mingw.

import re
import os
import sys

cliName = os.path.basename(sys.argv[0])

usage = '''Usage: '''+cliName+''' [OPTION]...
Automatically generate a basic makefile for C or C++ source files in the current
directory and optionally compile and execute it, streamlining and simplifying
the build process.

  --print         Print to the console instead of writing to a makefile.
  --make          'make' the generated makefile (compile the project).
  --run           Execute the compiled binary. Only to be used in combination
                  with --make.
  --debug         Add the -g and -DDEBUG debug flags to the gcc compilation
                  flags, and, if --run is specified, run it in gdb.
  --warn          Add the -Wall warning flag to the gcc compilation flags.
  --optimize      Add the -O3 optimization flag to the gcc compilation flags.
  --binary=NAME   Name the binary that the makefile generates. By default
                  Supermake will guess an acceptable binary name.
  --custom=FLAGS  Compile everything with additional custom gcc FLAGS. This can
                  be used, for example, for specifying extra -D defines.
  --lib=NAME      Build the project as a library instead. NAME specifies the name
                  (ex: ../lib/libamazing). This automatically adds both shared
                  (.so) and static (.a) library types, so do not specify an
                  extension in NAME.
  --quiet         Suppress all general messages and warnings that origin from
                  Supermake.
  --discrete      Do not add the "This makefile was generated by Supermake..."
                  message at the top of the makefile.

Ex: '''+cliName+'''
Ex: '''+cliName+''' --binary=../bin/myprogram.run --debug --warn --make
Ex: '''+cliName+''' --binary=myprogram.run --make --run.'''

makefileHeader = '#This makefile was generated by Supermake. Modify as you wish, but remember that your changes will not be preserved when you run Supermake again. Try to use the available basic options(see --help) to tune it how you desire, if possible. Lastly, remember that Supermake is not suitable for most involved projects\' build requirements.\n\n'

###All of the currently supported libraries. Expanding this list is encouraged!
libraries = {}
libraries['boost/regex.hpp'] = ['-lboost_regex'] #Far from extensive boost support...
libraries['SDL/SDL.h'] = ['`sdl-config --libs`']
libraries['SDL/SDL_image.h'] = ['-lSDL_image', '`sdl-config --libs`']
libraries['SDL/SDL_mixer.h'] = ['-lSDL_mixer', '`sdl-config --libs`']
libraries['SDL/SDL_opengl.h'] = ['-lGL', '`sdl-config --libs`']
libraries['SDL/SDL_ttf.h'] = ['-lSDL_ttf', '`sdl-config --libs`']
libraries['SDL/SDL_net.h'] = ['-lSDL_net', '`sdl-config --libs`']
libraries['SDL/SDL_thread.h'] = ['-lSDL', '-pthread']
libraries['GL/glfw.h'] = ['-lGL', '-lX11', '-lXrandr', '-pthread', '-lglfw']
libraries['Box2D/Box2D.h'] = ['-lBox2D']
libraries['openssl/sha.h'] = ['-lcrypto']
libraries['gcrypt.h'] = ['-lgcrypt', '-lgpg-error']
libraries['mysql/mysql.h'] = ['`mysql_config --libs`']
libraries['zmq.hpp'] = ['-lzmq']
libraries['zmq.h'] = ['-lzmq']
libraries['OIS/OISInputManager.h'] = ['-lOIS']
libraries['OIS/OISEvents.h'] = ['-lOIS']
libraries['OIS/OISInputManager.h'] = ['-lOIS']
libraries['ncurses.h'] = ['-lncurses']
libraries['GL/gl.h'] = ['-lGL']
libraries['GL/glu.h'] = ['-lGLU', '-lGL']
libraries['GL/glew.h'] = ['-lGLEW', '-lGLU', '-lGL']
libraries['GL/glut.h'] = ['-lGLUT', '-lGLU', '-lGL']
libraries['Horde3D/Horde3D.h'] = ['-lHorde3D']
libraries['Horde3D/Horde3DUtils.h'] = ['-lHorde3D', '-lHorde3DUtils']
libraries['OGRE/OgreCamera.h'] = ['-lOgreMain'] #There are more base ogre includes than the ones defined here. The thing is though, if it includes any of these(and it will if it uses ogre, for these are required for most uses) then it is already taken care of.
libraries['OGRE/OgreEntity.h'] = ['-lOgreMain']
libraries['OGRE/OgrePrerequisites.h'] = ['-lOgreMain']
libraries['OGRE/OgreRoot.h'] = ['-lOgreMain']
libraries['OGRE/OgreViewport.h'] = ['-lOgreMain']
libraries['OGRE/OgreSceneManager.h'] = ['-lOgreMain']
###

####### Globals
depend = [] #Library dependencies (Such as -lSDL)
fileDeps = [] #All found source files and the files that they individually have been determined to depend upon

quiet = False

isCCode = True #until proven otherwise.

####### Util Functions
def message(text, critical = False):
  if (not quiet) or critical:
    print('Supermake: ' + text)
    
fileCache = {}

def GetFileFromCache(filename): #This loads and caches all files for speed. (Supermake requests the same sorucecode files multiple times each run). This uses the lazy-load idiom.
  if filename not in fileCache:
    f = open(filename, 'r')
    fileCache[filename] = f.read()
    f.close()
  return fileCache[filename]

def splitOnExtension(path): #Splits 'example.txt' into ('example', 'txt'), similar in usage to os.path.split.
  return (path[path.rfind('.'):], path[:path.rfind('.')])
  
sourceCodeInDirectoryCache = None

def sourceCodeInDirectory(): #DOES NOT INCLUDE HEADERS
  global sourceCodeInDirectoryCache
  if not sourceCodeInDirectoryCache:
    sourceCodeInDirectoryCache = sorted([filename for filename in os.listdir('.') if ((not os.path.isdir(filename)) and (filename.endswith('.cpp') or filename.endswith('.cxx') or filename.endswith('.c++') or filename.endswith('.cc') or filename.endswith('.c')))])
  return sourceCodeInDirectoryCache
  
####### Helper Functions
def checkCommandlineOptions(argv):
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

  validArgumentRegexPatterns = ['--optimize', '--binary=.+', '--lib=.+', '--deplevel=\d+', '--custom=.+', '--warn', '--debug', '--discrete', '--quiet', '--print', '--make', '--run', '--override-depend', '--noautoclean', '--oprefix=.+']

  for argument in argv[1:]:
    argumentIsValid = False;
    for validArgumentPattern in validArgumentRegexPatterns:
      m = re.search('^'+validArgumentPattern+'$', argument, re.MULTILINE)
      if m:
        argumentIsValid = True
        break;
    if not argumentIsValid:
      message('Error: Invalid or malformed argument: "'+argument+'". See --help.', critical=True)
      exit(1)
      
  if '--run' in argv and os.name != 'posix':
    message('Error: --run is available only on unix-like platforms.', critical=True)
    exit(1)

  if '--print' in argv and '--make' in argv:
    message('Error: --print and --make specified but --print suppresses writing to makefile.', critical=True)
    exit(1)

  if libSpecified and '--run' in argv:
    message('Error: --run specified, but you are building a library (--lib specified).', critical=True)
    exit(1)

  if '--run' in argv and '--make' not in argv:
    message('Error: --run specified, but --run requires --make, which is unspecified.', critical=True)
    exit(1)

  if binarySpecified and libSpecified:
    message('Error: Both --lib and --binary specified.', critical=True)
    exit(1)

def getFileDeps(filename, maxrecurse): #takes a source file and finds all #includes(recursively) in order to determine what files the source-file depends upon
  global isCCode #you so silly python
  global depend
  maxrecurse -= 1
  if(maxrecurse < 0):
    emptylist = []
    return emptylist

  m = re.findall(r'^#include <(.+(?:\.h)?(?:pp)?)>', GetFileFromCache(filename), re.MULTILINE) #Warning, if #includes are commented out using C comments(/* */), they will still be included.  I don't know how to avoid this using regex, probably not possible with just regex. TODO
  for case in m:
    if case in libraries:
      depend.extend(libraries[case])
  m = re.findall(r'^#include "(.+\.h(?:pp)?)"', GetFileFromCache(filename), re.MULTILINE)
  deps = []
  for case in m:
    if case[-4:] == ('.hpp') > -1: #language is determined entirely by file extensions :x
      isCCode = False
    if case in libraries:
      depend.extend(libraries[case])
    else:
      if case not in deps:
        if os.path.exists(case):
          case = case
        elif os.path.exists(os.path.join('include',case)): #You might say this is hacky, but it fully follows the philosohpy of Supermake. Supermake is not a do-everything super-configurable makefile generator, it is designed only to work with usual situations (But work well!). #Making this not hacky would, of course, required multi-directory support, something I've thought about before, and probally will still eventualy add.
          case = os.path.join('include',case)
        elif os.path.exists(os.path.join('../include',case)):
          case = os.path.join('../include',case)
        else: #otherwise it is like #include "stdlib.h"
          continue 
        
        deps.append(os.path.join(os.path.split(filename)[0], os.path.normpath(case))) #Add the found file dependency, with proper directory
        deps.extend(getFileDeps(case, maxrecurse))
        deps = list(set(deps))
          
  return deps


def BinaryGuessingStrategy_ContainingProjectFolderName():
  #Guessing Strategy: Name the binary after the containing folder (if sourcecode is under 'src' path then it is likely it is part of a larger folder named as the projectname)
  #Eg: if the source directory[where supermake was ran from] is at say ~/projects/DeathStar/src/ then this will create the binary at ~/projects/DeathStar/DeathStar.run
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

def BinaryGuessingStrategy_GPLDisclaimerName():
  #Guessing Strategy: Look for the common GPL disclaimer and name it after the specified project name.
  for filename in sourceCodeInDirectory():
    m = re.search('\s*(.+) is free software(?:;)|(?::) you can redistribute it and/or modify', GetFileFromCache(filename))
    if m:
      if m.group(1) != 'This program' and m.group(1) != 'This software':
        return m.group(1)
      break; #breaks no-matter what, because if this file uses the generic one ('This program') then they all will
  return False


def BinaryGuessingStrategy_RootClassName():
  #Guessing Strategy: Look for the main() function and see if it is in the top-level application class file, which is semi common afaik, at least in java ;).
  #TODO
  return False

def BinaryGuessingStrategy_SingleFileName():
  #Guessing Strategy: If there is only one source file, name it after that.
  if len(sourceCodeInDirectory()) == 1:
    return splitOnExtension(sourceCodeInDirectory()[0])[0] + '.run'
  return False
  
def BinaryGuessingStrategy_ParentFolderName():
  #Guessing Strategy: Name it after the parent folder.
  return os.path.basename(os.path.realpath('.'))+'.run'

def BinaryGuessingStrategy_GenericName():
  #Guessing Strategy: Call it something totally generic.
  return 'program.run'
  
def determineIfAutocleanNeeded(oldMakefile, newMakefile): 
  if oldMakefile == newMakefile: #No reason to check further if they are identical.
    return False
  #Idea: Go through old makefile and if the only differences are in new files and new $OBJS, then don't autoclean. But if anything else changes, autoclean. ..This actually isn't that complicated :D (but is hacky -- really not too bad though).  
  #What it currently does: simply looks to see if $FLAGS differ.
  m1 = re.search('^FLAGS = .+$', oldMakefile, re.MULTILINE)
  if not m1:
    return True
  m2 = re.search('^FLAGS = .+$', newMakefile, re.MULTILINE)
  if m2.group() == m1.group():
    m3 = re.search('^CUSTOMFLAGS = .+$', oldMakefile, re.MULTILINE)
    m4 = re.search('^CUSTOMFLAGS = .+$', newMakefile, re.MULTILINE)
    if bool(m4) and bool(m3):
      if m4.group() == m3.group():
        return False
    else:
      if bool(m4) == bool(m3) == False:
        return False
    return True
  else:
    return True
  

####### Main - mostly everything
def main():
  global quiet
  global isCCode
  global depend

  argv = sys.argv

  if '--quiet' in argv:
    quiet = True

  if '--help' in argv or '-help' in argv or '-h' in argv or '-?' in argv or 'help' in argv or '/h' in argv or '/?' in argv:
    print(usage)
    sys.exit()
  
  if sys.hexversion < 0x02070000: #hexversion is used because it is the most compatible with older versions according to http://stackoverflow.com/questions/446052/python-best-way-to-check-for-python-version-in-program-that-uses-new-language-fe/3132402#3132402
    #I don't have any specific reason for putting the cutoff at 2.7, aside from the fact that I don't feel like installing older python versions to test. This was originally at python 3.0, but everything was back-compatible with 2.7 so..
    message('Warning: Your python interpreter is too old, Supermake may therefore perform erratically or crash. Supermake is intended for at least python 2.7.')

  checkCommandlineOptions(argv)

  #Determine maxrecurse(--deplevel).
  maxrecurse = 15 #default #I personally like to make code I write work with 1(but don't usually adhere to it in practice, not worth the cost/benefit trade-off), but there are different ideas on where you should place #includes. In most projects a deplevel of 15 is enough to cover them all, and making sure their project compiles right away is far more important to supermake's objectives than defaulting to enforcing a subjective methodology decision on users.
  for arg in argv:
    m = re.search('--deplevel=(\d+)', arg) #UNDOCUMENTED FEATURE: --DEPLEVEL
    if m:
      maxrecurse = int(m.group(1))

  #### Find sourcefiles and acquire their dependencies(Supermake considers a file to depend upon another if it is #included)
  hasSourceFiles = False
  if len(sourceCodeInDirectory()) <= 0:
    message('Error: No sourcecode found. For help see --help.', critical=True)
    sys.exit()
  for filename in sourceCodeInDirectory():
    if filename.endswith('.cpp') or filename.endswith('.cxx') or filename.endswith('.c++'):
      isCCode = False
    deps = sorted(getFileDeps(filename, maxrecurse))
    for depIndex in range(len(deps)):
      if splitOnExtension(deps[depIndex])[0] == splitOnExtension(filename)[0]: #This puts the corresponding header file right after the source file. [Eg :monster.cpp monster.h otherstuff.h otherstuff2.h]
        dep = deps[depIndex]
        deps.remove(deps[depIndex])
        deps.insert(0,dep)
        break;
    fileDeps.append((filename, deps))
  
  if '--override-depend' in argv: #UNDOCUMENTED FEATURE: --override-depend
    depend = []

  depend = list(set(depend)) #remove duplicates
  depend = sorted(depend) #These alphabetic sorts are just to make the output look nice and consistent.

  #Name the library
  library = ''
  for argument in argv:
    m = re.search('--lib=(\S+)', argument)
    if m:
      library = m.group(1)
      basename = os.path.basename(library)
      if not basename.startswith('lib'):
        library = os.path.join(os.path.dirname(library), 'lib'+ basename)
        message('Prepending "lib" to the library name: "'+library+'.so", "'+library+'.a".')

  #Name the binary
  binary = ''
  if library == '':
    for argument in argv:
      m = re.search('--binary=(\S+)', argument)
      if m:
        binary = m.group(1)
    if binary == '': #'Guess' an acceptable binary name
      binary = BinaryGuessingStrategy_ContainingProjectFolderName()
      if not binary:
        binary = BinaryGuessingStrategy_GPLDisclaimerName()
        if not binary:
          binary = BinaryGuessingStrategy_SingleFileName()
          if not binary:
            binary = BinaryGuessingStrategy_RootClassName()
            if not binary:
              binary = BinaryGuessingStrategy_ParentFolderName()
              if not binary:
                binary = BinaryGuessingStrategy_GenericName()
      message('Guessed a binary name: ' + binary + ' (use --binary=NAME to specify this yourself)')

  customFlags = ''
  for argument in argv:
    m = re.search('--custom=(.+)', argument)
    if m:
      customFlags = m.group(1)
      
  oprefix = ''
  for argument in argv:
    m = re.search('--oprefix=(.+)', argument)
    if m:
      oprefix = m.group(1)

  #### Write out the makefile.
  makefile = ''
  if not '--print' in argv and not '--descrete' in argv:
    makefile += makefileHeader

  makefile += 'OBJS ='
  for fileDep in fileDeps:
    makefile += ' ' + oprefix+splitOnExtension(fileDep[0])[0] + '.o'
  makefile += '\n'

  if customFlags != '':
    makefile += 'CUSTOMFLAGS = ' + customFlags + '\n'

  makefile += 'FLAGS ='

  makefile += ' -L/usr/local/include'
  
  #Add the include directory, if in use. 
  if os.path.exists('include'):
    makefile += ' -Iinclude'
  if os.path.exists('../include'):
    makefile += ' -I../include'

  makefile += ' ' + ' '.join(depend)

  if '--debug' in argv:
    makefile += ' -g -DDEBUG'# -pg'

  if '--warn' in argv:
    makefile += ' -Wall'
    
  if '--optimize' in argv:
    makefile += ' -O3'

  if customFlags != '':
    makefile += ' $(CUSTOMFLAGS)'

  makefile += '\n\n'

  compiler = 'g++'
  if isCCode:
    compiler = 'gcc'
    #message('Warning: Detected that this is a C project. C support in Supermake is not well tested, there is a chance you might encounter problems.')

  if library == '':
    makefile += binary + ': $(OBJS)\n'
    makefile += '\t'+compiler+' $(OBJS) $(FLAGS) -o '+binary+'\n\n'

  else:
    makefile += 'all: '+library+'.a '+library+'.so\n\n'
    #static library
    makefile += library+'.a: $(OBJS)\n'
    makefile += '\tar rcs '+library+'.a $(OBJS)\n\n'

    #shared library
    makefile += library + '.so: $(OBJS)\n'
    makefile += '\t'+compiler+' -shared -Wl,-soname,'+os.path.basename(library)+'.so $(OBJS) -o '+library+'.so\n\n'


  for fileDep in fileDeps:
    objectFileName = oprefix+splitOnExtension(fileDep[0])[0] + '.o'
    makefile += objectFileName+': '+fileDep[0]+' '+' '.join(fileDep[1])+'\n'
    makefile += '\t'+compiler+' $(FLAGS) -c '+fileDep[0]+' -o '+objectFileName+'\n\n'

  if library == '':
    makefile += 'clean:\n\trm -f '+binary+' *.o'
  else:
    makefile += 'clean:\n\trm -f '+library+'.a '+library+'.so *.o'
  #### Makefile contents have now been written out

  if '--print' in argv:
    print(makefile)
  else:
    #Determine if  `make clean` is needed
    needsAutoClean = False
    if os.path.exists('makefile') or os.path.exists('Makefile'):
      oldMakefileFilename = ''
      if os.path.exists('makefile'):
        oldMakefileFilename = 'makefile'
      elif os.path.exists('Makefile'):
        oldMakefileFilename = 'Makefile'

      if '--noautoclean' not in argv:
        needsAutoClean = determineIfAutocleanNeeded(open(oldMakefileFilename, 'r').read(), makefile);

      os.system('mv '+oldMakefileFilename+' /tmp/'+oldMakefileFilename+'.old')
      message('Warning: Overwriting previous makefile (previous makefile copied to /tmp/'+oldMakefileFilename+'.old in case you weren\'t ready for this!)')

    makefileFile = open('makefile', 'w')
    makefileFile.write(makefile)
    makefileFile.close()

    if needsAutoClean:
      message('Makefiles critically differ. Executing command: make clean')
      os.system('make clean')

    #Compile
    if '--make' in argv:
      cmd = 'make'
      #Run
      if '--run' in argv:
        (binaryParentFolder, binaryFilename) = os.path.split(binary)
        if binaryParentFolder != '':
          cmd += ' && cd "'+binaryParentFolder+'"' #move to the working directory likely expected by the binary
        cmd += ' && LD_LIBRARY_PATH=/usr/local/lib/'
        if '--debug' in argv:
          cmd += ' gdb'
        cmd += ' "./' + binaryFilename+'"'
      message('Executing command: ' + cmd)
      os.system(cmd)

if __name__ == '__main__':
  main()
