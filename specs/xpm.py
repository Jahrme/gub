
import gdbm as dbmodule
#import dbhash as dbmodule

import dbhash
import gzip
import os
import re
import string
#
import buildnumber
import framework
import gub
import fcntl
import sys

from misc import *

# X package manager (x for want of better name)

#
# TODO:

#
# separate into interface and
# implementation (loose all the _methods() )
#
class Package_manager:
	def __init__ (self, root, os_interface):
		self.root = root
		self.config = self.root + '/etc/xpm/'
		self.os_interface = os_interface
		self._packages = {}
		self.include_build_deps = True

		if not os.path.isdir (self.config):
			os_interface.system ('mkdir -p %s' % self.config)


		
		lock_file = self.config + 'lock'
		self._lock_file = open (lock_file, 'w')

		try:
			fcntl.flock (self._lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
		except IOError:			
			sys.stderr.write ("Can't acquire Package_manager lock %s\n\nAbort\n" % lock_file)
			sys.exit (1)


		self._file_package_db = dbmodule.open (self.config
						       + '/files.db', 'c')
		self._package_file_db = dbmodule.open (self.config
						       + '/packages.db', 'c')
		self._package_version_db = dbmodule.open (self.config
						       + '/versions.db', 'c')
		

	def is_installable (self, package):
		ball = package.expand ('%(gub_uploads)s/%(gub_name)s')
		return os.path.exists (ball)

	def installed_packages (self):
		names = self._package_file_db.keys ()
		return [self._packages[p] for p in names]

	def tarball_files (self, ball):
		flag = tar_compression_flag (ball)
		str = self.os_interface.read_pipe ('tar -tf%(flag)s "%(ball)s"'
						   % locals (), silent=True)
		lst = str.split ('\n')
		return lst

	def installed_files (self, package):
		return self._package_file_db[package.name ()].split ('\n')

	def is_installed (self, package):
		return self._package_file_db.has_key (package.name())

	def build_package (self, package):
		if self.is_installed (package):
			return
		if not self.is_installable (package):
			self.os_interface.log_command ('building package: %s\n'
						       % `package`)
			package.builder ()
		if (self.is_installable (package)
		    and not self.is_installed (package)):
			self.install_package (package)


	def is_downloaded (self, package):
		return package.is_downloaded ()
	
	def download_package (self, package):
		package.do_download ()

	def install_package (self, package):
		if self.is_installed (package):
			return
		self.os_interface.log_command ('installing package: %s\n'
					       % `package`)
		name = package.name ()
		if self._package_file_db.has_key (name):
			print 'already have package ', name
			raise 'abort'

		ball = package.expand ('%(gub_uploads)s/%(gub_name)s')

		self.os_interface.log_command ('installing package %(name)s from %(ball)s\n'
					       % locals ())

		flag = tar_compression_flag (ball)
		root = self.root
		lst = self.tarball_files (ball)

		conflicts = False
		for f in lst:
			if (self._file_package_db.has_key (f)
			    and not os.path.isdir (self.root + '/'+  f)):
				print 'already have file %s: %s' % (f, self._file_package_db[f])
				conflicts = True

		if conflicts and not package.settings.is_distro:
			raise 'abort'

		self.os_interface.system ('tar -C %(root)s -xf%(flag)s %(ball)s' % locals ())

		self._package_file_db[name] = '\n'.join (lst)
		self._package_version_db[name] = package.full_version ()
		for f in lst:
			
			# ignore directories.
			if f and  f[-1] != '/':
				self._file_package_db[f] = name
			
	def is_registered (self, package):
		return self._packages.has_key (package.name())
	
	def register_package (self, package):
		if package.verbose:
			self.os_interface.log_command ('registering package: %s\n'
						       % `package`)
		self._packages[package.name ()] = package

	def uninstall_package (self, package):
		self.os_interface.log_command ('uninstalling package: %s\n'
					       % `package`)
		lst = self.installed_files (package)
		name = package.name()
		
		dirs = []
		files = []
		for i in lst:
			f = os.path.join (self.root, i)
			if os.path.islink (f):
				files.append (f)
			elif (not os.path.exists (f)
			    and not package.settings.is_distro):
				print 'xpm: uninstall: %s' % package
				print 'xpm: no such file: %s' % f
				# should've dealt with this in install stage.
			        print "\n\nBARF\n\n" 
			elif os.path.isdir (f):
				dirs.append (f)
			else:
				files.append (f)

		for f in files:
			os.unlink (f)

		for d in reversed (dirs):
			try:
				os.rmdir (d)
			except OSError:
				print 'warning: %s not empty' % d

		for f in lst:
			if not f or f[-1] == '/':
				continue
			try:
				del self._file_package_db[f]
			except:
				print 'db delete failing for ', f
		del self._package_file_db[name]
		del self._package_version_db[name]
	
	# NAME_ shortcuts
	def name_build (self, name):
		self.build_package (self._packages[name])
	def name_download (self, name):
		self.download_package (self._packages[name])
	def name_files (self, name):
		return self.installed_files (self._packages[name])
	def name_install (self, name):
		self.install_package (self._packages[name])
	def name_uninstall (self, name):
		self.uninstall_package (self._packages[name])
	def name_is_installed (self, name):
		try:
			return self.is_installed (self._packages[name])
		except KeyError, k:
			print 'known packages', self._packages
			raise "Unknown package", k

class Dependency_manager (Package_manager):
	def determine_dependencies (self, package):
		if package.verbose:
			self.os_interface.log_command ('resolving dependencies: %s\n'
						       % `package`)
		package._dependencies = []
		package._build_dependencies = []
		try:
			package._dependencies = map (lambda x:
						     self._packages[x],
						     package.name_dependencies)
			if package in package._dependencies:
				print ('simple circular dependency',
				       package,
				       package.name_dependencies,
				       package._dependencies,
				       self._packages)
				raise 'BARF'

			package._build_dependencies = map (lambda x:
							   self._packages[x],
							   package.name_build_dependencies)

			if package in package._build_dependencies:
				print ('simple circular build dependency',
				       package,
				       package.name_build_dependencies,
				       package._build_dependencies,
				       self._packages)
				raise 'BARF'
			
			## should use name_dependencies ?
			#if self.include_build_deps:
			#	package._dependencies += package._build_dependencies


		except KeyError, k:
			print 'xpm: resolving dependencies for: %s' % package
			print 'xpm: unknown package: %s' % k
			print 'xpm: available packages: %s' % self._packages
			print 'xpm: deps: %s' % package.name_dependencies

			# don't barf.  This fucks up with SDK
			# packages, and separate target/framework
			# managers.


	def dependencies (self, package):
		if package._dependencies == None:
			self.determine_dependencies (package)

		return package._dependencies + package._build_dependencies
	
	def with_dependencies (self, package, action=None, recurse_stop_predicate=None):
		todo = []
		add_packages = [package]
		done = {package : 1}
		while add_packages:
			new_add = []
			for p in add_packages:
				for d in self.dependencies (p):
					if done.has_key (d):
						continue
					done[d] = True
					if recurse_stop_predicate and recurse_stop_predicate  (d):
						continue

					new_add.append (d)

			todo += add_packages
			add_packages = new_add
			
		sorted = self.topological_sort (todo)
		for p in sorted:
			action (p)


	def build_package (self, package):
		self.with_dependencies (package, action=bind_method (Package_manager.build_package, self),
					recurse_stop_predicate=self.is_installed)

	def download_package (self, package):
		self.with_dependencies (package, action=bind_method (Package_manager.download_package, self),
					recurse_stop_predicate=None)

	def install_package (self, package):
		self.with_dependencies (package, action=bind_method (Package_manager.install_package, self),
					recurse_stop_predicate=self.is_installed)

	def topological_sort (manager, nodes):
		deps = dict ([(n, [d for d in manager.dependencies (n)
				   if d in nodes])
			      for n in nodes])

		done = {}

		sorted = []
		while deps:
			min_dep_count = min ([len(ds) for (n,ds) in deps.items ()]) 
			rm = [n for (n, ds) in deps.items () if len (ds) == min_dep_count]

			if rm == []:
				raise 'barf'
			sorted += rm

			deps = dict ([(n, ds) for (n, ds) in deps.items ()
				      if len (ds) > min_dep_count])
			for ds in deps.values ():
				ds[:] = [d for d in ds if d not in rm]
				
		return sorted


	def package_version (self, pkg):
		return self._package_version_db[pkg.name()]


class Cygwin_package_manager (Dependency_manager):
	def __init__ (self, settings):
		Package_manager.__init__ (self, settings.system_root,
					  settings.os_interface)
		self.mirror = 'http://gnu.kookel.org/ftp/cygwin'
		self.settings = settings
		self.dist = 'curr'

	def get_packages (self, package_file):
		def get_package (name, dict):
			from new import classobj
			Package = classobj (name, (gub.Binary_package,), {})
			package = Package (self.settings)
			package.name_dependencies = []
			package.name_build_dependencies = []
			if dict.has_key ('requires'):
				deps = map (string.strip,
					    re.sub ('\([^\)]*\)', '',
						    dict['requires']).split ())
				blacklist = (
					'_update-info-dir',
					'bintutils',
					'gcc', 'gcc-core', 'gcc-g++',
					'gcc-mingw', 'gcc-mingw-core', 'gcc-mingw-g++',
					'libXft', 'libXft1', 'libXft2',
					'libbz2_1',
					'libguile16',
					'X-startup-scripts',
					'xorg-x11-bin-lndir',
					)
				deps = filter (lambda x: x not in blacklist, deps)
				package.name_dependencies = deps
			package.ball_version = dict['version']
			package.url = (self.mirror + '/'
				       + dict['install'].split ()[0])
			package.format = 'bz2'
			return package

		self._dists = {'test': [], 'curr': [], 'prev' : []}
		chunks = string.split (open (package_file).read (), '\n\n@ ')
		for i in chunks[1:]:
			lines = string.split (i, '\n')
			name = string.strip (lines[0])
			blacklist = ('binutils', 'gcc')
			if name in blacklist:
				continue
			packages = self._dists['curr']
			records = {
				'sdesc': name,
				'version': '0-0',
				'install': 'urg 0 0',
				}
			j = 1
			while j < len (lines) and string.strip (lines[j]):
				if lines[j][0] == '#':
					j = j + 1
					continue
				elif lines[j][0] == '[':
					packages.append (get_package (name,
								      records.copy ()))
					packages = self._dists[lines[j][1:5]]
					j = j + 1
					continue

				try:
					key, value = map (string.strip,
							  lines[j].split (': ',
									  1))
				except:
					print lines[j], package_file, self
					raise 'URG'
				if (value.startswith ('"')
				    and value.find ('"', 1) == -1):
					while 1:
						j = j + 1
						value += '\n' + lines[j]
						if lines[j].find ('"') != -1:
							break
				records[key] = value
				j = j + 1
			packages.append (get_package (name, records))
		return self._dists[self.dist]
		#return self._dists['curr'] + self._dists['test']

class Debian_package_manager (Dependency_manager):
	def __init__ (self, settings):
		Package_manager.__init__ (self, settings.system_root,
					  settings.os_interface)
		self.mirror = 'http://ftp.de.debian.org/debian'
		self.settings = settings

	def get_packages (self, package_file):
		return map (self.debian_package,
			    open (package_file).read ().split ('\n\n')[:-1])

	def debian_package (self, description):
		from new import classobj
		s = description[:description.find ('\nDescription')]
		d = dict (map (lambda line: line.split (': ', 1),
			       map (string.strip, s.split ('\n'))))
		Package = classobj (d['Package'], (gub.Binary_package,), {})
		package = Package (self.settings)
		package.name_dependencies = []
		if d.has_key ('Depends'):
			deps = map (string.strip,
				    re.sub ('\([^\)]*\)', '',
					    d['Depends']).split (', '))
			# FIXME: BARF, ignore choices
			deps = filter (lambda x: x.find ('|') == -1, deps)
			# FIXME: how to handle Provides: ?
			# FIXME: BARF, fixup libc Provides
			deps = map (lambda x: re.sub ('libc($|-)', 'libc6\\1',
						      x), deps)
			# FIXME: ugh, skip some
			blacklist = ('perl', 'perl-modules', 'perl-base')
			deps = filter (lambda x: x not in blacklist, deps)
			package.name_dependencies = deps
 
		package.name_build_dependencies = []
		package.ball_version = d['Version']
		package.url = self.mirror + '/' + d['Filename']
		package.format = 'deb'
		
		return package

def get_manager (settings):
	cross_module = None
	if settings.platform == 'cygwin':
		import cygwin
		cross_module = cygwin
	elif settings.platform == 'darwin':
		import darwintools
		cross_module = darwintools
	elif settings.platform.startswith ('debian'):
		import debian_unstable
		cross_module = debian_unstable
	elif settings.platform.startswith ('freebsd'):
		import freebsd
		cross_module = freebsd
	elif settings.platform.startswith ("linux"):
		import linux
		cross_module = linux
	elif settings.platform.startswith ('local'):
		import tools
		cross_module = tools
	elif settings.platform.startswith ('mingw'):
		import mingw
		cross_module = mingw

	cross_packages = cross_module.get_packages (settings)
	
	target_manager = Dependency_manager (settings.system_root,
					     settings.os_interface)

	map (target_manager.register_package, cross_packages)

	target_pkgs = framework.get_packages (settings)
	map (target_manager.register_package, target_pkgs)

	for p in target_manager._packages.values ():
		settings.build_number_db.set_build_number (p)

	cross_module.change_target_packages (target_manager._packages.values ())

	return target_manager

