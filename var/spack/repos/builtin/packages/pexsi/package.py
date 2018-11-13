# Copyright 2013-2018 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)


import inspect
import os.path

from spack import *


class Pexsi(MakefilePackage):
    """The PEXSI library is written in C++, and uses message passing interface
    (MPI) to parallelize the computation on distributed memory computing
    systems and achieve scalability on more than 10,000 processors.

    The Pole EXpansion and Selected Inversion (PEXSI) method is a fast
    method for electronic structure calculation based on Kohn-Sham density
    functional theory. It efficiently evaluates certain selected elements
    of matrix functions, e.g., the Fermi-Dirac function of the KS Hamiltonian,
    which yields a density matrix. It can be used as an alternative to
    diagonalization methods for obtaining the density, energy and forces
    in electronic structure calculations.
    """
    homepage = 'https://math.berkeley.edu/~linlin/pexsi/index.html'
    url = 'https://math.berkeley.edu/~linlin/pexsi/download/pexsi_v0.9.0.tar.gz'

    # version('1.0', '4600b03e235935fe623acf500df0edfa')
    version('0.10.2', '012f6800098671ec39c2ed7b38935e27')
    version('0.9.2', '0ce491a3a922d271c4edf9b20aa93076')
    version('0.9.0', '0c1a2de891ba1445dfc184b2fa270ed8')

    depends_on('parmetis')
    depends_on('superlu-dist@3.3:3.999', when='@:0.9.0')
    depends_on('superlu-dist@4.3:4.999', when='@0.9.2')
    depends_on('superlu-dist@5.1.2:5.3.999', when='@0.10.2:')

    variant(
        'fortran', default=False, description='Builds the Fortran interface'
    )

    parallel = False

    def edit(self, spec, prefix):

        substitutions = [
            ('@MPICC', self.spec['mpi'].mpicc),
            ('@MPICXX_LIB', self.spec['mpi:cxx'].libs.joined()),
            ('@MPICXX', self.spec['mpi'].mpicxx),
            ('@MPIFC', self.spec['mpi'].mpifc),
            ('@RANLIB', 'ranlib'),
            ('@PEXSI_STAGE', self.stage.source_path),
            ('@SUPERLU_PREFIX', self.spec['superlu-dist'].prefix),
            ('@METIS_PREFIX', self.spec['metis'].prefix),
            ('@PARMETIS_PREFIX', self.spec['parmetis'].prefix),
            ('@LAPACK_PREFIX', self.spec['lapack'].prefix),
            ('@BLAS_PREFIX', self.spec['blas'].prefix),
            ('@LAPACK_LIBS', self.spec['lapack'].libs.joined()),
            ('@BLAS_LIBS', self.spec['blas'].libs.joined()),
            # FIXME : what to do with compiler provided libraries ?
            ('@STDCXX_LIB', ' '.join(self.compiler.stdcxx_libs))
        ]

        if '@0.9.2' in self.spec:
            substitutions.append(
                ('@FLDFLAGS', '-Wl,--allow-multiple-definition')
            )
        else:
            substitutions.append(
                ('@FLDFLAGS', '')
            )

        template = join_path(
            os.path.dirname(inspect.getmodule(self).__file__),
            'make.inc'
        )
        makefile = join_path(
            self.stage.source_path,
            'make.inc'
        )
        copy(template, makefile)
        for key, value in substitutions:
            filter_file(key, value, makefile)

    def build(self, spec, prefix):
        super(Pexsi, self).build(spec, prefix)
        if '+fortran' in self.spec:
            make('-C', 'fortran')

    def install(self, spec, prefix):

        # 'make install' does not exist, despite what documentation says
        mkdirp(self.prefix.lib)

        install(
            join_path(self.stage.source_path, 'src', 'libpexsi_linux.a'),
            join_path(self.prefix.lib, 'libpexsi.a')
        )

        install_tree(
            join_path(self.stage.source_path, 'include'),
            self.prefix.include
        )

        # fortran "interface"
        if '+fortran' in self.spec:
            install_tree(
                join_path(self.stage.source_path, 'fortran'),
                join_path(self.prefix, 'fortran')
            )