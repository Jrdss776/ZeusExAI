"""ZeusExAI customization layer.

This package keeps ZeusExAI-specific behavior isolated from the OpenJarvis core,
which makes upstream synchronization safer.
"""

from openjarvis.zeusex.identity import ZEUSEX_IDENTITY, ZeusExIdentity

__all__ = ["ZEUSEX_IDENTITY", "ZeusExIdentity"]
