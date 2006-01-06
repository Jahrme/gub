import gub
import misc
import glob

class Cross_package (gub.Package):
	"""Package for cross compilers/linkers etc.
	"""

	def configure_command (self):
		return (gub.Package.configure_command (self)
			+ misc.join_lines ('''
--program-prefix=%(target_architecture)s-
--prefix=%(crossprefix)s/
--with-slibdir=/usr/lib/
--target=%(target_architecture)s
--with-sysroot=%(system_root)s/
'''))

	def install_command (self):
		return '''make DESTDIR=%(install_root)s prefix=/usr/cross/ install'''

		

class Binutils (Cross_package):
	def install (self):
		Cross_package.install (self)
		self.system ('rm %(install_root)s/usr/cross/lib/libiberty.a')

class Gcc (Cross_package):
	def configure_command (self):
		cmd = Cross_package.configure_command (self)
		# FIXME: using --prefix=%(tooldir)s makes this
		# uninstallable as a normal system package in
		# /usr/i686-mingw/
		# Probably --prefix=/usr is fine too
		
		
		languages = ['c', 'c++']

		if self.settings.__dict__.has_key ("no-c++"):
			del languages[1]

		language_opt = (' --enable-languages=%s ' % ','.join (languages))
		cxx_opt = '--enable-libstdcxx-debug '

		cmd += '''
--with-as=%(crossprefix)s/bin/%(target_architecture)s-as
--with-ld=%(crossprefix)s/bin/%(target_architecture)s-ld
--enable-static
--enable-shared '''

		cmd += language_opt
		if 'c++' in languages:
			cmd +=  ' ' + cxx_opt

		return misc.join_lines (cmd)

	def install (self):
		Cross_package.install (self)
		self.system ('''
cd %(install_root)s/usr/lib && ln -fs libgcc_s.so.1 libgcc_s.so
''')



def change_target_packages (packages):
	cross_packs = [p for p in packages if isinstance (p, Cross_package)]
	sdk_packs = [p for p in packages if isinstance (p, gub.Sdk_package)]
	other_packs = [p for p in packages if (not isinstance (p, Cross_package)
					       and not isinstance (p, gub.Sdk_package))]
	for p in other_packs:
		p.build_dependencies += cross_packs

	for p in other_packs + cross_packs:
		p.build_dependencies += sdk_packs
	

