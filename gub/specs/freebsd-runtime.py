from gub import build

class Freebsd_runtime (build.BinaryBuild, build.SdkBuild):
    source = 'http://lilypond.org/download/gub-sources/freebsd-runtime/freebsd-runtime-4.11-1.%(package_arch)s.tar.gz&strip=0'
    def untar (self):
        build.BinaryBuild.untar (self)

class Freebsd_runtime__freebsd__64 (Freebsd_runtime):
    source = 'http://lilypond.org/download/gub-sources/freebsd-runtime/freebsd-runtime-6.2-2.%(package_arch)s.tar.gz&strip=0'
