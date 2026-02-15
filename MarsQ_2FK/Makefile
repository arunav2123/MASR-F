# Makefile for MARS-Q with new FFT on venus - Arunav Kumar 9Feb 2026
# Cleaned + corrected for GNU Fortran (mpif90 / gfortran 11+ via conda)
# - fixes module build order (marsq USE kineticm)
# - removes gijum (not present)
# - adds reorbitm, ran_modm (required by your snapshot)
# - avoids linking .mod files (prevents "Modula-2 compiler not installed")
# - allows legacy argument mismatches (LSODE / old interfaces)

MARS    = marsq
PROG    = $(MARS).x
MARSOBJ = $(MARS).o

# -------------------------------------------------
# Suffixes
# -------------------------------------------------
.SUFFIXES:
.SUFFIXES: .f .f90 .mod .inc .o .x

# -------------------------------------------------
# Source files
# -------------------------------------------------

# Main Fortran sources (DO NOT include marsq.f here)
FSOURCES =  pams.f         smlpck.f        feedback.f     printatoh.f   \
            splines.f      kinetic.f                                    \
            torque.f       anisotropic.f   adaptive.f     output_t7.f   \
            fftdriver.f    fftroutines.f   fftoutpt.f     abortrun.f    \
            reorbit.f

# Pure module sources (NO gijum; include reorbitm + ran_modm)
MODSOURC =  dimensim.f     globalm.f       gijlm.f                      \
            feedbackm.f    gvacuumm.f      rcomdm.f                     \
            convolcofm.f   resmatm.f       adaptivem.f                  \
            anisotropicm.f kineticm.f      torquem.f                    \
            reorbitm.f     ran_modm.f

# Module + object sources
MSOURCES =  common_ntv.f   mpienv.f        ntv.f                        \
            ntv_lib.f      ntv_pre.f

# Fortran 90 module sources
MSOURC90 =  KineticExtendAnalysis.f90  ToolBox.f90

# -------------------------------------------------
# LSODE sources
# -------------------------------------------------
LSOURCES =  ./lsode/daxpy.f   ./lsode/dcopy.f   ./lsode/dewset.f        \
            ./lsode/dgbsl.f   ./lsode/dgesl.f   ./lsode/dprepj.f        \
            ./lsode/dsolsy.f  ./lsode/dstode.f  ./lsode/dvnorm.f        \
            ./lsode/iumach.f  ./lsode/lsode.f   ./lsode/xerrwd.f        \
            ./lsode/xsetun.f  ./lsode/dcfode.f  ./lsode/ddot.f          \
            ./lsode/dgbfa.f   ./lsode/dgefa.f   ./lsode/dintdy.f        \
            ./lsode/dscal.f   ./lsode/dsrcom.f  ./lsode/dumach.f        \
            ./lsode/idamax.f  ./lsode/ixsav.f   ./lsode/xsetf.f

# -------------------------------------------------
# Include files
# -------------------------------------------------
INCLUDES =  cdipam.inc     newrun.inc      tent.inc       vtophat.inc   \
            tophat.inc     comioc.inc      integc.inc                   \
            compam.inc     specmat.inc                                  \
            comfft.inc     setfft.inc                                   \
            vtent.inc

# -------------------------------------------------
# Targets / derived lists
# -------------------------------------------------
MODULES  = $(MODSOURC:.f=.mod) $(MSOURCES:.f=.mod)

# gfortran writes .mod in lower-case; keep explicit expected names
MODUL90  = kineticextendanalysis.mod toolbox.mod

OBJECTS  = $(FSOURCES:.f=.o)
MODOBJCT = $(MODSOURC:.f=.o)
MOBJECTS = $(MSOURCES:.f=.o)
MOBJEC90 = $(MSOURC90:.f90=.o)
LOBJECTS = $(LSOURCES:.f=.o)

# -------------------------------------------------
# Compiler (GNU MPI via conda)
# -------------------------------------------------
F95 = /home/arunavk/miniconda3/envs/marsq-build/bin/mpif90

F95FLAGS = -O2 -fopenmp -fdefault-real-8 -fdefault-double-8 \
           -ffree-line-length-none -J. -fallow-argument-mismatch

LDFLAGS =
LIBS    =

# -------------------------------------------------
# Build rules
# -------------------------------------------------
all: $(PROG)

# Link ONLY object files + libraries (never .mod)
$(PROG): $(MODOBJCT) $(MOBJECTS) $(MOBJEC90) $(LOBJECTS) $(MARSOBJ) $(OBJECTS)
	@echo "Linking $(PROG)"
	@$(F95) $(LDFLAGS) $(F95FLAGS) -o $@ $(MODOBJCT) $(MOBJECTS) $(MOBJEC90) $(LOBJECTS) $(MARSOBJ) $(OBJECTS) $(LIBS)

# Ensure modules exist before compiling objects that USE them (ordering only)
$(MARSOBJ) $(OBJECTS) $(MODOBJCT) $(MOBJECTS) $(MOBJEC90): $(MODULES) $(MODUL90)

# Compile marsq.o explicitly (after modules by ordering rule above)
$(MARSOBJ): $(MARS).f $(INCLUDES)
	@echo "Compiling $(MARSOBJ)"
	@$(F95) $(F95FLAGS) -c $(MARS).f -o $(MARSOBJ)

# Generic object compilation
%.o: %.f $(INCLUDES)
	@$(F95) $(F95FLAGS) -c $< -o $@

%.o: %.f90 $(INCLUDES)
	@$(F95) $(F95FLAGS) -c $< -o $@

# Module generation from .f
%.mod: %.f $(INCLUDES)
	@$(F95) $(F95FLAGS) -c $< -o $(basename $@).o

# F90 module case handling
toolbox.mod: ToolBox.f90 $(INCLUDES)
	@$(F95) $(F95FLAGS) -c $< -o ToolBox.o

kineticextendanalysis.mod: KineticExtendAnalysis.f90 $(INCLUDES)
	@$(F95) $(F95FLAGS) -c $< -o KineticExtendAnalysis.o

# -------------------------------------------------
# Explicit dependencies (tighten ordering for key modules)
# -------------------------------------------------
feedback.o: ran_modm.mod feedbackm.mod gvacuumm.mod resmatm.mod torquem.mod

anisotropic.o: anisotropicm.mod kineticm.mod
adaptive.o:    adaptivem.mod mpienv.mod torquem.mod

torque.o: torquem.mod ntv.mod ntv_lib.mod ntv_pre.mod common_ntv.mod \
          gvacuumm.mod feedbackm.mod convolcofm.mod resmatm.mod

kinetic.o: kineticm.mod mpienv.mod gvacuumm.mod resmatm.mod toolbox.mod \
           kineticextendanalysis.mod anisotropicm.mod convolcofm.mod

kineticm.mod: gvacuumm.mod resmatm.mod toolbox.mod \
              kineticextendanalysis.mod anisotropicm.mod convolcofm.mod

mpienv.o mpienv.mod: kineticm.mod reorbitm.mod
ntv.o ntv.mod: ntv_lib.mod common_ntv.mod
ntv_pre.o ntv_pre.mod: ntv_lib.mod
common_ntv.o common_ntv.mod: ntv_lib.mod ntv_pre.mod

KineticExtendAnalysis.o kineticextendanalysis.mod: toolbox.mod

# -------------------------------------------------
# Cleaning
# -------------------------------------------------
mostlyclean:
	@rm -f $(PROG) $(MARSOBJ) $(OBJECTS) $(MODOBJCT) $(MOBJECTS) $(MOBJEC90) $(LOBJECTS)

reallyclean:
	@rm -f $(PROG) $(MARSOBJ) $(OBJECTS) $(MODOBJCT) $(MOBJECTS) $(MOBJEC90) \
	        $(MODULES) $(MODUL90) $(LOBJECTS) *.mod