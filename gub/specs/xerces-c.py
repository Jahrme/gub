from gub import mirrors
from gub import gubb
from gub import misc
from gub import targetpackage

class Xerces_c (targetpackage.TargetBuildSpec):
    def __init__ (self, settings):
        targetpackage.TargetBuildSpec.__init__ (self, settings)
        self.with_tarball (mirror=mirrors.xerces_c, version='2_7_0')
        self.compile_dict = {
            'XERCESCROOT': '%(builddir)s',
            'TRANSCODER': 'NATIVE',
            'MESSAGELOADER': 'INMEM',
            'NETACCESSOR': 'Socket',
            'THREADS': 'pthread',
            'BITSTOBUILD': '32',
            'LIBS': ' -lpthread ',
            'ALLLIBS': "${LIBS}",
            'CFLAGS': ' -DPROJ_XMLPARSER -DPROJ_XMLUTIL -DPROJ_PARSERS -DPROJ_SAX4C -DPROJ_SAX2 -DPROJ_DOM -DPROJ_DEPRECATED_DOM -DPROJ_VALIDATORS -DXML_USE_NATIVE_TRANSCODER -DXML_USE_INMEM_MESSAGELOADER -DXML_USE_PTHREADS -DXML_USE_NETACCESSOR_SOCKET ',
            'CXXFLAGS': ' -DPROJ_XMLPARSER -DPROJ_XMLUTIL -DPROJ_PARSERS -DPROJ_SAX4C -DPROJ_SAX2 -DPROJ_DOM -DPROJ_DEPRECATED_DOM -DPROJ_VALIDATORS -DXML_USE_NATIVE_TRANSCODER -DXML_USE_INMEM_MESSAGELOADER -DXML_USE_PTHREADS -DXML_USE_NETACCESSOR_SOCKET ',
            }
        gubb.change_target_dict (self, self.compile_dict)
    def force_sequential_build (self):
        return True
    def patch (self):
        self.shadow_tree ('%(srcdir)s', '%(builddir)s')
    def configure_command (self):
        # We really did not understand autotools, so we cd and ENV
        # around it until it breaks.  And see, our webserver is soo
        # cool, it can serve the INSTALL file!  Let's remove it from
        # the tarball!
        return (self.makeflags () + ' '
                + targetpackage.TargetBuildSpec.configure_command (self)
                .replace ('/configure ', '/src/xercesc/configure ')
                .replace ('--config-cache', '--cache-file=%(builddir)s/config.cache'))
    def makeflags (self):
        s = ''
        for i in self.compile_dict.keys ():
            s += ' ' + i + '="' + self.compile_dict[i] + '"'
        return s
    def xcompile_command (self):
        return (targetpackage.TargetBuildSpec.compile_command (self)
                + self.makeflags ()
                + ';' + targetpackage.TargetBuildSpec.compile_command (self)
                + self.makeflags ()
                + ';' + targetpackage.TargetBuildSpec.compile_command (self)
                + self.makeflags ())
    def compile_command (self):
        return (targetpackage.TargetBuildSpec.compile_command (self)
                + self.makeflags ())
    def install_command (self):
        return (targetpackage.TargetBuildSpec.install_command (self)
                + self.makeflags ())
    def configure (self):
        self.config_cache ()
        self.system ('cd %(builddir)s/src/xercesc && %(configure_command)s')
    def compile (self):
        self.system ('cd %(builddir)s/src/xercesc && %(compile_command)s')
    def install (self):
        self.system ('cd %(builddir)s/src/xercesc && %(install_command)s')

class Xerces_c__linux__arm__vfp (Xerces_c):
    def __init__ (self, settings):
        Xerces_c.__init__ (self, settings)
        self.with_template (version='2_6_0',
                            mirror='http://archive.apache.org/dist/xml/xerces-c/Xerces-C_%(ball_version)s/%(name)s-src_%(ball_version)s.tar.%(format)s')
