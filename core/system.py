
"""
Functions relating to files, references, and system calls.

In particular, the system module contains the functionality of maya.cmds.file. The file command should not be imported into
the default namespace because it conflicts with python's builtin file class. Since the file command has so many flags, 
we decided to kill two birds with one stone: by breaking the file command down into multiple functions -- one for each 
primary flag -- the resulting functions are more readable and allow the file command's functionality to be used directly
within the pymel namespace.   

for example, instead of this:
    
    >>> expFile = cmds.file( exportAll=1, preserveReferences=1 )
    
you can do this:

    >>> expFile = exportAll( preserveReferences=1)
    
some of the new commands were changed slightly from their flag name to avoid name clashes and to add to readability:

    >>> importFile( expFile )  # flag was called import, but that's a python keyword
    >>> createReference( expFile )

Also, note that the 'type' flag is set automatically for you when your path includes a '.mb' or '.ma' extension.

"""


import pmtypes.pmcmds as cmds
#import maya.cmds as cmds
import maya.OpenMaya as OpenMaya


import pymel.util as util
import pmtypes.factories as _factories
from pmtypes.factories import createflag, add_docs
from pymel.util.scanf import fscanf


import sys
try:
    from luma.filepath import filepath as Filepath
    pathClass = Filepath
except:
    import pmtypes.path
    pathClass = pmtypes.path.path
    


def _getTypeFromExtension( path ):
    return {
        '.ma' : 'mayaAscii',
        '.mb' :    'mayaBinary'
    }[Path(path).ext]


def feof( fileid ):
    """Reproduces the behavior of the mel command of the same name. if writing pymel scripts from scratch, 
    you should use a more pythonic construct for looping through files:
    
    >>> f = open('myfile.txt')
    >>> for line in f:
    >>>     print line
    
    This command is provided for python scripts generated by py2mel"""
    
    os = fileid.tell()
    f.seek(0,2) # goto end of file
    end = fileid.tell() #get final position
    fileid.seek(pos)
    return pos == end


@add_docs( 'file', 'sceneName')
def sceneName():
    return Path( OpenMaya.MFileIO.currentFile() )    

def listNamespaces():
    """Returns a list of the namespaces of referenced files.
    REMOVE In Favor of listReferences('dict') ?""" 
    try:
        return [ cmds.file( x, q=1, namespace=1) for x in cmds.file( q=1, reference=1)  ]
    except:
        return []





def listReferences(type='list'):
    """file -q -reference
    By default returns a list of reference files as FileReference classes. The optional type argument can be passed a 'dict'
    (or dict object) to return the references as a dictionary with namespaces as keys and References as values.
    
    Untested: multiple references with no namespace...
    """
    
    # dict
    if type in ['dict', dict]:
        res = {}
        try:
            for x in cmds.file( q=1, reference=1):
                res[cmds.file( x, q=1, namespace=1)] = FileReference(x)
        except: pass
        return res
    
    # list
    return map( FileReference,cmds.file( q=1, reference=1) )

def getReferences(reference=None, recursive=False):
    res = {}    
    if reference is None:
        try:
            for x in cmds.file( q=1, reference=1):
                ref = FileReference(x)
                res[cmds.file( x, q=1, namespace=1)] = ref
                if recursive:
                    res.update( ref.subReferences() )
        except: pass
    else:
        try:
            for x in cmds.file( self, q=1, reference=1):
                res[cmds.file( x, q=1, namespace=1)] = FileReference(x)
        except: pass
    return res    

#-----------------------------------------------
#  Workspace Class
#-----------------------------------------------

class WorkspaceEntryDict(object):
    def __init__(self, entryType):
        self.entryType = entryType
    def __getitem__(self, item):
        res = cmds.workspace( item, **{'q' : 1, self.entryType + 'Entry' : 1 } )
        if not res:
            raise KeyError, item
        return res
    def __setitem__(self, item, value):
        return cmds.workspace( **{self.entryType: [item, value] } )
    def __contains__(self, key):
        return key in self.keys()
    def items(self):    
        entries = util.listForNone( cmds.workspace( **{'q' : 1, self.entryType : 1 } ) )
        res = []
        for i in range( 0, len(entries), 2):
            res.append( (entries[i], entries[i+1] ) )
        return res
    def keys(self):    
        return cmds.workspace( **{'q' : 1, self.entryType + 'List': 1 } )
    def values(self):    
        entries = util.listForNone( cmds.workspace( **{'q' : 1, self.entryType : 1 } ) )
        res = []
        for i in range( 0, len(entries), 2):
            res.append( entries[i+1] )
        return res
    def get(self, item, default=None):
        try:
            return self.__getitem__(item)
        except KeyError:
            return default
    has_key = __contains__
        
    
class Workspace(object):
    """
    This class is designed to lend more readability to the often confusing workspace command.
    The four types of workspace entries (objectType, fileRule, renderType, and variable) each
    have a corresponding dictiony for setting and accessing these mappings.
    
        >>> from pymel import *
        >>> workspace.renderTypes['audio']
        sound
        >>> workspace.renderTypes.keys()
        [u'3dPaintTextures', u'audio', u'clips', u'depth', u'images', u'iprImages', u'lights', u'mentalRay', u'particles', u'renderScenes', u'sourceImages', u'textures']
        >>> 'DXF' in workspace.fileRules
        True
        >>> workspace.fileRules['DXF']
        data
        >>> workspace.fileRules['super'] = 'data'
        >>> workspace.fileRules.get( 'foo', 'data' )
        data
        
    the workspace dir can be confusing because it works by maintaining a current working directory that is persistent
    between calls to the command.  In other words, it works much like the unix 'cd' command, or python's 'os.chdir'.
    In order to clarify this distinction, the names of these flags have been changed in their class method counterparts
    to resemble similar commands from the os module.
    
    old way (still exists for backward compatibility)
        >>> workspace(edit=1, dir='mydir')
        >>> workspace(query=1, dir=1)
        >>> workspace(create='mydir')
    
    new way    
        >>> workspace.chdir('mydir')
        >>> workspace.getcwd()    
        >>> workspace.mkdir('mydir')
    
    All paths are returned as an pymel.core.system.Path class, which makes it easy to alter or join them on the fly.    
        >>> workspace.path / workspace.fileRules['DXF']
        /Users/chad/Documents/maya/projects/default/path
        
    """
    __metaclass__ = util.Singleton
    
    objectTypes = WorkspaceEntryDict( 'objectType' )
    fileRules     = WorkspaceEntryDict( 'fileRule' )
    renderTypes = WorkspaceEntryDict( 'renderType' )
    variables     = WorkspaceEntryDict( 'variable' )
    
    def __init__(self):
        self.objectTypes = WorkspaceEntryDict( 'objectType' )
        self.fileRules     = WorkspaceEntryDict( 'fileRule' )
        self.renderTypes = WorkspaceEntryDict( 'renderType' )
        self.variables     = WorkspaceEntryDict( 'variable' )
    
    @classmethod
    def open(self, workspace):
        return cmds.workspace( workspace, openWorkspace=1 )
    @classmethod
    def save(self):
        return cmds.workspace( saveWorkspace=1 )
    @classmethod
    def update(self):
        return cmds.workspace( update=1 )
    @classmethod
    def new(self, workspace):
        return cmds.workspace( workspace, newWorkspace=1 )        
    @classmethod
    def getName(self):
        return cmds.workspace( q=1, act=1 )

    @classmethod
    def getPath(self):
        return Path(cmds.workspace( q=1, fn=1 ))
    
    @classmethod
    def chdir(self, newdir):
        return cmds.workspace( dir=newdir )
    @classmethod
    def getcwd(self):
        return Path(cmds.workspace( q=1, dir=1 ))
    @classmethod
    def mkdir(self, newdir):
        return cmds.workspace( cr=newdir )

    name = property( lambda x: cmds.workspace( q=1, act=1 ) )        
    path = property( lambda x: Path(cmds.workspace( q=1, fn=1 ) ) )
            
    def __call__(self, *args, **kwargs):
        """provides backward compatibility with cmds.workspace by allowing an instance
        of this class to be called as if it were a function"""
        return cmds.workspace( *args, **kwargs )

workspace = Workspace()

#-----------------------------------------------
#  FileInfo Class
#-----------------------------------------------

class FileInfo( object ):
    """
    store and get custom data specific to this file:
    
        >>> fileInfo['lastUser'] = env.user()
        
    if the python structures have valid __repr__ functions, you can
    store them and reuse them later:
    
        >>> fileInfo['cameras'] = str( ls( cameras=1) )
        >>> camList = eval(fileInfo['cameras'])
        >>> camList[0]
        # Result: frontShape #
        >>> camList[0].getFocalLength()  # it's still a valid pymel class
        # Result: 35.0 #
    
    for backward compatibility it retains it's original syntax as well:
        
        >>> fileInfo( 'myKey', 'myData' )
        
    """
    __metaclass__ = util.Singleton
    
    def __contains__(self, item):
        return item in self.keys()
        
    def __getitem__(self, item):
        return dict(self.items())[item]
        
    def __setitem__(self, item, value):
        cmds.fileInfo( item, value )
    
    def __call__(self, *args, **kwargs):
        if kwargs.get('query', kwargs.get('q', False) ):
            return self.items()
        else:
            cmds.FileInfo( *args, **kwargs )
            
    def items(self):
        res = cmds.fileInfo( query=1)
        newRes = []
        for i in range( 0, len(res), 2):
            newRes.append( (res[i], res[i+1]) )
        return newRes
        
    def keys(self):
        res = cmds.fileInfo( query=1)
        newRes = []
        for i in range( 0, len(res), 2):
            newRes.append(  res[i] )
        return newRes
            
    def values(self):
        res = cmds.fileInfo( query=1)
        newRes = []
        for i in range( 0, len(res), 2):
            newRes.append( res[i+1] )
        return newRes
    
    def pop(self, *args):
        if len(args) > 2:
            raise TypeError, 'pop expected at most 2 arguments, got %d' % len(args)
        elif len(args) < 1:
            raise TypeError, 'pop expected at least 1 arguments, got %d' % len(args)
        
        if args[0] not in self.keys():
            try:
                return args[1]
            except IndexError:
                raise KeyError, args[0]
                    
        cmds.fileInfo( rm=args[0])
    
    has_key = __contains__    
fileInfo = FileInfo()



#-----------------------------------------------
#  File Classes
#-----------------------------------------------
    
class Path(pathClass):
    """A basic Maya file class. it gets most of its power from the path class written by Jason Orendorff.
    see path.py for more documentation."""
    def __repr__(self):
        return "%s('%s')" % (self.__class__.__name__, self)
    
    writable = _factories.makeQueryFlagMethod( cmds.file, 'writable' )
    type = _factories.makeQueryFlagMethod( cmds.file, 'type' )
    setSubType = _factories.makeQueryFlagMethod( cmds.file, 'subType', 'setSubType')
   
class CurrentFile(Path):
    getRenameToSave = classmethod( _factories.makeQueryFlagMethod( cmds.file, 'renameToSave', 'getRenameToSave'))
    setRenameToSave = classmethod( _factories.makeCreateFlagMethod( cmds.file, 'renameToSave', 'setRenameToSave'))
    anyModified = classmethod( _factories.makeQueryFlagMethod( cmds.file, 'anyModified'))
    @classmethod
    @add_docs( 'file', 'lockFile')
    def lock(self):
        return cmds.file( lockFile=True)
    
    @classmethod
    @add_docs( 'file', 'lockFile')
    def unlock(self):
        return cmds.file( lockFile=False)  
    isModified = classmethod( _factories.makeQueryFlagMethod( cmds.file, 'modified', 'isModified'))
    setModified = classmethod( _factories.makeCreateFlagMethod( cmds.file, 'modified', 'setModified'))
    
    @classmethod
    @add_docs( 'file', 'sceneName')
    def name(self):
        return Path( OpenMaya.MFileIO.currentFile() ) 
  
        
class FileReference(Path):
    """A class for manipulating references which inherits Path and path.  you can create an 
    instance by supplying the path to a reference file, its namespace, or its reference node to the 
    appropriate keyword. The namespace and reference node of the reference can be retreived via 
    the namespace and refNode properties. The namespace property can also be used to change the namespace
    of the reference. 
    
    Use listRefences command to return a list of references as instances of the FileReference class.
    
    It is important to note that instances of this class will have their copy number stripped off
    and stored in an internal variable upon creation.  This is to maintain compatibility with the numerous methods
    inherited from the path class which requires a real file path. When calling built-in methods of FileReference, 
    the path will automatically be suffixed with the copy number before being passed to maya commands, thus ensuring 
    the proper results in maya as well. 
    """
    
    def __new__(cls, path=None, namespace=None, refnode=None):
        def create(path):
            def splitCopyNumber(path):
                """Return a tuple with the path and the copy number. Second element will be None if no copy number"""
                buf = path.split('{')
                try:
                    return ( buf[0], int(buf[1][:-1]) )
                except:
                    return (path, None)
                    
            path, copyNumber = splitCopyNumber(path)
            self = Path.__new__(cls, path)
            self._copyNumber = copyNumber
            return self
            
        if path:
            return create(path)
        if namespace:
            for path in map( FileReference, cmds.file( q=1, reference=1) ):
                 if path.namespace == namespace:
                    return create(path)
            raise ValueError, "Namespace '%s' does not match any found in scene" % namespace
        if refnode:
            path = cmds.referenceQuery( refnode, filename=1 )
            return create(path)
        raise ValueError, "Must supply at least one argument"    

    def subReferences(self):
        namespace = self.namespace + ':'
        res = {}
        try:
            for x in cmds.file( self, q=1, reference=1):
                res[namespace + cmds.file( x, q=1, namespace=1)] = pymel.FileReference(x)
        except: pass
        return res    
        
    @add_docs('namespace', 'exists')    
    def namespaceExists(self):
        return cmds.namespace(ex=self.namespace)
      
    def withCopyNumber(self):
        """return this path with the copy number at the end"""
        if self._copyNumber is not None:
            return Path( '%s{%d}' % (self, self._copyNumber) )
        return self
    
    @createflag('file', 'importReference')
    def importContents(self, **kwargs):
        return cmds.file( self.withCopyNumber(), **kwargs )
       
    @createflag('file', 'removeReference')
    def remove(self, **kwargs):
        return cmds.file( self.withCopyNumber(), **kwargs )
       
    @add_docs('file', 'unloadReference')
    def unload(self):
        return cmds.file( self.withCopyNumber(), unloadReference=1 )
       
    @add_docs('file', 'loadReference')
    def load(self, newFile=None, **kwargs):
        if not newFile:
            args = ()
        else:
            args = (newFile,)
        return cmds.file( loadReference=self.refNode,*args, **kwargs )
    
    @add_docs('file', 'cleanReference')
    def clean(self, **kwargs):
        return cmds.file( cleanReference=self.refNode, **kwargs )
    
    @add_docs('file', 'lockReference')
    def lock(self):
        return cmds.file( self.withCopyNumber(), lockReference=1 )
    
    @add_docs('file', 'lockReference')
    def unlock(self):
        return cmds.file( self.withCopyNumber(), lockReference=0 )
    
    @add_docs('file', 'deferReference')     
    def isDeferred(self):
        return cmds.file( self.withCopyNumber(), q=1, deferReference=1 )
       
    @add_docs('file', 'deferReference')
    def isLoaded(self):
        return not cmds.file( self.withCopyNumber(), q=1, deferReference=1 )
    
    @add_docs('referenceQuery', 'nodes')
    def nodes(self):
        import general
        return map( general.PyNode, cmds.referenceQuery( self.withCopyNumber(), nodes=1, dagPath=1 ) )
    
    @add_docs('file', 'copyNumberList')
    def copyNumberList(self):
        """returns a list of all the copy numbers of this file"""
        return cmds.file( self, q=1, copyNumberList=1 )
      
    @add_docs('file', 'selectAll')
    def selectAll(self):
        return cmds.file( self.withCopyNumber(), selectAll=1 )
            
    def _getNamespace(self):
        return cmds.file( self.withCopyNumber(), q=1, ns=1)
    def _setNamespace(self, namespace):
        return cmds.file( self.withCopyNumber(), e=1, ns=namespace)    
    namespace = property( _getNamespace, _setNamespace )

    def _getRefNode(self):
        #return node.DependNode(cmds.referenceQuery( self.withCopyNumber(), referenceNode=1 ))
        # TODO : cast this to PyNode
        try:
            import general
            return general.PyNode( cmds.referenceQuery( self.withCopyNumber(), referenceNode=1 ) )
        except RuntimeError:
            return None
        
    refNode = util.cacheProperty( _getRefNode, '_refNode')
    
    @add_docs('file', 'usingNamespaces')
    def isUsingNamespaces(self):
        return cmds.file( self.withCopyNumber(), q=1, usingNamespaces=1 )

    @add_docs('file', 'exportAnimFromReference')    
    def exportAnim( self, exportPath, **kwargs ):
        if 'type' not in kwargs:
            try: kwargs['type'] = _getTypeFromExtension(exportPath)
            except: pass
        return Path(cmds.file( exportPath, rfn=self.refNode, exportAnimFromReference=1))
          
    @add_docs('file', 'exportSelectedAnimFromReference')    
    def exportSelectedAnim( self, exportPath, **kwargs ):
        if 'type' not in kwargs:
            try: kwargs['type'] = _getTypeFromExtension(exportPath)
            except: pass
        return Path(cmds.file( exportPath, rfn=self.refNode, exportSelectedAnimFromReference=1))

# TODO: anyModified, modified, errorStatus, executeScriptNodes, lockFile, lastTempFile, renamingPrefixList, renameToSave

@createflag('file', 'reference')
def createReference( *args, **kwargs ):
    return FileReference(cmds.file(*args, **kwargs))

@createflag('file', 'loadReference')
def loadReference( file, refNode, **kwargs ):
    return FileReference(cmds.file(file, **kwargs))

@createflag('file', 'exportAll')    
def exportAll( exportPath, **kwargs ):
    if 'type' not in kwargs:
        try: kwargs['type'] = _getTypeFromExtension(exportPath)
        except: pass  
    return Path(cmds.file(*args, **kwargs))

@createflag('file', 'exportAsReference')
def exportAsReference( exportPath, **kwargs ):
    if 'type' not in kwargs:
        try: kwargs['type'] = _getTypeFromExtension(exportPath)
        except: pass
    return FileReference(cmds.file(*args, **kwargs))

@createflag('file', 'exportSelected')
def exportSelected( exportPath, **kwargs ):
    if 'type' not in kwargs:
        try: kwargs['type'] = _getTypeFromExtension(exportPath)
        except: pass
    return Path(cmds.file(exportPath, **kwargs))

@createflag('file', 'exportAnim')
def exportAnim( exportPath, **kwargs ):
    if 'type' not in kwargs:
        try: kwargs['type'] = _getTypeFromExtension(exportPath)
        except: pass
    return Path(cmds.file(exportPath, **kwargs))

@createflag('file', 'exportSelectedAnim')
def exportSelectedAnim( exportPath, **kwargs ):
    if 'type' not in kwargs:
        try: kwargs['type'] = _getTypeFromExtension(exportPath)
        except: pass
    return Path(cmds.file(exportPath, **kwargs))

@add_docs('file', 'exportAnimFromReference')    
def exportAnimFromReference( *args, **kwargs ):
    if 'type' not in kwargs:
        try: kwargs['type'] = _getTypeFromExtension(exportPath)
        except: pass
    return Path(cmds.file( *args, **kwargs))
      
@add_docs('file', 'exportSelectedAnimFromReference')    
def exportSelectedAnimFromReference( *args, **kwargs ):
    if 'type' not in kwargs:
        try: kwargs['type'] = _getTypeFromExtension(exportPath)
        except: pass
    return Path(cmds.file( *args, **kwargs))
    
@createflag('file', 'i')
def importFile( *args, **kwargs ):
    return Path(cmds.file(*args, **kwargs))

@createflag('file', 'newFile')
def newFile( *args, **kwargs ):
    return Path(cmds.file(*args, **kwargs))

@createflag('file', 'open')
def openFile( *args, **kwargs ):
    return Path(cmds.file(*args, **kwargs))    

@add_docs('file', 'rename')
def renameFile( *args, **kwargs ):
    return Path(cmds.file(rename=args[0]))

def saveAs(exportPath, **kwargs):
    cmds.file( rename=exportPath )
    kwargs['save']=True
    if 'type' not in kwargs:
        try: kwargs['type'] = _getTypeFromExtension(exportPath)
        except: pass
    return Path(cmds.file(**kwargs) )



#createReference = _factories.makecreateflagCmd( 'createReference', cmds.file, 'reference', __name__, returnFunc=FileReference )
#loadReference = _factories.makecreateflagCmd( 'loadReference', cmds.file, 'loadReference',  __name__, returnFunc=FileReference )
#exportAnim = _factories.makecreateflagCmd( 'exportAnim', cmds.file, 'exportAnim',  __name__, returnFunc=Path )
#exportAnimFromReference = _factories.makecreateflagCmd( 'exportAnimFromReference', cmds.file, 'exportAnimFromReference',  __name__, returnFunc=Path )
#exportSelectedAnim = _factories.makecreateflagCmd( 'exportSelectedAnim', cmds.file, 'exportSelectedAnim',  __name__, returnFunc=Path )
#exportSelectedAnimFromReference = _factories.makecreateflagCmd( 'exportSelectedAnimFromReference', cmds.file, 'exportSelectedAnimFromReference', __name__,  returnFunc=Path )
#importFile = _factories.makecreateflagCmd( 'importFile', cmds.file, 'i',  __name__, returnFunc=Path )
#newFile = _factories.makecreateflagCmd( 'newFile', cmds.file, 'newFile',  __name__, returnFunc=Path )
#openFile = _factories.makecreateflagCmd( 'openFile', cmds.file, 'open',  __name__, returnFunc=Path )
#renameFile = _factories.makecreateflagCmd( 'renameFile', cmds.file, 'rename',  __name__, returnFunc=Path )

_factories.createFunctions( __name__ )
