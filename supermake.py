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
# Supermake is created by personalcomputer <https://github.com/personalcomputer>

import re
import os
import sys
import subprocess
import tempfile

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
  --library=NAME  Build the project as a library instead. NAME specifies the
                  name and path of the library (Ex: ../lib/libamazing), similar
                  to --binary. This automatically creates both shared (.so) and
                  static (.a) library types, so do not specify an extension in
                  NAME.
  --clang         Prefer the clang (LLVM) compiler instead of gcc.
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
libraries = { #There are a lot of problems with the current approach, but most are inherit to Supermake's design, unfortunately. I just use the most common installation setups (specifically, whatever ubuntu uses ;)) for these libraries. #And, please don't run and tell me 'oh but the standard says...', 'cflags and libs are seperate arguments for a reason...', etc, Supermake is for the general case, nothing more. If anything presents a problem later it will be looked into and either acknkowledged as an unfixable design problem, or fixed.
  'Box2D.h': ['-lbox2d'],
  'openssl/sha.h': ['-lcrypto'],
  'gcrypt.h': ['-lgcrypt', '-lgpg-error'],
  'mysql/mysql.h': ['`mysql_config --cflags --libs`'],
  'sqlite3.h': ['-lsqlite3'],
  'sqlite.h': ['-lsqlite'],
  'zmq.h': ['-lzmq'],
  'ncurses.h': ['-lncurses'],
  'google/profiler.h': ['-lprofiler'],
  'pthread.h': ['-pthread'],
  'math.h': ['-lm'],
  'glib.h': ['`pkg-config --cflags --libs glib-2.0`'],
  'SFML': ['-lsfml-graphics -lsfml-window -lsfml-system'],
  'png': ['`libpng-config --cflags --ldflags --libs`'],
  
  'SDL/': ['`sdl-config --cflags --libs`'],
  'SDL/SDL_image.h': ['-lSDL_image'],
  'SDL/SDL_mixer.h': ['-lSDL_mixer'],
  'SDL/SDL_opengl.h': ['-lGL'],
  'SDL/SDL_ttf.h': ['-lSDL_ttf'],
  'SDL/SDL_net.h': ['-lSDL_net'],
  'SDL/SDL_thread.h': ['-pthread'],
  
  'GL/': ['-lGL'],
  'GL/glfw.h': ['`pkg-config --cflags --libs libglfw`'],
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
  
  'gtk/': ['`pkg-config --cflags --libs gtk+-3.0`'], #Sorry, no 2.x support. Supermake simply is not capable or designed to support multiple library versions. (but it will only take changing a single character if you need it..)
  
  'gtkmm': ['`pkg-config gtkmm-3.0 --cflags --libs`'],
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

make_cmd = {'nt':'mingw32-make', 'posix':'make'}[os.name]
forcedelete_cmd = {'nt':'del', 'posix':'rm -f'}[os.name]
executable_extension = {'nt':'.exe', 'posix':''}[os.name]

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

legalShellCharactersPattern = {'posix':r'([^-0-9a-zA-Z_./\n])', 'nt':r'([^-0-9a-zA-Z_./\\\n])'}[os.name]

def shellEscape(string):
  return re.sub(legalShellCharactersPattern, r'\\\1', string);
  #Q: Why not just use quotes? A: make does not like quotes.
            
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

    self._fullPath = os.path.join(self._directory, self._name+'.'+self._extension)
    
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
      if headerDeps: #Why doesn't python respect the assignment operator as a real operator with a return value?
        self._libraryDependencies.update(headerDeps)
      else: #Check for local inclusion
        header = os.path.relpath(os.path.join(self._directory, header))
        if os.path.exists(header):
          header = header
        elif os.path.exists(os.path.join('include', header)): #hacky
          header = os.path.join('include', header)
        elif os.path.exists(os.path.join('..','include',header)):
          header = os.path.join('..','include',header)
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
          self._codeFileDependencies.update(includeCodeFile.GetCodeFileDependencies())
          self._libraryDependencies.update(includeCodeFile.GetLibraryDependencies())

        except NotCodeError:
          #messenger.WarningMessage('Found unknown included file \''+header+'\'.')
          pass

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
    return self._fullPath
    
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
    self.prefix = ''
    self.customCFlags = ''
    self.printMakefile = False
    self.make = False
    self.run = False
    self.clang = False
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
      raise OptionsError('Both --library and --binary specified.')
      
    if self.printMakefile and self.make:
      raise OptionsError('--print and --make specified but --print suppresses writing to makefile as required by --make.')

    if self.run and self.libraryName:
      raise OptionsError('--run specified, but you are building a library (--library specified).')

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
        
      if argument.startswith('--library=') or argument.startswith('--lib='):
        self.libraryName = argument[argument.find('=')+1:]
        libdirname, libbasename = os.path.split(self.libraryName)
        if libbasename.endswith('.a') or libbasename.endswith('.so'):
          self.libraryName = os.path.join(libdirname, fileName(libbasename))
          messenger.NoticeMessage('Library file extension unnecessarily specified. Both \''+self.libraryName+'.so\', and \''+self.libraryName+'.a\'. will be created.')
          libdirname, libbasename = os.path.split(self.libraryName)
        if not libbasename.startswith('lib'):
          self.libraryName = os.path.join(libdirname, 'lib'+ libbasename)
          messenger.NoticeMessage('Prepending \'lib\' to the library name: \''+self.libraryName+'.so\', and \''+self.libraryName+'.a\'.')
        continue
      
      if argument.startswith('--binary='):
        self.binaryName = argument[argument.find('=')+1:]
        continue
        
      if argument.startswith('--prefix='): #Undocumented
        self.prefix = argument[argument.find('=')+1:]
        continue
        
      if argument.startswith('--custom='):
        if self.customCFlags:
          self.customCFlags += ' '
        self.customCFlags += argument[argument.find('=')+1:]
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
        
      if argument == '--quiet':
        self.quiet = True
        continue

      if argument == '--clang':
        self.clang = True
        continue
        
      if argument == '--discrete':
        self.discrete = True
        continue
      
      raise OptionsError('Unrecognized argument: \''+argument+'\' (For help, see --help)')
    
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
      if not self._buildName and not self._options.libraryName:
        self._buildName = self._GuessBuildName()
        self._buildName = os.path.join(os.path.dirname(self._buildName), self._options.prefix+os.path.basename(self._buildName))
        messenger.WarningMessage('Guessed a binary name \''+self._buildName+'\' (use --binary=NAME to specify this yourself)')
      
      # Create the Makefile :D
      self._makefile = self._GenerateMakefile()
      
      # Print the makefile
      if self._options.printMakefile:
        print(self._makefile)
        return
        
      # Find old makefile to determine if autoclean is needed and to make a backup
      self._oldMakefileName = ''
      if os.path.exists(self._options.prefix+'makefile'):
        self._oldMakefileName = self._options.prefix+'makefile'
      elif os.path.exists(self._options.prefix+'Makefile'):
        self._oldMakefileName = self._options.prefix+'Makefile'
      
      autoCleanNeeded = False
      if self._oldMakefileName:
        autoCleanNeeded = self._IsAutocleanNeeded()

        oldMakefileBackupFd, oldMakefileBackupPath = tempfile.mkstemp(prefix='old_'+self._oldMakefileName+'_', text=True)
        oldMakefileBackupFile = os.fdopen(oldMakefileBackupFd, 'w')

       	oldMakefileFile = open(self._oldMakefileName, 'r')
        oldMakefileBackupFile.write(oldMakefileFile.read())

        oldMakefileFile.close()
        oldMakefileBackupFile.close()

        messenger.WarningMessage('Overwriting previous makefile (previous makefile copied to \''+oldMakefileBackupPath+'\' in case you weren\'t ready for this!)')
      else:
        for filename in os.listdir('.'):
          if filename.endswith('.o'):
            autoCleanNeeded = True
            break
      # Write out new makefile
      makefileFile = open(self._options.prefix+'makefile', 'w')
      if not self._options.discrete:
        makefileFile.write(makefileHeader+'\n')
      makefileFile.write(self._makefile)
      makefileFile.close()
    
      # Autoclean
      if autoCleanNeeded:
        if self._oldMakefileName:
          messenger.NoticeMessage('Makefiles critically differ. Cleaning old build files.')
        else:
          messenger.NoticeMessage('Cleaning old build files.')
        if self._options.prefix:
          os.system(make_cmd+' -f '+self._options.prefix+'makefile clean')
        else:
          os.system(make_cmd+' clean')

      # Compile
      compilationSuccesful = False
      if self._options.make:
         compilationSuccesful = self._Compile()
      
      # Run
      if self._options.run:
        if not compilationSuccesful:
          raise SupermakeError('Compilation failed. Ignoring --run.')
        self._Run()
        
      if not compilationSuccesful:
        sys.exit(1);
            
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
      raise SupermakeError('No sourcecode found. For help, see --help.')
    
    libraryDependencies = set([])
    for codeFile in self._sourceCodeFiles:
      self._libraryDependencies.update(codeFile.GetLibraryDependencies())

    self._language = 'c'
    if 'c++' in [sourceCodeFile.GetLanguage() for sourceCodeFile in codeFilesStore] or 'c++' in [sourceCodeFile.GetLanguage() for sourceCodeFile in self._sourceCodeFiles]:
      self._language = 'c++'
    
    if self._options.overrideLibraryDependencies:
      self._libraryDependencies = set([])
    
  def _GuessBuildName(self):
    '''Guess what the project is called based off of heuristics involving surrounding files and directory names.'''
    binaryName = ''
    
    if not binaryName:
      #Guessing Strategy: Name the binary after the containing folder (if sourcecode is under 'src' path then it is likely it is part of a larger folder named as the projectname)
      #Eg: if the source directory[where Supermake was ran from] is at say ~/projects/DeathStar/src/ then this will create the binary at ~/projects/DeathStar/DeathStar.run
      if os.path.basename(os.getcwd()) == 'src' or os.path.basename(os.getcwd()) == 'source':
        binaryName = os.path.basename(os.path.realpath('..'))
        if os.path.isdir(os.path.join('..','bin')):
          binaryName = os.path.join('..','bin',binaryName)
        elif os.path.isdir('bin'):
          binaryName = os.path.join('bin',binaryName)
        else:
          binaryName = os.path.join('..',binaryName)
        
    if not binaryName:
      #Guessing Strategy: Look for the common GPL disclaimer and name it after the specified project name.
      for codeFile in self._sourceCodeFiles:
        m = re.search('\s*(.+) is free software(?:;)|(?::) you can redistribute it and/or modify', codeFile.GetContent())
        if m:
          if m.group(1) != 'This program' and m.group(1) != 'This software':
            binaryName = m.group(1)
            break

    if not binaryName:
      #Guessing Strategy: If there is only one source file, name it after that. (unless it is main.cpp)
      if len(self._sourceCodeFiles) == 1 and self._sourceCodeFiles[0].GetName() != 'main':
        binaryName = self._sourceCodeFiles[0].GetName() + executable_extension
    
    if not binaryName:
      #Guessing Strategy: Name it after the parent folder.
      binaryName = os.path.basename(os.path.realpath('.'))

    if not binaryName:
      #Guessing Strategy: Call it something totally generic.
      binaryName = 'program'
      
    return binaryName + executable_extension
    
  def _GenerateMakefile(self):
    '''From some abstract options, generate the actual text of a gnu makefile.'''#Not sure removing this from its own unique class was a good idea. Flow of information now isn't explicit... :|

    makefile = ''
    makefile += 'OBJS = '

    makefile += ' '.join(shellEscape(os.path.join(sourceCodeFile.GetDirectory(), self._options.prefix+sourceCodeFile.GetName()+'.o')) for sourceCodeFile in sorted(self._sourceCodeFiles, key=CodeFile.GetFullPath))
    
    makefile += '\n'

    CFlags = ''
    if os.name == 'posix':
      CFlags += ' -L/usr/local/include'

    #Add the 'include' directory, if in use. 
    if os.path.exists('include') and os.path.isdir('include'):
      CFlags += ' -Iinclude'
    if os.path.exists(os.path.join('..','include')) and os.path.isdir(os.path.join('..','include')):
      CFlags += ' -I'+os.path.join('..','include')
     
    #Add the 'lib' directory, if in use.
    additionalLibrarySearchPaths = '' #CLI args passed to compiler later on
    additionalLibrarySearchPath = ''
    if os.path.exists(os.path.join('..','lib')) and os.path.isdir(os.path.join('..','lib')) and os.listdir(os.path.join('..','lib')):
      additionalLibrarySearchPath = os.path.join('..','lib')
    elif os.path.exists('lib') and os.path.isdir('lib') and os.listdir('lib'):
      additionalLibrarySearchPath = 'lib'
    if additionalLibrarySearchPath:
      CFlags += ' -L'+additionalLibrarySearchPath
      additionalLibrarySearchPaths += ' -Wl,-rpath,'+os.path.relpath(additionalLibrarySearchPath, os.path.dirname(self._buildName))
      #Add the libraries in there. #This doesn't really belong here in GenerateMakefile, none of these include directory/lib directory related things do but it is the best simple solution I've thought of. Not gonig to go back and reinvent the entire library system when the only use here is a small special case.
      for library in sorted(os.listdir(additionalLibrarySearchPath)):
        m = re.match('lib([^\.]+)\.(?:so|a)',library)
        if m:
          self._libraryDependencies.add('-l'+m.group(1)) #Should not be adding to self._libraryDependencies because GenerateMakefile shouldn't modify state (it is jsut taking the already defined abstract makefile and converting it into what gmake reads). See above for the root problem.
    
    CFlags += ' ' + ' '.join(sorted(self._libraryDependencies))

    if self._options.debug:
      CFlags += ' -g -DDEBUG'# -pg'# -lprofiler' #You'll have to use `--custom` guys

    if self._options.warn:
      CFlags += ' -Wall'

    if self._options.optimize:
      CFlags += ' -O3'

    if self._options.customCFlags:
      CFlags += ' ' + self._options.customCFlags

    makefile += 'FLAGS =' + CFlags + '\n\n'

    if self._options.clang:
      compiler = 'clang'
    else:
      compiler = {'c++':'g++','c':'gcc'}[self._language]
    
    if self._options.libraryName:
      makefile += 'all: '+shellEscape(self._options.libraryName)+'.a '+shellEscape(self._options.libraryName)+'.so\n\n'
      #static library
      makefile += shellEscape(self._options.libraryName)+'.a: $(OBJS)\n'
      makefile += '\tar rcs '+shellEscape(self._options.libraryName)+'.a $(OBJS)\n\n'
      
      #shared library
      makefile += shellEscape(self._options.libraryName) + '.so: $(OBJS)\n'
      makefile += '\t'+compiler+' -shared -Wl,-soname,'+shellEscape(os.path.basename(self._options.libraryName))+'.so $(OBJS) -o '+shellEscape(self._options.libraryName)+'.so\n\n'
    else:
      makefile += shellEscape(self._buildName) + ': $(OBJS)\n'
      makefile += '\t'+compiler+' $(OBJS) $(FLAGS)'+additionalLibrarySearchPaths+' -o '+shellEscape(self._buildName)+'\n\n'
      
    for sourceCodeFile in sorted(self._sourceCodeFiles, key=CodeFile.GetFullPath):
      objectFileName = shellEscape(os.path.join(sourceCodeFile.GetDirectory(), self._options.prefix+sourceCodeFile.GetName()+'.o'))
      makefile += objectFileName+': '+shellEscape(sourceCodeFile.GetFullPath())+' '+' '.join([shellEscape(codeFile.GetFullPath()) for codeFile in sorted(sourceCodeFile.GetCodeFileDependencies(), key=CodeFile.GetFullPath)])+'\n'
      makefile += '\t'+compiler+' $(FLAGS) -c '+shellEscape(sourceCodeFile.GetFullPath())+' -o '+objectFileName+'\n\n'

    makefile += 'clean:\n\t'+forcedelete_cmd
    if self._options.libraryName:
      makefile +=' '+shellEscape(self._options.libraryName)+'.a '+shellEscape(self._options.libraryName)+'.so *.o'
    else:
      makefile +=' '+shellEscape(self._buildName)+' $(OBJS)'
    
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
    cmd = [make_cmd]
    if self._options.prefix:
      cmd.extend(['-f',shellEscape(self._options.prefix+'makefile')])
    return (subprocess.call(cmd) == 0)
   
  def _Run(self):
    (binaryParentFolder, binaryFilename) = os.path.split(self._buildName)
    
    executeBinaryCmd = binaryFilename
    if os.name == 'posix':
      executeBinaryCmd = './'+executeBinaryCmd
    executeBinaryCmd = shellEscape(executeBinaryCmd)
    
    if self._options.debug:
      cmdargs = ['gdb']
      if self._options.binaryArgs:
        cmdargs.append('--args')
      cmdargs.append(executeBinaryCmd)
      if self._options.binaryArgs:
        cmdargs.extend(self._options.binaryArgs)
    else:
      cmdargs = [executeBinaryCmd]
      cmdargs.extend(self._options.binaryArgs)
    
    if binaryParentFolder:
      #subprocess.Popen(cmdargs, cwd=binaryParentFolder) #This doesn't properly pipe the terminal stdin to gdb and I don't know how to resolve that, so using os.system for now.
      os.system('cd '+shellEscape(binaryParentFolder)+' &&'+' '.join(cmdargs))
    else:
      #subprocess.Popen(cmdargs)
      os.system(' '.join(cmdargs))

if __name__ == '__main__':
  Supermake()
