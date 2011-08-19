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
                  '5' and '4' to the binary when it is ran through --run)

Ex: supermake
Ex: supermake --binary=../bin/myprogram.run --debug --warn --make
Ex: supermake --binary=myprogram.run --make --run.''' #Genning this needs to be automated. DRY etc

helpArguments = set(['--help', '-help', '-h', 'h', '-?', 'help', '/h', '/?', '?', 'HELP'])

makefileHeader = '#This makefile was generated by Supermake. Modify as you wish, but remember that your changes will not be preserved when you run Supermake again. Try to use the available basic options(see --help) to tune it how you desire, if possible. Lastly, remember that Supermake is not suitable for most involved projects\' build requirements.\n\n'

# All of the currently supported libraries. Expanding this list is encouraged!
libraries = { #There are a lot of problems with the current approach, but this is inherit to Supermake's design, unfortunately. I just use the most common installation setups (specifically, whatever ubuntu uses ;)) for these libraries.
  'boost/regex.hpp': ['-lboost_regex'], #Far from extensive boost support...
  'SDL/SDL.h': ['`sdl-config --libs`'],
  'SDL/SDL_image.h': ['-lSDL_image', '`sdl-config --libs`'],
  'SDL/SDL_mixer.h': ['-lSDL_mixer', '`sdl-config --libs`'],
  'SDL/SDL_opengl.h': ['-lGL', '`sdl-config --libs`'],
  'SDL/SDL_ttf.h': ['-lSDL_ttf', '`sdl-config --libs`'],
  'SDL/SDL_net.h': ['-lSDL_net', '`sdl-config --libs`'],
  'SDL/SDL_thread.h': ['-lSDL', '-pthread'],
  'GL/glfw.h': ['-lGL', '-lX11', '-lXrandr', '-pthread', '-lglfw'],
  'Box2D.h': ['-lbox2d'],
  'openssl/sha.h': ['-lcrypto'],
  'gcrypt.h': ['-lgcrypt', '-lgpg-error'],
  'mysql/mysql.h': ['`mysql_config --libs`'],
  'zmq.hpp': ['-lzmq'],
  'zmq.h': ['-lzmq'],
  'OIS/OISInputManager.h': ['-lOIS'],
  'OIS/OISEvents.h': ['-lOIS'],
  'OIS/OISInputManager.h': ['-lOIS'],
  'ncurses.h': ['-lncurses'],
  'GL/gl.h': ['-lGL'],
  'GL/glu.h': ['-lGLU', '-lGL'],
  'GL/glew.h': ['-lGLEW', '-lGLU', '-lGL'],
  'GL/glut.h': ['-lGLUT', '-lGLU', '-lGL'],
  'Horde3D/Horde3D.h': ['-lHorde3D'],
  'Horde3D/Horde3DUtils.h': ['-lHorde3D', '-lHorde3DUtils'],
  'OGRE/OgreCamera.h': ['-lOgreMain'], #There are more base ogre includes than the ones defined here. The thing is though, if it includes any of these (and it will if it uses ogre, for these are required for most/all uses) then it is already taken care of.
  'OGRE/OgreEntity.h': ['-lOgreMain'],
  'OGRE/OgrePrerequisites.h': ['-lOgreMain'],
  'OGRE/OgreRoot.h': ['-lOgreMain'],
  'OGRE/OgreViewport.h': ['-lOgreMain'],
  'OGRE/OgreSceneManager.h': ['-lOgreMain']
}

# constants that should be part of CodeFile but python is a fucking inept piece of shit (I'm not fucking referring to a constant with 'self.' prepending)
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
    
    m = re.findall(r'^#include <(.+?)>$', self._content, re.MULTILINE) #Warning, if #includes are commented out using C comments(/* */), they will still be included.  I don't know how to avoid this using regex, probably not possible with just regex. TODO
    for include in m:
      if include in libraries:
        self._libraryDependencies.update(libraries[include])
    m = re.findall(r'^#include "(.+?)"$', self._content, re.MULTILINE)
    for include in m:
      if include in libraries:
        self._libraryDependencies.update(libraries[include])
      else:
        if os.path.exists(include):
          include = include
        elif os.path.exists(os.path.join('include', include)): #hacky
          include = os.path.join('include', include)
        elif os.path.exists(os.path.join('../include', include)):
          include = os.path.join('../include', include)
        else: #otherwise it is like #include "stdlib.h"
          continue
          
        try:
          includeCodeFile = None
          if include in self._codeFilesStore:
            includeCodeFile = self._codeFilesStore[include]
          else:
            includeCodeFile = CodeFile(include, self._codeFilesStore)
            self._codeFilesStore.add(includeCodeFile)
            
          self._codeFileDependencies.add(includeCodeFile)
          self._codeFileDependencies |= includeCodeFile.GetCodeFileDependencies()
          self._libraryDependencies |= includeCodeFile.GetLibraryDependencies()

        except NotCodeError:
          messenger.WarningMessage('Warning: Found unknown included file \''+include+'\'.')
          
    self._codeFileDependencies = set(sorted(self._codeFileDependencies, key=CodeFile.GetFullPath))

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
  
    
class Makefile:
  '''An abstract representation of a makefile suitable for conversion to a real makefile through Generate()'''  
  
  def __init__(self):
    '''Initialize a representation of a makefile for the project at the current path (ideally, provided directory, but not in first revision), determining all the needed info about the project and its internals needed to proceed to generate the final output makefile.'''
    self._sourceCodeFiles = []
    self._debug = False
    self._warn = False
    self._optimize = False
    self._libraryName = ''
    self._binaryName = ''
    self._objPrefix = ''
    self._customCFlags = set([])
    self._libraryDependencies = set([])
    
    if not self.SourceCodeInDirectory():
      raise SupermakeError('No sourcecode found. For help see --help.')
    
    self.Crawl()
    
  def SourceCodeInDirectory(self):
    return [filePath for filePath in os.listdir('.') if fileExtension(filePath) in all_source_extensions]

  def Crawl(self):
    '''Crawl, picking up all code files to generate a representation of all the code files and their dependencies.'''
    codeFilesStore = CodeFilesStore() #Should only be headers
    
    for filepath in self.SourceCodeInDirectory():
      try:
        self._sourceCodeFiles.append(CodeFile(filepath, codeFilesStore))
      except NotCodeError:
        pass
        
    self._sourceCodeFiles = sorted(self._sourceCodeFiles, key=CodeFile.GetFullPath)
      
    for codeFile in self._sourceCodeFiles:
      self._libraryDependencies |= codeFile.GetLibraryDependencies()
      
    self._libraryDependencies = sorted(self._libraryDependencies)

  def GuessBuildName(self):
    '''Guess what the project is called based off of heuristics involving surrounding files and directory names.'''
    #Guessing Strategy: Name the binary after the containing folder (if sourcecode is under 'src' path then it is likely it is part of a larger folder named as the projectname)
    #Eg: if the source directory[where Supermake was ran from] is at say ~/projects/DeathStar/src/ then this will create the binary at ~/projects/DeathStar/DeathStar.run
    if os.path.basename(os.getcwd()) == 'src' or os.path.basename(os.getcwd()) == 'source':
      binaryName = os.path.basename(os.path.realpath('..')) + '.run'
      if os.path.isdir('../bin'):
        binaryName = '..bin/'+binaryName
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
    if len(self.SourceCodeInDirectory()) == 1:
      return fileName(self.SourceCodeInDirectory()[0]) + '.run'
    
    #Guessing Strategy: Name it after the parent folder.
    return os.path.basename(os.path.realpath('.'))+'.run'

    #Guessing Strategy: Call it something totally generic.
    return 'program.run'
  
  def Generate(self):  
    makefile = ''
    makefile += 'OBJS = '

    makefile += ' '.join(os.path.join(sourceCodeFile.GetDirectory(), self._objPrefix+sourceCodeFile.GetName()+'.o') for sourceCodeFile in self._sourceCodeFiles)
    
    makefile += '\n'

    CFlags = ''
    CFlags += ' -L/usr/local/include'

    #Add the 'include' directory, if in use. 
    if os.path.exists('include'):
      CFlags += ' -Iinclude'
    if os.path.exists('../include'):
      CFlags += ' -I../include'

    CFlags += ' ' + ' '.join(self._libraryDependencies)

    if self._debug:
      CFlags += ' -g -DDEBUG'# -pg' #-lprofiler #You'll have to use `--custom` guys

    if self._warn:
      CFlags += ' -Wall'

    if self._optimize:
      CFlags += ' -O3'

    if self._customCFlags:
      makefile += 'CUSTOMFLAGS = ' + self._customCFlags + '\n'
      CFlags += ' $(CUSTOMFLAGS)'

    makefile += 'FLAGS = ' + CFlags + '\n\n'

    compiler = 'gcc'
    if 'c++' in [sourceCodeFile.GetLanguage() for sourceCodeFile in self._sourceCodeFiles]:
      compiler = 'g++'
    
    if self._libraryName:
      makefile += 'all: '+self._libraryName+'.a '+self._libraryName+'.so\n\n'
      #static library
      makefile += self._libraryName+'.a: $(OBJS)\n'
      makefile += '\tar rcs '+self._libraryName+'.a $(OBJS)\n\n'

      #shared library
      makefile += self._libraryName + '.so: $(OBJS)\n'
      makefile += '\t'+compiler+' -shared -Wl,-soname,'+os.path.basename(self._libraryName)+'.so $(OBJS) -o '+self._libraryName+'.so\n\n'
    else:
      if not self._binaryName:
        self._binaryName = self.GuessBuildName()
        messenger.WarningMessage('Guessed a binary name '+self._binaryName+' (use --binary=NAME to specify this yourself)')
      makefile += self._binaryName + ': $(OBJS)\n'
      makefile += '\t'+compiler+' $(OBJS) $(FLAGS) -o '+self._binaryName+'\n\n'
      
    for sourceCodeFile in self._sourceCodeFiles:
      objectFileName = os.path.join(sourceCodeFile.GetDirectory(), self._objPrefix+sourceCodeFile.GetName()+'.o')
      makefile += objectFileName+': '+sourceCodeFile.GetFullPath()+' '+' '.join([codeFile.GetFullPath() for codeFile in sourceCodeFile.GetCodeFileDependencies()])+'\n'
      makefile += '\t'+compiler+' $(FLAGS) -c '+sourceCodeFile.GetFullPath()+' -o '+objectFileName+'\n\n'

    if self._libraryName:
      makefile += 'clean:\n\trm -f '+self._libraryName+'.a '+self._libraryName+'.so *.o'
    else:
      makefile += 'clean:\n\trm -f '+self._binaryName+' *.o'
    
    makefile += '\n'
    
    return makefile
    
  def SetDebug(self, debug):
    self._debug = debug
    
  def SetWarn(self, warn):
    self._warn = warn
    
  def SetOptimize(self, optimize):
    self._optimize = optimize
    
  def SetLibraryName(self, libraryName):
    self._libraryName = libraryName
    
  def SetBuildName(self, binaryName):
    self._binaryName = binaryName
    
  def GetBuildName(self):
    return self._binaryName
    
  def SetObjPrefix(self, objPrefix):
    self._objPrefix = objPrefix
    
  def SetCustomCFlags(self, customCFlags):
    self._customCFlags = customCFlags
    
  def ClearLibraryDependencies(self):
    self._libraryDependencies = set([])
  
  def __str__(self):
    return self.Generate()
    
class Options: #Attempted to overengineer this way too many times, still want to do it again because I don't really like this solution #struct
  '''Commandline options given to Supermake'''
  
  def __init__(self, cliArguments = None):
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
          messager.Message('Prepending "lib" to the library name: "'+self.libraryName+'.so", and "'+self.libraryName+'.a".')
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
  
  _options = Options()

  def __init__(self):
    try:
      arguments = sys.argv[1:]
      if helpArguments & set(arguments):
        print(usage)
        sys.exit(0)
      self._options = Options(arguments)
      
      makefile = Makefile()
      
      makefile.SetDebug(self._options.debug)
      makefile.SetWarn(self._options.warn)
      makefile.SetOptimize(self._options.optimize)
      makefile.SetBuildName(self._options.binaryName)
      makefile.SetLibraryName(self._options.libraryName)
      makefile.SetObjPrefix(self._options.objPrefix)
      if self._options.overrideLibraryDependencies:
        makefile.ClearLibraryDependencies()
      makefile.SetCustomCFlags(self._options.customCFlags)
      
      if self._options.quiet:
        global messenger
        messenger.SetQuiet()
      
      makefileContent = makefile.Generate()
      
      if self._options.printMakefile:
        print(makefileContent)
        return
        

      # Determine if  `make clean` is needed
      needsAutoClean = False
      if os.path.exists('makefile') or os.path.exists('Makefile'):
        oldMakefileFilename = ''
        if os.path.exists('makefile'):
          oldMakefileFilename = 'makefile'
        elif os.path.exists('Makefile'):
          oldMakefileFilename = 'Makefile'

        if self._options.autoClean:
          oldMakefileContent = open(oldMakefileFilename, 'r').read()
          if oldMakefileContent == makefileContent:
            needsAutoClean = False
          else:
            #Simply look to see if $FLAGS differ. Simple, faulty, oh well.
            m1 = re.search('^FLAGS = .+$', oldMakefileContent, re.MULTILINE)
            if not m1:
              needsAutoClean = True
            m2 = re.search('^FLAGS = .+$', makefileContent, re.MULTILINE)
            if m2.group() == m1.group():
              needsAutoClean = False
            else:
              needsAutoClean = True

        shutil.copy(oldMakefileFilename, '/tmp/'+oldMakefileFilename+'.old')
        messenger.WarningMessage('Overwriting previous makefile (previous makefile copied to /tmp/'+oldMakefileFilename+'.old in case you weren\'t ready for this!)')

      makefileFile = open('makefile', 'w')
      if not self._options.discrete:
        makefileFile.write(makefileHeader+'\n')
      makefileFile.write(makefileContent)
      makefileFile.close()

      if needsAutoClean:
        messenger.Message('Makefiles critically differ. Executing command: make clean')
        subprocess.call(['make', 'clean'])

      # Compile
      if self._options.make:
        if subprocess.call('make') != 0:
          if self._options.run:
            messenger.Message('Compilation failed, ignoring --run.')
            return
        
        # Run
        if self._options.run:
          (binaryParentFolder, binaryFilename) = os.path.split(makefile.GetBuildName())
          
          if self._options.debug:
            cmdargs = ['gdb']
            if self._options.binaryArgs:
              cmdargs.append('--args')
            cmdargs.append('./'+binaryFilename)
            if self._options.binaryArgs:
              cmdargs.extend(self._options.binaryArgs)
            
            if binaryParentFolder:
              #subprocess.Popen(cmdargs, cwd=binaryParentFolder) #This doesn't properly pipe the terminal stdin to gdb and I don't know how to resolve that, so using os.system for now.
              os.system('cd '+binaryParentFolder+' '+' '.join(cmdargs))
            else:
              #subprocess.Popen(cmdargs)
              os.system(' '.join(cmdargs))
          else:
            cmdargs = ['./'+binaryFilename]
            cmdargs.extend(self._options.binaryArgs)
          
            if binaryParentFolder:
              subprocess.Popen(cmdargs, cwd=binaryParentFolder)
            else:
              subprocess.Popen(cmdargs)
            
    except SupermakeError as e:
      messenger.ErrorMessage(e.What()) 
 
if __name__ == '__main__':
  Supermake()
