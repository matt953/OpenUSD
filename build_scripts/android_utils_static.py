#
# Copyright 2024 Anthropic (based on apple_utils_static.py by Pixar)
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

# Utilities for managing Android build concerns.
#
# This follows the same pattern as apple_utils_static.py to provide
# Android-specific build configuration for build_usd_static.py

import sys
import os
import platform
from typing import Optional, List

# Android build targets (matching our build system convention)
TARGET_ANDROID_ARM64_V8A = "android-arm64-v8a"
TARGET_ANDROID_ARMEABI_V7A = "android-armeabi-v7a"
TARGET_ANDROID_X86_64 = "android-x86_64"
TARGET_ANDROID_X86 = "android-x86"

# All Android platforms
ANDROID_PLATFORMS = [
    TARGET_ANDROID_ARM64_V8A,
    TARGET_ANDROID_ARMEABI_V7A,
    TARGET_ANDROID_X86_64,
    TARGET_ANDROID_X86
]

def GetBuildTargets():
    """Return list of supported Android build targets"""
    return ANDROID_PLATFORMS

def GetBuildTargetDefault():
    """Default to arm64-v8a as it's the most common Android architecture"""
    return TARGET_ANDROID_ARM64_V8A

def Android():
    """Check if we're building for Android (detected by NDK environment)"""
    return (os.environ.get('ANDROID_NDK_HOME') is not None or
            os.environ.get('NDK_HOME') is not None or
            os.path.exists(os.path.expanduser('~/Library/Android/sdk/ndk')) or
            (os.environ.get('ANDROID_HOME') and
             os.path.exists(os.path.join(os.environ['ANDROID_HOME'], 'ndk'))))

def TargetNeedsStaticTBB(context):
    """Android builds always need static TBB"""
    return context.buildTarget in ANDROID_PLATFORMS

def GetAndroidABI(buildTarget):
    """Map build target to Android ABI"""
    mapping = {
        TARGET_ANDROID_ARM64_V8A: "arm64-v8a",
        TARGET_ANDROID_ARMEABI_V7A: "armeabi-v7a",
        TARGET_ANDROID_X86_64: "x86_64",
        TARGET_ANDROID_X86: "x86"
    }
    return mapping.get(buildTarget, "arm64-v8a")

def GetAndroidArch(buildTarget):
    """Map build target to Android architecture name"""
    mapping = {
        TARGET_ANDROID_ARM64_V8A: "aarch64",
        TARGET_ANDROID_ARMEABI_V7A: "arm",
        TARGET_ANDROID_X86_64: "x86_64",
        TARGET_ANDROID_X86: "x86"
    }
    return mapping.get(buildTarget, "aarch64")

def DetectNDK():
    """Detect Android NDK path from environment"""
    # Try ANDROID_NDK_HOME first
    if os.environ.get('ANDROID_NDK_HOME'):
        return os.environ['ANDROID_NDK_HOME']

    # Try NDK_HOME
    if os.environ.get('NDK_HOME'):
        return os.environ['NDK_HOME']

    # Try ANDROID_HOME/ndk
    if os.environ.get('ANDROID_HOME'):
        ndk_dir = os.path.join(os.environ['ANDROID_HOME'], 'ndk')
        if os.path.exists(ndk_dir):
            # Get latest NDK version
            versions = sorted([d for d in os.listdir(ndk_dir)
                             if os.path.isdir(os.path.join(ndk_dir, d))],
                            reverse=True)
            if versions:
                return os.path.join(ndk_dir, versions[0])

    # Try ~/Library/Android/sdk/ndk (macOS default)
    home_ndk = os.path.expanduser('~/Library/Android/sdk/ndk')
    if os.path.exists(home_ndk):
        versions = sorted([d for d in os.listdir(home_ndk)
                         if os.path.isdir(os.path.join(home_ndk, d))],
                        reverse=True)
        if versions:
            return os.path.join(home_ndk, versions[0])

    return None

def GetCMakeToolchainArgs(context):
    """Get CMake arguments for Android cross-compilation"""
    ndk_path = DetectNDK()
    if not ndk_path:
        raise RuntimeError("Android NDK not found. Please set ANDROID_NDK_HOME or NDK_HOME.")

    abi = GetAndroidABI(context.buildTarget)
    toolchain_file = os.path.join(ndk_path, "build/cmake/android.toolchain.cmake")

    if not os.path.exists(toolchain_file):
        raise RuntimeError(f"Android toolchain file not found at: {toolchain_file}")

    # Force Release build with optimizations and no debug symbols
    # The Android NDK toolchain defaults to Debug unless explicitly set
    # CRITICAL: The NDK toolchain adds -g by default! Must use -g0 to override
    return [
        f'-DCMAKE_TOOLCHAIN_FILE={toolchain_file}',
        f'-DANDROID_ABI={abi}',
        '-DANDROID_PLATFORM=android-28',
        '-DANDROID_STL=c++_static',
        '-DCMAKE_POSITION_INDEPENDENT_CODE=ON',
        # CRITICAL: -g0 disables debug symbols that NDK adds by default
        # Must come after optimization flags to override toolchain defaults
        '-DCMAKE_C_FLAGS="-O3 -DNDEBUG -g0"',
        '-DCMAKE_CXX_FLAGS="-O3 -DNDEBUG -std=c++17 -g0"',
        # Also set _RELEASE variants
        '-DCMAKE_C_FLAGS_RELEASE="-O3 -DNDEBUG -g0"',
        '-DCMAKE_CXX_FLAGS_RELEASE="-O3 -DNDEBUG -g0"',
        # Ensure we're using Release configuration
        '-DCMAKE_BUILD_TYPE=Release'
    ]

def GetCMakeGeneratorArgs(context):
    """Android builds use standard Unix Makefiles"""
    return ['Unix Makefiles', []]
