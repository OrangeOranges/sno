SPATIALITE_VERSION ?= 4.3.0a

SHELL = /bin/bash
export PREFIX ?= $(abspath env)

ifeq ($(OS),Windows_NT)
	PLATFORM := Windows
else
	PLATFORM := $(shell uname -s)
endif

SPATIALITE_ARCHIVE := libspatialite-$(SPATIALITE_VERSION).tar.gz

CFLAGS += -DACCEPT_USE_OF_DEPRECATED_PROJ_API_H

ifeq ($(PLATFORM),Darwin)
	CCACHE_PATH = /usr/local/opt/ccache/bin
	LIBSUFFIX = dylib
else ifeq ($(PLATFORM),Linux)
	LIBSUFFIX = so
	CCACHE_PATH = /usr/lib/ccache
	CCACHE_PATH := $(or $(CCACHE_PATH),/usr/lib64/ccache)
endif

export PKG_CONFIG_PATH := $(realpath $(PREFIX)/lib/pkgconfig)
PROJ_CFLAGS := $(shell PKG_CONFIG_PATH=$(PKG_CONFIG_PATH) pkg-config proj --cflags)
PROJ_LDFLAGS := $(shell PKG_CONFIG_PATH=$(PKG_CONFIG_PATH) pkg-config proj --libs)

export CFLAGS += $(PROJ_CFLAGS)
export LDFLAGS += $(PROJ_LDFLAGS)

# use ccache if available
export PATH := $(CCACHE_PATH):$(PREFIX)/bin:$(PATH)

build-spatialite = src/src/.libs/mod_spatialite.$(LIBSUFFIX)
configure-spatialite = src/config.status
libproj := $(PREFIX)/lib/libproj.$(LIBSUFFIX)
libgeos := $(PREFIX)/lib/libgeos.$(LIBSUFFIX)
libsqlite := $(PREFIX)/lib/libsqlite3.$(LIBSUFFIX)
libs := $(libproj) $(libgeos) $(libsqlite)

# default target
.PHONY: all
all: $(build-spatialite)

.PHONY: clean
clean:
	-$(RM) -r env
	-$(RM) src/src/.libs/libspatialite* src/src/.libs/mod_spatialite*
	-$(RM) src/src/libspatialite* src/src/mod_spatialite*
	-$(RM) src/spatialite.pc

.PHONY: cleaner
cleaner: clean
	-$(MAKE) -C src clean

.PHONY: cleanest
cleanest: cleaner
	-$(RM) -r src

.PHONY: clean-configure
clean-configure:
	-$(RM) $(configure-spatialite)

#
# Download Archives
#

$(SPATIALITE_ARCHIVE):
	wget http://www.gaia-gis.it/gaia-sins/$@

#
# Extract Archives
#

src: $(SPATIALITE_ARCHIVE)
	rm -rf $@
	mkdir -p $@
	@echo "Extracting $(SPATIALITE_ARCHIVE) ..."
	tar xzf $(SPATIALITE_ARCHIVE) --strip-components=1 -C $@


.PHONY: source
source: src

#
# SPATIALITE
#

$(configure-spatialite): export PATH:=$(realpath ../geos/env/bin):$(PATH)
$(configure-spatialite): export PKG_CONFIG_PATH=/dev/null
$(configure-spatialite): export LD_LIBRARY_PATH:=$(LD_LIBRARY_PATH):$(PREFIX)/lib
$(configure-spatialite): | src $(libs)
	@test "$(PROJ_CFLAGS)" || ( echo ">> PROJ_CFLAGS did not resolve"; exit 1 )
	@test "$(PROJ_LDFLAGS)" || ( echo ">> PROJ_LDFLAGS did not resolve"; exit 1 )
	@test "`command -v geos-config`" && echo ">> geos-config: `command -v geos-config`" || ( echo ">> geos-config not found"; exit 1 )
	cd src && ./configure \
		--prefix=$(PREFIX) \
		--disable-freexl \
		--disable-libxml2 \
		--disable-examples \
		--disable-gcp \
		--disable-gcov \
		--disable-dependency-tracking

.PHONY: configure
configure: clean-configure $(configure-spatialite)

$(build-spatialite): $(configure-spatialite)
	$(MAKE) -C src -j 2
# needs to be mod_spatialite.dylib
# https://github.com/Homebrew/homebrew-core/blob/master/Formula/libspatialite.rb#L46-L49
	if [ "$(PLATFORM)" = "Darwin" ]; then \
		ln -sf mod_spatialite.so $@; \
	fi
	$(MAKE) print-lib-deps-$(PLATFORM)

#
# INSTALLATION
#

.PHONY: install
install: $(build-spatialite)
	$(MAKE) -C src install
	cp -f $< $(PREFIX)/lib/

.PHONY: print-lib-deps
print-lib-deps: print-lib-deps-$(PLATFORM)

.PHONY: print-lib-deps-Darwin
print-lib-deps-Darwin:
	@echo -e "\nExamining library dependencies..."
	cd src && find . \( -name "*.dylib" -o -name "*.so" \) -exec otool -L {} \;

.PHONY: print-lib-deps-Linux
print-lib-deps-Linux:
	@echo -e "\nExamining library dependencies..."
	cd src  && find . -name "*.so" -print -exec ldd {} \;