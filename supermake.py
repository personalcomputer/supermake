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
# Lots of this is unix-like only (possibly even Linux only), but it should be fairly simple to get the resulting makefiles to work with mingw.
#
# bad code, all python's fault.

import re
import os
import sys
import subprocess
import shutil

usage = '''Usage: supermake [OPTION]...
Automatically generate a basic makefile for C or C++ source files in the current
directory and optionally compile and execute it, streamlining and simplifying
the build process.

  --print         Print to the console instead of writing to a makefile.
  --make          'make' the generated makefile (compile the project).
  --run           Execute the compiled binary. Only to be used in combination
                  with --make.
  --recurse, -R   Recursively add source code from subdirectories as well.
  --debug         Add the -g and -DDEBUG debug flags to the gcc compilation
                  flags, and, if --run is specified, run it in gdb.
  --warn          Add the -Wall warning flag to the gcc compilation flags.
  --optimize      Add the -O3 optimization flag to the gcc compilation flags.
  --binary=NAME   Name the binary that the makefile generates. By default
                  Supermake will guess an acceptable binary name.
  --custom=FLAGS  Compile everything with additional custom gcc FLAGS. This can
                  be used, for example, for specifying extra -D defines.
  --lib=NAME      Build the project as a library instead. NAME specifies the
                  name and path of the library (Ex: ../lib/libamazing), similar
                  to --binary. This automatically creates both shared (.so) and
                  static (.a) library types, so do not specify an extension in
                  NAME.
  --quiet         Suppress all general messages and warnings that origin from
                  Supermake.
  --discrete      Do not add the "This makefile was generated by Supermake..."
                  message at the top of the makefile.
  --args          Pass all arguments after the --args arg to the binary when
                  using --run. (Ex: `supermake --make --run --args 5 4` passes
                  '5' and '4' to the binary when it is run through --run)

Ex: supermake
Ex: supermake --binary=../bin/myprogram.run --debug --warn --make
Ex: supermake --binary=myprogram.run --make --run'''

helpArguments = set(['--help', '-help', '-h', 'h', '-?', 'help', '/h', '/?', '?', 'HELP'])

makefileHeader = '#This makefile was generated by Supermake (<https://github.com/personalcomputer/supermake>). Modify as you wish, but remember that your changes will not be preserved when you run Supermake again. Try to use the available basic options(see --help) to tune it how you desire, if possible. Lastly, remember that Supermake is not suitable for most involved projects\' build requirements.\n\n'

# All of the currently supported libraries. Expanding this list is encouraged!
# Only needs to match the first characters of the header for the libraries to be linked.
libraries = { #There are a lot of problems with the current approach, but this is inherit to Supermake's design, unfortunately. I just use the most common installation setups (specifically, whatever ubuntu uses ;)) for these libraries.
  'Box2D.h': ['-lbox2d'],
  'openssl/sha.h': ['-lcrypto'],
  'gcrypt.h': ['-lgcrypt', '-lgpg-error'],
  'mysql/mysql.h': ['`mysql_config --libs`'],
  'zmq.hpp': ['-lzmq'],
  'zmq.h': ['-lzmq'],
  'ncurses.h': ['-lncurses'],
  'google/profiler.h': ['-lprofiler'],
  
  'SDL/': ['`sdl-config --libs`'],
  'SDL/SDL_image.h': ['-lSDL_image'],
  'SDL/SDL_mixer.h': ['-lSDL_mixer'],
  'SDL/SDL_opengl.h': ['-lGL'],
  'SDL/SDL_ttf.h': ['-lSDL_ttf'],
  'SDL/SDL_net.h': ['-lSDL_net'],
  'SDL/SDL_thread.h': ['-pthread'],
  
  'GL/': ['-lGL'],
  'GL/glfw.h': ['-lX11', '-lXrandr', '-pthread', '-lglfw'],
  'GL/glu.h': ['-lGLU'],
  'GL/glew.h': ['-lGLEW', '-lGLU'],
  'GL/glut.h': ['-lGLUT', '-lGLU'],
  
  'Horde3D/': ['-lHorde3D'],
  'Horde3D/Horde3DUtils.h': ['-lHorde3DUtils'],
  
  'boost/': ['-lboost_system'],
  'boost/regex.hpp': ['-lboost_regex'],
  'boost/filesystem': ['-lboost_filesystem'],
  'boost/serialization': ['-lboost_serialization'],
  'boost/signal': ['-lboost_signals'],
  'boost/thread': ['-lboost_thread'],
  'boost/program_options/': ['-lboost_program_options'],
  'boost/mpi': ['-lboost_mpi'],
  'boost/test/': ['-lboost_unit_test_framework', '-DBOOST_TEST_DYN_LINK'], #You're on your own altering your makefile(s) after this to actually set up a testing environment. This is not fire-and-forget like the rest of Supermake. If it was a cli parameter it would be undocumented.

  'OGRE/': ['-lOgreMain'],
  
  'OIS/': ['-lOIS'],
  
  'gtk/': ['`pkg-config --cflags --libs gtk+-2.0`'], #Sorry, no 3.0 support. Supermake simply is not capable or designed to support multiple library versions. (but it will only take changing a single character if you need it..)
  
  'gtkmm': ['`pkg-config gtkmm-2.4 --cflags --libs`'],
}

# constants that should be part of CodeFile but python is lame.
c_source_extensions      = set(['c'])
c_header_extensions      = set(['h'])
cpp_source_extensions    = set(['c++', 'cc', 'cpp', 'cxx'])
cpp_header_extensions    = set(['h++', 'hh', 'hpp', 'hxx', 'h'])

c_exclusive_extensions   = (c_header_extensions | c_source_extensions) - (cpp_header_extensions | cpp_source_extensions)
cpp_exclusive_extensions = (cpp_header_extensions | cpp_source_extensions) - (c_header_extensions | c_source_extensions)

all_source_extensions    = cpp_source_extensions | c_source_extensions
all_header_extensions    = cpp_header_extensions | c_header_extensions
all_code_extensions      = all_source_extensions | all_header_extensions

class Messenger():
  '''Sends properly prefaced messages to the console'''
  def __init__(self):
    self._quiet = False
  
  def Message(self, msg, critical=False):
    if not self._quiet or critical:
      print('Supermake: '+msg)
      
  def NoticeMessage(self, msg):
    self.Message('Notice: '+msg)
  
  def ErrorMessage(self, msg):
    self.Message('Error: '+msg, critical=True)
  
  def WarningMessage(self, msg):
    self.Message('Warning: '+msg)
    
  def SetQuiet(self):
    self._quiet = True
    
messenger = Messenger()

class SupermakeError(Exception):
  _msg = ''

  def __init__(self, msg=''):
    self._msg = msg
    
  def What(self):
    return self._msg

class NotCodeError(SupermakeError):
  pass
  
class OptionsError(SupermakeError):
  pass
  
def fileExtension(basename): #Similar to os.path.basename
  try:
    return basename[basename.rindex('.')+1:]
  except ValueError:
    return False
  
def fileName(basename): #Similar to os.path.dirname
  try:
    return basename[:basename.rindex('.')]
  except ValueError:
    return False
    
def getLibs(header):
  libs = set([])

  if header in libraries:
    libs.update(libraries[header])
  
  for headerpart, library in libraries.items(): #I know, terrible :\. If this was C, I'd so be using gperf for all of this. Would be much more elegant, reliable, error-free, and much faster. I have no problem programmaticly specifying hundreds of headers to gperf.
    if header.startswith(headerpart):
      libs.update(library)
    
  return libs

class CodeFile:
  '''A file of code. Holds all dependencies as well.'''
  def __init__(self, filepath, codeFilesStore):
    '''Check to make sure it is really code, and then build dependency tree, recursively invoking numerous other files along the way'''
    self._directory, basename = os.path.split(os.path.normpath(os.path.relpath(filepath)))
    self._name = fileName(basename)
    self._extension = fileExtension(basename)
    
    if self._extension not in all_code_extensions and os.path.isfile(self.GetFullPath()):
      raise NotCodeError()
  
    self._codeFilesStore = codeFilesStore
    
    self._libraryDependencies = set([])
    self._codeFileDependencies = set([])
    
    self._content = open(self.GetFullPath(), 'r').read()
    
    m = re.findall(r'^#include <(.+?)>', self._content, re.MULTILINE) #Warning, if #includes are commented out using C comments(/* */), they will still be included.  I don't know how to avoid this using regex, probably not possible with just regex. TODO
    for header in m:
      self._libraryDependencies.update(getLibs(header))
    m = re.findall(r'^#include "(.+?)"', self._content, re.MULTILINE)
    for header in m:
      headerDeps = getLibs(header)
      if headerDeps: #Whole thing here is silly. Why doesn't python respect the assignment operator as a real operator with a return value?
        self._libraryDependencies.update(headerDeps)
      else: #Check for local inclusion
        if os.path.exists(header):
          header = header
        elif os.path.exists(os.path.join('include', header)): #hacky
          header = os.path.join('include', header)
        elif os.path.exists(os.path.join('../include', header)):
          header = os.path.join('../include', header)
        else: #otherwise it is like #include "stdlib.h"
          continue
          
        try:
          includeCodeFile = None
          if header in self._codeFilesStore:
            includeCodeFile = self._codeFilesStore[header]
          else:
            includeCodeFile = CodeFile(header, self._codeFilesStore)
            self._codeFilesStore.add(includeCodeFile)
            
          self._codeFileDependencies.add(includeCodeFile)
          self._codeFileDependencies |= includeCodeFile.GetCodeFileDependencies()
          self._libraryDependencies |= includeCodeFile.GetLibraryDependencies()

        except NotCodeError:
          messenger.WarningMessage('Warning: Found unknown included file \''+header+'\'.')

  def GetLanguage(self):
    '''Return the language of the code in this CodeFile, either C or C++.''' 
    if self._extension in cpp_exclusive_extensions:
      return 'c++'
    elif self._extension in c_exclusive_extensions:
      return 'c'
    else:
      return 'unknown'
      
  def GetLibraryDependencies(self):
    return self._libraryDependencies
    
  def GetCodeFileDependencies(self):
    return self._codeFileDependencies
  
  def GetFullPath(self):
    return os.path.join(self._directory, self._name+'.'+self._extension)
    
  def GetName(self):
    return self._name
  
  def GetDirectory(self):
    return self._directory
    
  def GetContent(self):
    return self._content
  
  def __str__(self):
    return 'Codefile: '+self.GetFullPath()
    
class CodeFilesStore(set): #more expensive than it should be. Todo: Separation of path from the codeFile and store the path as a dict key? class Path {str dir; str name; str extension; str fullPath;}
  def __contains__(self, path):
    for codeFile in self:
      if codeFile.GetFullPath() == path:
        return True
    return False
    
  def __getitem__(self, path):
    for codeFile in self:
      if codeFile.GetFullPath() == path:
        return codeFile
    raise KeyError()
    
class Options: #Attempted to overengineer this way too many times, still want to do it again because I don't really like this solution
  '''Commandline options given to Supermake'''
  
  def __init__(self, cliArguments = None):
    self.recurse = False
    self.debug = False
    self.warn = False
    self.optimize = False
    self.overrideLibraryDependencies = False
    self.libraryName = ''
    self.binaryName = ''
    self.objPrefix = ''
    self.customCFlags = []
    self.printMakefile = False
    self.make = False
    self.run = False
    self.autoClean = True
    self.quiet = False
    self.discrete = False
    self.binaryArgs = []
  
    if cliArguments != None:
      self.ParseArguments(cliArguments)
      self.ValidateOptions(cliArguments)
    
  def ValidateOptions(self, arguments):
    '''Users can supply an incompatible combination otherwise valid options, this checks and throws an exception if so.'''
    
    if self.libraryName and self.binaryName:
      raise OptionsError('Both --lib and --binary specified.')
      
    if self.printMakefile and self.make:
      raise OptionsError('--print and --make specified but --print suppresses writing to makefile as required by --make.')

    if self.run and self.libraryName:
      raise OptionsError('--run specified, but you are building a library (--lib specified).')

    if self.run and not self.make:
      raise OptionsError('--run specified, but --run requires --make, which is unspecified.')
      
    if self.binaryArgs and not self.run:
      raise OptionsError('--args specified, but --args requires --run, which is unspecified.')
    
  def ParseArguments(self, arguments):
    if '--args' in arguments:
      self.binaryArgs = arguments[arguments.index('--args')+1:]
      arguments = arguments[:arguments.index('--args')]
    
    for argument in arguments:
      if argument == '--recurse' or argument.upper() == '-R':
        self.recurse = True
        continue
      
      if argument == '--debug':
        self.debug = True
        continue
      
      if argument == '--warn':
        self.warn = True
        continue

      if argument == '--optimize':
        self.optimize = True
        continue
        
      if argument == '--override-depend': #Undocumented
        self.overrideLibraryDependencies = True
        continue
        
      if argument.startswith('--lib='):
        self.libraryName = argument[argument.find('=')+1:]
        basename = os.path.basename(self.libraryName)
        if not basename.startswith('lib'):
          self.libraryName = os.path.join(os.path.dirname(self.libraryName), 'lib'+ basename)
          messenger.NoticeMessage('Prepending "lib" to the library name: "'+self.libraryName+'.so", and "'+self.libraryName+'.a".')
        continue
      
      if argument.startswith('--binary='):
        self.binaryName = argument[argument.find('=')+1:]
        continue
        
      if argument.startswith('--oprefix='): #Undocumented
        self.objPrefix = argument[argument.find('=')+1:]
        continue
        
      if argument.startswith('--custom='):
        self.customCFlags = argument[argument.find('=')+1:].split()
        continue
        
      if argument == '--print':
        self.printMakefile = True
        continue
      
      if argument == '--make':
        self.make = True
        continue

      if argument == '--run':
        self.run = True
        continue
        
      if argument == '--no-autoclean': #Undocumented
        self.autoClean = False
        continue
        
      if argument == '--quiet':
        self.quiet = True
        continue
        
      if argument == '--discrete':
        self.discrete = True
        continue
      
      raise OptionsError('Invalid argument: '+argument)
    
class Supermake:
  '''Supermake :)'''

  def __init__(self):
    try:
      arguments = sys.argv[1:]
      if helpArguments & set(arguments):
        print(usage)
        sys.exit(0)
      self._options = Options(arguments)
      
      if self._options.quiet:
        global messenger
        messenger.SetQuiet()
        
      # Crawl
      self._Crawl()
      
      # Name binary
      self._buildName = self._options.binaryName
      if not self._buildName:
        self._buildName = self._GuessBuildName()
        messenger.WarningMessage('Guessed a binary name '+self._buildName+' (use --binary=NAME to specify this yourself)')
      
      # Create the Makefile :D
      self._makefile = self._GenerateMakefile()
      
      # Print the makefile
      if self._options.printMakefile:
        print(self._makefile)
        return
        
      # Find old makefile to determine if autoclean is needed and to make a backup
      self._oldMakefileName = ''
      if os.path.exists('makefile'):
        self._oldMakefileName = 'makefile'
      elif os.path.exists('Makefile'):
        self._oldMakefileName = 'Makefile'
      
      autoCleanNeeded = False
      if self._oldMakefileName:
        if self._options.autoClean:
          autoCleanNeeded = self._IsAutocleanNeeded()
        
        shutil.copy(self._oldMakefileName, '/tmp/'+self._oldMakefileName+'.old')
        messenger.WarningMessage('Overwriting previous makefile (previous makefile copied to /tmp/'+self._oldMakefileName+'.old in case you weren\'t ready for this!)')
        
      # Write out new makefile
      makefileFile = open('makefile', 'w')
      if not self._options.discrete:
        makefileFile.write(makefileHeader+'\n')
      makefileFile.write(self._makefile)
      makefileFile.close()
    
      # Autoclean
      if autoCleanNeeded:
        messenger.Message('Makefiles critically differ. Executing command: make clean')
        subprocess.call(['make', 'clean'])

      # Compile
      if self._options.make:
        self._Compile()
      
      # Run
      if self._options.run:
        self._Run()
            
    except SupermakeError as e:
      messenger.ErrorMessage(e.What())
  
  def _Crawl(self):
    '''Crawl, picking up all code files to generate a representation of all the code files and their dependencies.'''
    self._sourceCodeFiles = [] #actual source files, .cpp, .c, etc. Supermake makes a distinction between 'header' files and 'source' files.
    self._libraryDependencies = set([])
    codeFilesStore = CodeFilesStore() #Should only be headers

    sourceHierarchy = []
    if self._options.recurse:
      sourceHierarchy = [(directory, filenames) for (directory, unused, filenames) in os.walk('.')]
    else:
      sourceHierarchy = [('.', os.listdir('.'))]

    for directory, filenames in sourceHierarchy:
      for filepath in [os.path.join(directory, filename) for filename in filenames if fileExtension(filename) in all_source_extensions]:
        try:
          self._sourceCodeFiles.append(CodeFile(filepath, codeFilesStore))
        except NotCodeError:
          pass
          
    if not self._sourceCodeFiles:
      raise SupermakeError('No sourcecode found. For help see --help.')
    
    libraryDependencies = set([])
    for codeFile in self._sourceCodeFiles:
      self._libraryDependencies |= codeFile.GetLibraryDependencies()

    self._language = 'c'
    if 'c++' in [sourceCodeFile.GetLanguage() for sourceCodeFile in codeFilesStore] or 'c++' in [sourceCodeFile.GetLanguage() for sourceCodeFile in self._sourceCodeFiles]:
      self._language = 'c++'
    
    if self._options.overrideLibraryDependencies:
      self._libraryDependencies = set([])
    
  def _GuessBuildName(self):
    '''Guess what the project is called based off of heuristics involving surrounding files and directory names.'''
    #Guessing Strategy: Name the binary after the containing folder (if sourcecode is under 'src' path then it is likely it is part of a larger folder named as the projectname)
    #Eg: if the source directory[where Supermake was ran from] is at say ~/projects/DeathStar/src/ then this will create the binary at ~/projects/DeathStar/DeathStar.run
    if os.path.basename(os.getcwd()) == 'src' or os.path.basename(os.getcwd()) == 'source':
      binaryName = os.path.basename(os.path.realpath('..')) + '.run'
      if os.path.isdir('../bin'):
        binaryName = '../bin/'+binaryName
      elif os.path.isdir('./bin'):
        binaryName = './bin/'+binaryName
      else:
        binaryName = '../'+binaryName
      return binaryName

    #Guessing Strategy: Look for the common GPL disclaimer and name it after the specified project name.
    for codeFile in self._sourceCodeFiles:
      m = re.search('\s*(.+) is free software(?:;)|(?::) you can redistribute it and/or modify', codeFile.GetContent())
      if m:
        if m.group(1) != 'This program' and m.group(1) != 'This software':
          return m.group(1)
        break; #breaks no-matter what, because if this file uses the generic one ('This program') then they all will

    #Guessing Strategy: If there is only one source file, name it after that.
    if len(self._sourceCodeFiles) == 1:
      return fileName(self._sourceCodeFiles[0]) + '.run'
    
    #Guessing Strategy: Name it after the parent folder.
    return os.path.basename(os.path.realpath('.'))+'.run'

    #Guessing Strategy: Call it something totally generic.
    return 'program.run'
    
  def _GenerateMakefile(self):
    '''From some abstract options, generate the actual text of a gnu makefile.'''#Not sure removing this from its own unique class was a good idea. Flow of information now isn't explicit... :|
    makefile = ''
    makefile += 'OBJS = '

    makefile += ' '.join(os.path.join(sourceCodeFile.GetDirectory(), self._options.objPrefix+sourceCodeFile.GetName()+'.o') for sourceCodeFile in sorted(self._sourceCodeFiles, key=CodeFile.GetFullPath))
    
    makefile += '\n'

    CFlags = ''
    CFlags += ' -L/usr/local/include'

    #Add the 'include' directory, if in use. 
    if os.path.exists('include'):
      CFlags += ' -Iinclude'
    if os.path.exists('../include'):
      CFlags += ' -I../include'

    CFlags += ' ' + ' '.join(sorted(self._libraryDependencies))

    if self._options.debug:
      CFlags += ' -g -DDEBUG'# -pg' #-lprofiler #You'll have to use `--custom` guys

    if self._options.warn:
      CFlags += ' -Wall'

    if self._options.optimize:
      CFlags += ' -O3'

    if self._options.customCFlags:
      makefile += 'CUSTOMFLAGS = ' + self._options.customCFlags + '\n'
      CFlags += ' $(CUSTOMFLAGS)'

    makefile += 'FLAGS = ' + CFlags + '\n\n'

    compiler = {'c++':'g++','c':'gcc'}[self._language] #python! :D?
    
    if self._options.libraryName:
      makefile += 'all: '+self._options.libraryName+'.a '+self._options.libraryName+'.so\n\n'
      #static library
      makefile += self._options.libraryName+'.a: $(OBJS)\n'
      makefile += '\tar rcs '+self._options.libraryName+'.a $(OBJS)\n\n'

      #shared library
      makefile += self._options.libraryName + '.so: $(OBJS)\n'
      makefile += '\t'+compiler+' -shared -Wl,-soname,'+os.path.basename(self._options.libraryName)+'.so $(OBJS) -o '+self._options.libraryName+'.so\n\n'
    else:
      makefile += self._buildName + ': $(OBJS)\n'
      makefile += '\t'+compiler+' $(OBJS) $(FLAGS) -o '+self._buildName+'\n\n'
      
    for sourceCodeFile in sorted(self._sourceCodeFiles, key=CodeFile.GetFullPath):
      objectFileName = os.path.join(sourceCodeFile.GetDirectory(), self._options.objPrefix+sourceCodeFile.GetName()+'.o')
      makefile += objectFileName+': '+sourceCodeFile.GetFullPath()+' '+' '.join([codeFile.GetFullPath() for codeFile in sorted(sourceCodeFile.GetCodeFileDependencies(), key=CodeFile.GetFullPath)])+'\n'
      makefile += '\t'+compiler+' $(FLAGS) -c '+sourceCodeFile.GetFullPath()+' -o '+objectFileName+'\n\n'

    if self._options.libraryName:
      makefile += 'clean:\n\trm -f '+self._options.libraryName+'.a '+self._options.libraryName+'.so *.o'
    else:
      makefile += 'clean:\n\trm -f '+self._buildName+' *.o'
    
    makefile += '\n'
    
    return makefile
    
  def _IsAutocleanNeeded(self):
    '''Determine if `make clean` is needed (if the previously compiled object files were not compiled the same as they are set to be compiled now).'''
    oldMakefile = open(self._oldMakefileName, 'r').read()
    if oldMakefile == self._makefile:
      needsAutoClean = False
    else:
      #Simply look to see if $FLAGS differs. Simple, faulty, oh well.
      m1 = re.search('^FLAGS = .+$', oldMakefile, re.MULTILINE)
      if not m1:
        return True
      else:
        m2 = re.search('^FLAGS = .+$', self._makefile, re.MULTILINE)
        if m2.group() == m1.group():
          return False
        else:
          return True
    
  def _Compile(self):
    if subprocess.call('make') != 0:
      raise SupermakeError('Compilation failed. Ignoring --run.')
  
  def _Run(self):
    (binaryParentFolder, binaryFilename) = os.path.split(self._buildName)
    
    if self._options.debug:
      cmdargs = ['gdb']
      if self._options.binaryArgs:
        cmdargs.append('--args')
      cmdargs.append('./'+binaryFilename)
      if self._options.binaryArgs:
        cmdargs.extend(self._options.binaryArgs)
    else:
      cmdargs = ['./'+binaryFilename]
      cmdargs.extend(self._options.binaryArgs)
    
    if binaryParentFolder:
      #subprocess.Popen(cmdargs, cwd=binaryParentFolder) #This doesn't properly pipe the terminal stdin to gdb and I don't know how to resolve that, so using os.system for now.
      os.system('cd '+binaryParentFolder+' &&'+' '.join(cmdargs))
    else:
      #subprocess.Popen(cmdargs)
      os.system(' '.join(cmdargs))

if __name__ == '__main__':
  Supermake()
