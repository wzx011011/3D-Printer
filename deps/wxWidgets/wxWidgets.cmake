set(_wx_toolkit "")
set(_wx_private_font "-DwxUSE_PRIVATE_FONTS=1")
set(_wx_link_extra "")
if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
    set(_gtk_ver 2)

    if (DEP_WX_GTK3)
        set(_gtk_ver 3)
    endif ()

    set(_wx_toolkit "-DwxBUILD_TOOLKIT=gtk${_gtk_ver}")
	#set(_wx_link_extra
	#	"-DCMAKE_EXE_LINKER_FLAGS=-Wl,--no-as-needed"
	#	"-DCMAKE_CXX_STANDARD_LIBRARIES=-lpng16 -lz"
	#    )
endif()

if (MSVC)
    set(_wx_edge "-DwxUSE_WEBVIEW_EDGE=ON")
else ()
    set(_wx_edge "-DwxUSE_WEBVIEW_EDGE=OFF")
endif ()

# Note: The flatpak build builds wxwidgets separately due to CI size constraints.
# ANY CHANGES MADE IN HERE MUST ALSO BE REFLECTED IN `flatpak/io.github.SoftFever.OrcaSlicer.yml`.
# ** THIS INCLUDES BUILD ARGS. **
# ...if you can find a way around this size limitation, be my guest.

orcaslicer_add_cmake_project(
    wxWidgets
    URL "https://github.com/CrealityOfficial/Orca-deps-wxWidgets/archive/refs/tags/v1.0.0.tar.gz"
    URL_HASH SHA256=74089054448d887c1b551ac98f4b46fa8960a5168df48aa77700c7a58071148c
    DEPENDS ${PNG_PKG} ${ZLIB_PKG} ${EXPAT_PKG} ${TIFF_PKG} ${JPEG_PKG}
    CMAKE_ARGS
        -DwxBUILD_PRECOMP=ON
        ${_wx_toolkit}
        "-DCMAKE_DEBUG_POSTFIX:STRING="
        -DwxBUILD_DEBUG_LEVEL=0
        -DwxBUILD_SAMPLES=OFF
        -DwxBUILD_SHARED=OFF
        -DwxUSE_MEDIACTRL=ON
        -DwxUSE_DETECT_SM=OFF
        -DwxUSE_UNICODE=ON
        ${_wx_private_font}
        -DwxUSE_OPENGL=ON
        -DwxUSE_WEBREQUEST=ON
        -DwxUSE_WEBVIEW=ON
        ${_wx_edge}
        -DwxUSE_WEBVIEW_IE=OFF
        -DwxUSE_REGEX=builtin
        -DwxUSE_LIBXPM=builtin
        -DwxUSE_LIBSDL=OFF
        -DwxUSE_XTEST=OFF
        -DwxUSE_STC=OFF
        -DwxUSE_AUI=ON
        -DwxUSE_LIBPNG=sys
        -DwxUSE_ZLIB=sys
        -DwxUSE_LIBJPEG=sys
        -DwxUSE_LIBTIFF=sys
        -DwxUSE_NANOSVG=OFF
        -DwxUSE_EXPAT=sys
	#${_wx_link_extra}
)

if (MSVC)
    add_debug_dep(dep_wxWidgets)
endif ()

# For MSVC: Copy the actual setup.h from lib directory to include/wx/setup.h
# This is needed because platform.h includes "wx/setup.h"
if (MSVC)
    ExternalProject_Add_Step(dep_wxWidgets create_msvc_setup_h
        DEPENDEES install
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
            "${DESTDIR}/lib/vc_x64_lib/mswu/wx/setup.h"
            "${DESTDIR}/include/wx/setup.h"
    )
endif()
